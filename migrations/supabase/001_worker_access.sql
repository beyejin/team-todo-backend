BEGIN;

DO $$
DECLARE
    worker_role pg_roles%ROWTYPE;
BEGIN
    SELECT * INTO worker_role FROM pg_roles WHERE rolname = 'ttodo_worker';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Required database role ttodo_worker does not exist';
    END IF;
    IF worker_role.rolsuper
        OR worker_role.rolbypassrls
        OR worker_role.rolcreaterole
        OR worker_role.rolcreatedb
        OR worker_role.rolreplication
        OR worker_role.rolinherit THEN
        RAISE EXCEPTION 'Role ttodo_worker has unsafe role attributes';
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO ttodo_worker;
REVOKE CREATE ON SCHEMA public FROM ttodo_worker;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM ttodo_worker;

ALTER TABLE public.board_columns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.board_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.boards ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.checklist_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.issue_assignees ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.issue_labels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.labels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.milestones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workflow_statuses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workspace_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;

GRANT SELECT ON public.boards, public.board_columns, public.workflow_statuses,
    public.workspace_members, public.projects, public.profiles, public.issues,
    public.board_items, public.issue_assignees, public.issue_labels, public.labels
TO ttodo_worker;
GRANT INSERT ON public.issues, public.board_items, public.issue_assignees,
    public.issue_labels, public.labels TO ttodo_worker;
GRANT UPDATE (name) ON public.labels TO ttodo_worker;

CREATE POLICY ttodo_worker_server_access ON public.board_columns
    TO ttodo_worker USING (true) WITH CHECK (true);
CREATE POLICY ttodo_worker_server_access ON public.board_items
    TO ttodo_worker USING (true) WITH CHECK (true);
CREATE POLICY ttodo_worker_server_access ON public.boards
    TO ttodo_worker USING (true) WITH CHECK (true);
CREATE POLICY ttodo_worker_server_access ON public.issue_assignees
    TO ttodo_worker USING (true) WITH CHECK (true);
CREATE POLICY ttodo_worker_server_access ON public.issue_labels
    TO ttodo_worker USING (true) WITH CHECK (true);
CREATE POLICY ttodo_worker_server_access ON public.issues
    TO ttodo_worker USING (true) WITH CHECK (true);
CREATE POLICY ttodo_worker_server_access ON public.labels
    TO ttodo_worker USING (true) WITH CHECK (true);
CREATE POLICY ttodo_worker_server_access ON public.profiles
    TO ttodo_worker USING (true) WITH CHECK (true);
CREATE POLICY ttodo_worker_server_access ON public.projects
    TO ttodo_worker USING (true) WITH CHECK (true);
CREATE POLICY ttodo_worker_server_access ON public.workflow_statuses
    TO ttodo_worker USING (true) WITH CHECK (true);
CREATE POLICY ttodo_worker_server_access ON public.workspace_members
    TO ttodo_worker USING (true) WITH CHECK (true);
COMMIT;
