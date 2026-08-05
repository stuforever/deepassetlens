"""
技能包文件系统存储层
五件套目录结构：
📁 {SKILL_STORAGE_ROOT}/{skill_code}/
├── 📄 SKILL.md              # 技能身份证（元数据+说明+触发规则）
├── 📁 scripts/              # 代码执行抽屉
├── 📁 references/           # 业务资料库
├── 📁 assets/               # 配置附件包
└── 📄 requirements.txt      # 运行依赖清单

设计原则：
1. 所有技能内容（代码、提示词、配置）100% 存放在文件系统
2. 数据库仅存储元数据（skill_id、skill_code、status、version、tags）
3. 技能包可整体 ZIP 压缩，跨环境导入即用
"""

import os
import shutil
import zipfile
import yaml
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# 存储根目录（可从环境变量配置；默认基于本文件位置定位 backend/data/skills，避免工作目录依赖）
SKILL_STORAGE_ROOT = Path(os.environ.get("SKILL_STORAGE_ROOT", str(Path(__file__).resolve().parent.parent.parent / "data" / "skills")))
SKILL_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

# 五件套目录名
FIVE_PIECE_DIRS = ["scripts", "references", "assets"]
FIVE_PIECE_FILES = ["SKILL.md", "requirements.txt"]


class SkillStorage:
    """
    技能包文件系统存储管理器
    所有内容操作都通过此类完成，上层不得直接操作文件系统
    """

    def __init__(self, root: Path = None):
        self.root = root or SKILL_STORAGE_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def _skill_path(self, skill_code: str) -> Path:
        """获取技能包目录路径（强制小写）"""
        return self.root / skill_code.lower()

    def create_skeleton(self, skill_code: str, metadata: Dict[str, Any] = None) -> Path:
        """
        创建五件套标准目录骨架
        返回技能包根目录路径
        """
        sp = self._skill_path(skill_code)
        if sp.exists():
            raise FileExistsError(f"技能包已存在: {sp}")

        sp.mkdir(parents=True)

        # 创建目录
        for d in FIVE_PIECE_DIRS:
            (sp / d).mkdir(exist_ok=True)

        # 创建 SKILL.md
        skill_md = self._generate_skill_md(metadata or {})
        (sp / "SKILL.md").write_text(skill_md, encoding="utf-8")

        # 创建 requirements.txt
        (sp / "requirements.txt").write_text("# 运行依赖清单\n", encoding="utf-8")

        return sp

    def _generate_skill_md(self, metadata: Dict[str, Any]) -> str:
        """生成 SKILL.md 内容"""
        name = metadata.get("name", "未命名技能")
        desc = metadata.get("description", "")
        skill_type = metadata.get("skill_type", "python")
        trigger = metadata.get("trigger_conditions", [])

        # claude 类型：YAML frontmatter 格式（Claude SKILL.md 标准）
        if skill_type == "claude":
            md = f"""---
name: {skill_code if (skill_code := metadata.get('skill_code', '')) else name.lower().replace(' ', '-')}
description: {desc}
---

# {name}

## 何时使用
{chr(10).join(f"- {t}" for t in trigger) if trigger else "- 默认触发"}

## 执行步骤
（在此编写技能指令，引导 LLM 调用 kg_api 工具完成任务）
"""
            return md

        md = f"""# {name}

## 基本信息
- **名称**: {name}
- **类型**: {skill_type}
- **描述**: {desc}
- **创建时间**: {datetime.now().isoformat()}

## 触发规则
{chr(10).join(f"- {t}" for t in trigger) if trigger else "- 默认触发"}

## 输入参数
详见 assets/input_schema.json

## 输出参数
详见 assets/output_schema.json

## 执行入口
- **脚本**: scripts/main.{self._ext_for_type(skill_type)}
- **函数**: execute(inputs: dict) -> dict

## 依赖
详见 requirements.txt
"""
        return md

    def _ext_for_type(self, skill_type: str) -> str:
        return {"python": "py", "sql": "sql", "http": "yaml", "natural": "txt", "mixed": "yaml", "claude": "md"}.get(skill_type, "py")

    def read_file(self, skill_code: str, rel_path: str) -> str:
        """读取技能包内文件"""
        sp = self._skill_path(skill_code)
        target = sp / rel_path
        # 安全检查：禁止越权访问
        self._ensure_within_skill(sp, target)
        if not target.exists():
            raise FileNotFoundError(f"文件不存在: {rel_path}")
        return target.read_text(encoding="utf-8")

    def write_file(self, skill_code: str, rel_path: str, content: str) -> None:
        """写入技能包内文件（自动创建父目录）"""
        sp = self._skill_path(skill_code)
        target = sp / rel_path
        self._ensure_within_skill(sp, target)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            try:
                existing = target.read_text(encoding="utf-8")
                if existing == content:
                    return
            except Exception:
                pass
        target.write_text(content, encoding="utf-8")

    def delete_file(self, skill_code: str, rel_path: str) -> None:
        """删除技能包内文件"""
        sp = self._skill_path(skill_code)
        target = sp / rel_path
        self._ensure_within_skill(sp, target)
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

    def list_files(self, skill_code: str) -> List[Dict[str, Any]]:
        """列出技能包内所有文件树"""
        sp = self._skill_path(skill_code)
        if not sp.exists():
            return []

        files = []
        for item in sorted(sp.rglob("*")):
            rel = item.relative_to(sp).as_posix()
            files.append({
                "path": rel,
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else 0,
                "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
            })
        return files

    def get_entrypoint_script(self, skill_code: str, skill_type: str) -> str:
        """获取入口脚本内容"""
        ext = self._ext_for_type(skill_type)
        try:
            return self.read_file(skill_code, f"scripts/main.{ext}")
        except FileNotFoundError:
            # 回退：查找 scripts 目录下第一个匹配文件
            sp = self._skill_path(skill_code)
            scripts_dir = sp / "scripts"
            if scripts_dir.exists():
                for f in sorted(scripts_dir.iterdir()):
                    if f.suffix == f".{ext}":
                        return f.read_text(encoding="utf-8")
            raise FileNotFoundError(f"找不到入口脚本: scripts/main.{ext}")

    def get_requirements(self, skill_code: str) -> List[str]:
        """获取依赖清单"""
        try:
            content = self.read_file(skill_code, "requirements.txt")
            return [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
        except FileNotFoundError:
            return []

    def get_schema(self, skill_code: str, schema_type: str) -> Optional[Dict[str, Any]]:
        """获取 input_schema 或 output_schema"""
        try:
            content = self.read_file(skill_code, f"assets/{schema_type}_schema.json")
            return json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def set_schema(self, skill_code: str, schema_type: str, schema: Dict[str, Any]) -> None:
        """设置 input_schema 或 output_schema"""
        self.write_file(skill_code, f"assets/{schema_type}_schema.json", json.dumps(schema, indent=2, ensure_ascii=False))

    def read_skill_md(self, skill_code: str) -> str:
        """读取 SKILL.md"""
        return self.read_file(skill_code, "SKILL.md")

    def parse_skill_md(self, skill_code: str) -> Dict[str, Any]:
        """解析 SKILL.md 为元数据字典（兼容中文格式和 YAML frontmatter 格式）"""
        md = self.read_skill_md(skill_code)
        metadata = {"raw": md}

        # YAML frontmatter 格式（Claude SKILL.md 标准）：以 --- 开头
        if md.strip().startswith("---"):
            frontmatter_match = re.match(r'^---\n(.*?)\n---', md, re.DOTALL)
            if frontmatter_match:
                try:
                    fm = yaml.safe_load(frontmatter_match.group(1))
                    if isinstance(fm, dict):
                        if fm.get("name"):
                            metadata["name"] = fm["name"]
                        if fm.get("description"):
                            metadata["description"] = fm["description"]
                        metadata["skill_type"] = "claude"
                except Exception:
                    pass
                return metadata

        # 中文格式（V2 原有格式）
        name_match = re.search(r'^#\s+(.+)$', md, re.MULTILINE)
        if name_match:
            metadata["name"] = name_match.group(1).strip()

        type_match = re.search(r'\*\*类型\*\*:\s*(\w+)', md)
        if type_match:
            metadata["skill_type"] = type_match.group(1).strip()

        desc_match = re.search(r'\*\*描述\*\*:\s*(.+)', md)
        if desc_match:
            metadata["description"] = desc_match.group(1).strip()

        # 提取触发规则
        trigger_section = re.search(r'## 触发规则\n(.+?)(?=##|\Z)', md, re.DOTALL)
        if trigger_section:
            triggers = re.findall(r'^-\s*(.+)$', trigger_section.group(1), re.MULTILINE)
            metadata["trigger_conditions"] = [t.strip() for t in triggers]

        return metadata

    def update_skill_md(self, skill_code: str, updates: Dict[str, Any]) -> None:
        """更新 SKILL.md 的指定字段"""
        md = self.read_skill_md(skill_code)

        if "name" in updates:
            md = re.sub(r'^#\s+.+$', f'# {updates["name"]}', md, flags=re.MULTILINE, count=1)
        if "description" in updates:
            md = re.sub(r'(\*\*描述\*\*:\s*).+', r'\1' + updates["description"], md)
        if "skill_type" in updates:
            md = re.sub(r'(\*\*类型\*\*:\s*)\w+', r'\1' + updates["skill_type"], md)

        self.write_file(skill_code, "SKILL.md", md)

    def export_zip(self, skill_code: str, dest_path: Optional[Path] = None) -> Path:
        """
        导出技能包为 ZIP
        返回 ZIP 文件路径
        """
        sp = self._skill_path(skill_code)
        if not sp.exists():
            raise FileNotFoundError(f"技能包不存在: {skill_code}")

        zip_name = f"{skill_code.lower()}_v{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        dest = dest_path or (self.root / "exports" / zip_name)
        dest.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as zf:
            for item in sp.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(sp).as_posix()
                    zf.write(item, rel)

        return dest

    def import_zip(self, zip_path: Path, new_skill_code: Optional[str] = None) -> str:
        """
        从 ZIP 导入技能包
        返回导入后的 skill_code
        包含安全校验：拦截恶意路径
        """
        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP 文件不存在: {zip_path}")

        # 安全校验
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                # 拦截恶意路径
                if ".." in name or name.startswith("/") or ":" in name:
                    raise ValueError(f"ZIP 包含恶意路径，已拦截: {name}")
                # 校验文件名合法性
                if not re.match(r'^[\w\-/\.]+$', name):
                    raise ValueError(f"ZIP 包含非法文件名: {name}")

            # 必须有五件套核心文件
            required = {"SKILL.md"}
            has_required = any(req in zf.namelist() for req in required)
            if not has_required:
                raise ValueError("ZIP 缺少 SKILL.md，不符合技能包标准")

        # 解压
        if new_skill_code:
            target = self._skill_path(new_skill_code)
        else:
            # 从 ZIP 中读取 SKILL.md 提取 skill_code，或生成默认
            target = None

        if target is None:
            # 使用时间戳生成临时 code
            import uuid as uuid_mod
            new_skill_code = f"imported_{uuid_mod.uuid4().hex[:8]}"
            target = self._skill_path(new_skill_code)

        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(target)

        return new_skill_code.lower()

    def delete_skill_package(self, skill_code: str) -> None:
        """删除整个技能包目录"""
        sp = self._skill_path(skill_code)
        if sp.exists():
            shutil.rmtree(sp)

    def clone(self, src_code: str, dest_code: str) -> Path:
        """克隆技能包"""
        src = self._skill_path(src_code)
        dest = self._skill_path(dest_code)
        if not src.exists():
            raise FileNotFoundError(f"源技能包不存在: {src_code}")
        if dest.exists():
            raise FileExistsError(f"目标技能包已存在: {dest_code}")
        shutil.copytree(src, dest)
        # 更新 SKILL.md 中的名称
        self.update_skill_md(dest_code, {"name": f"{self.parse_skill_md(dest_code).get('name', dest_code)} (副本)"})
        return dest

    def _ensure_within_skill(self, skill_root: Path, target: Path) -> None:
        """安全检查：确保目标路径在技能包目录内"""
        try:
            target.resolve().relative_to(skill_root.resolve())
        except ValueError:
            raise PermissionError(f"越权访问: {target} 不在技能包 {skill_root} 内")


# 全局单例
skill_storage = SkillStorage()


def get_skill_storage() -> SkillStorage:
    return skill_storage
