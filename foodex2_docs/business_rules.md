# FoodEx2 Business Rules

## Overview

The FoodEx2 validator implements `BR01`-`BR31` to enforce EFSA-oriented coding constraints. These rules cover:

- term-type compatibility
- facet legality
- hierarchy and source relationships
- process conflicts
- structural validity

For validation, severities collapse into four practical categories:

- `ERROR`: blocking error, validation fails
- `HIGH`: hard warning, validation fails
- `LOW`: soft warning, validation passes with advisory review
- `NONE`: informational only

## Severity Classification

| Severity | Validation impact | Business rules |
| --- | --- | --- |
| `ERROR` | Blocking, validation fails | `BR17`, `BR19`, `BR20`, `BR21`, `BR25`, `BR29`, `BR30`, `BR31` |
| `HIGH` | Blocking, validation fails | `BR01`, `BR03`, `BR04`, `BR05`, `BR06`, `BR07`, `BR08`, `BR13`, `BR14`, `BR16`, `BR24`, `BR26`, `BR27`, `BR28` |
| `LOW` | Soft warning, validation passes | `BR10`, `BR11`, `BR12`, `BR15`, `BR23` |
| `NONE` | Informational only | `BR22` |

`BR02`, `BR09`, and `BR18` are placeholders and are not implemented.

## Term Types

| Term type | Meaning |
| --- | --- |
| `r` | Raw commodity |
| `d` | Derivative |
| `c` | Composite / aggregated |
| `s` | Simple composite |
| `f` | Facet descriptor |
| `g` | Generic / group term |
| `h` | Hierarchy term |
| `n` | Non-specific term |

## Common Facet Categories

| Facet | Meaning |
| --- | --- |
| `F01` | Source |
| `F03` | Physical state |
| `F04` | Ingredient |
| `F27` | Source commodities |
| `F28` | Process |

## Business Rules

### BR01: Source Commodity Validation for Raw Terms

- Severity: `HIGH`
- Applies to: raw commodity terms (`r`) with explicit `F27`
- Rule: explicit `F27` must be:
  - a child of an already implicit `F27`, or
  - a child of the base term itself
- Example:
  - Invalid: `A0EZJ#F27.A000J`
  - Valid: `A0EZJ#F27.A0EZK`
- Purpose: prevents illogical source specifications on raw foods

### BR02

- Status: placeholder, not implemented

### BR03: No Source Facet in Composite Foods

- Severity: `HIGH`
- Applies to: composite terms (`c`, `s`)
- Rule: `F01` cannot be used with composite foods; use `F04` instead
- Example:
  - Invalid: `A000J#F01.A0F6E`
  - Valid: `A000J#F04.A0F6E`
- Purpose: composites have ingredients, not a single source

### BR04: No Source-Commodities in Composite Foods

- Severity: `HIGH`
- Applies to: composite terms (`c`, `s`)
- Rule: `F27` cannot be used with composite foods
- Example:
  - Invalid: `A02LS#F27.A0EZJ`
  - Valid: `A02LS#F04.A0EZJ`
- Purpose: composites have ingredients, not source commodities

### BR05: F27 Restrictions for Derivatives

- Severity: `HIGH`
- Applies to: derivative terms (`d`)
- Rule: explicit `F27` on derivatives must be more specific than implicit `F27`
- Example:
  - Base: `A0B6F` with implicit fruit-source logic
  - Invalid: `A0B6F#F27.A01BS`
  - Valid: `A0B6F#F27.A0EZJ`
- Purpose: preserves logical specialization of derivatives

### BR06: F01 Source Requires F27

- Severity: `HIGH`
- Applies to: derivative terms (`d`)
- Rule: `F01` can only be used when an `F27` source-commodity is present, implicit or explicit
- Example:
  - Invalid: generic derivative + `F01` with no `F27`
  - Valid: derivative with valid `F27` chain + `F01`
- Purpose: source animals or plants only make sense when source commodities are defined

### BR07: F01 for Single F27 Only

- Severity: `HIGH`
- Applies to: derivative terms (`d`)
- Rule: `F01` can only be used when exactly one `F27` is present
- Example:
  - Invalid: mixed fruit juice + `F01`
  - Valid: apple juice + `F01`
- Purpose: avoids assigning one source to a multi-commodity derivative

### BR08: Non-Reportable Terms Forbidden

- Severity: `HIGH`
- Applies to: all non-reportable terms
- Rule: terms must belong to the reporting hierarchy unless dismissed by another rule path
- Purpose: ensures only reportable terms are used

### BR09

- Status: placeholder, not implemented

### BR10: Non-Specific Terms Discouraged

- Severity: `LOW`
- Applies to: non-specific terms (`n`)
- Rule: non-specific base terms are discouraged
- Purpose: pushes coding toward more precise classification

### BR11: Generic Process Terms Discouraged

- Severity: `LOW`
- Applies to: `F28` process facets
- Rule: generic process terms such as broadly "processed" are discouraged
- Example:
  - Warning: `A0B9Z#F28.A07XS`
  - Better: `A0B9Z#F28.A07JS`
- Purpose: favors specific process reporting

### BR12: Ingredient Facet Restrictions

- Severity: `LOW`
- Applies to: raw (`r`) and derivative (`d`) terms
- Rule: `F04` should be used only for minor ingredients in these term types
- Example:
  - Warning: `A03NC#F04.A033J`
- Purpose: main components should use the proper source/origin model

### BR13: Physical State Creates Derivatives

- Severity: `HIGH`
- Applies to: raw commodity terms (`r`)
- Rule: `F03` cannot be applied to raw commodities because it creates a derivative
- Example:
  - Invalid: `A0EZJ#F03.A0BZS`
- Purpose: prevents raw terms from being used where a derivative should exist

### BR14: ICT/DCF Only Rule

- Severity: `HIGH`
- Applies to: special validation context
- Rule: certain checks activate only in ICT and DCF workflows

### BR15: DCF Only Rule

- Severity: `LOW`
- Applies to: DCF context only
- Rule: certain checks activate only in DCF workflows

### BR16: Process Detail Level Check

- Severity: `HIGH`
- Applies to: derivative terms (`d`)
- Rule: explicit process facets must not be less detailed than implicit ones
- Example:
  - Base: dried fruit with implicit drying
  - Invalid: adding a broader preserving process
  - Valid: adding a more specific drying subtype
- Purpose: avoids contradictory or weaker restatements of implicit process

### BR17: Facets as Base Terms Forbidden

- Severity: `ERROR`
- Applies to: facet terms (`f`)
- Rule: facet descriptors cannot be used as base terms
- Example:
  - Invalid: using "Frozen" as base term
  - Valid: use a food base term plus a frozen facet
- Purpose: facets are descriptors, not foods

### BR18

- Status: placeholder, not implemented

### BR19: Forbidden Processes on Raw Commodities

- Severity: `ERROR`
- Applies to: raw commodity terms (`r`)
- Rule: processes that create derivatives cannot be applied to raw commodities
- Example:
  - Invalid: `A000L#F28.A07LG`
  - Valid: use the flaked cereal derivative instead
- Purpose: certain processes fundamentally change the food nature

### BR20: Deprecated Terms

- Severity: `ERROR`
- Applies to: deprecated terms
- Rule: deprecated terms cannot be used

### BR21: Dismissed Terms

- Severity: `ERROR`
- Applies to: dismissed terms
- Rule: dismissed terms cannot be used

### BR22: Success Message

- Severity: `NONE`
- Type: informational
- Rule: confirmation that a valid base term was added

### BR23: Hierarchy Terms Discouraged

- Severity: `LOW`
- Applies to: hierarchy terms in the exposure hierarchy
- Rule: hierarchy terms as base terms are discouraged
- Purpose: encourages specific coding

### BR24: Non-Exposure Hierarchy Warning

- Severity: `HIGH`
- Applies to: hierarchy terms outside the exposure hierarchy
- Rule: these should not be used as base terms
- Purpose: only exposure hierarchy terms are suitable in those reporting cases

### BR25: Single Cardinality Enforcement

- Severity: `ERROR`
- Applies to: single-cardinality facet families
- Rule: only one explicit value is allowed for:
  - `F01`
  - `F02`
  - `F03`
  - `F07`
  - `F11`
  - `F22`
  - `F24`
  - `F26`
  - `F30`
  - `F32`
  - `F34`
- Example:
  - Invalid: `A0B9Z#F03.A0BZT#F03.A0BZU`
  - Valid: `A0B9Z#F03.A0BZT`

### BR26: Mutually Exclusive Processes

- Severity: `HIGH`
- Applies to: derivatives (`d`) with `F28`
- Rule: processes with the same ordinal code cannot be used together
- Example:
  - Invalid: flaking + grinding when both share ordinal `1`
- Purpose: same-group processes are alternatives, not cumulative states

### BR27: Decimal Ordcode Process Conflicts

- Severity: `HIGH`
- Applies to: derivative terms (`d`)
- Rule: decimal ordcodes within the same integer family also conflict
- Example:
  - Invalid: juicing + concentrating in the same derivative path
- Purpose: decimal branches represent distinct derivative routes

### BR28: Reconstitution Restrictions

- Severity: `HIGH`
- Applies to: dehydrated, concentrated, or powdered products
- Rule: reconstitution or dilution cannot be added to those terms; use the reconstituted product instead
- Example:
  - Invalid: milk powder + reconstitution process
- Purpose: reconstitution creates a different product identity

### BR29: Code Structure Validation

- Severity: `ERROR`
- Applies to: all codes
- Rule: code must follow the basic FoodEx2 pattern
- Valid examples:
  - `A0B9Z`
  - `A0B9Z#F28.A07JS`
  - `A0B9Z#F28.A07JS#F01.A0F6E`
- Invalid examples:
  - `INVALID`
  - `A0B9Z#F28`

### BR30: Invalid Facet Category

- Severity: `ERROR`
- Applies to: all facet codes
- Rule: facet category must exist
- Example:
  - Invalid: `A0B9Z#F99.A07JS`

### BR31: Facet Not in Category Hierarchy

- Severity: `ERROR`
- Applies to: all facet descriptors
- Rule: the descriptor must belong to the chosen facet category
- Example:
  - Invalid: `A0B9Z#F28.AAAAA`
  - Valid: `A0B9Z#F28.A07JS`

## Validation Examples

### Valid

- `A0B9Z`
- `A0B9Z#F28.A07JS`
- `A0BXM#F01.A0F6E`

### Invalid

- `A0EZJ#F03.A0BZS` (`BR13`)
- `A000J#F01.A0F6E` (`BR03`)
- `A03NC#F04.A033J` (`BR12`, warning)
- `DEPRECATED_TERM` (`BR20`)

## Best Practices

- Start with the correct base term.
- Understand term-type differences before adding facets.
- Use source, ingredient, and process facets for their intended roles.
- Respect single-cardinality limits.
- Check process compatibility before stacking `F28` facets.
- Validate incrementally while constructing codes.
