"""One canonical study ledger/policy across resumable checkpoint windows. No API calls."""
import math
from pathlib import Path
import json
from .inference import StopRun, atomic_json


def study_budget(directory, total, reserve, prior, max_requests=None):
    values=[total,reserve,prior]
    if any(not math.isfinite(v) or v<0 for v in values) or reserve+prior>=total:
        raise ValueError('Invalid study budget, safety reserve or prior-spend allowance')
    policy={'total_budget_usd':total,'safety_reserve_usd':reserve,'prior_spend_allowance_usd':prior,
            'request_ledger_ceiling_usd':total-reserve-prior,'max_requests':max_requests,
            'scope':'All study requests in this canonical directory, including pilot and resumed batches',
            'limitation':'Local estimates do not guarantee a provider billing ceiling; unrelated API calls are not automatically visible.'}
    path=Path(directory)/'budget-policy.json'
    if path.exists():
        if json.loads(path.read_text())!=policy:raise StopRun('Saved cumulative budget policy differs; do not reset it between batches')
    else:atomic_json(path,policy)
    return policy


def window_policy(directory,start,count,max_requests,budget):
    if max_requests<1 or not math.isfinite(budget) or budget<=0:raise ValueError('Invalid window limits')
    policy={'checkpoint_start':start,'checkpoint_count':count,'max_requests':max_requests,'budget_usd':budget}
    path=Path(directory)/'windows'/f'{start:03d}-{start+count-1:03d}-policy.json'
    if path.exists() and json.loads(path.read_text())!=policy:raise StopRun('Window limits differ from their saved policy')
    if not path.exists():atomic_json(path,policy)
    return policy
