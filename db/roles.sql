-- Ground-truth isolation, enforced by the database rather than by convention.
--
-- The spec (§4.1) says to "lock the sheet — move it out of the repo path the
-- agent reads." But the agent has no filesystem tool: its read path is the
-- database, the retrieval index, and its prompts. So hiding a CSV protects
-- nothing that matters. The real control is here.
--
--   sunset_app   -- the role the FastAPI app and the LangGraph pipeline use.
--                   REVOKE'd from schema `truth`. Cannot read the answers.
--   sunset_eval  -- the role the scoring harness uses. Owns schema `truth`.
--
-- tests/test_isolation.py connects as sunset_app and asserts that
-- `SELECT * FROM truth.ground_truth` raises InsufficientPrivilege. That test
-- is the claim; this file is the implementation.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sunset_app') THEN
    CREATE ROLE sunset_app LOGIN PASSWORD 'sunset_app';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sunset_eval') THEN
    CREATE ROLE sunset_eval LOGIN PASSWORD 'sunset_eval';
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- public schema: both roles work here. This is the evidence the agent reads.
-- ---------------------------------------------------------------------------
GRANT USAGE, CREATE ON SCHEMA public TO sunset_app, sunset_eval;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sunset_app, sunset_eval;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO sunset_app, sunset_eval;

-- ---------------------------------------------------------------------------
-- truth schema: the golden set. sunset_eval only.
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS truth AUTHORIZATION sunset_eval;

REVOKE ALL ON SCHEMA truth FROM PUBLIC;
REVOKE ALL ON SCHEMA truth FROM sunset_app;
GRANT USAGE, CREATE ON SCHEMA truth TO sunset_eval;

REVOKE ALL ON ALL TABLES IN SCHEMA truth FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA truth FROM sunset_app;

-- Future tables in `truth` inherit the denial. Without this, adding a table to
-- the schema later would silently re-open the hole.
ALTER DEFAULT PRIVILEGES FOR ROLE sunset_eval IN SCHEMA truth
  REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE sunset_eval IN SCHEMA truth
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sunset_eval;

-- ---------------------------------------------------------------------------
-- checkpoints schema: LangGraph's PostgresSaver. App-owned.
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS checkpoints AUTHORIZATION sunset_app;
GRANT USAGE, CREATE ON SCHEMA checkpoints TO sunset_app;
