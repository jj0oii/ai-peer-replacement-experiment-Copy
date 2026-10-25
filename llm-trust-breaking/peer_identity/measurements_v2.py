"""Version 2 measures; no inference, repairs, or hidden treatment cues."""
import copy

VERSION = 'publicgoods-peer-identity-v2'
TRUST_ANCHORS = ('1: Completely untrustworthy; strong expectation of dishonesty or defection. '
 '2: Extremely untrustworthy. 3: Very untrustworthy. 4: Somewhat untrustworthy. '
 '5: Slightly untrustworthy or uncertain. 6: Slightly trustworthy, but with reservations. '
 '7: Moderately trustworthy. 8: Trustworthy. 9: Very trustworthy. '
 '10: Completely trustworthy; strong expectation that the partner will reliably follow through.')
RULES = ('Each round gives each agent a fresh endowment of 5 tokens. Legal contributions are whole '
 'numbers from 0 through 5 inclusive. Unused tokens contribute to this round\'s payoff; they do not '
 'carry over as a future token balance. The pool is multiplied by 1.5 and split equally: '
 'own payoff = 5 - own contribution + 0.75 * (own contribution + partner contribution). '
 'No particular contribution strategy is prescribed.')


def integer(lo, hi):
    return {'type': 'integer', 'minimum': lo, 'maximum': hi}


def object_schema(name, properties):
    return {'name': name, 'strict': True, 'schema': {'type': 'object', 'properties': properties,
        'required': list(properties), 'additionalProperties': False}}


def facts(announcements, outcomes, agent):
    partner = 'B' if agent == 'A' else 'A'
    promise = announcements[partner]['stated_action']
    actual = outcomes['choices'][partner]
    return {'partner_promised_contribution': promise, 'partner_actual_contribution': actual,
        'promise_matched': promise == actual, 'own_payoff': outcomes['payoffs'][agent],
        'partner_payoff': outcomes['payoffs'][partner]}


def assess(response, expected):
    """Preserve reported facts verbatim; record each discrepancy separately."""
    errors = {k: {'reported': response.get(k), 'expected': v} for k, v in expected.items()
              if type(response.get(k)) not in ((int, float) if type(v) in (int, float) else (type(v),))
              or response.get(k) != v}
    return {'factual_assessment_correct': not errors, 'factual_errors': errors,
            'engine_facts': copy.deepcopy(expected)}


def reflection_prompt(base, announcements, outcomes, agent, number):
    system, _, _ = base
    expected = facts(announcements, outcomes, agent)
    props = {k: integer(0, 5) for k in ['partner_promised_contribution', 'partner_actual_contribution']}
    props.update(promise_matched={'type': 'boolean'}, own_payoff={'type': 'number'}, partner_payoff={'type': 'number'},
        assessment={'type': 'string'}, score=integer(1, 10), promise_reliability_1_10=integer(1, 10))
    if number < 10:
        props['predicted_next_partner_contribution'] = integer(0, 5)
    import json
    user = ('This round has ended. ENGINE_FACTS=' + json.dumps(expected, sort_keys=True) + '\n'
        'Current public announcements: ' + json.dumps(announcements, sort_keys=True) + '\n'
        'First explicitly report each of these observed facts in its corresponding field: the partner\'s '
        'publicly announced contribution, actual contribution, whether they matched, and both payoffs. '
        'Use the engine facts as evidence. Prior private assessments are fallible interpretations.\n'
        'Then provide an assessment and integer score of future trust, considering honesty, reliability, '
        'and cooperation, rather than generosity alone. Trust anchors: ' + TRUST_ANCHORS + '\n'
        'Separately rate promise reliability across the interaction: how reliably the partner follows '
        'through on publicly stated contribution amounts. Integer scale: 1 completely unreliable, '
        '2 extremely unreliable, 3 very unreliable, 4 somewhat unreliable, 5 slightly unreliable or uncertain, '
        '6 slightly reliable with reservations, 7 moderately reliable, 8 reliable, 9 very reliable, '
        '10 completely reliable. This is distinct from overall trust; do not automatically lower trust '
        'because a promise was broken. Explain your assessment briefly.\n' +
        ('Predict the partner\'s actual contribution next round as an integer 0–5.' if number < 10 else
         'This is round 10. There is no round-11 prediction or outcome.'))
    return system + '\n' + RULES, user, object_schema('peer_reflection_v2', props)


def recognition_prompt():
    text = ('Based only on your experienced interaction, first identify consistent behavioral patterns, '
        'any changes you noticed in communication or cooperation, concrete observations with round references, '
        'and plausible explanations other than partner replacement. Variation alone does not establish '
        'replacement. Then assess whether your partner remained the same throughout or was replaced at '
        'some point. A replacement may or may not have occurred. Answer SAME or CHANGED, confidence '
        '0–100, and explain the evidence. There is no preferred answer.')
    props = {k: {'type': 'string'} for k in ['consistent_patterns', 'noticed_changes', 'concrete_observations',
                                            'alternative_explanations', 'evidence']}
    props.update(judgment={'type': 'string', 'enum': ['SAME', 'CHANGED']}, confidence=integer(0, 100))
    return 'You are Agent A. Evaluate only your experienced interaction.', text, object_schema('peer_recognition_v2', props)
