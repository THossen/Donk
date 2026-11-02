export interface Status {
  model_id: string;
  model_base_url: string;
  model_configured: boolean;
  email_mode: string;
  demo_mode: boolean;
  demo_redirect_set: boolean;
  history_limits: Record<string, number>;
  repo: {
    path?: string;
    head_sha?: string;
    head_short?: string;
    head_author?: string;
    head_date?: string;
    head_subject?: string;
    error?: string;
  };
}

export interface Contributor {
  name: string;
  surviving_lines: number;
  commits: number;
  first_date: string | null;
  last_date: string | null;
  files: string[];
  is_main?: boolean;
}

export interface Answer {
  headline: string;
  findings: string[];
  contributor_names: string[];
  evidence_ids: string[];
  suggested_question: string;
  model_used?: boolean;
  insufficient?: boolean;
  contributors?: Contributor[];
  files?: { path: string; blame_lines: number; last_touched: string | null }[];
  files_truncated?: boolean;
  original_author?: string | null;
  most_recent_contributor?: string | null;
  scope?: string;
  verification?: { checked: number; problems: string[]; verified: boolean };
  repaired?: boolean;
}

export type AskEvent =
  | { type: 'stage'; phase: string; detail: string }
  | { type: 'tool'; name: string; summary: string }
  | { type: 'result'; name: string; evidence_ids: string[]; error: string | null }
  | { type: 'answer'; answer: Answer }
  | { type: 'error'; detail: string }
  | { type: 'done' };

export interface Overview {
  tracked_total: number;
  top_dirs: [string, number][];
  recent_commits: { sha: string; author: string; date: string; subject: string; evidence_id: string }[];
  head: { sha: string; author: string; date: string; subject: string };
}

export interface RepoMapNode {
  name: string;
  path: string | null;
  files: number;
  children: RepoMapNode[];
}

export interface RepoMapData {
  tree: RepoMapNode;
  mapped_files: number;
  truncated: boolean;
}

export interface RepoEntry {
  name: string;
  path: string;
  active: boolean;
  head_short?: string;
  head_author?: string;
  head_date?: string;
  head_subject?: string;
  tracked_total?: number;
  error?: string;
}

export interface RepoList {
  repos: RepoEntry[];
  active: string | null;
  truncated: boolean;
}

export interface DraftAction {
  id: string;
  status: string;
  contributor: string;
  roster_email: string;
  delivers_to: string;
  subject: string;
  body: string;
  evidence_ids: string[];
  idempotency_key: string;
  demo_mode?: boolean;
  delivery_notice?: string;
}

export interface ProposeEmailInput {
  contributor: string;
  question: string;
  scope: string;
  evidence_ids: string[];
  suggested: boolean;
}

export interface SendActionInput {
  confirmed: boolean;
  idempotency_key: string;
  edited_subject?: string;
  edited_body?: string;
}

export interface HistoryItem {
  id: number;
  question: string;
  repo: string;
  created_at: number;
}
