-- Ideate: free-form brainstorming chats not bound to a seed (messages live in `chat`, seed_id = chat id).
CREATE TABLE IF NOT EXISTS ideate_chats (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  seed_id TEXT NOT NULL DEFAULT '',   -- set once the chat was converted into a seed
  context TEXT NOT NULL DEFAULT '[]', -- dragged-in items: [{kind, id, title}]
  created TEXT NOT NULL,
  updated TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ideate_updated ON ideate_chats(updated DESC);
