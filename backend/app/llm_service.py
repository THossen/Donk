"""Backend model service: the application's own Muse integration.

Uses the configured Responses API endpoint with a validated tool-execution
loop. Credentials come from the environment only and are never logged.
"""
import json
import logging
from typing import Any, Callable

import httpx

from . import evidence as ev
from .config import Settings
from .gittools import GitError, GitRepo

log = logging.getLogger("donk.llm")

SYSTEM_PROMPT = """You are Donk, an AI teammate that investigates a Git repository to find who contributed to a part of the code.
You have tools to search files, read snippets, inspect commit history, and roll up authorship.
Rules:
- Always investigate with tools before answering. Never invent file paths, commit hashes, contributor names, or numbers.
- Cite evidence with the evidence_id values returned by tools.
- Distinguish original authorship (who wrote it first), recent contributions (who touched it last), and substantial surviving contributions (who has the most surviving blamed lines).
- Say "main contributor" — never assert official ownership or responsibility.
- If evidence is ambiguous, name multiple contributors and explain why.
- If evidence is insufficient, say so plainly and suggest what would resolve it.
- The user may ask follow-ups in the same conversation: earlier turns give the prior scope, findings, and evidence. Reuse them and re-investigate only what is new; "why them?" or "only the backend" refers to the previous investigation.
- Keep the final answer short: a one-sentence headline plus up to three findings.
- "suggested_question" is a ready-to-send question FOR the contributor about their code (e.g. "Could you walk me through ...?"). Never address the user, never offer follow-ups ("do you want...", "would you like...", "should I..."), never narrate the investigation.
- Your final message must be a single JSON object: {"headline": str, "findings": [str,...], "contributor_names": [str,...], "evidence_ids": [str,...], "suggested_question": str}.
"""

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "name": "search_files",
        "description": "Case-insensitive fixed-string search over tracked file contents. Returns bounded hits with evidence ids.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path_prefix": {"type": "string"},
                "max_results": {"type": "integer"},
            },
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "name": "read_snippet",
        "description": "Read bounded lines of a file at HEAD.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer"},
                "num_lines": {"type": "integer"},
            },
            "required": ["path", "start_line", "num_lines"],
        },
    },
    {
        "type": "function",
        "name": "git_log",
        "description": "Bounded commit history, optionally for one path. Newest first.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_count": {"type": "integer"},
            },
        },
    },
    {
        "type": "function",
        "name": "explain_authorship",
        "description": "Deterministic authorship rollup (original author, recent contributors, surviving lines) for a path or directory prefix.",
        "parameters": {
            "type": "object",
            "properties": {"path_or_prefix": {"type": "string"}},
            "required": ["path_or_prefix"],
        },
    },
]


class ModelService:
    def __init__(self, settings: Settings):
        self.settings = settings

    # -- tool executor (shared by model loop and fallback) ------------------
    def execute_tool(self, repo: GitRepo, name: str, args: dict) -> dict:
        s = self.settings
        if name == "search_files":
            q = str(args.get("query", ""))[:120]
            prefix = str(args.get("path_prefix", "") or "")
            max_r = min(int(args.get("max_results", s.search_max_results) or 20), 50)
            res = repo.search(q, prefix, max_r)
            out_hits = []
            for h in res["hits"]:
                eid = ev.hit_id(h["path"], h["line"])
                out_hits.append({**h, "evidence_id": eid})
            return {"hits": out_hits, "truncated": res["truncated"]}
        if name == "read_snippet":
            n = min(int(args.get("num_lines", 40) or 40), s.snippet_max_lines)
            data = repo.snippet(
                str(args.get("path", "")), int(args.get("start_line", 1) or 1), n
            )
            data["evidence_id"] = ev.snippet_id(
                data["path"], data["start_line"], n
            )
            return data
        if name == "git_log":
            m = min(int(args.get("max_count", 20) or 20), s.git_max_commits)
            res = repo.log(str(args.get("path", "") or ""), m)
            commits = []
            for c in res["commits"]:
                commits.append({**c, "evidence_id": ev.commit_id(c["sha"])})
            return {"commits": commits, "truncated": res["truncated"]}
        if name == "explain_authorship":
            return ev.explain_authorship(
                repo, str(args.get("path_or_prefix", "") or "")
            )
        raise GitError(f"unknown tool: {name}")

    # -- Responses API -------------------------------------------------------
    def _headers(self) -> dict:
        # Key is used here only; never logged (see call sites).
        return {"Authorization": f"Bearer {self.settings.model_api_key}"}

    def _post(self, payload: dict) -> dict:
        url = self.settings.model_base_url.rstrip("/") + "/responses"
        with httpx.Client(timeout=self.settings.model_timeout_s) as client:
            resp = client.post(url, headers=self._headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise ValueError("unexpected model response shape")
        return data

    @staticmethod
    def _extract_output(data: dict) -> tuple[str, list[dict]]:
        """Return (text, function_calls). Tolerant of minor shape variants."""
        output = data.get("output", data.get("outputs", []))
        texts: list[str] = []
        calls: list[dict] = []
        if isinstance(output, str):
            return output, []
        for item in output if isinstance(output, list) else []:
            if not isinstance(item, dict):
                continue
            t = item.get("type", "")
            if t in ("function_call", "tool_call"):
                args = item.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args or "{}")
                    except ValueError:
                        args = {"_raw": args}
                calls.append(
                    {
                        "call_id": item.get("call_id") or item.get("id") or "",
                        "name": item.get("name") or item.get("function", ""),
                        "arguments": args if isinstance(args, dict) else {},
                        "raw": item,
                    }
                )
            elif t in ("message", "output_text", "text"):
                content = item.get("content", item.get("text", ""))
                if isinstance(content, str):
                    texts.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and isinstance(
                            block.get("text"), str
                        ):
                            texts.append(block["text"])
                        elif isinstance(block, str):
                            texts.append(block)
        # Some servers put assistant text at top level.
        if not texts and isinstance(data.get("text"), str):
            texts.append(data["text"])
        return "\n".join(texts), calls

    def health_check(self) -> dict:
        """Minimal real request (no tools). Raises on failure."""
        data = self._post(
            {
                "model": self.settings.model_id,
                "input": "Reply with the single word OK.",
                # Reasoning tokens count against this budget; 16 starves the reply.
                "max_output_tokens": 64,
            }
        )
        text, _ = self._extract_output(data)
        return {"ok": True, "echo": text.strip()[:64]}

    def investigate(
        self,
        repo: GitRepo,
        question: str,
        on_event: Callable[[dict], None] | None = None,
        prior_turns: list[dict] | None = None,
    ) -> dict:
        """Tool-using investigation. Returns structured answer + raw tool log."""
        if not self.settings.model_configured:
            raise RuntimeError("model not configured")
        emit = on_event or (lambda e: None)
        convo: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        # Prior turns as compact Q/A summaries: scope, findings, names, and
        # evidence ids carry over so follow-ups build on the same investigation.
        for turn in (prior_turns or [])[-3:]:
            pa = turn.get("answer", {}) if isinstance(turn, dict) else {}
            summary = {
                "headline": pa.get("headline", ""),
                "findings": pa.get("findings", []),
                "contributor_names": pa.get("contributor_names", []),
                "evidence_ids": pa.get("evidence_ids", []),
                "scope": pa.get("scope", ""),
                "suggested_question": pa.get("suggested_question", ""),
            }
            convo.append({"role": "user", "content": str(turn.get("question", ""))[:2000]})
            convo.append({"role": "assistant", "content": json.dumps(summary)})
        convo.append({"role": "user", "content": question[:2000]})
        tool_log: list[dict] = []
        known_ids: set[str] = set()
        file_mentions: dict[str, int] = {}
        final_text = ""
        for it in range(self.settings.model_max_tool_iters):
            data = self._post(
                {
                    "model": self.settings.model_id,
                    "input": convo,
                    "tools": TOOL_SCHEMAS,
                    "tool_choice": "auto",
                    "temperature": 0.2,
                    "max_output_tokens": self.settings.model_max_output_tokens,
                }
            )
            text, calls = self._extract_output(data)
            if text.strip():
                final_text = text
            if not calls:
                break
            for call in calls:
                name = call["name"]
                emit({"type": "tool", "name": name, "summary": summarize_args(name, call["arguments"])})
                try:
                    result = self.execute_tool(repo, name, call["arguments"])
                    err = None
                except (GitError, ValueError, KeyError) as e:
                    result = {"error": str(e)[:300]}
                    err = str(e)[:300]
                collect_ids(result, known_ids)
                for p in tool_file_paths(name, call["arguments"], result):
                    file_mentions[p] = file_mentions.get(p, 0) + 1
                tool_log.append({
                    "name": name,
                    "arguments": call["arguments"],
                    "error": err,
                    "result_text": json.dumps(result)[:4000],
                })
                emit(
                    {
                        "type": "result",
                        "name": name,
                        "evidence_ids": sorted(known_ids)[-12:],
                        "error": err,
                    }
                )
                convo.extend(tool_result_inputs(call, result))
        answer = parse_final_json(final_text)
        answer["model_used"] = True
        answer["investigated_files"] = ev.rank_investigated_files(repo, file_mentions)
        return {"answer": answer, "tool_log": tool_log, "known_ids": sorted(known_ids)}


def tool_result_inputs(call: dict, result: dict) -> list[dict]:
    """Follow-up input items for one executed call.

    The Responses API rejects Chat-style {"role": "tool"} items; it wants
    the original function_call echoed back plus a function_call_output.
    """
    return [
        call["raw"],
        {
            "type": "function_call_output",
            "call_id": call["call_id"],
            "output": json.dumps(result)[:12000],
        },
    ]


def summarize_args(name: str, args: dict) -> str:
    if name == "search_files":
        return f"search {args.get('query', '')!r}"
    if name == "read_snippet":
        return f"{args.get('path', '')}:{args.get('start_line', '')}"
    if name == "git_log":
        return f"history {args.get('path', '') or '(repo)'}"
    if name == "explain_authorship":
        return f"authorship {args.get('path_or_prefix', '')}"
    return name


def tool_file_paths(name: str, args: dict, result: dict) -> list[str]:
    """File paths a tool call actually touched (for scope preservation)."""
    if not isinstance(result, dict) or "error" in result:
        return []
    if not isinstance(args, dict):
        args = {}
    if name == "search_files":
        return [
            h["path"] for h in result.get("hits", [])
            if isinstance(h, dict) and h.get("path")
        ]
    if name == "read_snippet":
        return [result["path"]] if result.get("path") else []
    if name == "git_log":
        return [args["path"]] if args.get("path") else []
    if name == "explain_authorship":
        paths = [
            f["path"] for f in result.get("files", [])
            if isinstance(f, dict) and f.get("path")
        ]
        if args.get("path_or_prefix"):
            paths.append(args["path_or_prefix"])
        return paths
    return []


def collect_ids(obj: Any, into: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "evidence_id" and isinstance(v, str):
                into.add(v)
            else:
                collect_ids(v, into)
    elif isinstance(obj, list):
        for v in obj:
            collect_ids(v, into)


def parse_final_json(text: str) -> dict:
    """Lenient parse of the model's final JSON; falls back to plain text."""
    fallback = {
        "headline": (text.strip().splitlines() or ["Investigation complete."])[0][:240],
        "findings": [],
        "contributor_names": [],
        "evidence_ids": [],
        "suggested_question": "",
        "raw_text": text.strip()[:2000],
    }
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return fallback
    try:
        data = json.loads(text[start : end + 1])
    except ValueError:
        return fallback
    if not isinstance(data, dict):
        return fallback
    out = dict(fallback)
    for key in ("headline", "suggested_question"):
        if isinstance(data.get(key), str) and data[key].strip():
            out[key] = data[key].strip()[:500]
    for key in ("findings", "contributor_names", "evidence_ids"):
        if isinstance(data.get(key), list):
            out[key] = [str(x)[:300] for x in data[key][:12]]
    out.pop("raw_text", None)
    return out


# -- deterministic fallback (no key needed) -----------------------------------
STOPWORDS = {
    "who", "what", "when", "where", "which", "worked", "work", "working",
    "wrote", "write", "writes", "maintain", "maintains", "maintainer",
    "owns", "owner", "about", "with", "from", "that", "this", "code",
    "file", "files", "repo", "repository", "team", "person", "people",
    "contributor", "contributors", "author", "authors", "change",
    "changed", "changes", "touch", "touched", "last", "most", "more",
    "than", "does", "did", "are", "the", "and", "for", "our",
}


def fallback_investigate(
    repo: GitRepo,
    question: str,
    settings: Settings,
    on_event: Callable[[dict], None] | None = None,
    prior: dict | None = None,
) -> dict:
    """Deterministic keyword investigation used when no model key is set.

    `prior` carries the previous thread turn; when a follow-up matches no new
    files, the investigation continues in the previous scope instead of
    failing with no context.
    """
    emit = on_event or (lambda e: None)
    words = [
        w.strip("?.,!:'\"").lower()
        for w in question.split()
        if len(w.strip("?.,!:'\"")) > 2
    ]
    keywords = [w for w in words if w not in STOPWORDS][:4]
    emit({"type": "stage", "phase": "finding_files", "detail": f"keywords: {', '.join(keywords) or '(none)'}"})
    # Highest-precision signal first: tracked PATHS containing a keyword.
    path_scope = ""
    if keywords:
        try:
            tracked = repo.all_files()
        except GitError:
            tracked = []
        matches = [f for f in tracked if any(k in f.lower() for k in keywords)]
        # Skip vendored mirrors for scoping.
        matches = [f for f in matches if not f.startswith(GitRepo.SEARCH_EXCLUDED_PREFIXES)]
        if len(matches) == 1 and "/" not in matches[0]:
            path_scope = matches[0]
        elif matches:
            by_dir2: dict[str, int] = {}
            for f in matches:
                d = f.rsplit("/", 1)[0] if "/" in f else ""
                if d:
                    by_dir2[d] = by_dir2.get(d, 0) + 1
            if by_dir2:
                path_scope = sorted(by_dir2.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            elif len(matches) == 1:
                path_scope = matches[0]
    hits: list[dict] = []
    per_file: dict[str, int] = {}
    for kw in keywords:
        emit({"type": "tool", "name": "search_files", "summary": f"search {kw!r}"})
        res = repo.search(kw, "", settings.search_max_results)
        for h in res["hits"]:
            # Diversify: one chatty file must not capture the whole scope.
            if per_file.get(h["path"], 0) >= 3:
                continue
            per_file[h["path"]] = per_file.get(h["path"], 0) + 1
            eid = ev.hit_id(h["path"], h["line"])
            hits.append({**h, "evidence_id": eid})
        emit({"type": "result", "name": "search_files", "evidence_ids": [h["evidence_id"] for h in hits[-12:]], "error": None})
        if len(hits) >= settings.search_max_results:
            break
    if not hits and prior and prior.get("scope"):
        # Follow-up with no new file matches: continue in the prior scope.
        scope = prior["scope"]
        emit({"type": "stage", "phase": "checking_history", "detail": f"continuing in {scope}"})
        emit({"type": "tool", "name": "explain_authorship", "summary": f"authorship {scope}"})
        rollup = ev.explain_authorship(repo, scope)
        emit({"type": "result", "name": "explain_authorship",
              "evidence_ids": list(prior.get("evidence_ids", []))[:12], "error": None})
        if not rollup.get("insufficient") and rollup["contributors"]:
            mains = rollup["main_contributors"] or [rollup["contributors"][0]["name"]]
            top = rollup["contributors"][0]
            return {
                "answer": {
                    "headline": f"Continuing in {scope}: main contributor is {mains[0]}.",
                    "findings": [
                        f"Same scope as the previous question: {scope}.",
                        f"Top match: {top['name']} ({top['surviving_lines']} surviving lines, {top['commits']} commits in scope).",
                    ],
                    "contributor_names": [c["name"] for c in rollup["contributors"][:4]],
                    "evidence_ids": list(prior.get("evidence_ids", []))[:12],
                    "suggested_question": f"Could you walk me through the {scope} implementation and any edge cases?",
                    "model_used": False,
                    "rollup": rollup,
                    "scope": scope,
                    "investigated_files": list(prior.get("investigated_files", [])),
                    "continued": True,
                },
                "tool_log": [],
                "known_ids": list(prior.get("evidence_ids", [])),
            }
    if not hits:
        return {
            "answer": {
                "headline": "Insufficient evidence in this snapshot.",
                "findings": [
                    "No tracked files matched the question keywords.",
                    "Try naming a file, directory, or symbol (e.g. 'auth', 'server', 'EnvironmentAuth').",
                ],
                "contributor_names": [],
                "evidence_ids": [],
                "suggested_question": "",
                "model_used": False,
                "insufficient": True,
            },
            "tool_log": [],
            "known_ids": [],
        }
    # Scope: prefer files whose PATH matches a keyword (e.g. "auth" ->
    # apps/server/src/auth/*), then code files, then anything. This keeps
    # "who worked on X" scoped to X's implementation instead of chatty docs.
    CODE_EXTS = GitRepo.CODE_EXTENSIONS
    pool = [h for h in hits if any(k in h["path"].lower() for k in keywords)]
    if not pool:
        pool = [h for h in hits if h["path"].lower().endswith(CODE_EXTS)]
    if not pool:
        pool = hits
    if path_scope:
        pool = [h for h in hits if h["path"] == path_scope or h["path"].startswith(path_scope + "/")] or pool
    # Scope: the top directory when pool hits concentrate there, else top file.
    by_dir: dict[str, int] = {}
    by_file: dict[str, int] = {}
    for h in pool:
        d = h["path"].rsplit("/", 1)[0] if "/" in h["path"] else ""
        if d:
            by_dir[d] = by_dir.get(d, 0) + 1
        by_file[h["path"]] = by_file.get(h["path"], 0) + 1
    scope = path_scope
    if not scope and by_dir:
        top_dir, top_n = sorted(by_dir.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        if top_n >= 3 and top_n >= 0.4 * len(pool):
            scope = top_dir
    if not scope:
        scope = sorted(by_file.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    emit({"type": "stage", "phase": "checking_history", "detail": f"scope: {scope or '(repo root)'}"})
    emit({"type": "tool", "name": "explain_authorship", "summary": f"authorship {scope or '(repo)'}"})
    rollup = ev.explain_authorship(repo, scope)
    emit({"type": "result", "name": "explain_authorship", "evidence_ids": [h["evidence_id"] for h in hits[:12]], "error": None})
    if rollup.get("insufficient") or not rollup["contributors"]:
        return {
            "answer": {
                "headline": "Insufficient evidence in this snapshot.",
                "findings": ["Matching files exist but authorship history could not be rolled up."],
                "contributor_names": [],
                "evidence_ids": [h["evidence_id"] for h in hits[:12]],
                "suggested_question": "",
                "model_used": False,
                "insufficient": True,
            },
            "tool_log": [],
            "known_ids": [h["evidence_id"] for h in hits],
        }
    mains = rollup["main_contributors"] or [rollup["contributors"][0]["name"]]
    top = rollup["contributors"][0]
    findings = [
        f"Top match: {top['name']} ({top['surviving_lines']} surviving lines, {top['commits']} commits in scope).",
    ]
    if rollup["original_author"]:
        findings.append(f"Wrote it first: {rollup['original_author']}.")
    if rollup["most_recent_contributor"]:
        findings.append(f"Most recent contributor: {rollup['most_recent_contributor']}.")
    if len(mains) > 1:
        findings.append(f"Ambiguous: {', '.join(mains)} all have substantial surviving contributions.")
    answer = {
        "headline": f"Main contributor for {scope or 'matching files'}: {mains[0]}.",
        "findings": findings[:4],
        "contributor_names": [c["name"] for c in rollup["contributors"][:4]],
        "evidence_ids": [h["evidence_id"] for h in hits[:12]],
        "suggested_question": f"Could you walk me through the {scope or 'matched code'} implementation and any edge cases?",
        "model_used": False,
        "rollup": rollup,
        "scope": scope,
    }
    return {"answer": answer, "tool_log": [], "known_ids": [h["evidence_id"] for h in hits]}
