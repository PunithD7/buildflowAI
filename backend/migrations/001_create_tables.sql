-- BuildFlow Secure AI — Supabase Migration
-- Run this SQL in your Supabase project's SQL Editor:
-- https://supabase.com/dashboard/project/_/sql
--
-- Creates all tables required for workflow persistence and artifact storage.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. WORKFLOWS
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.workflows (
  id                bigserial primary key,
  workflow_id       text not null unique,
  user_id           text,
  project_id        text,
  user_input        text,
  status            text default 'pending',
  output_summary    jsonb default '{}'::jsonb,
  created_at        double precision,
  updated_at        double precision
);

create index if not exists idx_workflows_workflow_id on public.workflows(workflow_id);
create index if not exists idx_workflows_user_id     on public.workflows(user_id);
create index if not exists idx_workflows_status      on public.workflows(status);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. AGENT OUTPUTS
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.agent_outputs (
  id              bigserial primary key,
  workflow_id     text not null references public.workflows(workflow_id) on delete cascade,
  agent_name      text not null,
  output_key      text,
  status          text,
  data_preview    text,      -- First 2000 chars of output (not full data)
  execution_time  double precision,
  created_at      double precision
);

create index if not exists idx_agent_outputs_workflow on public.agent_outputs(workflow_id);
create index if not exists idx_agent_outputs_agent   on public.agent_outputs(agent_name);

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. GENERATED FILES (metadata only — actual files live on filesystem)
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.generated_files (
  id            bigserial primary key,
  workflow_id   text not null references public.workflows(workflow_id) on delete cascade,
  file_path     text not null,
  language      text,
  size_bytes    integer default 0,
  created_at    double precision
);

create index if not exists idx_generated_files_workflow  on public.generated_files(workflow_id);
create index if not exists idx_generated_files_language  on public.generated_files(language);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. PROJECT ARTIFACTS (zip downloads, exports)
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.project_artifacts (
  id              bigserial primary key,
  workflow_id     text not null references public.workflows(workflow_id) on delete cascade,
  artifact_type   text not null,   -- e.g. 'zip', 'export', 'preview'
  artifact_path   text,
  created_at      double precision
);

create index if not exists idx_artifacts_workflow on public.project_artifacts(workflow_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. EXECUTION HISTORY (event log)
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.execution_history (
  id                bigserial primary key,
  workflow_id       text not null,
  user_id           text,
  event             text,           -- e.g. 'workflow_completed', 'agent_failed'
  status            text,
  agents_run        integer default 0,
  files_generated   integer default 0,
  timestamp         double precision
);

create index if not exists idx_history_workflow on public.execution_history(workflow_id);
create index if not exists idx_history_user     on public.execution_history(user_id);
create index if not exists idx_history_event    on public.execution_history(event);

-- ─────────────────────────────────────────────────────────────────────────────
-- Row Level Security
-- ─────────────────────────────────────────────────────────────────────────────
-- Enable RLS on every table.
-- FORCE ROW LEVEL SECURITY ensures the policies are evaluated even when the
-- session is running as a table owner (which the Supabase service_role is).
-- Without FORCE, the service_role would bypass RLS entirely by default.

alter table public.workflows          enable row level security;
alter table public.agent_outputs      enable row level security;
alter table public.generated_files    enable row level security;
alter table public.project_artifacts  enable row level security;
alter table public.execution_history  enable row level security;

alter table public.workflows          force row level security;
alter table public.agent_outputs      force row level security;
alter table public.generated_files    force row level security;
alter table public.project_artifacts  force row level security;
alter table public.execution_history  force row level security;

-- ─────────────────────────────────────────────────────────────────────────────
-- Service-role policies  (idempotent — safe to run multiple times)
--
-- Pattern:
--   FOR ALL  — covers SELECT, INSERT, UPDATE, DELETE in one policy
--   TO service_role  — policy applies only to the Supabase service key role
--   USING (true)     — all existing rows are visible (SELECT / UPDATE / DELETE)
--   WITH CHECK (true) — all new/changed rows are accepted (INSERT / UPDATE)
-- ─────────────────────────────────────────────────────────────────────────────

-- workflows
drop policy if exists "service_role_all_workflows" on public.workflows;
create policy "service_role_all_workflows"
  on public.workflows
  for all
  to service_role
  using     (true)
  with check (true);

-- agent_outputs
drop policy if exists "service_role_all_agent_outputs" on public.agent_outputs;
create policy "service_role_all_agent_outputs"
  on public.agent_outputs
  for all
  to service_role
  using     (true)
  with check (true);

-- generated_files
drop policy if exists "service_role_all_generated_files" on public.generated_files;
create policy "service_role_all_generated_files"
  on public.generated_files
  for all
  to service_role
  using     (true)
  with check (true);

-- project_artifacts
drop policy if exists "service_role_all_project_artifacts" on public.project_artifacts;
create policy "service_role_all_project_artifacts"
  on public.project_artifacts
  for all
  to service_role
  using     (true)
  with check (true);

-- execution_history
drop policy if exists "service_role_all_execution_history" on public.execution_history;
create policy "service_role_all_execution_history"
  on public.execution_history
  for all
  to service_role
  using     (true)
  with check (true);

