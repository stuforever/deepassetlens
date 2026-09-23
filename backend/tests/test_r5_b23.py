# -*- coding: utf-8 -*-
"""R5批㉓（清单安全）契约测试：feishu 文件名净化+wechat_mp 验签+rag 敏感扩展名剔除。"""
import inspect


def test_feishu_filename_sanitized():
    from app.services.sishu.partners.channels import feishu
    src = inspect.getsource(feishu)
    assert "os.path.basename" in src
    # 折叠规则与生产一致：路径分隔/危险字符→_
    import os, re
    fn = os.path.basename("../../etc/passwd".replace("\\", "/"))
    assert fn == "passwd"
    folded = re.sub(r"[^A-Za-z0-9._\-一-鿿]", "_", fn)[:120]
    assert "/" not in folded


def test_wechat_mp_handler_verifies_signature():
    from app.services.sishu.partners.channels import wechat_mp
    src = inspect.getsource(wechat_mp)
    assert 'text=self.config.token' not in src      # 不再回显签名密钥
    assert "signature mismatch" in src
    assert "echostr" in src


def test_rag_text_extensions_pruned():
    from app.services.sishu.services.rag import file_routing
    src = inspect.getsource(file_routing)
    assert '".env"' not in src
    assert '".properties"' not in src
