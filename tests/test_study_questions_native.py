"""Native-domain integration; all numerical inputs are hypothetical."""
import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_study_questions_v2 import example as legacy_example
from test_study_questions_v2 import execute

from anibench.cross_domain_collection_v1 import (
    compile_cross_domain_collection,
    evaluate_cross_domain_collection,
)
from anibench.question_routes_v1 import digest
from anibench.study_questions_v2 import StudyQuestionError

ROOT = Path(__file__).resolve().parents[1]


def native_example():
    payload = json.loads((ROOT / 'examples/cross_domain_collection/input.json').read_text())
    definitions = [
        ('digital_state', 'Activity resolution', ['observer_state']),
        ('cognitive_state', 'Reaction-time resolution', ['function_state']),
        ('individual_change', 'Individual change', ['observer_individual_change', 'function_individual_change']),
        ('population_change', 'Population change', ['observer_mean_change', 'function_mean_change']),
        ('linked_change', 'Linked activity and reaction-time change', ['observer_function_change_relation']),
        ('exposure_response', 'Exposure-aligned change', ['exposure_aligned_function_change']),
        ('controlled_effect', 'Controlled effect', ['controlled_function_effect']),
    ]
    profile = {
        'contract': 'anibench.study-question-profile.v2',
        'profile_id': 'hypothetical-activity-cognition-integration.v1',
        'scope': 'One source-inspired hypothetical question; not a UKB score or adopted broad reference',
        'selection_rationale': 'Checks linked digital and independently measured cognitive observations',
        'weighting_rationale': 'One fixed question budget per category, no overall aggregate',
        'questions': [{'question_id': 'activity_cognition', 'biological_identity': 'activity-reaction-two-occasion',
                       'engine': 'cross_domain_collection', 'definition': payload['question']}],
        'categories': [
            {'category_id': key, 'label': label, 'question': payload['question']['question'],
             'questions': [{'question_id': 'activity_cognition', 'outcomes': outcomes, 'weight': 1}]}
            for key, label, outcomes in definitions],
        'scenarios': [{'scenario_id': 'reference', 'rationale': 'Unchanged illustrative additive Gaussian reference',
                       'paired_biological_covariance': {'activity_cognition': payload['scenario']['biological_covariance']}}],
    }
    request = {'contract': 'anibench.study-questions-request.v2', 'profile_sha256': digest(profile),
               'study_id': 'hypothetical_activity_cognition', 'lifecycle': 'hypothetical',
               'scenarios': [{'scenario_id': 'reference', 'inputs': {'activity_cognition': payload}}]}
    return deepcopy(profile), deepcopy(request)


def categories(result):
    return {row['category_id']: row for row in result['scenarios'][0]['categories']}


def test_native_results_match_original_engine_and_keep_domains():
    p, r = native_example()
    before = deepcopy((p, r))
    result = execute(p, r)
    assert (p, r) == before
    original = evaluate_cross_domain_collection(r['scenarios'][0]['inputs']['activity_cognition'])
    assert result['scenarios'][0]['questions']['activity_cognition']['receipt'] == original
    assert result['contract'] == 'anibench.study-questions-result.v2'
    assert {x['biological_domain'] for x in original['native_coordinates']} == {'digital', 'cognitive'}
    for key, row in categories(result).items():
        expected = 0 if key in {'controlled_effect', 'exposure_response'} else 100
        assert row['passed_percent'] == row['upper_percent'] == expected
    assert result['robust_reference_attainment'] == 'not_attained'
    assert result['public_rank_emission_permitted'] is False




@pytest.mark.parametrize('omission', ['question', 'function', 'followup', 'linkage', 'noise'])
def test_missing_native_evidence_is_not_fabricated(omission):
    p, r = native_example()
    inputs = r['scenarios'][0]['inputs']
    payload = inputs['activity_cognition']
    if omission == 'question':
        inputs.clear()
    elif omission == 'function':
        payload['design']['support']['independently_measured_function'] = False
    elif omission == 'followup':
        payload['design']['patterns'][0]['acquisitions'] = [
            a for a in payload['design']['patterns'][0]['acquisitions'] if a['occasion_index'] == 0]
    elif omission == 'linkage':
        payload['design']['support']['cross_domain_linkage'] = False
    else:
        payload['scenario']['measurement_error_covariance'] = None
    rows = categories(execute(p, r))
    if omission in {'question', 'noise'}:
        assert rows['individual_change']['unknown_weight'] == 1
        assert rows['individual_change']['passed_percent'] == 0
        assert rows['individual_change']['upper_percent'] == 100
    else:
        assert rows['linked_change']['passed_percent'] == rows['linked_change']['upper_percent'] == 0
        if omission == 'followup':
            assert rows['digital_state']['passed_percent'] == 100


def test_people_improve_population_precision_not_per_person_measurement():
    p, r = native_example()
    large = categories(execute(p, r))
    design = r['scenarios'][0]['inputs']['activity_cognition']['design']
    design['n_people'] = design['patterns'][0]['n_people'] = 2
    small = categories(execute(p, r))
    # Supporting-person provenance changes; individual resolution does not.
    for category in ('digital_state', 'individual_change'):
        for metric in ('passed_percent', 'upper_percent', 'precision_toward_targets'):
            assert small[category][metric] == large[category][metric]
    assert small['population_change']['passed_percent'] < large['population_change']['passed_percent']
    assert small['linked_change']['precision_toward_targets']['lower_percent'] < large['linked_change']['precision_toward_targets']['lower_percent']


def test_native_duplicates_and_metadata_do_not_change_categories():
    p, r = native_example()
    expected = categories(execute(p, r))
    design = r['scenarios'][0]['inputs']['activity_cognition']['design']
    design['patterns'][0]['acquisitions'] *= 50
    design['metadata'] = {'ethics': 'approved', 'published': True, 'cost': 1e9, 'name': 'favored'}
    assert categories(execute(p, r)) == expected


@pytest.mark.parametrize('mutation', ['legacy_copy', 'native_relabel'])
def test_equivalent_native_and_legacy_questions_cannot_add_votes(mutation):
    p, r = native_example()
    clone = deepcopy(p['questions'][0])
    clone.update(question_id='renamed', biological_identity='different-label')
    if mutation == 'legacy_copy':
        _, compiled = compile_cross_domain_collection(r['scenarios'][0]['inputs']['activity_cognition'])
        clone.update(engine='paired_collection', definition=compiled['question'])
    else:
        clone['definition']['coordinates'][0]['biological_domain'] = 'neural'
        clone['definition']['question_id'] = 'another-name'
        clone['definition']['tolerances']['observer_state'] = [300]
    p['questions'].append(clone)
    with pytest.raises(StudyQuestionError, match='equivalent question'):
        execute(p, r)


@pytest.mark.parametrize('mutation', ['old_profile', 'old_request', 'wrong_outcome', 'stale_hash', 'missing_reference'])
def test_explicit_native_contracts_required(mutation):
    p, r = native_example()
    if mutation == 'old_profile':
        p['contract'] = 'anibench.study-question-profile.v1'
    elif mutation == 'old_request':
        r['contract'] = 'anibench.study-questions-request.v1'
    elif mutation == 'wrong_outcome':
        p['categories'][0]['questions'][0]['outcomes'] = ['molecular_state']
    elif mutation == 'stale_hash':
        r['scenarios'][0]['inputs']['activity_cognition']['design']['question_sha256'] = 'sha256:' + '0' * 64
    else:
        p['scenarios'][0]['paired_biological_covariance'] = {}
    with pytest.raises(ValueError):
        execute(p, r)


def test_native_templates_cannot_reuse_route_physical_ids():
    p, r = native_example()
    legacy_p, legacy_r = legacy_example()
    p['questions'].append(legacy_p['questions'][0])
    p['categories'][0]['questions'].append({'question_id': 'route', 'outcomes': ['target'], 'weight': 1})
    route = legacy_r['scenarios'][0]['inputs']['route']
    r['scenarios'][0]['inputs']['route'] = route
    r['scenarios'][0]['inputs']['activity_cognition']['design']['patterns'][0]['acquisitions'][0]['physical_id'] = route['observations'][0]['physical_acquisition_id']
    with pytest.raises(StudyQuestionError, match='template mapping'):
        execute(p, r)


def test_native_geometry_cannot_change_inside_uncertainty_envelope():
    p, r = native_example()
    p['scenarios'].append({**deepcopy(p['scenarios'][0]), 'scenario_id': 'other'})
    r['scenarios'].append({**deepcopy(r['scenarios'][0]), 'scenario_id': 'other'})
    design = r['scenarios'][1]['inputs']['activity_cognition']['design']
    design['n_people'] = design['patterns'][0]['n_people'] = 2
    with pytest.raises(StudyQuestionError, match='separate design'):
        execute(p, r)
