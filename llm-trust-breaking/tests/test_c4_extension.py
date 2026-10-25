"""C4 tests use synthetic transports; no sockets, credentials or paid calls."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from peer_identity import c4_extension as c
from peer_identity.inference import atomic_json, digest, StopRun, validate
from peer_identity.protocol import Config, initial_state, run_round, recognize
from peer_identity import measurements_v2 as v2

class C4Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / 'source'; self.source.mkdir()
        self.root = self.base / 'extension'; self.root.mkdir()
        config = Config(protocol_version=v2.VERSION)
        capture = c.Capture(); state = initial_state()
        for rnd in range(1,6):
            run_round(state, {'A':config.model_a,'B':config.model_b}, capture, 'establish', rnd, config.seed, config)
        from dataclasses import asdict
        self.cp = {'checkpoint_id':'checkpoint-000','state':state,'state_hash':digest(state),
            'settings':asdict(config),'runtime_ids':{'A':'a','B':'b'}}
        atomic_json(self.source/'checkpoint-000/checkpoint.json',self.cp)
        self.inventory=c.source_inventory(self.source)
        self.mock=c.RoutedMock()
        self.journal=c.ExtensionJournal(self.root,self.source,self.inventory,'trial',51,.5,True,self.mock,self.mock)
        self.prompts=c.probe_prompts(self.source)

    def test_five_exact_schemas(self):
        self.assertEqual(len(self.prompts),5)
        before=self.prompts[3][2][2]['schema']['properties']
        final=self.prompts[4][2][2]['schema']['properties']
        self.assertIn('predicted_next_partner_contribution',before)
        self.assertNotIn('predicted_next_partner_contribution',final)
        for _,_,prompt,_,_ in self.prompts:
            schema=prompt[2]['schema'];self.assertFalse(schema['additionalProperties'])
            self.assertEqual(set(schema['required']),set(schema['properties']))

    def test_state_and_handoff(self):
        _,_,state,meta=c.load_checkpoint(self.source,0)
        self.assertEqual(state['agents']['A'],self.cp['state']['agents']['A'])
        self.assertEqual(state['public'],self.cp['state']['public'])
        self.assertEqual(state['agents']['B']['handoff'],c.HANDOFF)
        self.assertEqual(meta['models']['B'],c.MODEL)

    def test_corrupt_source_rejected(self):
        self.cp['state_hash']='wrong';atomic_json(self.source/'checkpoint-000/checkpoint.json',self.cp)
        with self.assertRaises(StopRun):c.load_checkpoint(self.source,0)

    def test_provider_pin_and_only_b_route(self):
        _,_,prompt,seed,temp=self.prompts[0]
        p=self.journal.payload(c.MODEL,prompt,seed,temp)
        self.assertEqual(p['provider'],c.PIN)
        self.assertFalse(p['provider']['allow_fallbacks'])
        self.assertEqual(p['response_format']['json_schema'],prompt[2])
        self.journal.ask('trial/r6/planning/B',c.MODEL,prompt,seed,temp)
        with self.assertRaises(StopRun):self.journal.ask('trial/r6/judge/B',c.MODEL,prompt,seed,temp)
        with self.assertRaises(StopRun):self.journal.ask('trial/r6/planning/B','gpt-4o-mini',prompt,seed,temp)

    def test_full_continuation_exports_and_resume(self):
        cp,config,state,meta=c.load_checkpoint(self.source,0)
        for rnd in range(6,11):c.run_round(state,meta['models'],self.journal,'trial',rnd,config.seed,config)
        recognition=c.recognize(state,self.journal,'trial',config.model_a,config.seed,config)
        self.assertEqual(self.journal.totals()['requests'],51)
        records=self.journal.records()
        self.assertEqual(sum(r['payload']['model']==c.MODEL for r in records),20)
        self.assertEqual(sum(r['payload']['model']=='gpt-5-mini' for r in records),10)
        self.assertEqual(sum(r['payload']['model']=='gpt-4o-mini' for r in records),21)
        atomic_json(self.root/'manifest.json',{'mock':True})
        atomic_json(self.root/'trials/checkpoint-000/result.json',{'checkpoint_id':cp['checkpoint_id'],
            'source_checkpoint_hash':cp['state_hash'],'run_id':'trial','condition':'C4','setting':'natural',
            'metadata':meta,'state':state,'recognition':recognition})
        out=c.export(self.root)
        with (out/'rounds.csv').open() as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),10);self.assertEqual({r['condition'] for r in rows},{'C4'})
        self.assertEqual({r['round'] for r in rows},{'6','7','8','9','10'})
        initial_calls=self.mock.backend.calls
        _,_,fresh,meta=c.load_checkpoint(self.source,0)
        for rnd in range(6,11):c.run_round(fresh,meta['models'],self.journal,'trial',rnd,config.seed,config)
        c.recognize(fresh,self.journal,'trial',config.model_a,config.seed,config)
        self.assertEqual(self.mock.backend.calls,initial_calls)
        self.assertEqual(c.source_inventory(self.source),self.inventory)

    def test_request_cap(self):
        self.journal.max_requests=1
        _,_,p,s,t=self.prompts[0]
        self.journal.ask('trial/r6/planning/B',c.MODEL,p,s,t)
        with self.assertRaises(StopRun):self.journal.ask('trial/r7/planning/B',c.MODEL,p,s,t)
        self.assertEqual(self.mock.backend.calls,1)

    def test_spending_guard(self):
        self.journal.budget=.0000001
        _,_,p,s,t=self.prompts[0]
        with self.assertRaises(StopRun):self.journal.ask('trial/r6/planning/B',c.MODEL,p,s,t)
        self.assertEqual(self.mock.backend.calls,0)

    def test_cumulative_reserve_guard(self):
        self.journal.source_spend=49.6
        _,_,p,s,t=self.prompts[0]
        with self.assertRaises(StopRun):self.journal.ask('trial/r6/planning/B',c.MODEL,p,s,t)
        self.assertEqual(self.mock.backend.calls,0)

    def test_wrong_provider_blocks_and_does_not_retry(self):
        def wrong(p):
            r=self.mock(p);r['provider']='Other';return r
        self.journal.router=wrong
        _,_,p,s,t=self.prompts[0]
        with self.assertRaises(StopRun):self.journal.ask('trial/r6/planning/B',c.MODEL,p,s,t)
        with self.assertRaises(StopRun):self.journal.ask('trial/r6/planning/B',c.MODEL,p,s,t)
        self.assertEqual(self.mock.backend.calls,1)

    def test_saved_response_recovers_without_dispatch(self):
        _,_,p,s,t=self.prompts[0]
        self.journal.ask('trial/r6/planning/B',c.MODEL,p,s,t)
        path=next(self.journal.path.glob('*.json'));record=c.read(path)
        record['status']='blocked';record.pop('parsed');atomic_json(path,record)
        before=path.read_bytes()
        self.journal.ask('trial/r6/planning/B',c.MODEL,p,s,t)
        self.assertEqual(self.mock.backend.calls,1)
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual(self.journal.totals()['complete'],1)

    def test_pending_never_retried(self):
        _,_,p,s,t=self.prompts[0]
        self.journal.ask('trial/r6/planning/B',c.MODEL,p,s,t)
        path=next(self.journal.path.glob('*.json'));record=c.read(path)
        record['status']='pending';record.pop('response');atomic_json(path,record)
        with self.assertRaises(StopRun):self.journal.ask('trial/r6/planning/B',c.MODEL,p,s,t)
        self.assertEqual(self.mock.backend.calls,1)

    def test_schema_missing_and_type_rejected(self):
        schema=self.prompts[3][2][2]['schema']
        with self.assertRaises(ValueError):validate({},schema)
        payload=self.journal.payload(c.MODEL,self.prompts[3][2],1,1)
        value=json.loads(self.mock(payload)['content']);value['score']='8'
        with self.assertRaises(ValueError):validate(value,schema)
        value['score']=11
        with self.assertRaises(ValueError):validate(value,schema)

    def test_live_gate_requires_explicit_stage_approval(self):
        with self.assertRaises(SystemExit):
            c.main(['--source',str(self.source),'--output',str(self.root),'--stage','probe','--max-requests','5','--budget-usd','.1'])

    def test_changed_source_stops_before_dispatch(self):
        self.cp['extra']='changed';atomic_json(self.source/'checkpoint-000/checkpoint.json',self.cp)
        _,_,p,s,t=self.prompts[0]
        with self.assertRaises(StopRun):self.journal.ask('trial/r6/planning/B',c.MODEL,p,s,t)
        self.assertEqual(self.mock.backend.calls,0)

if __name__=='__main__':unittest.main()
