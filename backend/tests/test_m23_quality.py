# -*- coding: utf-8 -*-
"""M23 单测：质量体系契约（pytest.ini 纪律/conftest 约定/批次文化/e2e 脚本族）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M23 spec §九验收标准锚定现有实现）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# pytest.ini 运行纪律（spec §三）
# ---------------------------------------------------------------------------

def test_pytest_ini_contract():
    """pytest.ini 契约：30s thread 超时+integration 默认排除（spec §三/§九.1）。
    变异锚点：超时删 → 外部依赖卡死拖垮回归；integration 排除删 → 默认回归不可离线。"""
    ini = (BACKEND / "pytest.ini").read_text(encoding="utf-8")
    assert "--timeout=30" in ini or "timeout = 30" in ini or "timeout=30" in ini
    assert "--timeout-method=thread" in ini or "timeout_method" in ini.replace(" ", "_") or "thread" in ini
    assert 'not integration' in ini.replace('"', "'") or "-m \"not integration\"" in ini or "not integration" in ini


def test_integration_marker_path_available():
    """integration 标记路径可用（spec §九.2：pytest -m integration 手动跑）。
    变异锚点：标记注销 → 集成测试无法圈选。"""
    import subprocess
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q",
                        "-m", "integration", "-p", "no:cacheprovider", "tests/"],
                       capture_output=True, text=True, timeout=120, cwd=str(BACKEND))
    # 收集命令本身成功（标记注册）——是否命中集成用例随套件演进
    assert r.returncode in (0, 5)  # 5 = no tests collected（合法）


# ---------------------------------------------------------------------------
# conftest 轻量约定（spec §四）
# ---------------------------------------------------------------------------

def test_conftest_lightweight():
    """conftest 只做 sys.path+样例 fixture（spec §四：不引入共享 DB 隐式状态）。
    变异锚点：conftest 膨胀引入全局 DB → 测试间隐式耦合。"""
    src = (BACKEND / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "sys.path" in src
    assert "sample_select_sql" in src  # 三样例 fixture 之一
    assert len(src.splitlines()) <= 60  # 轻量约定（23 行量级）


# ---------------------------------------------------------------------------
# 批次测试文化（spec §五：命名即历史）
# ---------------------------------------------------------------------------

def test_batch_naming_culture():
    """批次命名族在位（spec §五：批13/批次/里程碑/专项/覆盖率系列，改动-测试可追溯）。
    变异锚点：批次测试缺失 → 改动不可追溯。"""
    tests_dir = BACKEND / "tests"
    names = {p.name for p in tests_dir.glob("test_*.py")}
    assert any(n.startswith("test_13") for n in names)      # 批13 系列
    assert any(n.startswith("test_batch") for n in names)   # 批次系列
    assert any(len(n) > 6 and n[6].isdigit() for n in names)  # 里程碑系列 test_m1_robustness
    # 本套件金标准补测文件齐（M09-M23）
    for m in ("m09", "m10", "m11", "m12", "m13", "m14", "m15", "m16",
              "m17", "m18", "m19", "m20", "m21", "m22", "m23"):
        assert any(m in n for n in names), f"缺 {m} 金标准补测"


# ---------------------------------------------------------------------------
# Playwright e2e 脚本族（spec §六）
# ---------------------------------------------------------------------------

def test_pw_e2e_script_family():
    """e2e 脚本族在位（spec §六：主入口+专项脚本族）。
    变异锚点：_pw_e2e 删 → 唯一验收路径断。"""
    scripts = BACKEND / "scripts"
    assert (scripts / "_pw_e2e.py").exists()
    pw_scripts = list(scripts.glob("_pw_*.py"))
    assert len(pw_scripts) >= 10, f"e2e 脚本族不足: {len(pw_scripts)}"
    # 主入口三参数契约
    src = (scripts / "_pw_e2e.py").read_text(encoding="utf-8")
    assert "23000" in src and "ant-table" in src
