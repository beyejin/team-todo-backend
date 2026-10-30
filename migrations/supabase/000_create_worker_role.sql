-- Run once through the authenticated SQL Editor before 001_worker_access.sql.
-- The returned credentials are secrets: never save query results in Git.
CREATE OR REPLACE FUNCTION pg_temp.create_ttodo_worker_credentials()
RETURNS TABLE (database_password text, api_token text)
LANGUAGE plpgsql
AS $function$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ttodo_worker') THEN
        RAISE EXCEPTION 'Database role ttodo_worker already exists';
    END IF;

    database_password := replace(gen_random_uuid()::text, '-', '')
        || replace(gen_random_uuid()::text, '-', '');
    api_token := replace(gen_random_uuid()::text, '-', '')
        || replace(gen_random_uuid()::text, '-', '');

    EXECUTE format(
        'CREATE ROLE ttodo_worker LOGIN NOINHERIT NOCREATEDB NOCREATEROLE '
        'NOREPLICATION NOBYPASSRLS PASSWORD %L',
        database_password
    );
    RETURN NEXT;
END;
$function$;

SELECT * FROM pg_temp.create_ttodo_worker_credentials();
