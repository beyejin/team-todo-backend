CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    description TEXT,
    status TEXT NOT NULL DEFAULT 'assigned'
        CHECK (status IN ('assigned', 'in_progress', 'completed')),
    priority TEXT NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('low', 'medium', 'high')),
    due_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);
CREATE TABLE task_assignees (
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    assignee_name TEXT NOT NULL,
    PRIMARY KEY (task_id, assignee_name)
);
CREATE TABLE task_tags (
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (task_id, tag)
);
CREATE TABLE task_labels (
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    PRIMARY KEY (task_id, label)
);
CREATE INDEX idx_tasks_status_deleted_created
    ON tasks(status, deleted_at, created_at);
CREATE INDEX idx_tasks_due_at ON tasks(due_at);
CREATE INDEX idx_assignees_name_task ON task_assignees(assignee_name, task_id);
CREATE INDEX idx_tags_tag_task ON task_tags(tag, task_id);
CREATE INDEX idx_labels_label_task ON task_labels(label, task_id);
