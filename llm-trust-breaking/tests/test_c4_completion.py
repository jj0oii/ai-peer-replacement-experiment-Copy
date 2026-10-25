"""Prepared completion gate and recovered-response replay; all calls synthetic."""
import json
import unittest
import test_c4_recovery as fixtures
from peer_identity import c4_extension as c,c4_recovery as r,c4_resume_smoke as s
from peer_identity.inference import atomic_json,digest,StopRun

class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.RecoveryTests(methodName='test_repeat_success_never_resends')
        self.fixture.setUp();self.addCleanup(self.fixture.f.tmp.cleanup);self.addCleanup(self.fixture.patch.stop)
        self.root=self.fixture.root
        cp,config,state,meta=c.load_checkpoint(self.fixture.f.source,0)
        class Capture(c.Capture):
            def ask(self,request_id,model,prompt,seed,temperature=1):
                result=super().ask(request_id,model,prompt,seed,temperature)
                if request_id.endswith('/planning/A'):
                    self.a=(model,prompt,seed,temperature,result)
                return result
        capture=Capture()
        c.run_round(state,meta['models'],capture,'checkpoint-000/natural-C4-rep000',6,config.seed,config)
        model,prompt,seed,temp,parsed=capture.a
        path=self.root/'requests'/(digest(r.A_TARGET)+'.json')
        saved=c.read(path);saved['payload']=self.fixture.f.journal.payload(model,prompt,seed,temp)
        saved['payload_hash']=digest(saved['payload']);saved['parsed']=parsed;atomic_json(path,saved)
        self.attempt=self.fixture.recover()

    def test_full_mock_completion_reuses_both_planning_responses(self):
        source,receipt,attempt=s.verified_recovery(self.root)
        mock=c.RoutedMock()
        journal=s.CompletionJournal(self.root,source,receipt['source_inventory'],attempt,mock,mock)
        original=r.files(self.root)
        cp,config,state,meta=c.load_checkpoint(source,0)
        prefix='checkpoint-000/natural-C4-rep000'
        for rnd in range(6,11):c.run_round(state,meta['models'],journal,prefix,rnd,config.seed,config)
        recognition=c.recognize(state,journal,prefix,config.model_a,config.seed,config)
        self.assertEqual(mock.backend.calls,49)
        self.assertEqual(journal.new_calls,49)
        self.assertEqual(sum(record['stage']=='trial' for record in journal.records()),52)
        for name,value in original.items():self.assertEqual(r.files(self.root)[name],value)
        self.assertEqual(sum(p['model']==c.MODEL for p in mock.backend.payloads),19)
        atomic_json(self.root/'trials/checkpoint-000/result.json',{'checkpoint_id':cp['checkpoint_id'],
            'source_checkpoint_hash':cp['state_hash'],'run_id':prefix,'condition':'C4','setting':'natural',
            'metadata':meta,'recognition':recognition,'state':state})
        # Synthetic inputs, but preserve mock=False fixture to exercise actual accounting.
        manifest=c.read(self.root/'manifest.json');manifest['mock']=False;atomic_json(self.root/'manifest.json',manifest)
        output=s.export_completion(self.root,journal)
        import csv
        with (output/'rounds.csv').open() as f:self.assertEqual(len(list(csv.DictReader(f))),10)
        with (output/'attempts.csv').open() as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),53) # fixture has one probe, not five
        self.assertEqual(sum(row['status']=='blocked' for row in rows),1)
        self.assertTrue(c.read(output/'metadata.json')['accounting']['accounted_usd']>attempt['cost_usd'])
        previous=mock.backend.calls
        cp,config,state,meta=c.load_checkpoint(source,0)
        for rnd in range(6,11):c.run_round(state,meta['models'],journal,prefix,rnd,config.seed,config)
        c.recognize(state,journal,prefix,config.model_a,config.seed,config)
        self.assertEqual(mock.backend.calls,previous)

    def test_refuses_other_checkpoints(self):
        source,receipt,attempt=s.verified_recovery(self.root)
        mock=c.RoutedMock();journal=s.CompletionJournal(self.root,source,receipt['source_inventory'],attempt,mock,mock)
        _,_,prompt,seed,temp=self.fixture.f.prompts[0]
        with self.assertRaises(StopRun):journal.ask('checkpoint-001/natural-C4-rep000/r6/planning/B',c.MODEL,prompt,seed,temp)
        self.assertEqual(mock.backend.calls,0)

    def test_completion_requires_separate_approval(self):
        with self.assertRaises(SystemExit):s.main(['--output',str(self.root),'--max-new-requests','49',
            '--max-total-trial-attempts','52','--trial-budget-usd','.50'])

if __name__=='__main__':unittest.main()
