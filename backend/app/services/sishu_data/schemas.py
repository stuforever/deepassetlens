# -*- coding: utf-8 -*-
"""v4批2 2.1：sishu_ 表族全族 DDL（spec §四蓝图；与 data/init/pg_schema.sql 单源同文）。
ensure() 幂等（CREATE TABLE IF NOT EXISTS / ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS）。
既有 learning_* 四表由 scripts/sishu_migrate/rename_learning_tables.py 先行改名（2.2）——
本文件四表 DDL 仅服务全新部署路径（改名后 CREATE IF NOT EXISTS 零输出=幂等）。"""

# 学习族（四表=learning_* 改名同构；recitation/practice_gen 列面批6 迁移时 ADD COLUMN 扩）
_LEARNING = [
    """CREATE TABLE IF NOT EXISTS sishu_review_cards (
      card_id VARCHAR(64) PRIMARY KEY,
      kind VARCHAR(20) NOT NULL,
      item_id VARCHAR(128) NOT NULL,
      user_id VARCHAR(128) NOT NULL,
      stability DOUBLE PRECISION NOT NULL DEFAULT 0,
      difficulty DOUBLE PRECISION NOT NULL DEFAULT 0,
      reps INT NOT NULL DEFAULT 0,
      lapses INT NOT NULL DEFAULT 0,
      due TIMESTAMPTZ NOT NULL DEFAULT now(),
      last_review TIMESTAMPTZ,
      UNIQUE (kind, item_id, user_id))""",
    """CREATE TABLE IF NOT EXISTS sishu_review_records (
      id BIGSERIAL PRIMARY KEY,
      card_id VARCHAR(64) NOT NULL REFERENCES sishu_review_cards(card_id) ON DELETE CASCADE,
      user_id VARCHAR(128) NOT NULL,
      rating SMALLINT NOT NULL,
      scheduled_interval DOUBLE PRECISION NOT NULL,
      reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_wrong_questions (
      wq_id VARCHAR(64) PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL,
      mother_question_id VARCHAR(64) NOT NULL,
      variant_text TEXT NOT NULL,
      error_context TEXT,
      status VARCHAR(20) NOT NULL DEFAULT 'open',
      wrong_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      resolved_at TIMESTAMPTZ)""",
    # ⑤补补-5（M00 +4 列）随单源收编：question/my_answer/error_type/source（幂等 ALTER）
    "ALTER TABLE sishu_wrong_questions ADD COLUMN IF NOT EXISTS question JSON",
    "ALTER TABLE sishu_wrong_questions ADD COLUMN IF NOT EXISTS my_answer TEXT",
    "ALTER TABLE sishu_wrong_questions ADD COLUMN IF NOT EXISTS error_type VARCHAR(32)",
    "ALTER TABLE sishu_wrong_questions ADD COLUMN IF NOT EXISTS source VARCHAR(16)",
    """CREATE TABLE IF NOT EXISTS sishu_mother_questions (
      mq_id VARCHAR(64) PRIMARY KEY,
      title TEXT NOT NULL,
      archetype_text TEXT NOT NULL,
      knowledge_point_id VARCHAR(128) NOT NULL,
      variant_count INT NOT NULL DEFAULT 0,
      enabled BOOLEAN NOT NULL DEFAULT TRUE)""",
    """CREATE TABLE IF NOT EXISTS sishu_recitation (
      id BIGSERIAL PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_practice_gen (
      id BIGSERIAL PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL,
      kind VARCHAR(32),
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    "ALTER TABLE sishu_practice_gen ADD COLUMN IF NOT EXISTS chapter_id VARCHAR(128) DEFAULT ''",
    "CREATE INDEX IF NOT EXISTS idx_sishu_practice_gen_ch ON sishu_practice_gen (user_id, chapter_id)",
    """CREATE TABLE IF NOT EXISTS sishu_learner_profile (
      user_id VARCHAR(128) PRIMARY KEY,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_self_learning_progress (
      id BIGSERIAL PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL,
      chapter_id VARCHAR(128) NOT NULL,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (user_id, chapter_id))""",
]

# 母题域（v4批6：vendor mother_questions JSON store 184 题迁移——与 learning_* 窄表
# sishu_mother_questions（批2 改名，错题联动）异实体同名，族名 sishu_mq_* 避撞（E-60））。
# user_id（批6 6.B）：?u= data-class 隔离单轨列——vendor 经 user_context 切目录，PG 换列
# （local-admin=桌缺省；h5_<slug>=H5 用户）；存量行经 DEFAULT 回填（迁移源=admin 仓）。
_MOTHER = [
    """CREATE TABLE IF NOT EXISTS sishu_mq_docs (
      mq_id VARCHAR(64) PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL DEFAULT 'local-admin',
      doc JSONB NOT NULL,                      -- vendor MotherQuestion 全字段（形状冻结 index.json）
      status VARCHAR(20) NOT NULL DEFAULT 'active',
      subject VARCHAR(32),
      grade VARCHAR(32),
      knowledge_point_id VARCHAR(128),
      mastery_status VARCHAR(32),
      simhash VARCHAR(64),
      update_time BIGINT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_question_variants (
      vq_id VARCHAR(64) PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL DEFAULT 'local-admin',
      mother_id VARCHAR(64) NOT NULL,
      doc JSONB NOT NULL,
      status VARCHAR(20) NOT NULL DEFAULT 'active',
      update_time BIGINT)""",
    "CREATE INDEX IF NOT EXISTS idx_sishu_mq_status ON sishu_mq_docs (status)",
    "CREATE INDEX IF NOT EXISTS idx_sishu_mq_kp ON sishu_mq_docs (knowledge_point_id)",
    # 既有部署升级（CREATE 内新列对老表幂等补齐——先于依赖 user_id 的索引执行）
    "ALTER TABLE sishu_mq_docs ADD COLUMN IF NOT EXISTS user_id VARCHAR(128) NOT NULL DEFAULT 'local-admin'",
    "ALTER TABLE sishu_question_variants ADD COLUMN IF NOT EXISTS user_id VARCHAR(128) NOT NULL DEFAULT 'local-admin'",
    # 复习状态/标签/attempt/review_log（vendor rs/tags/att/review_log JSON 文件迁移）
    """CREATE TABLE IF NOT EXISTS sishu_mq_review_state (
      mq_id VARCHAR(64) PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL DEFAULT 'local-admin',
      doc JSONB NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS sishu_mq_tags (
      name VARCHAR(64) PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL DEFAULT 'local-admin',
      color VARCHAR(16),
      doc JSONB NOT NULL DEFAULT '{}'::jsonb)""",
    """CREATE TABLE IF NOT EXISTS sishu_mq_attempts (
      attempt_id VARCHAR(64) PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL DEFAULT 'local-admin',
      mother_id VARCHAR(64),
      doc JSONB NOT NULL)""",
    "ALTER TABLE sishu_mq_review_state ADD COLUMN IF NOT EXISTS user_id VARCHAR(128) NOT NULL DEFAULT 'local-admin'",
    "ALTER TABLE sishu_mq_tags ADD COLUMN IF NOT EXISTS user_id VARCHAR(128) NOT NULL DEFAULT 'local-admin'",
    "ALTER TABLE sishu_mq_attempts ADD COLUMN IF NOT EXISTS user_id VARCHAR(128) NOT NULL DEFAULT 'local-admin'",
    "CREATE INDEX IF NOT EXISTS idx_sishu_mq_user ON sishu_mq_docs (user_id)",
    "CREATE INDEX IF NOT EXISTS idx_sishu_vq_mother ON sishu_question_variants (mother_id)",
    "CREATE INDEX IF NOT EXISTS idx_sishu_vq_user ON sishu_question_variants (user_id)",
    """CREATE TABLE IF NOT EXISTS sishu_mq_review_log (
      seq BIGSERIAL PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL DEFAULT 'local-admin',
      doc JSONB NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_sishu_mq_review_log_user ON sishu_mq_review_log (user_id)",
    "CREATE INDEX IF NOT EXISTS idx_sishu_mq_attempts_user ON sishu_mq_attempts (user_id)",
    "CREATE INDEX IF NOT EXISTS idx_sishu_mq_review_state_user ON sishu_mq_review_state (user_id)",
]

# 笔记族（chat_history.db notebook 三表批6 迁移；typed 列面=批6 6.C 扩——
# payload 全文档+过滤热列；epoch 列保留 sqlite REAL 语义（排序/快照））
_NOTEBOOK = [
    """CREATE TABLE IF NOT EXISTS sishu_notebook_entries (
      id BIGSERIAL PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL,
      title TEXT,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    "ALTER TABLE sishu_notebook_entries ADD COLUMN IF NOT EXISTS session_id VARCHAR(128) DEFAULT ''",
    "ALTER TABLE sishu_notebook_entries ADD COLUMN IF NOT EXISTS session_title TEXT DEFAULT ''",
    "ALTER TABLE sishu_notebook_entries ADD COLUMN IF NOT EXISTS turn_id VARCHAR(128) DEFAULT ''",
    "ALTER TABLE sishu_notebook_entries ADD COLUMN IF NOT EXISTS question_id VARCHAR(128) DEFAULT ''",
    "ALTER TABLE sishu_notebook_entries ADD COLUMN IF NOT EXISTS is_correct BOOLEAN DEFAULT FALSE",
    "ALTER TABLE sishu_notebook_entries ADD COLUMN IF NOT EXISTS bookmarked BOOLEAN DEFAULT FALSE",
    "ALTER TABLE sishu_notebook_entries ADD COLUMN IF NOT EXISTS created_at_epoch DOUBLE PRECISION DEFAULT 0",
    "ALTER TABLE sishu_notebook_entries ADD COLUMN IF NOT EXISTS updated_at_epoch DOUBLE PRECISION DEFAULT 0",
    "CREATE INDEX IF NOT EXISTS idx_sishu_nb_entries_session ON sishu_notebook_entries (user_id, session_id, created_at_epoch DESC)",
    "CREATE INDEX IF NOT EXISTS idx_sishu_nb_entries_bookmarked ON sishu_notebook_entries (user_id, bookmarked, created_at_epoch DESC)",
    """CREATE TABLE IF NOT EXISTS sishu_notebook_categories (
      id BIGSERIAL PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL,
      name TEXT,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb)""",
    "ALTER TABLE sishu_notebook_categories ADD COLUMN IF NOT EXISTS created_at_epoch DOUBLE PRECISION DEFAULT 0",
    """CREATE TABLE IF NOT EXISTS sishu_notebook_entry_categories (
      entry_id BIGINT NOT NULL,
      category_id BIGINT NOT NULL,
      PRIMARY KEY (entry_id, category_id))""",
]

# 书族（book_bk_* 目录七件套 1:1——批5 产物/批7 迁移消费）
_BOOK = [
    """CREATE TABLE IF NOT EXISTS sishu_books (
      book_id VARCHAR(64) PRIMARY KEY,
      title TEXT NOT NULL,
      description TEXT,
      language VARCHAR(16) DEFAULT 'zh',
      status VARCHAR(32),
      manifest JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_book_spines (
      book_id VARCHAR(64) PRIMARY KEY REFERENCES sishu_books(book_id) ON DELETE CASCADE,
      spine JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_book_pages (
      page_id VARCHAR(64) PRIMARY KEY,
      book_id VARCHAR(64) NOT NULL REFERENCES sishu_books(book_id) ON DELETE CASCADE,
      page_no INT NOT NULL DEFAULT 0,
      title TEXT,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_book_blocks (
      block_id VARCHAR(64) PRIMARY KEY,
      page_id VARCHAR(64) NOT NULL REFERENCES sishu_book_pages(page_id) ON DELETE CASCADE,
      block_type VARCHAR(32),
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_book_assets (
      asset_id VARCHAR(96) PRIMARY KEY,
      book_id VARCHAR(64) NOT NULL REFERENCES sishu_books(book_id) ON DELETE CASCADE,
      filename TEXT,
      mime VARCHAR(128),
      size BIGINT NOT NULL DEFAULT 0,
      sha256 CHAR(64),
      content BYTEA,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_book_logs (
      id BIGSERIAL PRIMARY KEY,
      book_id VARCHAR(64) NOT NULL REFERENCES sishu_books(book_id) ON DELETE CASCADE,
      content TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_book_progress (
      book_id VARCHAR(64) PRIMARY KEY REFERENCES sishu_books(book_id) ON DELETE CASCADE,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_book_inputs (
      book_id VARCHAR(64) PRIMARY KEY REFERENCES sishu_books(book_id) ON DELETE CASCADE,
      inputs JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
]

# 会话族（chat_history.db 四表 1.2GB 批8 迁移）
_SESSIONS = [
    """CREATE TABLE IF NOT EXISTS sishu_sessions (
      session_id VARCHAR(64) PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL DEFAULT 'admin',
      expert_id VARCHAR(64) NOT NULL DEFAULT 'sishu',
      title TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_messages (
      id BIGSERIAL PRIMARY KEY,
      session_id VARCHAR(64) NOT NULL,
      seq INT NOT NULL DEFAULT 0,
      role VARCHAR(16),
      content TEXT,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_turns (
      turn_id VARCHAR(64) PRIMARY KEY,
      session_id VARCHAR(64) NOT NULL,
      seq INT NOT NULL DEFAULT 0,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_turn_events (
      id BIGSERIAL PRIMARY KEY,
      turn_id VARCHAR(64) NOT NULL,
      seq INT NOT NULL DEFAULT 0,
      event_type VARCHAR(32),
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
]

# 课程教材族（2.3GB 批9 迁移；资产 bytea）
_CURRICULUM = [
    """CREATE TABLE IF NOT EXISTS sishu_textbooks (
      textbook_id VARCHAR(96) PRIMARY KEY,
      name TEXT,
      subject VARCHAR(64),
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_chapters (
      chapter_id VARCHAR(96) PRIMARY KEY,
      textbook_id VARCHAR(96) NOT NULL,
      title TEXT,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb)""",
    """CREATE TABLE IF NOT EXISTS sishu_knowledge_points (
      kp_id VARCHAR(96) PRIMARY KEY,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb)""",
    """CREATE TABLE IF NOT EXISTS sishu_curriculum_assets (
      asset_id VARCHAR(96) PRIMARY KEY,
      domain VARCHAR(20) NOT NULL,             -- curriculum | grade3 | grade7 | pages
      key TEXT NOT NULL,
      mime VARCHAR(128),
      size BIGINT NOT NULL DEFAULT 0,
      sha256 CHAR(64),
      content BYTEA,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
]

# 伙伴/分享/记忆/通用资产/迁移基建
_MISC = [
    """CREATE TABLE IF NOT EXISTS sishu_partners (
      partner_id VARCHAR(64) PRIMARY KEY,
      name TEXT NOT NULL,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_partner_sessions (
      session_id VARCHAR(64) PRIMARY KEY,
      partner_id VARCHAR(64) NOT NULL,
      user_id VARCHAR(128) NOT NULL DEFAULT 'admin',
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_h5_links (
      link_id VARCHAR(64) PRIMARY KEY,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      expires_at TIMESTAMPTZ)""",
    """CREATE TABLE IF NOT EXISTS sishu_memory_items (
      id BIGSERIAL PRIMARY KEY,
      domain VARCHAR(32) NOT NULL,
      user_id VARCHAR(128) NOT NULL DEFAULT 'admin',
      scope VARCHAR(64),
      key TEXT,
      value JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_assets (
      asset_id VARCHAR(96) PRIMARY KEY,
      domain VARCHAR(32) NOT NULL,             -- mother_question | book | curriculum | misc
      purpose VARCHAR(64),
      filename TEXT,
      mime VARCHAR(128),
      size BIGINT NOT NULL DEFAULT 0,
      sha256 CHAR(64),
      content BYTEA,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sishu_migration_cursor (
      domain VARCHAR(64) PRIMARY KEY,
      last_id TEXT,
      rows_done BIGINT NOT NULL DEFAULT 0,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
]

# 热路径索引（1.2GB/2.3GB 无索引=切换日拖垮 h5 历史抽屉与教材阅读）
_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sishu_sessions_user_updated ON sishu_sessions (user_id, updated_at)",
    "CREATE INDEX IF NOT EXISTS idx_sishu_messages_session_seq ON sishu_messages (session_id, seq)",
    "CREATE INDEX IF NOT EXISTS idx_sishu_turn_events_turn ON sishu_turn_events (turn_id)",
    "CREATE INDEX IF NOT EXISTS idx_sishu_book_pages_book ON sishu_book_pages (book_id)",
    "CREATE INDEX IF NOT EXISTS idx_sishu_book_blocks_page ON sishu_book_blocks (page_id)",
    "CREATE INDEX IF NOT EXISTS idx_sishu_notebook_entries_user ON sishu_notebook_entries (user_id)",
    "CREATE INDEX IF NOT EXISTS idx_sishu_curriculum_assets_dom_key ON sishu_curriculum_assets (domain, key)",
]

DDL: list[str] = (_LEARNING + _MOTHER + _NOTEBOOK + _BOOK + _SESSIONS + _CURRICULUM
                  + _MISC + _INDEXES)


def ensure() -> int:
    """全族 DDL 幂等 apply；返回本轮实际执行的语句数（幂等重跑=0 输出语句仍计数，
    验收口径=二跑「新建对象数」为 0——由调用方对比 information_schema 前后快照）。"""
    from .pg import engine
    n = 0
    with engine.begin() as c:
        for ddl in DDL:
            c.execute(__import__("sqlalchemy").text(ddl))
            n += 1
    return n


def object_snapshot() -> dict[str, list[str]]:
    """information_schema 快照（表+索引）——幂等验收对比用。"""
    from sqlalchemy import text
    from .pg import engine
    with engine.connect() as c:
        tables = [r[0] for r in c.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'sishu%' ORDER BY 1"))]
        indexes = [r[0] for r in c.execute(text(
            "SELECT indexname FROM pg_indexes WHERE schemaname='public' AND indexname LIKE 'idx_sishu%' ORDER BY 1"))]
    return {"tables": tables, "indexes": indexes}
