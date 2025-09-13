-- Supabase setup for openai_memory_chats table
-- Run these commands in your Supabase SQL editor

-- 1. Create the table (if not already created)
CREATE TABLE IF NOT EXISTS openai_memory_chats (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    content JSONB NOT NULL,
    "order" INTEGER NOT NULL,
    response_id TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_openai_memory_chats_session_id ON openai_memory_chats(session_id);
CREATE INDEX IF NOT EXISTS idx_openai_memory_chats_order ON openai_memory_chats(session_id, "order");
CREATE INDEX IF NOT EXISTS idx_openai_memory_chats_timestamp ON openai_memory_chats(timestamp);
CREATE INDEX IF NOT EXISTS idx_openai_memory_chats_response_id ON openai_memory_chats(response_id);

-- 3. Enable Row Level Security (RLS)
ALTER TABLE openai_memory_chats ENABLE ROW LEVEL SECURITY;

-- 4. Create policies to allow all operations (for development)
-- WARNING: These policies allow anyone with the anon key to read/write
-- For production, you should implement proper user authentication

-- Allow anonymous users to insert messages
CREATE POLICY "Allow anonymous insert" ON openai_memory_chats
    FOR INSERT WITH CHECK (true);

-- Allow anonymous users to read all messages
CREATE POLICY "Allow anonymous select" ON openai_memory_chats
    FOR SELECT USING (true);

-- Allow anonymous users to update messages
CREATE POLICY "Allow anonymous update" ON openai_memory_chats
    FOR UPDATE USING (true);

-- Allow anonymous users to delete messages
CREATE POLICY "Allow anonymous delete" ON openai_memory_chats
    FOR DELETE USING (true);

-- 5. Grant necessary permissions to the anon role
GRANT ALL ON openai_memory_chats TO anon;
GRANT USAGE, SELECT ON SEQUENCE openai_memory_chats_id_seq TO anon;