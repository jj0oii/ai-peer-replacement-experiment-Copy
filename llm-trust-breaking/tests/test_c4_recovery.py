"""Single-recovery regression tests: injected transports, no network calls."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch
import test_c4_extension as fixtures
from peer_identity import c4_extension as c, c4_recovery as r, c4_http_diagnostics as d
from peer_identity.inference import atomic_json,digest,StopRun

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.C4Tests(methodName='test_state_and_handoff');self.f.setUp()
        self.addCleanup(self.f.tmp.cleanup)
        self.root=self.f.root
        _,_,prompt,seed,temp=self.f.prompts[0]
        payload=self.f.journal.payload(c.MODEL,prompt,seed,temp)
        self.patch=patch.object(r,'EXPECTED_PAYLOAD',digest(payload));self.patch.start();self.addCleanup(self.patch.stop)
        a_payload=self.f.journal.payload('gpt-4o-mini',prompt,seed,temp)
        a={'request_id':r.A_TARGET,'stage':'trial','status':'complete','payload':a_payload,
           'payload_hash':digest(a_payload),'reserved_usd':.002,'cost_usd':.0005,'parsed':{'intended_action':4,'reasoning':'saved A'}}
        b={'request_id':r.TARGET,'stage':'trial','status':'blocked','payload':payload,
           'payload_hash':digest(payload),'reserved_usd':.0017,'error_type':'StopRun'}
        probe={'request_id':'probe/schema-0','stage':'probe','status':'complete','payload':payload,
               'payload_hash':digest(payload),'reserved_usd':.0017,'cost_usd':.0002}
        for record in (a,b,probe):atomic_json(self.root/'requests'/(digest(record['request_id'])+'.json'),record)
        identity={'source':str(self.f.source),'source_inventory':c.source_inventory(self.f.source),'mock':False,
            'code_hash':'old-code','core_code_hashes':{n:digest((Path(c.__file__).parent/n).read_text()) for n in ('protocol.py','inference.py','measurements_v2.py')},
            'prompt_code_hash':digest(Path(c.prompts.__file__).read_text())}
        atomic_json(self.root/'manifest.json',{'identity':identity})
        self.review=self.f.base/'review.json'
        atomic_json(self.review,{'old_extension_code_hash':'old-code','new_extension_code_hash':digest(Path(c.__file__).read_text())})
        self.before=r.files(self.root)
        self.mock=c.RoutedMock()
    def recover(self,transport=None):return r.recover(self.root,transport or self.mock,review_path=self.review)

    def test_exact_payload_only_one_b_request_and_no_a(self):
        original=c.read(self.root/'requests'/(digest(r.TARGET)+'.json'))
        result=self.recover()
        self.assertEqual(result['status'],'complete')
        self.assertEqual(self.mock.backend.calls,1)
        self.assertEqual(self.mock.backend.payloads,[original['payload']])
        self.assertEqual(r.files(self.root),self.before)
        self.assertEqual(result['original_record_hash'],digest(original))
        accounting=c.read(self.root/'explicit-recovery/accounting.json')
        self.assertEqual(accounting['original_unknown_reservation_usd'],.0017)
        self.assertAlmostEqual(accounting['extension_accounted_usd_including_original_reservation'],.0005+.0017+.0002+result['cost_usd'])
        self.assertTrue(accounting['no_rounds_continued'])
        self.assertFalse((self.root/'trials').exists())

    def test_repeat_success_never_resends(self):
        self.recover()
        with self.assertRaises(StopRun):self.recover()
        self.assertEqual(self.mock.backend.calls,1)

    def test_failure_preserves_http_details_and_no_retry(self):
        calls=[]
        def fail(payload):
            calls.append(payload)
            raise d.RouterDiagnosticFailure({'http_status':503,'provider_error':{'message':'upstream unavailable'},'could_have_incurred_charge':True})
        for _ in range(2):
            with self.assertRaises(StopRun):self.recover(fail)
        self.assertEqual(len(calls),1)
        saved=c.read(self.root/'explicit-recovery/attempt-1.json')
        self.assertEqual(saved['http_diagnostic']['http_status'],503)
        self.assertEqual(saved['status'],'blocked')
        self.assertNotIn('cost_usd',saved)
        self.assertEqual(r.files(self.root),self.before)

    def test_pending_intent_never_resends(self):
        directory=self.root/'explicit-recovery';directory.mkdir()
        atomic_json(directory/'attempt-1.json',{'status':'pending'})
        with self.assertRaises(StopRun):self.recover()
        self.assertEqual(self.mock.backend.calls,0)

    def test_payload_mutation_rejected(self):
        p=self.root/'requests'/(digest(r.TARGET)+'.json');record=c.read(p)
        record['payload']['temperature']=.5;atomic_json(p,record)
        with self.assertRaises(StopRun):self.recover()
        self.assertEqual(self.mock.backend.calls,0)

    def test_guard_stops_before_dispatch(self):
        p=self.root/'requests'/(digest(r.TARGET)+'.json');record=c.read(p)
        record['reserved_usd']=.02;atomic_json(p,record)
        with self.assertRaises(StopRun):self.recover()
        self.assertEqual(self.mock.backend.calls,0)

    def test_wrong_provider_is_retained_and_blocked(self):
        def wrong(payload):
            response=self.mock(payload);response['provider']='Other';return response
        with self.assertRaises(StopRun):self.recover(wrong)
        self.assertEqual(c.read(self.root/'explicit-recovery/attempt-1.json')['status'],'blocked')
        with self.assertRaises(StopRun):self.recover(wrong)
        self.assertEqual(self.mock.backend.calls,1)

    def test_code_identity_change_blocks(self):
        atomic_json(self.review,{'old_extension_code_hash':'old-code','new_extension_code_hash':'different'})
        with self.assertRaises(StopRun):self.recover()
        self.assertEqual(self.mock.backend.calls,0)

    def test_cli_requires_exact_approval_and_caps(self):
        for args in [[],['--approve-one-paid-recovery','--max-new-requests','2','--budget-usd','.01'],
                     ['--approve-one-paid-recovery','--max-new-requests','1','--budget-usd','.02']]:
            with self.assertRaises(SystemExit):r.main(['--output',str(self.root)]+args)

if __name__=='__main__':unittest.main()
