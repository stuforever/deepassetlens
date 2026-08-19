"""P0 安全测试：技能目录穿越封堵。

验证 CompositeBackend + FilesystemBackend(virtual_mode=True) 能封堵所有目录穿越攻击，
且不影响正常技能文件读取。这是评审认定的最高优先级安全漏洞修复的验收测试。
"""
import pytest
from pathlib import Path
from deepagents.backends import StateBackend, FilesystemBackend, CompositeBackend


@pytest.fixture
def backend():
    """与 tupu_deepagent.py 中 create_tupu_agent 相同的 Backend 配置。"""
    skills_root = Path(__file__).resolve().parent.parent / "data" / "skills"
    fs_backend = FilesystemBackend(root_dir=str(skills_root), virtual_mode=True)
    return CompositeBackend(default=StateBackend(), routes={"/skills/": fs_backend})


def _try_read(backend, path):
    """返回 (是否可读, 内容或错误信息)。"""
    try:
        result = backend.read(path)
        content = getattr(result, "content", result)
        return bool(content), content
    except Exception as e:
        return False, str(e)[:80]


class TestSkillFileReadable:
    """正常技能文件必须能读（功能不能被安全规则破坏）。"""

    def test_read_skill_main(self, backend):
        ok, content = _try_read(backend, "/skills/scenarios/distribution-overload/SKILL.md")
        assert ok, f"正常技能文件读不到: {content}"
        text = str(content)
        assert "distribution-overload" in text or "重过载" in text

    def test_read_skill_subfile_template(self, backend):
        ok, content = _try_read(backend, "/skills/scenarios/distribution-overload/templates/step1_household_transformer.sql")
        assert ok, f"技能子文件读不到: {content}"

    def test_read_skill_subfile_reference(self, backend):
        ok, content = _try_read(backend, "/skills/scenarios/distribution-overload/reference/rules.md")
        assert ok, f"技能 reference 读不到: {content}"

    def test_read_locate_skill(self, backend):
        ok, content = _try_read(backend, "/skills/locate/SKILL.md")
        assert ok, f"locate 技能读不到: {content}"


class TestPathTraversalBlocked:
    """目录穿越攻击必须全部被封堵。"""

    @pytest.mark.parametrize("attack_path", [
        "/skills/../../requirements.txt",
        "/skills/../../../backend/.env",
        "/skills/../../../etc/passwd",
        "/skills/../locate/SKILL.md",
        "/etc/passwd",
        "/.env",
        "/requirements.txt",
    ])
    def test_traversal_blocked(self, backend, attack_path):
        ok, _ = _try_read(backend, attack_path)
        assert not ok, f"目录穿越未被封堵: {attack_path} 可读!"

    def test_windows_path_blocked(self, backend):
        """Windows 绝对路径也应被封堵。"""
        ok, _ = _try_read(backend, "C:\\Windows\\win.ini")
        assert not ok, "Windows 系统文件未被封堵"

    def test_skills_subdir_traversal_blocked(self, backend):
        """从技能子目录穿越也必须封堵。"""
        ok, _ = _try_read(backend, "/skills/scenarios/../../requirements.txt")
        assert not ok
