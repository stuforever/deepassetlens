# -*- coding: utf-8 -*-
"""⑤批1（⑤a 验收）：DAO 三态+重放重建断言（流水=恢复锚）。
真 PG（pg_tupu）+固定 user_id 残留清理 fixture——幂等复跑。"""
import pytest

from app.services.learning import learning_dao as dao
from app.services.learning.pg import _engine
from app.services.learning.service import review_card
from sqlalchemy import text

_UID = "tutor-dao-test"


@pytest.fixture()
def _clean():
    with _engine.begin() as c:
        c.execute(text("DELETE FROM sishu_review_cards WHERE user_id=:u"), {"u": _UID})
    yield
    with _engine.begin() as c:
        c.execute(text("DELETE FROM sishu_review_cards WHERE user_id=:u"), {"u": _UID})


def test_dao_three_states(_clean):
    """三态：读 miss→None；写 upsert 建；更新幂等（同键覆写）。"""
    assert dao.get_card(_UID, "knowledge_point", "kp-dao") is None          # miss
    card_id = dao.upsert_card(_UID, "knowledge_point", "kp-dao",
                              {"stability": 3.1, "difficulty": 5.2, "reps": 1,
                               "lapses": 0, "due": 9999999999.0, "last_review": 1000000.0})
    assert card_id == "knowledge_point:kp-dao:" + _UID
    got = dao.get_card(_UID, "knowledge_point", "kp-dao")
    assert got["stability"] == 3.1 and got["reps"] == 1                      # 写入可读
    dao.upsert_card(_UID, "knowledge_point", "kp-dao",
                    {"stability": 4.4, "difficulty": 5.0, "reps": 2,
                     "lapses": 0, "due": 9999999999.0, "last_review": 1000001.0})
    got2 = dao.get_card(_UID, "knowledge_point", "kp-dao")
    assert got2["stability"] == 4.4 and got2["reps"] == 2                    # 更新幂等


def test_rebuild_from_records(_clean):
    """重放重建断言（⑤a 验收+行为契约「FSRS 状态损坏→review_cards 行级重建」）：
    真实评分流水→**损坏卡状态**（不物理删行——records.card_id 是 CASCADE 外键，
    删卡带走流水与恢复锚矛盾，故损坏不删）→rebuild→与损坏前一致→覆写回。"""
    out1 = review_card(_UID, "mother_question", "mq-dao", 3)
    out2 = review_card(_UID, "mother_question", "mq-dao", 1)
    out3 = review_card(_UID, "mother_question", "mq-dao", 4)
    live = dao.get_card(_UID, "mother_question", "mq-dao")
    assert live["reps"] == 3 and live["lapses"] == 1
    # 模拟 FSRS 状态损坏（行为契约：行级重建的触发场景）
    with _engine.begin() as c:
        c.execute(text("UPDATE sishu_review_cards SET stability=-1, reps=0, lapses=99 "
                       "WHERE card_id=:c"), {"c": out1["card_id"]})
    rebuilt = dao.rebuild_card_from_records(_UID, "mother_question", "mq-dao")
    # 重放终态与损坏前 live 状态一致（浮点 1e-6 容差）
    assert rebuilt["reps"] == 3 and rebuilt["lapses"] == 1
    assert abs(rebuilt["stability"] - live["stability"]) < 1e-6
    assert abs(rebuilt["difficulty"] - live["difficulty"]) < 1e-6
    # 覆写回（行级重建落库）
    rebuilt["due"] = live["due"]
    rebuilt["last_review"] = live["last_review"]
    dao.upsert_card(_UID, "mother_question", "mq-dao", rebuilt)
    restored = dao.get_card(_UID, "mother_question", "mq-dao")
    assert abs(restored["stability"] - live["stability"]) < 1e-6
