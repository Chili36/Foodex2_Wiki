# Page-Selection Gold Set

Ground truth for measuring the `/wiki/context-pack` page selector. Each case is a
real context-pack request plus three-tier page labels. The scorer
(`wiki_api/selection_scoring.py`) compares the pages a run selected against these
labels to produce recall, precision, and leak metrics.

`gold_cases.json` shape: `{"version": 1, "cases": [ ... ]}`.

All cases in this seed are drafts (`"reviewed": false`) awaiting David's sign-off.
The runner exposes `--only-reviewed` to score the trusted subset.

## Case Schema

```json
{
  "id": "SEL-0001",
  "source": "wiki_ask_10_tests_2026-06-19:EFSA-TD-0001",   // or "synthetic"
  "reviewed": false,
  "request": {
    "search_term": "Bordsdruvor – färsk frukt (table grapes, fresh fruit)",
    "deconstructed_query": {"food": "table grapes", "state": "fresh"},
    "context": {"reporting_domain": "pesticides"},          // {} when no domain signal
    "candidate_hints": [],                                   // objects {code, name, termType}
    "max_pages": 7
  },
  "labels": {
    "must_have":  ["base-term-selection.md", "pesticides-foodex2.md", "term-type-facet-constraints.md"],
    "acceptable": ["facet-coding-rules.md", "implicit-vs-explicit-facets.md", "..."],
    "must_not":   ["contaminants-foodex2.md", "vmpr-foodex2.md", "maintenance-*", "README.md"],
    "notes": "Justification citing the rubric rule(s) below."
  }
}
```

Conventions:

- `index.md` and `RUNTIME_RULES.md` are excluded from scoring (always present by
  construction) — do **not** label them.
- `must_not` entries support `fnmatch` globs (e.g. `maintenance-*`).
- A selected page that appears in no tier is counted as `unlabeled` (a label gap to
  triage), not an automatic error.
- `candidate_hints` `termType` follows the FoodEx2 term-type codes verified in
  `term-type-facet-constraints.md`: `r` raw commodity, `d` derivative, `c` composite,
  `s` simple composite, `f` facet term (`h`/`g` hierarchy/group, `n` non-specific).

## Labeling Rubric

Labels are derived from category policy plus case facts — you do not need to be a
FoodEx2 sage to label a case.

1. **Code-construction case** (the downstream caller will build a code — true for all
   DMT context-pack calls): `must_have` includes `base-term-selection.md`, at least one
   facet page (`facet-coding-rules.md` or `implicit-vs-explicit-facets.md`), and at least
   one validation page (`term-type-facet-constraints.md` by default;
   `process-validation-rules.md` when the food is processed).
2. **Domain overlays:** the overlay page for the case's explicit domain is `must_have`;
   every *other* overlay page is `must_not`. If no domain signal exists, *all* overlay
   pages are `must_not` (all-domain default). The exclusivity-bound overlay set is
   `pesticides-foodex2.md`, `contaminants-foodex2.md`, `vmpr-foodex2.md`,
   `vmpr-legislative-mapping.md`, and `additives-flavourings-foodex2.md` (per
   `WIKI_ARCHITECTURE_FOR_MODELS.md`'s Domain Overlay Pages list), plus
   `domoic-acid-scallops.md`, which `README.md`/`SCHEMA.md` classify as a niche overlay.
   `chemical-monitoring-foodex2.md` (the routing entry page) and
   `domain-specific-validation.md` (treated as a validation page, not exclusivity-bound)
   are deliberately not subject to this exclusivity rule: `chemical-monitoring-foodex2.md`
   is `acceptable` in domain cases but `must_not` when there is no domain signal.
3. **Maintenance pages:** `must_not` (glob `maintenance-*`) unless the question is
   explicitly about annual changes.
4. **Orientation pages:** always `must_not` in context-pack cases (`README.md`,
   `PROJECT_CONTEXT.md`, `KNOWLEDGE_ARCHITECTURE.md`, `WIKI_ARCHITECTURE_FOR_MODELS.md`,
   `INGEST_WORKFLOW.md`, `MAINTENANCE_WORKFLOW.md`, `SCHEMA.md`, `log.md`).
5. **Case-fact adjustments:** packaging mentioned → `packaging-facets.md` must-have;
   mixed/composite food → `ingredient-facets.md` must-have; processing/treatment mentioned
   → `process-facets.md` must-have (and `process-validation-rules.md` as the validation
   page); derivative needing a source facet → `implicit-vs-explicit-facets.md` must-have;
   and so on.
6. **The tier-decision question:** when unsure between `must_have` and `acceptable`, ask:
   *would a competent coder produce a wrong or incomplete code without this page?* Yes →
   `must_have`. No, but it is on-topic → `acceptable`. This modulates rule 1: for a plain
   raw commodity whose facets are implicit (e.g. fresh whole fruit), the generic facet
   page drops to `acceptable`, so `must_have` is `base-term-selection.md` + the domain
   overlay (if any) + the validation page — matching the SEL-0001 worked example.

## Consistency Invariants (mechanical)

- Exactly one domain overlay is `must_have` when the domain is explicit; all overlays are
  `must_not` when there is no domain signal.
- `maintenance-*` and orientation pages are `must_not` in every case (no annual-change
  cases in this seed).
- No non-glob `must_have` or `acceptable` page may match any `must_not` glob in the same
  case (overlap makes scores silently confusing).
- Every labeled non-glob page must exist as a served page (`raw/efsa-guidance/*.md` or a
  root `*.md`).
