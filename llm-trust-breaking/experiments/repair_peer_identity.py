"""Explicit offline validator correction/recovery. No API transport or engine execution."""
import argparse
import fcntl
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from peer_identity.repair import record_software_correction,recover_request,recover_finished_trial

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study',type=Path)
    parser.add_argument('--request-id',required=True)
    args=parser.parse_args()
    with (args.study/'.run.lock').open('a') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        receipt=record_software_correction(args.study)
        recovery=recover_request(args.study,args.request_id)
        result=recover_finished_trial(args.study,args.request_id)
        print(json.dumps({'software_correction':str(receipt),'recovery_receipt':str(recovery),
            'recovered_result':str(result),'new_api_requests':0,'additional_cost_usd':0},indent=2))
