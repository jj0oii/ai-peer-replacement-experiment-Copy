"""All tests are offline; socket operations are blocked for this entire module."""
import copy
import importlib.util
import json
import pathlib
import socket
import tempfile
import unittest
from unittest.mock import patch
from contextlib import ExitStack

from peer_identity.inference import (Journal, MockTransport, DirectOpenAI, StopRun, ENDPOINT,
    atomic_json, digest, reservation, usage_cost, validate)
from peer_identity.protocol import (Config, PARAMS, HANDOFF, clone_branch, initial_state, run_round,
    run_study, recognize, state_context, qualification)
from peer_identity.analysis import analyze, branch_metrics, cluster_interval
from src.games.publicgoods import PublicGoodsGame
from src.endogenous.core.prompt_builders import build_stage1_prompt

SOCKET_BLOCK = ExitStack()
def setUpModule():
    for name in ['connect','connect_ex']:
        SOCKET_BLOCK.enter_context(patch.object(socket.socket,name,side_effect=AssertionError('NETWORK FORBIDDEN')))
    SOCKET_BLOCK.enter_context(patch.object(socket,'getaddrinfo',side_effect=AssertionError('NETWORK FORBIDDEN')))
def tearDownModule():
    SOCKET_BLOCK.close()

class StudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = pathlib.Path(cls.temp.name)
        cls.config = Config(checkpoints=2)
        cls.transport = MockTransport()
        cls.journal = Journal(cls.directory,cls.transport,916,100,mock=True)
        cls.results = run_study(cls.config,cls.directory,cls.journal)
        cls.cp = json.loads((cls.directory/'checkpoint-000/checkpoint.json').read_text())
        cls.summary = analyze(cls.directory,make_figures=False)
    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_public_goods_payoffs(self):
        game=PublicGoodsGame(['A','B'],**PARAMS)
        self.assertEqual(game.evaluate({'A':'5','B':'5'}),{'A':7.5,'B':7.5})
        self.assertEqual(game.evaluate({'A':'0','B':'5'}),{'A':8.75,'B':3.75})

    def test_exact_request_counts(self):
        self.assertEqual(self.transport.calls,916)
        self.assertEqual(self.transport.fresh_count,12)
        self.assertEqual(self.journal.totals()['completed'],916)
        self.assertEqual(Config(checkpoints=30,repetitions=3).calls(),38220)
        self.assertEqual(self.journal.totals()['accounted_usd'],0)

    def test_checkpoint_complete_serialization(self):
        self.assertEqual(len(self.cp['state']['rounds']),5)
        self.assertEqual(len(self.cp['state']['public']),5)
        self.assertEqual(len(self.cp['state']['agents']['A']['private']),5)
        self.assertEqual(json.loads(json.dumps(self.cp)),self.cp)
        self.assertEqual(digest(self.cp['state']),self.cp['state_hash'])
        self.assertEqual(self.cp['state']['agents']['A']['takeaways']['B']['score'],4)

    def test_branch_a_public_state_identical(self):
        for c in self.config.conditions:
            state,meta=clone_branch(self.cp,c,'natural',self.config)
            self.assertEqual(state['agents']['A'],self.cp['state']['agents']['A'])
            self.assertEqual(state['public'],self.cp['state']['public'])
            self.assertEqual(meta['a_initial_state_hash'],digest(self.cp['state']['agents']['A']))

    def test_branch_mutations_do_not_leak(self):
        x,_=clone_branch(self.cp,'C0','natural',self.config)
        y,_=clone_branch(self.cp,'C1','natural',self.config)
        x['agents']['A']['private'][0]['stage1']['reasoning']='changed'
        self.assertNotEqual(x['agents']['A'],y['agents']['A'])
        self.assertEqual(y['agents']['A'],self.cp['state']['agents']['A'])

    def test_no_swap_sham_identical_inputs_different_runtime(self):
        no,m0=clone_branch(self.cp,'C0','natural',self.config)
        sham,m1=clone_branch(self.cp,'C1','natural',self.config)
        self.assertEqual(no,sham)
        self.assertNotEqual(m0['runtime_ids']['B'],m1['runtime_ids']['B'])
        self.assertFalse(m0['truth_changed']);self.assertFalse(m1['truth_changed'])
        # First post-checkpoint B prompt identical, including inference seed.
        records=self.journal.records()
        def payload(c):
            return next(r['payload'] for r in records if r['request_id_local']==f'checkpoint-000/natural-{c}-rep000/r6/planning/B')
        self.assertEqual(payload('C0'),payload('C1'))

    def test_same_different_replacements_reset_only_b(self):
        states=[]
        for c,model in [('C2','gpt-4o-mini'),('C3','gpt-4.1-mini')]:
            state,meta=clone_branch(self.cp,c,'natural',self.config)
            self.assertEqual(meta['models']['B'],model)
            self.assertEqual(state['agents']['B'],{'private':[],'takeaways':{},'handoff':HANDOFF})
            self.assertTrue(meta['truth_changed']);states.append(state)
        self.assertEqual(states[0],states[1])

    def test_blinding_and_private_state_projection(self):
        state=copy.deepcopy(self.cp['state'])
        state['agents']['B']['private'][0]['stage1']['reasoning']='B_ONLY_SECRET'
        ctx=json.dumps(state_context(state,'A'))
        self.assertNotIn('B_ONLY_SECRET',ctx)
        forbidden=['C0','C1','C2','C3','OpenAI','OpenRouter','gpt-','checkpoint-','natural-C','controlled-C']
        for record in self.journal.records():
            text=json.dumps(record['payload']['messages'])
            for f in forbidden:
                self.assertNotIn(f,text)
            if '/recognition/' not in record['request_id_local']:
                self.assertNotIn('replacement',text.lower())

    def test_controlled_policy_and_proposal_logged(self):
        for result in self.results:
            for rnd in result['state']['rounds'][5:]:
                b=rnd['agents']['B']
                self.assertEqual(b['proposed_contribution'],4)
                self.assertEqual(b['actual_contribution'],3 if result['metadata']['setting']=='controlled' else 4)
                self.assertEqual(b['imposed'],result['metadata']['setting']=='controlled')
                self.assertEqual(b['commitment_breaking'],result['metadata']['setting']=='controlled')
                if b['imposed']:
                    self.assertEqual(rnd['outcomes']['payoffs'],{'A':6.25,'B':7.25})
                    self.assertIn('"B":3',json.dumps(rnd['outcomes']['choices'],separators=(',',':')))

    def test_round_order_and_no_outcome_leak_at_round6(self):
        r=self.results[0]['state']['rounds'][5]
        self.assertEqual([x['stage'] for x in r['events']],['planning']*2+['announcement']*2+['decision']*2+['judge']*2+['reflection']*2)
        records=self.journal.records()
        for x in records:
            if '/r6/decision/A' in x['request_id_local']:
                system=x['payload']['messages'][0]['content']
                self.assertIn('"round":5',system)
                self.assertNotIn('"round":6',system)
                self.assertIn('public announcements',x['payload']['messages'][1]['content'])

    def test_reflections_use_actual_outcomes(self):
        rec=next(r for r in self.journal.records() if r['request_id_local']=='checkpoint-000/controlled-C3-rep000/r6/reflection/A')
        text=rec['payload']['messages'][1]['content']
        self.assertIn('chose 3',text)
        self.assertIn('7.2',text)  # starter formats payoffs to one decimal

    def test_recognition_timing_and_truth_labels(self):
        with self.assertRaises(ValueError):
            recognize(self.cp['state'],self.journal,'bad','gpt-4o-mini',1,self.config)
        for result in self.results:
            self.assertEqual(len(result['state']['rounds']),10)
            self.assertEqual(result['recognition']['judgment'],'SAME')
        counts={m['setting']:m for m in self.summary['recognition']}
        for row in counts.values():
            self.assertEqual(row['false_positive_rate'],0)
            self.assertEqual(row['true_positive_rate'],0)
            self.assertEqual(row['balanced_accuracy'],.5)

    def test_analysis_matched_inputs_and_checkpoint_unit(self):
        self.assertEqual(self.summary['completed_checkpoints'],2)
        self.assertEqual(self.summary['completed_continuations'],16)
        self.assertEqual(self.summary['incomplete_continuations'],0)
        for row in self.summary['matched_comparisons']:
            self.assertEqual(row['independent_checkpoints'],2)
            self.assertEqual(row['mean_matched_immediate_change'],0)
        m=branch_metrics(self.results[0])
        self.assertEqual(m['immediate_change_a'],0)
        self.assertEqual(m['post_average_change_a'],0)

    def test_resume_completed_results_no_new_calls(self):
        t=MockTransport();j=Journal(self.directory,t,916,100,mock=True)
        again=run_study(self.config,self.directory,j)
        self.assertEqual(t.calls,0)
        self.assertEqual(again,self.results)

    def test_configuration_changes_refused_on_resume(self):
        cfg=copy.deepcopy(self.config);cfg.seed+=1
        with self.assertRaises(StopRun):run_study(cfg,self.directory,self.journal)

    def test_unqualified_histories_retained(self):
        state=copy.deepcopy(self.cp['state'])
        for rnd in state['rounds']:
            for a in ['A','B']:
                rnd['agents'][a]['actual_contribution']=0
                rnd['agents'][a]['reflection']['score']=1
        q=qualification(state,self.config)
        self.assertFalse(q['high_trust']);self.assertTrue(q['retained_in_primary_analysis'])

    def test_cross_provider_disabled(self):
        with self.assertRaises(ValueError):Config(conditions=['C0','C4']).validate()

    def test_checkpoint_independent_seeds(self):
        records=self.journal.records()
        seeds=[next(r['payload']['seed'] for r in records if r['request_id_local']==f'checkpoint-{i:03d}/establishment/r1/planning/A') for i in range(2)]
        self.assertNotEqual(seeds[0],seeds[1])

class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.directory=pathlib.Path(self.tmp.name)
        self.transport=MockTransport()
        self.prompt=build_stage1_prompt('publicgoods','A',['A','B'],PARAMS)
    def tearDown(self):self.tmp.cleanup()
    def journal(self,max_requests=100,budget=1,mock=True,transport=None):
        return Journal(self.directory,transport or self.transport,max_requests,budget,mock)
    def ask(self,j,identity='request',prompt=None):
        return j.ask(identity,'gpt-4o-mini',prompt or self.prompt,42)

    def test_count_limit_before_network(self):
        j=self.journal(max_requests=1)
        self.ask(j)
        with self.assertRaises(StopRun):self.ask(j,'second')
        self.assertEqual(self.transport.calls,1)

    def test_budget_limit_before_network(self):
        j=self.journal(budget=.000001)
        with self.assertRaises(StopRun):self.ask(j)
        self.assertEqual(self.transport.calls,0)

    def test_conservative_reservation_and_usage_cost(self):
        cost=usage_cost('gpt-4o-mini',{'prompt_tokens':1000,'completion_tokens':100,'prompt_tokens_details':{'cached_tokens':500}})
        self.assertAlmostEqual(cost,.0001725)
        payload={'model':'gpt-4o-mini','messages':[{'role':'user','content':'hello'}],'max_completion_tokens':2000}
        tokens,res=reservation(payload)
        self.assertGreater(tokens,1024);self.assertGreater(res,.0012)

    def test_cached_response_reused_and_copy_isolated(self):
        j=self.journal();answer=self.ask(j);answer['intended_action']=0
        self.assertEqual(self.ask(j)['intended_action'],4)
        self.assertEqual(self.transport.calls,1)

    def test_mid_round_resume_has_no_duplicate_calls(self):
        cfg=Config(checkpoints=1,conditions=['C0'],settings=['natural'])
        j=self.journal(max_requests=3)
        with self.assertRaises(StopRun):run_study(cfg,self.directory,j)
        self.assertEqual(self.transport.calls,3)
        second=MockTransport();j2=self.journal(max_requests=101,transport=second)
        result=run_study(cfg,self.directory,j2)
        self.assertEqual(second.calls,98)
        self.assertEqual(len(result),1)
        self.assertEqual(j2.totals()['requests'],101)

    def test_ambiguous_network_failure_not_retried(self):
        calls=[]
        def fail(payload):calls.append(1);raise TimeoutError('sensitive text must not be logged')
        j=self.journal(transport=fail)
        with self.assertRaises(StopRun):self.ask(j)
        with self.assertRaises(StopRun):self.ask(j)
        self.assertEqual(len(calls),1)
        self.assertNotIn('sensitive text',json.dumps(j.records()))
        self.assertGreater(j.totals()['accounted_usd'],0)

    def test_pending_crash_record_blocks_resume(self):
        class Crash(BaseException):pass
        def crash(payload):raise Crash()
        j=self.journal(transport=crash)
        with self.assertRaises(Crash):self.ask(j)
        j2=self.journal()
        with self.assertRaises(StopRun):self.ask(j2)
        self.assertEqual(self.transport.calls,0)

    def test_request_payload_change_refused(self):
        j=self.journal();self.ask(j)
        system,user,schema=self.prompt
        with self.assertRaises(StopRun):self.ask(j,prompt=(system,user+' changed',schema))
        self.assertEqual(self.transport.calls,1)

    def test_invalid_outputs_stop_no_repair_calls(self):
        for value in [None,'bad json',json.dumps({'intended_action':99,'reasoning':'bad'}),
                      json.dumps({'intended_action':True,'reasoning':'bad'}),json.dumps({'intended_action':2})]:
            with self.subTest(value=value),tempfile.TemporaryDirectory() as directory:
                def invalid(payload):
                    r=self.transport(payload);r['content']=value;return r
                j=Journal(directory,invalid,10,1,mock=True)
                before=self.transport.calls
                with self.assertRaises(StopRun):self.ask(j)
                with self.assertRaises(StopRun):self.ask(j)
                self.assertEqual(self.transport.calls-before,1)

    def test_truncated_outputs_block(self):
        def truncated(payload):
            r=self.transport(payload);r['finish_reason']='length';return r
        with self.assertRaises(StopRun):self.ask(self.journal(transport=truncated))

    def test_wrong_endpoint_or_model_blocked(self):
        for field,value in [('endpoint','https://openrouter.ai/api/v1/chat/completions'),('model_returned','different')]:
            with tempfile.TemporaryDirectory() as directory:
                def bad(payload):r=self.transport(payload);r[field]=value;return r
                with self.assertRaises(StopRun):self.ask(Journal(directory,bad,10,1,mock=True))

    def test_output_schema_confidence_bounds(self):
        from peer_identity.protocol import RECOGNITION
        for confidence in [-1,101,True]:
            with self.assertRaises(ValueError):validate({'judgment':'SAME','confidence':confidence,'evidence':'ok'},RECOGNITION['schema'])

    def test_nonfinite_budget_and_invalid_usage_rejected(self):
        for limit in [float('nan'),float('inf'),0,-1]:
            with self.assertRaises(ValueError):self.journal(budget=limit)
        with self.assertRaises(ValueError):usage_cost('gpt-4o-mini',{'prompt_tokens':-1,'completion_tokens':1})
        with self.assertRaises(ValueError):Config(temperature=float('nan')).validate()

    def test_repetitions_and_cluster_interval(self):
        self.assertIsNone(cluster_interval([1]))
        self.assertEqual(cluster_interval([0,0,0]),[0,0])
        self.assertEqual(Config(checkpoints=1,repetitions=3).calls(),1274)

    def test_direct_transport_uses_only_openai_no_redirect(self):
        env=self.directory/'test.env'
        env.write_text('LLM_BASE_URL=https://api.openai.com/v1\nLLM_API_KEY=FAKE_OFFLINE_TEST_ONLY\n')
        with patch.dict('os.environ',{'LLM_BASE_URL':'https://api.openai.com/v1','LLM_API_KEY':'FAKE_OFFLINE_TEST_ONLY','LLM_MODEL':''}):
            backend=DirectOpenAI(env)
            class FakeResponse:
                status_code=200;headers={'x-request-id':'offline'}
                def json(self):return {'id':'offline','model':'gpt-4o-mini','usage':{'prompt_tokens':1,'completion_tokens':1},'choices':[{'message':{'content':'{}'},'finish_reason':'stop'}]}
            fresh=backend.fresh()
            self.assertIsNot(fresh._session,backend._session)
            fresh.close()
            with patch.object(backend._session,'post',return_value=FakeResponse()) as post:
                backend({'model':'gpt-4o-mini'})
                self.assertEqual(post.call_args.args[0],ENDPOINT)
                self.assertFalse(post.call_args.kwargs['allow_redirects'])

class DistanceTests(unittest.TestCase):
    def data(self):
        return {'source':'heldout_calibration','independent_of_experiment_outcomes':True,'records':[
            {'prompt_id':'heldout-1','prompt':'same public state','model':m,'contribution':c,
             'announcement':5,'trust':t,'message':'cooperate'} for m,c,t in [('first',5,5),('second',0,1)]]}
    def test_normalized_heldout_features(self):
        from peer_identity.distance import measure_heldout
        p=measure_heldout(self.data())['pairs'][0]
        self.assertEqual(p['contribution_difference_0to1'],1)
        self.assertEqual(p['trust_difference_0to1'],1)
        self.assertEqual(p['promise_breaking_rate_difference_0to1'],1)
        self.assertEqual(p['message_vocabulary_jaccard_distance_0to1'],0)
    def test_outcome_reuse_and_mismatched_prompts_refused(self):
        from peer_identity.distance import measure_heldout
        d=self.data();d['source']='experiment_outcomes'
        with self.assertRaises(ValueError):measure_heldout(d)
        d=self.data();d['records'][1]['prompt']='different'
        with self.assertRaises(ValueError):measure_heldout(d)

if __name__=='__main__':unittest.main()
