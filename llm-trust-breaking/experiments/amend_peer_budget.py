"""Preview or explicitly authorize a local cumulative budget amendment. Never calls an API."""
import argparse
import fcntl
import json
import math
from pathlib import Path
import sys
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from peer_identity.inference import atomic_json,digest
from peer_identity.provenance import utc_now


def amend(directory,new_total,reserve=None,expected_total=None,approve=False):
    directory=Path(directory)
    if not (directory/'budget-policy.json').is_file():raise ValueError('Existing canonical study budget policy required')
    with (directory/'.run.lock').open('a') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        old=json.loads((directory/'budget-policy.json').read_text())
        if expected_total is not None and old['total_budget_usd']!=expected_total:
            raise ValueError('Current total differs from the explicitly expected policy')
        held=old['safety_reserve_usd'] if reserve is None else reserve
        if not math.isfinite(new_total) or not math.isfinite(held) or new_total<=old['total_budget_usd'] or held<0:
            raise ValueError('Require a finite explicit increase and valid reserve')
        new=dict(old,total_budget_usd=new_total,safety_reserve_usd=held,
                 request_ledger_ceiling_usd=new_total-held-old['prior_spend_allowance_usd'])
        accounted=0.
        for p in (directory/'requests').glob('*.json'):
            r=json.loads(p.read_text());accounted+=r.get('cost_usd',r['reserved_usd'])
        if new['request_ledger_ceiling_usd']<accounted:raise ValueError('Amended allowance cannot cover already accounted spending')
        result={'approved_operation_requested':approve,'old_policy':old,'proposed_policy':new,
                'existing_accounted_usd':accounted,'request_limit_unchanged':new['max_requests']==old['max_requests'],
                'ledger_and_checkpoints_unchanged':True}
        if not approve:
            result['status']='preview_only_no_policy_change'
            return result
        history=directory/'budget-history'/('amendment_'+uuid.uuid4().hex+'.json')
        event={'operation':'authorized_policy_amendment','status':'intent','created_at':utc_now(),
               'old_policy':old,'new_policy':new,'old_hash':digest(old),'new_hash':digest(new)}
        atomic_json(history,event)
        atomic_json(directory/'budget-policy.json',new)
        event['status']='applied';atomic_json(history,event)
        result['status']='applied';result['audit_record']=str(history)
        return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('study',type=Path)
    p.add_argument('--new-total',type=float,required=True)
    p.add_argument('--reserve',type=float)
    p.add_argument('--expected-current-total',type=float)
    p.add_argument('--approve-budget-change',action='store_true',help='Use only AFTER the user explicitly authorizes the increase')
    a=p.parse_args()
    print(json.dumps(amend(a.study,a.new_total,a.reserve,a.expected_current_total,a.approve_budget_change),indent=2))
