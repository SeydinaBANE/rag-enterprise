-- Users table for JWT auth + RBAC
CREATE TABLE IF NOT EXISTS users (
    id                   UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    email                VARCHAR(255) UNIQUE NOT NULL,
    hashed_password      VARCHAR(255) NOT NULL,
    full_name            VARCHAR(255),
    role                 VARCHAR(50)  NOT NULL DEFAULT 'user',  -- 'admin' | 'user'
    allowed_collections  TEXT[]       NOT NULL DEFAULT '{general}',
    is_active            BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS users_email_idx ON users (email);
