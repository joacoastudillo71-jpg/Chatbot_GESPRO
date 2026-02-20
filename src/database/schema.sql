-- Enable pgvector extension if not already enabled
create extension if not exists vector;

-- Table for LangGraph Checkpoints (if not automatically created by AsyncPostgresSaver)
-- Note: AsyncPostgresSaver usually creates its own tables (checkpoints, checkpoint_blobs, checkpoint_writes).
-- This is just for reference or manual creation if needed.

-- Client Metadata Table (Vendor Agnostic)
create table if not exists client_metadata (
    id uuid primary key default gen_random_uuid(),
    company_id text not null, -- 'civetta', 'costamar', etc.
    channel text, -- 'whatsapp', 'web', etc.
    lopdp_consent boolean default false,
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Event Store for Interaction logging
create table if not exists event_store (
    id uuid primary key default gen_random_uuid(),
    session_id text not null,
    event_type text not null, -- 'user_message', 'bot_response', 'tool_call'
    payload jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now())
);
