-- Runs once, on first container start. The AGE image already preloads the
-- library; this makes the extension available in the application database.
CREATE EXTENSION IF NOT EXISTS age;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
