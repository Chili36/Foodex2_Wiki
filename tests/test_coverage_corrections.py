"""Guard retrieval-visible corrections and the source distinctions they preserve."""
import json
from pathlib import Path

from wiki_api.wiki_store import WikiStore

ROOT = Path(__file__).resolve().parents[1]


def projected(name):
    store = WikiStore(ROOT)
    return store.prompt_content_for_context_pack(store.read_page(name))


def test_vmpr_corrected_codes_reach_prompt_context():
    text = projected('vmpr-foodex2.md')
    assert 'dairy/reproductive goat feed (`A18EY`)' in text
    assert 'kid feed (`A18EX`)' in text
    assert 'A0F1J#F01.A0CDD$F27.A01ZQ' in text
    record = json.loads((ROOT / 'reports/source-coverage/2026-09-30-catalogue-check.json').read_text())
    children = {r['term_code']: r['extended_name'] for r in record['terms'] if r['parent_code'] == 'A07VF'}
    assert children['A18EY'] == 'Dairy/reproductive goat feed'
    assert children['A18EX'] == 'Kids reared for reproduction or meat production feed'


def test_contaminant_recommendations_are_retrievable_without_becoming_universal():
    text = projected('contaminants-foodex2.md')
    for term in ('CHEMON18', 'CHEMON19', 'CHEMON15', 'CHEMON17', 'Hijiki', 'excluding muesli and porridge'):
        assert term in text
    assert 'not universal requirements or automatic grounds for rejecting' in text
    assert 'Retain the mandatory acrylamide `F33` requirement separately' in text
    assert 'do not justify inventing' in text


def test_additives_categories_and_nonimplicit_condition_survive_projection():
    text = projected('additives-flavourings-foodex2.md')
    assert 'highly recommended when not already implicit' in text
    for category in ('1', '6.3', '12.5', '12.6', '13', '14.1.2', '14.1.3', '14.1.4', '14.1.5', '17'):
        assert f'| {category} |' in text


def test_lifecycle_scope_does_not_disable_br21():
    text = projected('business-rules.md')
    assert 'a `BR21` dismissal result remains a blocking error' in text
    assert 'dismissed in one hierarchy can remain reportable in another' in text
    assert 'must not be bypassed' in text
    assert 'deprecated and dismissed terms are always invalid' not in projected('validation-rules.md')


def test_reference_definitions_reach_prompt_context():
    overview = projected('foodex2-overview.md')
    for code in 'HCEMP':
        assert f'| `{code}` |' in overview
    facets = projected('facet-coding-rules.md')
    for code in ('F08', 'F12', 'F22'):
        assert f'| `{code}` |' in facets


def test_resolution_evidence_still_exists_in_the_wiki():
    store = WikiStore(ROOT)
    audit = json.loads((ROOT / 'docs/source-coverage.json').read_text())
    assert len(audit['findings']) == 11
    for finding in audit['findings']:
        assert finding['status'] == 'resolved'
        for evidence in finding['resolution_evidence']:
            assert evidence['quote'] in store.read_page(evidence['page']).body
