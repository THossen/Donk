"""Evidence verification for model answers.

Checks that every cited evidence ID resolves against the pinned snapshot and
that named contributors appear in the tool outputs. One targeted repair is
attempted by the caller; persistent failures are flagged unverified.

Verification confirms references resolve — it does not prove every
AI interpretation is correct. The UI must say so.
"""
from . import evidence as ev
from .gittools import GitError, GitRepo


def verify_answer(
    repo: GitRepo,
    answer: dict,
    known_ids: set[str],
    tool_texts: list[str],
) -> dict:
    problems: list[str] = []
    checked = 0
    for eid in answer.get("evidence_ids", [])[:20]:
        checked += 1
        if eid not in known_ids:
            problems.append(f"uncited-by-tools: {eid}")
            continue
        try:
            ev.resolve(repo, eid)
        except GitError as e:
            problems.append(f"unresolvable: {eid} ({e})")
    corpus = "\n".join(tool_texts).lower()
    for name in answer.get("contributor_names", [])[:8]:
        if name and name.lower() not in corpus:
            problems.append(f"name-not-in-tool-output: {name}")
    return {
        "checked": checked,
        "problems": problems,
        "verified": not problems,
    }
