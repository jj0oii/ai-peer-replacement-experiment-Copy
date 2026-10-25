"""Optional analysis-only held-out behavioral distance. Never makes model calls.

Input must be separate calibration data, NOT checkpoint/continuation outcomes.
Each prompt must have identical text across models and equal sample counts.
No single composite distance or provider ordering is assumed.
"""
from collections import defaultdict
import json
from pathlib import Path
import re
from statistics import mean
from .inference import digest


def measure_heldout(data):
    if data.get('source') != 'heldout_calibration' or not data.get('independent_of_experiment_outcomes'):
        raise ValueError('Require explicitly held-out calibration data')
    version=data.get('protocol_version','publicgoods-peer-identity-v1')
    if version not in ('publicgoods-peer-identity-v1','publicgoods-peer-identity-v2'):
        raise ValueError('Unknown calibration protocol')
    trust_max=10 if version.endswith('-v2') else 5
    grouped = defaultdict(list)
    prompt_hashes = {}
    for record in data['records']:
        if record.get('protocol_version',version)!=version:
            raise ValueError('Mixed calibration measurement protocols')
        for key in ['prompt_id','prompt','model','contribution','announcement','trust','message']:
            if key not in record:
                raise ValueError('Incomplete held-out record')
        for key,low,high in [('contribution',0,5),('announcement',0,5),('trust',1,trust_max)]:
            if type(record[key]) is not int or not low <= record[key] <= high:
                raise ValueError('Out-of-range calibration response')
        prompt_id = record['prompt_id']
        fingerprint = digest(record['prompt'])
        if prompt_id in prompt_hashes and prompt_hashes[prompt_id] != fingerprint:
            raise ValueError('Models did not receive identical held-out prompt')
        prompt_hashes[prompt_id] = fingerprint
        grouped[(record['model'],prompt_id)].append(record)
    models = sorted({m for m,p in grouped})
    prompts = sorted(prompt_hashes)
    if len(models) < 2 or not prompts:
        raise ValueError('Need at least two models and one held-out prompt')
    for prompt in prompts:
        sizes = [len(grouped[(m,prompt)]) for m in models]
        if not sizes[0] or len(set(sizes)) != 1:
            raise ValueError('Require complete balanced samples per prompt/model')
    pairs = []
    for i,m in enumerate(models):
        for n in models[i+1:]:
            per_prompt = []
            for prompt in prompts:
                a,b = grouped[(m,prompt)],grouped[(n,prompt)]
                words = lambda rows: set(w for r in rows for w in re.findall(r'\w+',r['message'].lower()))
                wa,wb = words(a),words(b)
                la,lb = mean(len(r['message']) for r in a),mean(len(r['message']) for r in b)
                per_prompt.append({'contribution_difference_0to1': abs(mean(r['contribution'] for r in a)-mean(r['contribution'] for r in b))/5,
                    'promise_breaking_rate_difference_0to1': abs(mean(r['contribution']!=r['announcement'] for r in a)-mean(r['contribution']!=r['announcement'] for r in b)),
                    'trust_difference_0to1': abs(mean(r['trust'] for r in a)-mean(r['trust'] for r in b))/(trust_max-1),
                    'message_length_difference_0to1': abs(la-lb)/max(la,lb,1),
                    'message_vocabulary_jaccard_distance_0to1': 1-len(wa&wb)/len(wa|wb) if wa|wb else 0})
            pairs.append({'model_1':m,'model_2':n,'heldout_prompts':len(prompts),
                          **{k:mean(r[k] for r in per_prompt) for k in per_prompt[0]}})
    return {'pairs':pairs,'note':'Descriptive held-out feature differences, not an identity or harmful-collusion classifier; no composite distance. No uncertainty estimated for finite calibration samples.'}
