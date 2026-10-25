"""Explicit offline recovery overlays. Original requests, responses and manifests stay immutable."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import re
from .inference import ENDPOINT, StopRun, atomic_json, digest, usage_cost, validate
from .measurements_v2 import VERSION, recognition_prompt

CORRECTION = 'schema-string-minLength-v1'
RECEIPT = 'validator-string-length-v1.json'


def verified_response(record):
    """Only fully recorded, billed V2 recognition responses; never ambiguous network failures."""
    if not re.fullmatch(r'checkpoint-\d{3,}/(?:natural|controlled)-C[0-3]-rep\d{3}/recognition/A',record['request_id_local']):
        raise StopRun('Only Version 2 recognition recovery is supported')
    if record['status'] not in ('blocked','pending') or record.get('reservation_exceeded'):
        raise StopRun('Not a recoverable locally rejected/interrupted response')
    if record['status']=='blocked' and record.get('error_type')!='ValueError':
        raise StopRun('Recovery does not cover provider or ambiguous failures')
    payload=record['payload'];response=record.get('response',{})
    if digest(payload)!=record['payload_hash'] or payload['response_format']['json_schema']!=recognition_prompt()[2]:
        raise StopRun('Payload/schema mismatch')
    model=payload['model'];returned=response.get('model_returned','')
    if model!='gpt-4o-mini' or not (returned==model or returned.startswith(model+'-')):
        raise StopRun('Unexpected recognition model')
    if response.get('endpoint')!=ENDPOINT or response.get('finish_reason')!='stop' or not response.get('response_id') or not response.get('request_id'):
        raise StopRun('Incomplete or unverified provider response')
    if not response.get('usage') or 'cost_usd' not in record:
        raise StopRun('Missing recorded usage/cost; no automatic billing recovery')
    expected_cost=0. if record['mock'] else usage_cost(model,response['usage'])
    if abs(record['cost_usd']-expected_cost)>1e-10 or record['cost_usd']>record['reserved_usd']:
        raise StopRun('Cost/reservation mismatch')
    parsed=json.loads(response['content']);validate(parsed,payload['response_format']['json_schema']['schema'])
    return parsed


def effective_request(directory, record):
    """Read a hash-bound sidecar; never rewrite the journal or silently repair a response."""
    path=Path(directory)/'recoveries'/(digest(record['request_id_local'])+'.json')
    if not path.exists():return record
    receipt=json.loads(path.read_text())
    if receipt.get('correction')!=CORRECTION or receipt.get('original_record_digest')!=digest(record) or receipt.get('request_id_local')!=record['request_id_local']:
        raise StopRun('Recovery receipt does not match the original immutable request')
    parsed=verified_response(record)
    if digest(parsed)!=receipt.get('parsed_digest'):
        raise StopRun('Recovered response digest mismatch')
    result=copy.deepcopy(record)
    result.update(status='complete',parsed=parsed,local_recovery=receipt)
    # error_type remains in the immutable original and effective audit trail.
    return result


def recover_request(directory, request_id):
    directory=Path(directory)
    manifest=json.loads((directory/'manifest.json').read_text())
    if manifest['config']['protocol_version']!=VERSION:raise StopRun('Version 1 recovery is not permitted')
    raw_path=directory/'requests'/(digest(request_id)+'.json');record=json.loads(raw_path.read_text())
    path=directory/'recoveries'/raw_path.name
    if path.exists():effective_request(directory,record);return path
    parsed=verified_response(record)
    from .provenance import utc_now
    receipt={'correction':CORRECTION,'request_id_local':request_id,'original_record_digest':digest(record),
        'parsed_digest':digest(parsed),'recovered_at':utc_now(),'new_api_requests':0,'additional_cost_usd':0,
        'reason':'Complete provider response satisfies the original unchanged response schema under corrected JSON string length validation.'}
    atomic_json(path,receipt)
    return path


def record_software_correction(directory):
    """Explicit reviewed migration: unchanged prompt/config/model files, hash-bound code receipt."""
    from .protocol import code_identity
    from .provenance import utc_now
    directory=Path(directory);root=Path(__file__).resolve().parents[1]
    manifest=json.loads((directory/'manifest.json').read_text())
    if manifest['config']['protocol_version']!=VERSION:raise StopRun('Only V2 software correction supported')
    baseline=json.loads((directory/'source-snapshot.json').read_text())
    allowed={'peer_identity/inference.py','peer_identity/protocol.py','peer_identity/export.py'}
    for name,text in baseline.items():
        if name not in allowed and (root/name).read_text()!=text:
            raise StopRun('Scientific protocol or unreviewed source changed; refuse migration')
    protected=['peer_identity/measurements_v2.py','src/endogenous/core/prompt_builders.py','src/games/publicgoods.py']
    for name in protected:
        if (root/name).read_text()!=baseline[name]:raise StopRun('Prompt/game changes are not a validator correction')
    identity_names=['peer_identity/measurements_v2.py','peer_identity/protocol.py','peer_identity/inference.py',
        'peer_identity/provenance.py','peer_identity/spending.py','src/endogenous/core/prompt_builders.py','src/games/publicgoods.py']
    if digest({name:baseline[name] for name in identity_names})!=manifest['code_hash']:
        raise StopRun('Original source snapshot does not match manifest')
    path=directory/'software-corrections'/RECEIPT
    new_hash=code_identity()
    if path.exists():
        existing=json.loads(path.read_text())
        if existing['new_code_hash']!=new_hash:raise StopRun('Software correction code changed after review')
        return path
    sources={name:(root/name).read_text() for name in sorted(allowed|{'peer_identity/repair.py'})}
    receipt={'correction':CORRECTION,'created_at':utc_now(),'original_manifest_digest':digest(manifest),
        'original_code_hash':manifest['code_hash'],'new_code_hash':new_hash,'config_digest':digest(manifest['config']),
        'changed_source_snapshot':sources,'protocol_and_prompt_changes':False,
        'protected_source_hashes':{name:digest(baseline[name]) for name in protected},
        'note':'Explicit offline software correction; original source snapshot, provider responses, costs and completed results retained.'}
    atomic_json(path,receipt);return path


def compatible_manifest(directory, expected):
    directory=Path(directory);path=directory/'software-corrections'/RECEIPT
    if not path.exists():return False
    old=json.loads((directory/'manifest.json').read_text());receipt=json.loads(path.read_text())
    if old['config']['protocol_version']!=VERSION:return False
    return (receipt.get('correction')==CORRECTION and receipt.get('original_manifest_digest')==digest(old)
        and receipt.get('new_code_hash')==expected['code_hash'] and receipt.get('config_digest')==digest(expected['config'])
        and {k:v for k,v in old.items() if k!='code_hash'}=={k:v for k,v in expected.items() if k!='code_hash'})


def recover_finished_trial(directory, request_id):
    """Finalize only an already-played ten-round game; no engine loop or transport invocation."""
    directory=Path(directory);cp,branch,_,_=request_id.split('/')
    raw=json.loads((directory/'requests'/(digest(request_id)+'.json')).read_text())
    response=effective_request(directory,raw)
    if response['status']!='complete':raise StopRun('Recognition has not been recovered')
    result_path=directory/cp/branch/'result.json'
    if result_path.exists():
        if json.loads(result_path.read_text())['recognition']!=response['parsed']:raise StopRun('Existing result differs')
        return result_path
    progress=json.loads((result_path.parent/'progress.json').read_text());checkpoint=json.loads((directory/cp/'checkpoint.json').read_text())
    if [r['round'] for r in progress['state']['rounds']]!=list(range(1,11)):
        raise StopRun('Cannot finalize a game with missing rounds')
    # Full journal/state/condition/derived validation before creating any completed result.
    from .export import build_datasets, sources, validate_datasets
    manifest=json.loads((directory/'manifest.json').read_text());batch=json.loads((directory/'batch.json').read_text())
    tables,config,_=build_datasets(directory,sources(directory),manifest,batch)
    validate_datasets(tables,config,batch['batch_id'])
    trial=next(r for r in tables['trials'] if r['run_id']==batch['batch_id']+':'+cp+':'+branch)
    if trial['status']!='recovered_complete':raise StopRun('Trial is not fully recoverable')
    atomic_json(result_path,{'schema_version':1,'checkpoint_id':cp,'checkpoint_hash':checkpoint['state_hash'],
        'branch_id':branch,'repetition':int(branch.split('rep')[-1]),'metadata':progress['metadata'],
        'qualification':checkpoint['qualification'],'recognition':response['parsed'],'state':progress['state']})
    return result_path


def recognition_review(response):
    """Conservative lexical review flag, not a semantic classifier or corrected judgment."""
    text=' '.join(response.get(k,'') for k in ['evidence','alternative_explanations'])
    contradiction=(response.get('judgment')=='CHANGED' and bool(re.search(
        r'rather than (?:an? (?:actual )?)?partner (?:change|replacement)|partner remained the same|partner was not replaced',text,re.I)))
    return {'requires_human_review':contradiction,'reason':'Judgment/evidence tension; narrow lexical flag, not exhaustive semantic validation' if contradiction else '',
            'empty_evidence_fields':[k for k in ['consistent_patterns','noticed_changes','concrete_observations','alternative_explanations','evidence'] if response.get(k)=='' ]}
