-- PostgreSQL 演示业务表结构。
-- pg_init_data.sql 仅保留数据，因此全新部署时必须先执行本文件。
-- 2026-09-13 第七批：PS 字段由 DDIC 口径对齐 OData V4 CamelCase（wbs_element→WBSElement 等）。
CREATE TABLE IF NOT EXISTS public.dim_ps_wbs_cost (
    id INTEGER PRIMARY KEY,
    "CostId" VARCHAR(50) NOT NULL,
    "WBSElement" VARCHAR(50) NOT NULL,
    "FiscalYear" VARCHAR(10) NOT NULL,
    "CostElement" VARCHAR(50) NOT NULL,
    "ActualCost" NUMERIC(18, 2),
    "CommittedCost" NUMERIC(18, 2),
    "PlannedCost" NUMERIC(18, 2),
    "Variance" NUMERIC(18, 2),
    "Currency" VARCHAR(10),
    "PostingDate" DATE
);


-- ===== v4批2：sishu_ 表族全族 DDL（与 app/services/sishu_data/schemas.py 单源同文）=====
CREATE TABLE IF NOT EXISTS sishu_review_cards (
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
      UNIQUE (kind, item_id, user_id));
CREATE TABLE IF NOT EXISTS sishu_review_records (
      id BIGSERIAL PRIMARY KEY,
      card_id VARCHAR(64) NOT NULL REFERENCES sishu_review_cards(card_id) ON DELETE CASCADE,
      user_id VARCHAR(128) NOT NULL,
      rating SMALLINT NOT NULL,
      scheduled_interval DOUBLE PRECISION NOT NULL,
      reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_wrong_questions (
      wq_id VARCHAR(64) PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL,
      mother_question_id VARCHAR(64) NOT NULL,
      variant_text TEXT NOT NULL,
      error_context TEXT,
      status VARCHAR(20) NOT NULL DEFAULT 'open',
      wrong_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      resolved_at TIMESTAMPTZ);
ALTER TABLE sishu_wrong_questions ADD COLUMN IF NOT EXISTS question JSON;
ALTER TABLE sishu_wrong_questions ADD COLUMN IF NOT EXISTS my_answer TEXT;
ALTER TABLE sishu_wrong_questions ADD COLUMN IF NOT EXISTS error_type VARCHAR(32);
ALTER TABLE sishu_wrong_questions ADD COLUMN IF NOT EXISTS source VARCHAR(16);
CREATE TABLE IF NOT EXISTS sishu_mother_questions (
      mq_id VARCHAR(64) PRIMARY KEY,
      title TEXT NOT NULL,
      archetype_text TEXT NOT NULL,
      knowledge_point_id VARCHAR(128) NOT NULL,
      variant_count INT NOT NULL DEFAULT 0,
      enabled BOOLEAN NOT NULL DEFAULT TRUE);
CREATE TABLE IF NOT EXISTS sishu_recitation (
      id BIGSERIAL PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_practice_gen (
      id BIGSERIAL PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL,
      kind VARCHAR(32),
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_learner_profile (
      user_id VARCHAR(128) PRIMARY KEY,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_self_learning_progress (
      id BIGSERIAL PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL,
      chapter_id VARCHAR(128) NOT NULL,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (user_id, chapter_id));
CREATE TABLE IF NOT EXISTS sishu_notebook_entries (
      id BIGSERIAL PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL,
      title TEXT,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_notebook_categories (
      id BIGSERIAL PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL,
      name TEXT,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb);
CREATE TABLE IF NOT EXISTS sishu_notebook_entry_categories (
      entry_id BIGINT NOT NULL,
      category_id BIGINT NOT NULL,
      PRIMARY KEY (entry_id, category_id));
CREATE TABLE IF NOT EXISTS sishu_books (
      book_id VARCHAR(64) PRIMARY KEY,
      title TEXT NOT NULL,
      description TEXT,
      language VARCHAR(16) DEFAULT 'zh',
      status VARCHAR(32),
      manifest JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_book_spines (
      book_id VARCHAR(64) PRIMARY KEY REFERENCES sishu_books(book_id) ON DELETE CASCADE,
      spine JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_book_pages (
      page_id VARCHAR(64) PRIMARY KEY,
      book_id VARCHAR(64) NOT NULL REFERENCES sishu_books(book_id) ON DELETE CASCADE,
      page_no INT NOT NULL DEFAULT 0,
      title TEXT,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_book_blocks (
      block_id VARCHAR(64) PRIMARY KEY,
      page_id VARCHAR(64) NOT NULL REFERENCES sishu_book_pages(page_id) ON DELETE CASCADE,
      block_type VARCHAR(32),
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_book_assets (
      asset_id VARCHAR(96) PRIMARY KEY,
      book_id VARCHAR(64) NOT NULL REFERENCES sishu_books(book_id) ON DELETE CASCADE,
      filename TEXT,
      mime VARCHAR(128),
      size BIGINT NOT NULL DEFAULT 0,
      sha256 CHAR(64),
      content BYTEA,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_book_logs (
      id BIGSERIAL PRIMARY KEY,
      book_id VARCHAR(64) NOT NULL REFERENCES sishu_books(book_id) ON DELETE CASCADE,
      content TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_book_progress (
      book_id VARCHAR(64) PRIMARY KEY REFERENCES sishu_books(book_id) ON DELETE CASCADE,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_book_inputs (
      book_id VARCHAR(64) PRIMARY KEY REFERENCES sishu_books(book_id) ON DELETE CASCADE,
      inputs JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_sessions (
      session_id VARCHAR(64) PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL DEFAULT 'admin',
      expert_id VARCHAR(64) NOT NULL DEFAULT 'sishu',
      title TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_messages (
      id BIGSERIAL PRIMARY KEY,
      session_id VARCHAR(64) NOT NULL,
      seq INT NOT NULL DEFAULT 0,
      role VARCHAR(16),
      content TEXT,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_turns (
      turn_id VARCHAR(64) PRIMARY KEY,
      session_id VARCHAR(64) NOT NULL,
      seq INT NOT NULL DEFAULT 0,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_turn_events (
      id BIGSERIAL PRIMARY KEY,
      turn_id VARCHAR(64) NOT NULL,
      seq INT NOT NULL DEFAULT 0,
      event_type VARCHAR(32),
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_textbooks (
      textbook_id VARCHAR(96) PRIMARY KEY,
      name TEXT,
      subject VARCHAR(64),
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_chapters (
      chapter_id VARCHAR(96) PRIMARY KEY,
      textbook_id VARCHAR(96) NOT NULL,
      title TEXT,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb);
CREATE TABLE IF NOT EXISTS sishu_knowledge_points (
      kp_id VARCHAR(96) PRIMARY KEY,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb);
CREATE TABLE IF NOT EXISTS sishu_curriculum_assets (
      asset_id VARCHAR(96) PRIMARY KEY,
      domain VARCHAR(20) NOT NULL,             -- curriculum | grade3 | grade7 | pages
      key TEXT NOT NULL,
      mime VARCHAR(128),
      size BIGINT NOT NULL DEFAULT 0,
      sha256 CHAR(64),
      content BYTEA,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_partners (
      partner_id VARCHAR(64) PRIMARY KEY,
      name TEXT NOT NULL,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_partner_sessions (
      session_id VARCHAR(64) PRIMARY KEY,
      partner_id VARCHAR(64) NOT NULL,
      user_id VARCHAR(128) NOT NULL DEFAULT 'admin',
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_h5_links (
      link_id VARCHAR(64) PRIMARY KEY,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      expires_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS sishu_memory_items (
      id BIGSERIAL PRIMARY KEY,
      domain VARCHAR(32) NOT NULL,
      user_id VARCHAR(128) NOT NULL DEFAULT 'admin',
      scope VARCHAR(64),
      key TEXT,
      value JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_assets (
      asset_id VARCHAR(96) PRIMARY KEY,
      domain VARCHAR(32) NOT NULL,             -- mother_question | book | curriculum | misc
      purpose VARCHAR(64),
      filename TEXT,
      mime VARCHAR(128),
      size BIGINT NOT NULL DEFAULT 0,
      sha256 CHAR(64),
      content BYTEA,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sishu_migration_cursor (
      domain VARCHAR(64) PRIMARY KEY,
      last_id TEXT,
      rows_done BIGINT NOT NULL DEFAULT 0,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS idx_sishu_sessions_user_updated ON sishu_sessions (user_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_sishu_messages_session_seq ON sishu_messages (session_id, seq);
CREATE INDEX IF NOT EXISTS idx_sishu_turn_events_turn ON sishu_turn_events (turn_id);
CREATE INDEX IF NOT EXISTS idx_sishu_book_pages_book ON sishu_book_pages (book_id);
CREATE INDEX IF NOT EXISTS idx_sishu_book_blocks_page ON sishu_book_blocks (page_id);
CREATE INDEX IF NOT EXISTS idx_sishu_notebook_entries_user ON sishu_notebook_entries (user_id);
CREATE INDEX IF NOT EXISTS idx_sishu_curriculum_assets_dom_key ON sishu_curriculum_assets (domain, key);
