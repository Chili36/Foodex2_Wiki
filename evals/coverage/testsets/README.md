# Versioned coverage testsets

Files in this directory are generated deliberately from authoritative source chunks
with `generate.py` and committed. Human review is not required: an automated claim gate
keeps only decision-relevant operational, structural, and exception facts with mechanically
verified source evidence, and a second gate rejects quote-, citation-, footnote-, and
example-recall questions. Exclusions remain auditable but stay outside the denominator.

Never synthesize a replacement question from wiki content when a source is missing.
Create a new testset file only when a source revision changes; retain older files for
comparison.
