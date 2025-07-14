-- Initialize the family wiki database
-- This file will be executed when the PostgreSQL container first starts

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE family_wiki TO family_wiki_user;

-- The SQLAlchemy models will create the actual tables when the app starts