# Physical division and BR13 guidance repair

## Problem and reproduction

The ordinary ground-turmeric question caused `/wiki/ask` to recommend a powdered
or derivative base and, if none could be found, to declare the candidate set
incomplete. The selected pages already contained the marketed-dry spice
exception and the A07LA grinding entry. This was not a missing MCP connection or
a failure to retrieve that drying exception. The captured
[baseline](baseline.json) records the exact question, answer, six selected pages,
models and knowledge revision `sha256:8c03a062830c15d629ec71e10897a9ec83bb9f6971e342488208edf568e77bdb`.

## Source interpretation

- EFSA FoodEx2 revision 2 (2015), pp. 15–16 and 43–44, distinguishes physical
  division from production of recognised derivatives. Table 22 lists
  grinding/milling/crushing (A07LA) among processes normally applied directly to
  raw commodities, with exceptions where specific groups exist. Grain milling
  associated with separation uses specific grain-milling descriptors and
  derivative bases. The missing-specific-term example on p. 48 preserves the
  generic derivative route for quinoa flour.
- The same guidance, pp. 42–43, establishes the separate marketed-dry spice
  exception. Annual maintenance 2015, p. 15, preserves it for spices and herbal
  infusion materials while separating Camellia sinensis. The August correction
  remains valid.
- The inspected official [BR13 implementation](https://github.com/openefsa/catalogue-browser/blob/9a028ee0efe6a018e7f941ce0a4f7e6488b80e43/src/main/java/business_rules/TermRules.java#L403-L417)
  checks a raw base plus a forbidden physical-state descriptor. That rejection
  does not choose a replacement base. The seven forbidden F03 descriptors and
  the validator severity are unchanged by this repair.
- Norway's official [ground-turmeric entry](https://www.matvaretabellen.no/en/turmeric-ground/)
  corroborates raw turmeric A01AC with process F28.A07LA. It is a concrete
  application, not the authority for a new universal spice exception.
- A user-supplied excerpt attributed to an EFSA reply also described turmeric
  roots plus grinding when no powder term exists. The complete correspondence
  was not available or archived here; the repair relies on the independently
  inspected published guidance. It does not claim a fresh complete MTX audit.

The relevant foundational pages were read as text, and complete rendered pages
43 and 44 were inspected to verify Table 22's row and exception relationship.
The 2026 chemical-monitoring example on p. 37 also uses A07LA for powdered
migratory locust; it corroborates that this is not only a spice-specific issue.

## Root cause and history

The derivative examples were already conditional and illustrative. Commit
`ac23239` made that explicit in April. The problem was not that every mention
of milling mandated a derivative. Instead:

1. The wiki preserved a grinding code list without clearly preserving Table 22's
   general rule and its commodity-specific exceptions.
2. The BR13 worked example explicitly instructed readers to use a powdered or
   derivative base, overprescribing the repair. That wording was present before
   the August change.
3. Selection case SEL-0036 repeated that BR13 "forces" a derivative. It was a
   selection rubric, not a runtime instruction, but encoded the same error.
4. Commit `30c6020` correctly repaired marketed-dry status and BR19 repair
   reasoning on August 1. Its four drying/tea cases did not address grinding;
   the broader suite already contained the mislabelled ground-spice case.
5. Coding-context projection omitted both the worked example and the large
   appendix. Its apparently better outcome did not establish that it contained
   the full rule: the reproduced context did not contain A07LA at all.

## Repair and limits

The main process page now explains physical division versus derivative
production, including the F28 descriptor. Base selection preserves applicable
derivative precedence and distinguishes a missing specific term, a missing
search result and catalogue absence. BR13's title, operational reading and
worked example now separate facet rejection from food classification. A short
general clarification in runtime rules preserves this distinction without
embedding a spice exception or a turmeric demonstration in every prompt.

The detailed rule stays in normal prompt-visible sections, with updated page
selection summaries. Eight source-reviewed evaluation cases cover reproduction,
explicit catalogue fixtures, transfer and negative controls. The references were
written from sources before observing repaired answers. Keyword assertions are
smoke checks; semantic review must establish the actual decision and conditions.

The first live pass exposed an additional wording problem: one answer treated
the word "ground" like "powder" when discussing whether processing was known.
The process page now explicitly separates reported grinding from powder-only
physical-state evidence. All eight physical-division cases were rerun after
that refinement. The [answer review](answer-review.json) records the captured
answers and the limits of their ancillary advice, not just keyword scores.

This permits neither arbitrary processes on raw bases nor automatic replacement
of F03 powder with grinding. Unknown production remains unknown. An applicable
generic derivative still takes precedence over raw plus grinding when an exact
species-specific derivative is missing.

## Coverage audit reconciliation

The prior source snapshots are unchanged. The changed guidance pages were
reviewed against the existing findings COV-009, COV-010, M25-002 and M25-003:
lifecycle/reportability, Corex, infant/pig reportability and cooking details remain
intact. Every prior recorded resolution excerpt was rechecked in the revised
wiki. The coverage manifest adds the two concrete physical-division/BR13 findings
and records their resolutions; it does not claim an exhaustive corpus audit.

## Verification and refresh

Verification results and the curated-index refresh are recorded in
[validation.json](validation.json). The immutable source documents are unchanged,
so their separate source index does not need re-embedding. The curated Markdown
index must be re-embedded, obsolete chunks removed, and live drift checked.
Restarting the API refreshes cached selector/catalogue metadata; MCP clients use
that same service. No validator algorithm, answer-model prompt or MCP transport
change is part of this repair.

The standard indexer timed out on its third embedding batch after updating 89
chunks. A drift check identified only two stale pages. The refresh resumed with
the same embedding/chunking functions, one complete stale page per request,
retaining document context; obsolete IDs were then removed. The
[refresh record](index-refresh.json) captures the final zero-drift state.

The final page-selection run resolves all eight physical-division decisions,
and both drying/tea controls retain their expected distinction. The vector-only
`diverse_pages` run obtains the repaired grinding rule, including the supplied
turmeric code case, but remains less reliable as a complete brief: six of ten
queries retrieve an unrequested domain overlay. DIV-001 selects the base-term
decision section without the separate drying exception and ends with ambiguous
missing-candidate wording. Its keyword assertions pass, but semantic review
marks it partial. The failed retrieval-scope checks remain in the evidence;
this repair does not claim to resolve general RAG section coverage or domain
filtering. The MCP guidance tool uses the page-selection path.

The PR is isolated on a clean checkout of main. Local live checks use the
already-installed MCP pilot and the existing Jev/Sonnet 5.5 runtime; their
implementation and answer-model changes belong to separate work. Raw-source
documents and their existing index were not changed by this repair.
