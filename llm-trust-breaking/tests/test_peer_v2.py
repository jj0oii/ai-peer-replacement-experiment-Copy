"""Offline Version 2 regression and measurement-validity tests."""
import copy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from peer_identity import measurements_v2 as m
from peer_identity.protocol import Config, initial_state, run_round, clone_branch, run_study, recognize
from peer_identity.inference import Journal, MockTransport, validate, StopRun
from peer_identity.export import export_bundle, verify_bundle, build_datasets, sources, validate_datasets, ExportError
from src.games.publicgoods import PublicGoodsGame

class V2Tests(unittest.TestCase):
    def config(self):return Config(checkpoints=1,protocol_version=m.VERSION,trust_threshold=8)
    def prompt(self,number=6):
        announcements={'A':{'stated_action':4},'B':{'stated_action':4}}
        outcomes={'choices':{'A':4,'B':3},'payoffs':{'A':6.25,'B':7.25}}
        return m.reflection_prompt(('system','old',{}),announcements,outcomes,'A',number)
    def response(self):
        return dict(partner_promised_contribution=4,partner_actual_contribution=3,promise_matched=False,
                    own_payoff=6.25,partner_payoff=7.25,assessment='Trust and promises differ.',score=10,
                    promise_reliability_1_10=3,predicted_next_partner_contribution=3)
    def test_scale_all_integer_values(self):
        for score in range(1,11):
            r=self.response();r['score']=score;validate(r,self.prompt()[2]['schema'])
    def test_invalid_missing_scores(self):
        for field in ['score','promise_reliability_1_10']:
            for value in [None,0,11,5.5,True,'10']:
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                    r=self.response();r[field]=value;validate(r,self.prompt()[2]['schema'])
            r=self.response();del r[field]
            with self.assertRaises(ValueError):validate(r,self.prompt()[2]['schema'])
    def test_facts_correct_and_incorrect(self):
        expected={k:v for k,v in self.response().items() if k in ['partner_promised_contribution','partner_actual_contribution','promise_matched','own_payoff','partner_payoff']}
        self.assertTrue(m.assess(self.response(),expected)['factual_assessment_correct'])
        for key,value in expected.items():
            r=self.response();r[key]=not value if type(value)is bool else value+1
            check=m.assess(r,expected)
            self.assertFalse(check['factual_assessment_correct']);self.assertIn(key,check['factual_errors'])
            self.assertEqual(r[key],check['factual_errors'][key]['reported'])
    def test_boolean_not_coerced(self):
        r=self.response();r['promise_matched']=1
        with self.assertRaises(ValueError):validate(r,self.prompt()[2]['schema'])
    def test_prediction_bounds(self):
        for val in [-1,6,2.5,None]:
            r=self.response();r['predicted_next_partner_contribution']=val
            with self.assertRaises(ValueError):validate(r,self.prompt()[2]['schema'])
    def test_no_round11_prediction(self):
        self.assertNotIn('predicted_next_partner_contribution',self.prompt(10)[2]['schema']['properties'])
    def test_neutral_recognition(self):
        text=m.recognition_prompt()[1]
        for hidden in ['round 6','C0','C1','C2','C3','OpenAI','gpt-']:
            self.assertNotIn(hidden,text)
        schema=m.recognition_prompt()[2]['schema']
        for judgment in ['SAME','CHANGED']:
            r={k:'Observed evidence.' for k in schema['properties']};r.update(judgment=judgment,confidence=95)
            validate(r,schema)
        del r['noticed_changes']
        with self.assertRaises(ValueError):validate(r,schema)
    def test_comprehension_payoffs_and_range(self):
        game=PublicGoodsGame(['A','B'],initial_tokens=5,multiplier=1.5)
        for a in range(6):
            for b in range(6):
                result=game.evaluate({'A':str(a),'B':str(b)})
                self.assertEqual(result['A'],5-a+.75*(a+b))
                self.assertEqual(result['B'],5-b+.75*(a+b))
        self.assertIn('fresh endowment of 5',m.RULES);self.assertIn('do not carry over',m.RULES)
        self.assertIn('0 through 5 inclusive',m.RULES)
    def test_v1_default_unchanged(self):
        c=Config();self.assertEqual(c.protocol_version,'publicgoods-peer-identity-v1');self.assertEqual(c.trust_threshold,4)
    def test_unknown_protocol_rejected(self):
        c=self.config();c.protocol_version='unknown'
        with self.assertRaises(ValueError):c.validate()

class V2Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.raw=cls.root/'raw'
        cls.cfg=Config(checkpoints=2,protocol_version=m.VERSION,trust_threshold=8)
        cls.network=patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK FORBIDDEN'));cls.network.start()
        cls.transport=MockTransport()
        run_study(cls.cfg,cls.raw,Journal(cls.raw,cls.transport,916,8,mock=True))
        cls.bundle,cls.report=export_bundle(cls.raw,cls.root/'export')
        cls.tables,_,_=build_datasets(cls.raw,sources(cls.raw),json.loads((cls.raw/'manifest.json').read_text()),json.loads((cls.raw/'batch.json').read_text()))
    @classmethod
    def tearDownClass(cls):cls.network.stop();cls.tmp.cleanup()
    def test_exact_counts_and_valid_export(self):
        self.assertEqual(self.transport.calls,916)
        self.assertEqual(self.report['row_counts'],{'rounds':180,'trials':16,'detections':16,'checkpoints':2,'run_metrics':16})
        self.assertTrue(verify_bundle(self.bundle)['valid'])
    def test_factual_and_promise_measures(self):
        rows=self.tables['rounds']
        self.assertTrue(all(r['factual_assessment_correct'] for r in rows))
        broken=[r for r in rows if r['agent']=='A' and r['setting']=='controlled']
        self.assertEqual(len(broken),40)
        self.assertTrue(all(r['promise_compliance'] is False for r in broken))
        self.assertTrue(all(r['partner_promised_contribution']==4 and r['partner_actual_contribution']==3 for r in broken))
        self.assertTrue(all(r['promise_compliance'] for r in rows if r['setting']=='natural'))
    def test_prediction_scoring(self):
        rows=self.tables['rounds']
        self.assertTrue(all(r['prediction_error']==1 for r in rows if r['agent']=='A' and r['setting']=='controlled' and r['round']<10))
        self.assertTrue(all(r['prediction_error'] is None and not r['prediction_evaluable'] for r in rows if r['round'] in [5,10]))
        self.assertTrue(all(r['round6_prediction_error']==1 for r in rows if r['agent']=='A' and r['setting']=='controlled' and r['round']==6))
    def test_structured_recognition(self):
        for r in self.tables['detections']:
            e=json.loads(r['recognition_evidence']);self.assertIn('noticed_changes',e);self.assertIn('alternative_explanations',e)
    def test_condition_state_invariants(self):
        for checkpoint in self.raw.glob('checkpoint-*'):
            results=[json.loads(p.read_text()) for p in checkpoint.glob('*/result.json')]
            self.assertEqual(len(results),8)
            self.assertEqual(len({r['metadata']['a_initial_state_hash'] for r in results}),1)
            self.assertEqual(len({r['metadata']['public_initial_hash'] for r in results}),1)
            by={r['metadata']['condition']:r['metadata'] for r in results}
            self.assertEqual(by['C0']['b_initial_state_hash'],by['C1']['b_initial_state_hash'])
            self.assertEqual(by['C2']['b_initial_state_hash'],by['C3']['b_initial_state_hash'])
            self.assertEqual(by['C3']['models']['B'],'gpt-4.1-mini')
    def test_export_tampering_rejected(self):
        for field,val in [('trust_score_1_10',11),('promise_compliance',False),('factual_assessment_correct',False),('prediction_error',99)]:
            tables=copy.deepcopy(self.tables);tables['rounds'][0][field]=val
            with self.subTest(field=field),self.assertRaises(ExportError):validate_datasets(tables,self.cfg,self.report['batch_id'])
    def test_bad_facts_retained_without_repair(self):
        class WrongFacts(MockTransport):
            def __call__(self,payload):
                result=super().__call__(payload)
                if 'promise_reliability_1_10' in payload['response_format']['json_schema']['schema']['properties']:
                    r=json.loads(result['content']);r['partner_actual_contribution']=0;result['content']=json.dumps(r)
                return result
        with tempfile.TemporaryDirectory() as tmp:
            transport=WrongFacts();state=initial_state();c=self.cfg
            run_round(state,{'A':c.model_a,'B':c.model_b},Journal(Path(tmp),transport,10,8,mock=True),'checkpoint-000/establishment',1,c.seed,c)
            self.assertEqual(transport.calls,10)
            self.assertFalse(state['rounds'][0]['agents']['A']['factual_validation']['factual_assessment_correct'])
            self.assertEqual(state['rounds'][0]['agents']['A']['reflection']['partner_actual_contribution'],0)

class V2FailureHandling(unittest.TestCase):
    def test_invalid_score_raw_saved_and_incomplete_export(self):
        class InvalidScore(MockTransport):
            def __call__(self,payload):
                response=super().__call__(payload)
                if 'promise_reliability_1_10' in payload['response_format']['json_schema']['schema']['properties']:
                    parsed=json.loads(response['content']);parsed['score']=11;response['content']=json.dumps(parsed)
                return response
        with tempfile.TemporaryDirectory() as tmp,patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK FORBIDDEN')):
            root=Path(tmp);raw=root/'raw';transport=InvalidScore();cfg=Config(checkpoints=1,protocol_version=m.VERSION,trust_threshold=8)
            with self.assertRaises(StopRun):run_study(cfg,raw,Journal(raw,transport,458,8,mock=True))
            self.assertEqual(transport.calls,9)
            blocked=[json.loads(p.read_text()) for p in (raw/'requests').glob('*.json') if json.loads(p.read_text())['status']=='blocked']
            self.assertEqual(len(blocked),1);self.assertEqual(json.loads(blocked[0]['response']['content'])['score'],11)
            bundle,report=export_bundle(raw,root/'export')
            self.assertTrue(verify_bundle(bundle)['valid']);self.assertEqual(report['incomplete_trials'],8)
    def test_nonfinite_and_bool_payoffs_rejected(self):
        for value in [float('nan'),float('inf'),True]:
            with self.assertRaises(ValueError):validate(value,{'type':'number'})
    def test_v2_heldout_scale_and_no_pooling(self):
        from peer_identity.distance import measure_heldout
        data={'source':'heldout_calibration','independent_of_experiment_outcomes':True,'protocol_version':m.VERSION,
              'records':[dict(prompt_id='x',prompt='same',model=model,contribution=3,announcement=3,trust=10,message='hello') for model in ['a','b']]}
        self.assertEqual(measure_heldout(data)['pairs'][0]['trust_difference_0to1'],0)
        data['records'][0]['protocol_version']='publicgoods-peer-identity-v1'
        with self.assertRaises(ValueError):measure_heldout(data)
