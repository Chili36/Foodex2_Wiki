"""Independent LLM cross-check of unreviewed gold-case labels.

For each case with reviewed=false, an LLM (blind to the draft labels)
produces three-tier labels from the same rubric + page list. The script
diffs them against the drafts and writes a report: agreements are
auto-acceptable; disagreements go to David.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from anthropic import Anthropic  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

try:
    from wiki_api.librarian import _resolve_model  # noqa: E402
except ImportError:
    def _resolve_model(*env_keys: str, default: str) -> str:
        for key in env_keys:
            value = os.getenv(key)
            if value:
                return value
        return default

from wiki_api.wiki_store import WikiStore  # noqa: E402

SYSTEM = """You label FoodEx2 wiki page-selection gold cases.
Given the labeling rubric, the list of selectable wiki pages with their
descriptions, and one context-pack request, return the three-tier labels
this case SHOULD have. Work only from the rubric and page descriptions.
Return JSON only:
{"must_have": [...], "acceptable": [...], "must_not": [...], "reasoning": "..."}
Rules: page names must come from the provided list (globs like maintenance-*
allowed in must_not). Apply overlay exclusivity, maintenance/orientation
must_not, and the must_have bar: would a competent coder produce a wrong or
incomplete code without this page?"""


def label_case(client: Anthropic, model: str, rubric: str, catalog: str, case: dict) -> dict:
    prompt = json.dumps(
        {"rubric": rubric, "selectable_pages": catalog, "request": case["request"]},
        ensure_ascii=False,
    )
    response = client.messages.create(
        model=model, max_tokens=2000, system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])


def diff_labels(draft: dict, check: dict) -> dict:
    out = {}
    for tier in ("must_have", "must_not"):
        d, c = set(draft.get(tier, [])), set(check.get(tier, []))
        if d != c:
            out[tier] = {"draft_only": sorted(d - c), "crosscheck_only": sorted(c - d)}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-path", default="evals/selection/gold_cases.json")
    parser.add_argument("--model", default=None, help="Override; defaults to repo librarian model resolution.")
    args = parser.parse_args()

    model = args.model or _resolve_model("WIKI_LIBRARIAN_MODEL", default="claude-3-7-sonnet-latest")
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    store = WikiStore(str(REPO_ROOT))
    rubric = (REPO_ROOT / "evals/selection/README.md").read_text()
    catalog = "\n".join(
        f"- {n}: {store.read_page(n).select_when or store.read_page(n).summary}"
        for n in store.list_pages()
    )
    gold = json.loads(pathlib.Path(args.gold_path).read_text())
    targets = [c for c in gold["cases"] if not c.get("reviewed")]

    out_dir = REPO_ROOT / "reports" / "gold-crosscheck" / dt.date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    all_checks, agreements, disagreements, errors = {}, [], [], []
    for case in targets:
        try:
            check = label_case(client, model, rubric, catalog, case)
        except Exception as exc:  # noqa: BLE001 - keep the run alive on a single bad response
            errors.append((case["id"], str(exc)))
            print(f"{case['id']}: ERROR — needs manual look ({exc})")
            continue
        all_checks[case["id"]] = check
        delta = diff_labels(case["labels"], check)
        if delta:
            disagreements.append((case["id"], delta, check.get("reasoning", "")))
        else:
            agreements.append(case["id"])
        print(f"{case['id']}: {'AGREE' if not delta else 'DISAGREE ' + json.dumps(delta, ensure_ascii=False)}")

    (out_dir / "crosscheck_labels.json").write_text(json.dumps(all_checks, ensure_ascii=False, indent=2))
    lines = [f"# Gold cross-check {dt.date.today().isoformat()} (model: {model})", "",
             f"Agreements ({len(agreements)}): {', '.join(agreements)}", "", "## Disagreements — David to resolve", ""]
    for cid, delta, why in disagreements:
        lines += [f"### {cid}", f"- delta: `{json.dumps(delta, ensure_ascii=False)}`", f"- cross-check reasoning: {why}", ""]
    if errors:
        lines += ["## Errors — needs manual look", ""]
        for cid, err in errors:
            lines += [f"### {cid}", f"- error: `{err}`", ""]
    (out_dir / "report.md").write_text("\n".join(lines))
    print(f"\n{len(agreements)} agree / {len(disagreements)} disagree / {len(errors)} error -> {out_dir}/report.md")


if __name__ == "__main__":
    main()
