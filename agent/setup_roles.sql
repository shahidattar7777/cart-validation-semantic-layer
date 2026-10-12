-- Read-only role for the "raw schema" condition: can see the pd tables only,
-- not the AGE graph. run_eval.py and selftest.py apply this automatically.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cart_raw') THEN
    CREATE ROLE cart_raw LOGIN PASSWORD 'cart_raw';
  END IF;
END $$;
GRANT CONNECT ON DATABASE cartpd TO cart_raw;
GRANT USAGE ON SCHEMA pd TO cart_raw;
GRANT SELECT ON ALL TABLES IN SCHEMA pd TO cart_raw;
ALTER ROLE cart_raw SET search_path = pd;
ALTER ROLE cart_raw SET default_transaction_read_only = on;
ALTER ROLE cart_raw SET statement_timeout = '30s';
