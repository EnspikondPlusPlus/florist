-- Florist store v1. Records are validated JSON documents (see florist/schemas.py)
-- with a few indexed columns pulled out for filtering and sorting.

CREATE TABLE IF NOT EXISTS seeds (
  id TEXT PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  state TEXT NOT NULL,
  tier TEXT NOT NULL,
  priority INTEGER NOT NULL,
  passive INTEGER NOT NULL DEFAULT 0,
  updated TEXT NOT NULL,
  doc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feed_sources (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  doc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feed_items (
  id TEXT PRIMARY KEY,
  dedupe_key TEXT UNIQUE NOT NULL,
  source_id TEXT,
  status TEXT NOT NULL,
  score REAL NOT NULL DEFAULT 0,
  created TEXT NOT NULL,
  doc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS feed_items_status ON feed_items(status, score DESC);

CREATE TABLE IF NOT EXISTS compost (
  id TEXT PRIMARY KEY,
  cluster TEXT,
  created TEXT NOT NULL,
  updated TEXT NOT NULL,
  doc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY,
  seed_id TEXT NOT NULL,
  round INTEGER NOT NULL,
  kind TEXT NOT NULL,
  status TEXT NOT NULL,
  dedupe_key TEXT,
  created TEXT NOT NULL,
  doc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS nodes_seed ON nodes(seed_id, kind);
CREATE UNIQUE INDEX IF NOT EXISTS nodes_dedupe ON nodes(seed_id, dedupe_key) WHERE dedupe_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS edges (
  seed_id TEXT NOT NULL,
  src TEXT NOT NULL,
  dst TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'grew',
  PRIMARY KEY (src, dst, kind)
);
CREATE INDEX IF NOT EXISTS edges_seed ON edges(seed_id);

CREATE TABLE IF NOT EXISTS flowers (
  seed_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  created TEXT NOT NULL,
  doc TEXT NOT NULL,
  PRIMARY KEY (seed_id, version)
);

CREATE TABLE IF NOT EXISTS smoke (
  id TEXT PRIMARY KEY,
  seed_id TEXT NOT NULL,
  status TEXT NOT NULL,
  created TEXT NOT NULL,
  doc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS visuals (
  id TEXT PRIMARY KEY,
  seed_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  round INTEGER NOT NULL,
  doc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  seed_id TEXT NOT NULL,
  mode TEXT NOT NULL,            -- live | passive | agent
  status TEXT NOT NULL,          -- running | waiting | done | stopped | failed
  round INTEGER NOT NULL DEFAULT 0,
  step TEXT NOT NULL DEFAULT '',
  state TEXT NOT NULL DEFAULT '{}',  -- resumable loop state (pending agent task, cursors)
  error TEXT NOT NULL DEFAULT '',
  stop_requested INTEGER NOT NULL DEFAULT 0,
  started TEXT NOT NULL,
  finished TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS runs_seed ON runs(seed_id, started DESC);

CREATE TABLE IF NOT EXISTS chat (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seed_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  actions TEXT NOT NULL DEFAULT '[]',
  consumed INTEGER NOT NULL DEFAULT 0,  -- steering notes already fed into a round
  created TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,
  target_kind TEXT NOT NULL,
  target_id TEXT NOT NULL,
  signal REAL NOT NULL,
  features TEXT NOT NULL DEFAULT '{}',
  created TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TEXT NOT NULL,
  step TEXT NOT NULL,
  seed_id TEXT NOT NULL DEFAULT '',
  run_id TEXT NOT NULL DEFAULT '',
  backend TEXT NOT NULL,
  model TEXT NOT NULL,
  input_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  cost_usd REAL NOT NULL DEFAULT 0,
  latency_ms INTEGER NOT NULL DEFAULT 0,
  ok INTEGER NOT NULL DEFAULT 1,
  error TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS llm_calls_seed ON llm_calls(seed_id);

CREATE TABLE IF NOT EXISTS research_cache (
  key TEXT PRIMARY KEY,
  tool TEXT NOT NULL,
  query TEXT NOT NULL,
  created TEXT NOT NULL,
  payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TEXT NOT NULL,
  kind TEXT NOT NULL,
  seed_id TEXT NOT NULL DEFAULT '',
  message TEXT NOT NULL,
  data TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS packs (
  seed_id TEXT NOT NULL,
  path TEXT NOT NULL,
  created TEXT NOT NULL,
  PRIMARY KEY (seed_id, path)
);

CREATE TABLE IF NOT EXISTS kv (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
