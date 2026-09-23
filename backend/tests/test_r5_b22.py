# -*- coding: utf-8 -*-
"""R5批㉒（清单安全）契约测试：kb_name 净化+partner_ 前缀保留。"""
import inspect

import pytest


def test_progress_tracker_kb_name_sanitized():
    from app.services.sishu.knowledge.progress_tracker import ProgressTracker
    for bad in ("../evil", "a/b", "", None, "x" * 200):
        with pytest.raises(ValueError):
            ProgressTracker(bad, __import__("pathlib").Path("/tmp/x"))
    t = ProgressTracker("kb-1", __import__("pathlib").Path("/tmp/x"))
    assert t.kb_dir.name == "kb-1"


def test_save_user_rejects_partner_prefix():
    from app.services.sishu.compat import identity
    src = inspect.getsource(identity.save_user)
    assert 'username.startswith("partner_")' in src
    with pytest.raises(ValueError):
        identity.save_user("partner_evil", "hash")
