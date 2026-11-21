from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import wiki_api.app as app
import wiki_api.jev_selector as jev
from wiki_api.librarian import (
    AnthropicWikiPageSelector, JsonWikiPageSelector, infer_model_provider,
    resolve_selector_model,
)
from wiki_api.wiki_store import WikiStore

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    for name in ('WIKI_CONTEXT_MODEL', 'WIKI_LIBRARIAN_MODEL', 'WIKI_LLM_PROVIDER',
                 'LLM_PROVIDER', 'WIKI_LMSTUDIO_MODEL', 'LMSTUDIO_MODEL',
                 'TYPESAFE_API_KEY', 'ANTHROPIC_API_KEY'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(app, 'selector_runner', None)
    monkeypatch.setattr(app, 'ask_selector_runner', None)


def mock_service(monkeypatch, scores=None):
    calls = []
    monkeypatch.setenv('TYPESAFE_API_KEY', 'test-only-key')
    def post(**kwargs):
        calls.append(kwargs)
        body = kwargs['payload']
        return {
            'model': 'jev-1.13.0',
            'answers': {key: {'type': 'score', 'score': (scores or {}).get(
                q['instructions']['page']['filename'], 0)} for key, q in body['questions'].items()},
            'usage': {'input_tokens': 9123, 'output_tokens': 362},
        }
    monkeypatch.setattr(jev, '_http_post_json', post)
    return calls


def test_default_and_model_overrides(monkeypatch):
    assert resolve_selector_model() == 'jev-1.13.0'
    assert infer_model_provider('jev-latest') == 'typesafe'
    assert isinstance(app.get_selector_runner(), jev.JevWikiPageSelector)
    assert isinstance(app.get_selector_runner(model='gpt-5.6-terra'), JsonWikiPageSelector)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-only-key')
    assert isinstance(app.get_selector_runner(model='claude-sonnet-5'), AnthropicWikiPageSelector)
    monkeypatch.setenv('WIKI_LIBRARIAN_MODEL', 'claude-sonnet-5')
    assert resolve_selector_model() == 'claude-sonnet-5'
    monkeypatch.setenv('WIKI_CONTEXT_MODEL', 'jev-latest')
    assert resolve_selector_model() == 'jev-latest'
    assert resolve_selector_model('gemini-3.5-flash') == 'gemini-3.5-flash'


def test_env_hosted_override_routes_without_anthropic_key(monkeypatch):
    monkeypatch.setenv('WIKI_CONTEXT_MODEL', 'gpt-5.6-terra')
    assert isinstance(app.get_selector_runner(), JsonWikiPageSelector)


def test_global_local_routing_is_preserved(monkeypatch):
    monkeypatch.setenv('WIKI_LLM_PROVIDER', 'lmstudio')
    monkeypatch.setenv('WIKI_LMSTUDIO_MODEL', 'local-model')
    selector = app.get_selector_runner()
    assert isinstance(selector, AnthropicWikiPageSelector)
    assert selector.model == 'local-model'


def test_ranking_threshold_caps_usage_and_scopes(monkeypatch):
    calls = mock_service(monkeypatch, {'packaging-facets.md': 3, 'ingredient-facets.md': 2,
                                     'base-term-selection.md': 1.05, 'process-facets.md': 1.04})
    coding = app.get_selector_runner()
    ask = app.get_selector_runner(scope='ask')
    assert coding is not ask
    coding.max_pages = 3
    result = coding.run({'search_term': 'packed food'})
    assert result.pages_used == ['index.md', 'packaging-facets.md', 'ingredient-facets.md']
    assert result.token_summary['input_tokens'] == 9123
    assert result.token_summary['output_tokens'] == 362
    assert result.token_summary['model'] == 'jev-1.13.0'
    assert result.timing_summary['calls'] == 1
    assert calls[0]['url'] == 'https://api.typesafe.ai/v1/systemone'
    assert calls[0]['headers'] == {'Authorization': 'Bearer test-only-key'}
    assert calls[0]['payload']['state']['mode'] == 'coding'
    assert calls[0]['payload']['model'] == 'jev-1.13.0'
    ask.max_pages = 3
    result = ask.run({'search_term': 'packed food'})
    assert result.pages_used == ['packaging-facets.md', 'ingredient-facets.md', 'base-term-selection.md']
    assert calls[1]['payload']['state']['mode'] == 'ask'
    assert coding.catalog_scope == 'coding'
    assert app.get_selector_runner() is coding


@pytest.mark.parametrize('score', [None, True, '3', -1, 3.1, float('nan'), float('inf')])
def test_rejects_invalid_scores(score):
    with pytest.raises(ValueError, match='invalid page score'):
        jev.ranked_pages({'answers': {'p': {'type': 'score', 'score': score}}}, {'p': 'a.md'})


@pytest.mark.parametrize('answers', [{}, {'unexpected': {'type': 'score', 'score': 3}}, None])
def test_rejects_missing_or_unknown_question_ids(answers):
    with pytest.raises(ValueError, match='question IDs'):
        jev.ranked_pages({'answers': answers}, {'p': 'a.md'})


def test_empty_selection_is_valid_and_ties_are_stable():
    mapping = {'p1': 'z.md', 'p2': 'a.md'}
    def response(score):
        return {'answers': {k: {'type': 'score', 'score': score} for k in mapping}}
    assert jev.ranked_pages(response(0), mapping) == []
    assert jev.ranked_pages(response(3), mapping) == ['a.md', 'z.md']


def test_context_endpoint_keeps_structural_policy_and_cap(monkeypatch):
    mock_service(monkeypatch, {'packaging-facets.md': 3})
    response = TestClient(app.app).post('/wiki/context-pack', json={'search_term': 'packed food', 'max_pages': 7})
    assert response.status_code == 200
    data = response.json()
    assert 'RUNTIME_RULES.md' in data['pages_used']
    assert 'base-term-selection.md' in data['pages_used']
    assert 'packaging-facets.md' in data['pages_used']
    assert len(data['pages_used']) <= 7


def test_missing_key_is_actionable_503():
    response = TestClient(app.app).post('/wiki/context-pack', json={'search_term': 'food'})
    assert response.status_code == 503
    assert 'TYPESAFE_API_KEY' in response.json()['detail']


def test_provider_failure_is_sanitized(monkeypatch):
    monkeypatch.setenv('TYPESAFE_API_KEY', 'secret-test-key')
    def fail(**kwargs):
        raise RuntimeError('upstream body secret-test-key')
    monkeypatch.setattr(jev, '_http_post_json', fail)
    response = TestClient(app.app).post('/wiki/context-pack', json={'search_term': 'food'})
    assert response.status_code == 503
    assert response.json()['detail'] == 'TypeSafe page selection request failed'
    assert 'secret-test-key' not in response.text


def test_ask_selection_can_pick_maintenance_without_writing_answers(monkeypatch):
    calls = mock_service(monkeypatch, {'maintenance-2024.md': 3})
    response = TestClient(app.app).post('/wiki/ask/select-pages', json={
        'question': 'What changed in the 2024 maintenance?', 'max_pages': 1,
    })
    assert response.status_code == 200
    assert response.json()['pages_used'] == ['maintenance-2024.md']
    assert len(calls) == 1
    assert calls[0]['payload']['state']['mode'] == 'ask'


def test_invalid_provider_result_is_a_503(monkeypatch):
    monkeypatch.setenv('TYPESAFE_API_KEY', 'test-only-key')
    monkeypatch.setattr(jev, '_http_post_json', lambda **kwargs: {'answers': {}})
    response = TestClient(app.app).post('/wiki/ask/select-pages', json={'question': 'food'})
    assert response.status_code == 503
    assert 'question IDs' in response.json()['detail']
