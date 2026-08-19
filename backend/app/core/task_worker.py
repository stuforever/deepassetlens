"""
异步任务工作线程
后台消费 TaskQueue 中的 pending 任务
"""

import threading
import time
import uuid
import traceback
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.execution_engine import ExecutionEngineV2
from app.models.scheduler import TaskQueue
from app.services.skill_manager import SkillService

logger = logging.getLogger(__name__)


class TaskWorker(threading.Thread):
    """
    任务消费工作线程
    单线程顺序消费，按优先级排序
    """

    def __init__(self, poll_interval: float = 1.0, max_workers: int = 1):
        super().__init__(name="TaskWorker", daemon=True)
        self.poll_interval = poll_interval
        self.max_workers = max_workers
        self._stop_event = threading.Event()
        self._running = False
        self._concurrent_count = 0
        self._lock = threading.Lock()
        # 低优先级周期任务：[(interval_seconds, fn, last_run)]
        self.periodic_hooks: list = []
        self._hooks_lock = threading.Lock()

    def register_periodic(self, interval_seconds: float, fn) -> None:
        """注册低优先级周期任务（如查询日志 30 天清理），在轮询循环里按间隔执行。"""
        with self._hooks_lock:
            self.periodic_hooks.append([float(interval_seconds), fn, 0.0])

    def stop(self):
        """优雅停止"""
        self._stop_event.set()
        self._running = False

    def is_stopped(self) -> bool:
        return self._stop_event.is_set()

    def run(self):
        """主循环"""
        self._running = True
        while not self._stop_event.is_set():
            try:
                self._process_next_task()
                self._run_periodic_hooks()
            except Exception as e:
                logger.error(f"[TaskWorker] 异常: {e}")
                traceback.print_exc()
            time.sleep(self.poll_interval)

    def _run_periodic_hooks(self):
        """按间隔执行已注册的周期任务（异常隔离，不影响队列消费）。"""
        now = time.time()
        with self._hooks_lock:
            hooks = list(self.periodic_hooks)
        for h in hooks:
            interval, fn, last = h
            if now - last >= interval:
                try:
                    fn()
                except Exception as e:
                    logger.error(f"[TaskWorker] 周期任务异常: {e}")
                    traceback.print_exc()
                h[2] = now

    def _process_next_task(self):
        """处理下一个任务"""
        db = SessionLocal()
        try:
            # 获取下一个 pending 任务（按优先级排序）
            task = db.query(TaskQueue).filter(
                TaskQueue.status == "pending"
            ).order_by(
                TaskQueue.priority.asc(),
                TaskQueue.created_at.asc()
            ).with_for_update().first()

            if not task:
                return

            # 标记为 running
            task.status = "running"
            task.started_at = datetime.utcnow()
            db.commit()

            # 在独立 session 中执行（避免长事务）
            db.expunge(task)
        finally:
            db.close()

        # 执行任务
        self._execute_task(task)

    def _execute_task(self, task: TaskQueue):
        """执行单个任务"""
        db = SessionLocal()
        try:
            # 重新获取 task 对象
            task = db.query(TaskQueue).filter(
                TaskQueue.task_code == task.task_code
            ).first()
            if not task or task.status != "running":
                return

            # 获取技能
            skill = SkillService.get_skill(db, task.task_ref_id)
            if not skill:
                task.status = "failed"
                task.error_message = "技能不存在"
                task.completed_at = datetime.utcnow()
                db.commit()
                return

            # 执行
            engine = ExecutionEngineV2(db)
            result = engine.execute(
                skill_id=task.task_ref_id,
                input_payload=task.input_payload or {},
                created_via="schedule"
            )

            if result.get("success"):
                task.status = "completed"
                task.output_payload = result.get("output")
            else:
                task.status = "failed"
                task.error_message = result.get("error")
                # 检查是否需要重试
                if task.retry_count < task.max_retries:
                    task.status = "pending"
                    task.retry_count += 1
                    task.error_message = f"{result.get('error')} (将在重试 {task.retry_count}/{task.max_retries})"

            task.completed_at = datetime.utcnow()
            db.commit()

        except Exception as e:
            db.rollback()
            try:
                task = db.query(TaskQueue).filter(
                    TaskQueue.task_code == task.task_code
                ).first()
                if task:
                    task.status = "failed"
                    task.error_message = f"{str(e)}\n{traceback.format_exc()}"
                    task.completed_at = datetime.utcnow()
                    db.commit()
            except:
                pass
        finally:
            db.close()


class TaskWorkerManager:
    """
    工作线程管理器
    支持启动、停止、状态监控
    """

    def __init__(self):
        self.worker: Optional[TaskWorker] = None

    def start(self, poll_interval: float = 1.0):
        """启动工作线程"""
        if self.worker and self.worker.is_alive():
            return
        self.worker = TaskWorker(poll_interval=poll_interval)
        self.worker.start()
        logger.info(f"[TaskWorkerManager] 工作线程已启动 (轮询间隔: {poll_interval}s)")

    def register_periodic(self, interval_seconds: float, fn) -> None:
        """注册低优先级周期任务（转发给工作线程；未启动则记录到 worker 实例待启动后生效）。"""
        self.start()
        self.worker.register_periodic(interval_seconds, fn)

    def stop(self):
        """停止工作线程"""
        if self.worker:
            self.worker.stop()
            self.worker.join(timeout=5.0)
            logger.info("[TaskWorkerManager] 工作线程已停止")

    def is_running(self) -> bool:
        return self.worker is not None and self.worker.is_alive()

    def get_status(self) -> dict:
        return {
            "running": self.is_running(),
            "thread_name": self.worker.name if self.worker else None,
            "daemon": self.worker.daemon if self.worker else None,
        }


# 全局管理器实例
task_worker_manager = TaskWorkerManager()
