# FoodEx2 Harmonization Paper: Learning For DMT Tests

Source: `/Users/davidfoster/Downloads/nutrients-16-01065.pdf`

Extracted text: `reports/dmt-foodex2-paper/nutrients-16-01065.txt`

Paper: D'Addezio et al., "FoodEx2 Harmonization of the Food Consumption Database from the Italian IV SCAI Children's Survey", Nutrients 2024, 16, 1065.

## Why This Paper Matters

This paper is a strong test source for DMT because it describes real FoodEx2 coding work on a national children’s food-consumption database, including concrete constructed FoodEx2 strings. It is especially relevant to our current problem because many examples are not base-term-only cases. They require candidate recall across base terms and facet descriptors.

Important boundary: this is a consumption-data paper, not a monitoring-data paper. The examples describe foods as consumed in a dietary survey workflow. They should not be treated as monitoring-domain gold codes, pesticide/contaminants/VMPR guidance, or evidence about sample-taking rules. Their value for DMT is as facet-heavy FoodEx2 construction and retrieval probes.

The paper reports that 1514 unique FoodEx2 codes were used for 2022 original food-list items, and 1183 of those unique codes were complex codes with at least one facet. This supports our suspicion that a useful tool cannot stop after finding a plausible base term.

## Main Learning

1. Consumption-database coding is facet-heavy.

   Complex codes dominated the IV SCAI children’s survey database. Infant foods, breakfast cereals, bakery products, dairy products, fruit juices, and supplements frequently required F04, F09, F10, F03, F07, F18, F20, F21, F27, or F28.

2. The base term still comes first, but the hard work is often fact coverage.

   The paper repeats the FoodEx2 principle that the first coding question is the degree of processing. But the examples show that, after the base term is selected, the coder often needs to preserve label-level facts such as fortification, flavor, fat percentage, packaging, organic production, physical state, and characterising ingredients.

3. DMT is likely useful if it can retrieve both base and facet building blocks.

   A simple vector matcher that returns only one base term will fail many examples from this paper. A useful DMT flow should retrieve candidate base terms and candidate facet descriptors, then let a classifier construct and validate the final code.

4. DMT should be tested for candidate recall, not only final answer exactness.

   Many examples depend on retrieving specific descriptor codes, such as F09 vitamins/minerals, F10 fortified, F07 fat percentage, F03 liquid/powder/tablets, F18 jar, F06 surrounding medium, and F20 without peel/surrounding medium.

5. Consumption examples are useful probes, but not monitoring authority.

   The paper gives example codes from a dietary-survey workflow. It does not teach every legality boundary, nor does it define how a monitoring sample should be reported. The wiki/validator still needs to decide whether the same facet use is legal and appropriate in a new reporting context.

6. Recipe aggregation is a domain/workflow decision.

   The paper explains that many composite dishes were disaggregated, but some categories were aggregated into single foods for reporting: traditional cakes/pies/biscuits/pastries, fruit mousses/smoothies, dairy desserts, pizza bases, pasta doughs, and sauces/gravies. DMT could help identify the correct FoodEx2 term, but the caller must know whether the workflow wants recipe disaggregation or aggregate consumed-food coding.

## DMT Usefulness Hypothesis

DMT should be useful here if it can:

- retrieve exact or near-exact base terms from natural food descriptions
- retrieve facet descriptors across multiple facet families
- keep candidate lists broad enough for multi-facet construction
- expose term type and facet family so the classifier does not put a descriptor under the wrong facet
- support candidate recall tests where the expected base and expected facet codes must appear in the retrieved candidate set

DMT will be less useful if it:

- returns only the most likely single matrix code
- hides facet terms from the classifier
- over-prioritizes semantically similar base terms and misses facet descriptors
- cannot distinguish F04 ingredient, F09 fortification agent, F10 qualitative info, F07 fat content, and F03 physical state

## Recommended Evaluation Shape

For each test case:

1. Send the natural-language `input`.
2. Ask DMT candidate retrieval for a larger result set, e.g. top 40-80, not top 10.
3. Check whether the expected base term appears.
4. Check whether the expected facet descriptor codes appear.
5. Let the classifier construct the code only after candidate recall is adequate.
6. Validate the constructed code.
7. Score separately:
   - base recall
   - facet recall
   - correct facet-family placement
   - final code exactness
   - acceptable alternative handling

## High-Value Test Themes

- Fortified branded products: breakfast cereal, infant formula, flavoured milk.
- Infant/baby foods: formula, baby meals, baby cereal, fruit juices, organic baby foods.
- Supplements: vitamin-only, mineral-only, mixed vitamin/mineral, probiotic/prebiotic, physical state.
- Dairy products: lactose free, low fat, exact fat percentage, multiple milk sources, flavour ingredients.
- Processed vegetables/fruits: canned, surrounding medium, without peel, generic processed base plus source facet.
- Consumption-occasion processing: boiled vegetables, grilled meat, breaded/deep-fried fish.
- Composite or recipe aggregation: pizza dough, tiramisu, ready-to-eat child meal.

## Candidate-Recall Smoke Test

The DMT backend was not running locally on port 8000, so the smoke test queried the underlying Qdrant matrix collection directly. The collection name contains `monitoring`, but this test is not asserting monitoring-domain behavior; it is using the available FoodEx2 matrix catalogue index to test candidate recall for consumption-derived examples:

- Collection: `mtx_monitoring_openai_current`
- Embedding model: `text-embedding-3-large`
- Test cases: 26
- Expected base/facet codes: 99

Results:

| Retrieval mode | Expected codes found | Cases with all expected codes | Cases where base was found |
| --- | ---: | ---: | ---: |
| Single natural-language query, top 80 | 56 / 99 | 8 / 26 | 25 / 26 |
| Component queries, top 20 per component | 98 / 99 | 25 / 26 | 26 / 26 |

Interpretation:

- DMT-style candidate retrieval is useful, but not as a single-query search for the whole food string.
- The matrix collection usually finds the base term, but single-query retrieval misses many facet descriptors.
- A deconstruction step that searches the base and each meaningful source fact separately makes the tool dramatically more useful.
- The only component-level miss was `A07SH` in the cooked poultry slices example, because the article's descriptor is not self-explanatory in the test-case text and needs catalogue context.

This supports a DMT workflow shaped like:

`source text -> fact deconstruction -> base candidate search + per-fact facet candidate searches -> wiki guidance/context -> classifier -> validator`

It does not support a workflow shaped like:

`source text -> one vector search -> choose one code`
