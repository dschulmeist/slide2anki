-- Initialize slide2anki database schema
-- This runs on first startup of the postgres container

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Decks table
CREATE TABLE IF NOT EXISTS decks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'empty',
    card_count INTEGER NOT NULL DEFAULT 0,
    pending_review_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Uploads table
CREATE TABLE IF NOT EXISTS uploads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deck_id UUID NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    pdf_object_key VARCHAR(500) NOT NULL,
    page_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Slides table
CREATE TABLE IF NOT EXISTS slides (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deck_id UUID NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    page_index INTEGER NOT NULL,
    image_object_key VARCHAR(500) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deck_id UUID NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    progress FLOAT NOT NULL DEFAULT 0,
    current_step VARCHAR(255),
    error TEXT,
    logs_object_key VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE
);

-- Claims table
CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slide_id UUID NOT NULL REFERENCES slides(id) ON DELETE CASCADE,
    kind VARCHAR(50) NOT NULL,
    statement TEXT NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 0,
    evidence_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Card drafts table
CREATE TABLE IF NOT EXISTS card_drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deck_id UUID NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    slide_id UUID REFERENCES slides(id) ON DELETE SET NULL,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    confidence FLOAT NOT NULL DEFAULT 0,
    flags_json JSONB DEFAULT '[]',
    evidence_json JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Exports table
CREATE TABLE IF NOT EXISTS exports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deck_id UUID NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    object_key VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_uploads_deck_id ON uploads(deck_id);
CREATE INDEX IF NOT EXISTS idx_slides_deck_id ON slides(deck_id);
CREATE INDEX IF NOT EXISTS idx_jobs_deck_id ON jobs(deck_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_claims_slide_id ON claims(slide_id);
CREATE INDEX IF NOT EXISTS idx_card_drafts_deck_id ON card_drafts(deck_id);
CREATE INDEX IF NOT EXISTS idx_card_drafts_status ON card_drafts(status);
CREATE INDEX IF NOT EXISTS idx_exports_deck_id ON exports(deck_id);

-- Updated at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at trigger to relevant tables
DROP TRIGGER IF EXISTS update_decks_updated_at ON decks;
CREATE TRIGGER update_decks_updated_at
    BEFORE UPDATE ON decks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_card_drafts_updated_at ON card_drafts;
CREATE TRIGGER update_card_drafts_updated_at
    BEFORE UPDATE ON card_drafts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
