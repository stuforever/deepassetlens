# -*- coding: utf-8 -*-
"""M10 单测：12 表契约/审批状态机/发布快照回滚/血缘防环（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M10 spec §九验收标准锚定现有实现）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from fastapi import HTTPException  # noqa: E402

from app.models.base import (  # noqa: E402
    Metric,
    MetricAuditLog,
    MetricFilterWhitelist,
    MetricUsageStat,
    MetricVersion,
)


# ---------------------------------------------------------------------------
# 任务 1：12 表模型契约（spec §三-§五）
# ---------------------------------------------------------------------------

def test_metric_master_columns():
    """主档双口径轨+状态默认 draft（spec §三）。
    变异锚点：口径轨列删 → 口径对账断；status 缺省漂移 → 新指标绕过草稿态。"""
    cols = {c.name for c in Metric.__table__.columns}
    assert {"business_caliber", "tech_caliber", "status", "version_current"} <= cols
    assert Metric.__table__.c.status.default.arg == "draft"


def test_whitelist_dual_level():
    """过滤白名单：字段级+算子级（spec §四/§八.3 问数安全边界）。
    变异锚点：op_whitelist_json 删 → 问数过滤算子无边界。"""
    cols = {c.name for c in MetricFilterWhitelist.__table__.columns}
    assert {"field_full_name", "op_whitelist_json"} <= cols


def test_usage_stat_fingerprint():
    """使用统计按查询指纹聚合（spec §五/§八.5）。
    变异锚点：query_fingerprint 删 → 同构查询逐条堆日志。"""
    assert "query_fingerprint" in {c.name for c in MetricUsageStat.__table__.columns}


def test_version_and_audit_models():
    """版本快照+审计前后态（spec §三：发布即快照/全操作审计）。
    变异锚点：snapshot_json/审计 before·after 删 → 回滚与回放断。"""
    vcols = {c.name for c in MetricVersion.__table__.columns}
    assert {"version", "status", "snapshot_json", "created_by"} <= vcols
    acols = {c.name for c in MetricAuditLog.__table__.columns}
    assert {"action", "before_json", "after_json", "operator"} <= acols


# ---------------------------------------------------------------------------
# 任务 3：审批状态机（spec §九.1）
# ---------------------------------------------------------------------------

@pytest.fixture()
def draft_metric():
    """造一条 draft 指标，测后清理。"""
    from app.core.database import SessionLocal
    import uuid
    db = SessionLocal()
    m = Metric(
        metric_code=f"m10t{uuid.uuid4().hex[:8]}",
        metric_name="M10测试指标",
        metric_type="atomic",
        status="draft",
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    yield m, db
    try:
        db.query(MetricAuditLog).filter(MetricAuditLog.metric_id == str(m.id)).delete()
        db.query(MetricVersion).filter(MetricVersion.metric_id == str(m.id)).delete()
        db.query(Metric).filter(Metric.id == m.id).delete()
        db.commit()
    finally:
        db.close()


def test_state_machine_full_chain(draft_metric):
    """draft→submit→approve→publish 全链（spec §九.1：产版本快照+审计+version_current 自增）。
    变异锚点：任一状态迁移删/乱序放行 → 审批流绕过。"""
    from app.api.metric_center import WorkflowActionRequest, approve_metric, publish_metric, submit_metric
    m, db = draft_metric
    mid = str(m.id)
    wf = WorkflowActionRequest(operator="m10tester")
    submit_metric(mid, wf, db=db)
    db.refresh(m)
    assert m.status == "reviewing"  # 实际状态字面量（spec 写 pending_review，以代码为准登记偏差）
    approve_metric(mid, wf, db=db)
    db.refresh(m)
    assert m.status == "approved"
    publish_metric(mid, wf, db=db)
    db.refresh(m)
    assert m.status == "published"
    # 发布产版本快照+审计+版本自增
    versions = db.query(MetricVersion).filter(MetricVersion.metric_id == mid).all()
    assert len(versions) >= 1 and versions[-1].snapshot_json
    audits = db.query(MetricAuditLog).filter(MetricAuditLog.metric_id == mid).all()
    assert len(audits) >= 3  # submit/approve/publish 各一条
    assert int(m.version_current or 0) >= 1


def test_illegal_transition_rejected(draft_metric):
    """draft 直跳 publish → 400（spec 状态前置校验：非法迁移 400）。
    变异锚点：前置校验删 → 草稿直发绕过审批。"""
    from app.api.metric_center import WorkflowActionRequest, publish_metric
    m, db = draft_metric
    with pytest.raises(HTTPException) as ei:
        publish_metric(str(m.id), WorkflowActionRequest(operator="m10tester"), db=db)
    assert ei.value.status_code == 400


def test_reject_returns_draft(draft_metric):
    """reject → 回 draft 附原因（spec §三状态机）。
    变异锚点：reject 分支删 → 拒绝路径死锁。"""
    from app.api.metric_center import WorkflowActionRequest, reject_metric, submit_metric
    m, db = draft_metric
    mid = str(m.id)
    wf = WorkflowActionRequest(operator="m10tester")
    submit_metric(mid, wf, db=db)
    reject_metric(mid, WorkflowActionRequest(operator="m10tester", reason="口径不符"), db=db)
    db.refresh(m)
    assert m.status == "draft"
