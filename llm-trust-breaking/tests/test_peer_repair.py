"""Schema, immutable recovery, interrupted responses and at-most-once resume regressions."""
import copy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from peer_identity.inference import Journal,MockTransport,StopRun,validate,digest,atomic_json
from peer_identity.measurements_v2 import recognition_prompt,VERSION
from peer_identity.protocol import Config,run_study,prepare_study
from peer_identity.repair import recover_request,effective_request,recover_finished_trial,recognition_review
from peer_identity.export import export_bundle,verify_bundle


def response():
    return dict(consistent_patterns='Partner kept promises.',noticed_changes='',concrete_observations='Round 10 matched.',
        alternative_explanations='',evidence='No observed changes.',judgment='SAME',confidence=95)

class SchemaTests(unittest.TestCase):
    def test_empty_fields_are_schema_valid_and_preserved(self):
        value=response();before=copy.deepcopy(value);validate(value,recognition_prompt()[2]['schema']);self.assertEqual(value,before)
    def test_each_missing_field_rejected(self):
        for field in response():
            with self.subTest(field=field),self.assertRaises(ValueError):
                value=response();del value[field];validate(value,recognition_prompt()[2]['schema'])
    def test_incorrect_types(self):
        for key in response():
            for val in [None,[],{},True]:
                with self.subTest(key=key,val=val),self.assertRaises(ValueError):
                    value=response();value[key]=val;validate(value,recognition_prompt()[2]['schema'])
    def test_bad_judgments(self):
        for val in ['same','UNKNOWN','',0]:
            with self.assertRaises(ValueError):
                value=response();value['judgment']=val;validate(value,recognition_prompt()[2]['schema'])
    def test_confidence_bounds(self):
        for val in [-1,101,95.5,'95',True]:
            with self.assertRaises(ValueError):
                value=response();value['confidence']=val;validate(value,recognition_prompt()[2]['schema'])
    def test_schema_minlength_enforced_without_stripping(self):
        validate('',{'type':'string'});validate(' ',{'type':'string','minLength':1})
        with self.assertRaises(ValueError):validate('',{'type':'string','minLength':1})
        with self.assertRaises(ValueError):validate('long',{'type':'string','maxLength':2})
    def test_contradiction_flag_does_not_alter_judgment(self):
        value=response();value.update(judgment='CHANGED',evidence='This suggests a shift in behavior rather than a partner change.')
        before=copy.deepcopy(value);validate(value,recognition_prompt()[2]['schema'])
        self.assertTrue(recognition_review(value)['requires_human_review']);self.assertEqual(value,before)
    def test_empty_is_not_contradiction(self):
        self.assertFalse(recognition_review(response())['requires_human_review'])
        self.assertEqual(recognition_review(response())['empty_evidence_fields'],['noticed_changes','alternative_explanations'])

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.net=patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK FORBIDDEN'));self.net.start();self.addCleanup(self.net.stop)
        self.cfg=Config(checkpoints=1,conditions=['C0'],settings=['natural'],protocol_version=VERSION,trust_threshold=8)
        class EmptyRecognition(MockTransport):
            def __call__(self,payload):
                result=super().__call__(payload)
                if 'noticed_changes' in payload['response_format']['json_schema']['schema']['properties']:
                    result['content']=json.dumps(response())
                return result
        self.transport=EmptyRecognition();self.raw=self.root/'raw'
        run_study(self.cfg,self.raw,Journal(self.raw,self.transport,101,8,mock=True))
        self.rid='checkpoint-000/natural-C0-rep000/recognition/A'
        self.path=self.raw/'requests'/(digest(self.rid)+'.json')
        self.complete=json.loads(self.path.read_text())
        (self.raw/'checkpoint-000/natural-C0-rep000/result.json').unlink()
    def rejected(self,status='blocked'):
        value=copy.deepcopy(self.complete);value.pop('parsed');value.update(status=status,error_type='ValueError');atomic_json(self.path,value)
        return self.path.read_bytes()
    def test_rejected_response_recovery_preserves_bytes_and_cost(self):
        original=self.rejected();recover_request(self.raw,self.rid);effective=effective_request(self.raw,json.loads(original))
        self.assertEqual(effective['parsed'],response());self.assertEqual(effective['cost_usd'],self.complete['cost_usd'])
        self.assertEqual(self.path.read_bytes(),original);self.assertEqual(effective['status'],'complete')
        recover_request(self.raw,self.rid);self.assertEqual(self.path.read_bytes(),original)
    def test_saved_response_after_interruption(self):
        self.rejected('pending');recover_request(self.raw,self.rid)
        self.assertEqual(effective_request(self.raw,json.loads(self.path.read_text()))['status'],'complete')
    def test_ambiguous_pending_without_response_refused(self):
        self.rejected('pending');r=json.loads(self.path.read_text());r.pop('response');atomic_json(self.path,r)
        with self.assertRaises(StopRun):recover_request(self.raw,self.rid)
    def test_invalid_response_not_recovered(self):
        self.rejected();r=json.loads(self.path.read_text());v=response();v['confidence']=101;r['response']['content']=json.dumps(v);atomic_json(self.path,r)
        with self.assertRaises(ValueError):recover_request(self.raw,self.rid)
    def test_tampering_detected(self):
        self.rejected();recover_request(self.raw,self.rid);r=json.loads(self.path.read_text());r['cost_usd']=.1
        with self.assertRaises(StopRun):effective_request(self.raw,r)
    def test_no_duplicate_calls_or_recovered_trial_requests_on_resume(self):
        self.rejected();recover_request(self.raw,self.rid);recover_finished_trial(self.raw,self.rid)
        def forbidden(payload):raise AssertionError('NO REQUEST MAY BE MADE DURING RESUME')
        run_study(self.cfg,self.raw,Journal(self.raw,forbidden,101,8,mock=True))
        self.assertEqual(len(list((self.raw/'requests').glob('*.json'))),101)
        bundle,report=export_bundle(self.raw,self.root/'export');self.assertEqual(report['incomplete_trials'],0);self.assertTrue(verify_bundle(bundle)['valid'])
    def test_replay_before_result_materialization_uses_original_response(self):
        self.rejected();recover_request(self.raw,self.rid)
        def forbidden(payload):raise AssertionError('NO DUPLICATE REQUEST')
        run_study(self.cfg,self.raw,Journal(self.raw,forbidden,101,8,mock=True))
        saved=json.loads((self.raw/'checkpoint-000/natural-C0-rep000/result.json').read_text())
        self.assertEqual(saved['recognition'],response())
    def test_all_conditions_get_identical_validation(self):
        for condition in ['C0','C1','C2','C3']:
            rid=f'checkpoint-000/natural-{condition}-rep000/recognition/A'
            target=self.root/condition;target.mkdir()
            atomic_json(target/'manifest.json',{'config':{'protocol_version':VERSION}})
            record=copy.deepcopy(self.complete);record.update(request_id_local=rid,status='blocked',error_type='ValueError');record.pop('parsed')
            path=target/'requests'/(digest(rid)+'.json');atomic_json(path,record);before=path.read_bytes()
            recover_request(target,rid)
            self.assertEqual(effective_request(target,record)['parsed'],response())
            self.assertEqual(path.read_bytes(),before)
    def test_complete_request_still_reused(self):
        prompt=recognition_prompt();path=self.root/'single';transport=MockTransport();j=Journal(path,transport,1,1,mock=True)
        first=j.ask(self.rid,'gpt-4o-mini',prompt,1)
        def forbidden(payload):raise AssertionError('DUPLICATE')
        second=Journal(path,forbidden,1,1,mock=True).ask(self.rid,'gpt-4o-mini',prompt,1)
        self.assertEqual(first,second);self.assertEqual(transport.calls,1)

class MigrationTests(unittest.TestCase):
    def test_real_legacy_source_migration_is_explicit_and_hash_bound(self):
        from peer_identity.repair import record_software_correction
        legacy=Path(__file__).resolve().parents[1]/'outputs/peer-identity/study-200-v2'
        if not legacy.exists():self.skipTest('Local legacy fixture absent in portable checkout')
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            for name in ['manifest.json','source-snapshot.json','batch.json']:
                shutil.copy2(legacy/name,target/name)
            cfg=Config(**json.loads((target/'manifest.json').read_text())['config'])
            with self.assertRaises(StopRun):prepare_study(cfg,target,False)
            receipt=record_software_correction(target);prepare_study(cfg,target,False)
            value=json.loads(receipt.read_text());value['new_code_hash']='tampered';atomic_json(receipt,value)
            with self.assertRaises(StopRun):prepare_study(cfg,target,False)
    def test_version1_migration_refused(self):
        from peer_identity.repair import record_software_correction
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);atomic_json(path/'manifest.json',{'config':{'protocol_version':'publicgoods-peer-identity-v1'}})
            with self.assertRaises(StopRun):record_software_correction(path)
