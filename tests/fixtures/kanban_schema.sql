CREATE TABLE profiles (
    id uuid PRIMARY KEY,
    display_name text NOT NULL,
    github_username text NOT NULL UNIQUE
);
CREATE TABLE workspaces (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    created_by uuid NOT NULL REFERENCES profiles(id)
);
CREATE TABLE workspace_members (
    workspace_id uuid NOT NULL REFERENCES workspaces(id),
    profile_id uuid NOT NULL REFERENCES profiles(id),
    role text NOT NULL DEFAULT 'member',
    PRIMARY KEY (workspace_id, profile_id)
);
CREATE TABLE projects (
    id uuid PRIMARY KEY,
    workspace_id uuid NOT NULL REFERENCES workspaces(id),
    project_key text NOT NULL,
    name text NOT NULL,
    created_by uuid NOT NULL REFERENCES profiles(id)
);
CREATE TABLE workflow_statuses (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id),
    name text NOT NULL,
    category text NOT NULL,
    position integer NOT NULL
);
CREATE TABLE boards (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id),
    name text NOT NULL,
    created_by uuid NOT NULL REFERENCES profiles(id)
);
CREATE TABLE board_columns (
    id uuid PRIMARY KEY,
    board_id uuid NOT NULL REFERENCES boards(id),
    workflow_status_id uuid NOT NULL REFERENCES workflow_statuses(id),
    name text NOT NULL,
    position integer NOT NULL
);
CREATE TABLE milestones (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL REFERENCES projects(id),
    name text NOT NULL
);
CREATE TABLE issues (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL REFERENCES projects(id),
    issue_number integer NOT NULL,
    title text NOT NULL,
    description text,
    story_point integer,
    milestone_id uuid,
    created_by uuid NOT NULL REFERENCES profiles(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (project_id, issue_number)
);
CREATE TABLE checklist_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id uuid NOT NULL REFERENCES issues(id),
    content text NOT NULL,
    is_completed boolean NOT NULL DEFAULT false
);
CREATE TABLE board_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id uuid NOT NULL REFERENCES boards(id),
    issue_id uuid NOT NULL REFERENCES issues(id),
    column_id uuid NOT NULL REFERENCES board_columns(id),
    position integer NOT NULL,
    added_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE issue_assignees (
    issue_id uuid NOT NULL REFERENCES issues(id),
    profile_id uuid NOT NULL REFERENCES profiles(id),
    PRIMARY KEY (issue_id, profile_id)
);
CREATE TABLE labels (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL REFERENCES projects(id),
    name text NOT NULL,
    color text NOT NULL,
    UNIQUE (project_id, name)
);
CREATE TABLE issue_labels (
    issue_id uuid NOT NULL REFERENCES issues(id),
    label_id uuid NOT NULL REFERENCES labels(id),
    PRIMARY KEY (issue_id, label_id)
);
INSERT INTO profiles (id, display_name, github_username)
VALUES ('00000000-0000-0000-0000-000000000001', '한예진', 'han-yejin');
INSERT INTO workspaces (id, name, created_by)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    'Team 6',
    '00000000-0000-0000-0000-000000000001'
);
INSERT INTO workspace_members (workspace_id, profile_id, role)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000001',
    'owner'
);
INSERT INTO projects (id, workspace_id, project_key, name, created_by)
VALUES (
    '00000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000002',
    'TEAM6',
    'Team 6 Kanban',
    '00000000-0000-0000-0000-000000000001'
);
INSERT INTO boards (id, project_id, name, created_by)
VALUES (
    '00000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000003',
    'Team 6 Board',
    '00000000-0000-0000-0000-000000000001'
);
INSERT INTO workflow_statuses (id, project_id, name, category, position)
VALUES
    ('00000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000003', 'Todo', 'todo', 0),
    ('00000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-000000000003', 'In Progress', 'in_progress', 1),
    ('00000000-0000-0000-0000-000000000007', '00000000-0000-0000-0000-000000000003', 'Done', 'done', 2);
INSERT INTO board_columns (id, board_id, workflow_status_id, name, position)
VALUES
    ('00000000-0000-0000-0000-000000000008', '00000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000005', 'Todo', 0),
    ('00000000-0000-0000-0000-000000000009', '00000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000006', 'In Progress', 1),
    ('00000000-0000-0000-0000-000000000010', '00000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000007', 'Done', 2);
