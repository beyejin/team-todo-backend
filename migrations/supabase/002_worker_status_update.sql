BEGIN;

-- Reuse 001_worker_access.sql policies and allow only board status movement.
GRANT UPDATE (column_id, position, updated_at)
ON public.board_items TO ttodo_worker;
GRANT UPDATE (updated_at) ON public.issues TO ttodo_worker;

COMMIT;
