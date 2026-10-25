"""Offline study-window, cumulative-spending and 200-trial planning checks."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from peer_identity.inference import Journal,MockTransport,StopRun,atomic_json
from peer_identity.protocol import Config,run_study,PARAMS
from peer_identity.spending import study_budget,window_policy
from peer_identity.study_costs import groups,estimate,refine
from src.endogenous.core.prompt_builders import build_stage1_prompt

ROOT=Path(__file__).resolve().parents[1]

class StudyBudgetTests(unittest.TestCase):
    def test_exact_two_hundred_trial_counts_and_phase_estimates(self):
        cfg=Config(checkpoints=25,repetitions=1)
        self.assertEqual(cfg.checkpoints*len(cfg.conditions)*len(cfg.settings),200)
        self.assertEqual(cfg.calls(),11450)
        self.assertEqual(sum(groups().values()),11450)
        self.assertAlmostEqual(estimate(10000,300)['total_usd'],25.231)
        self.assertAlmostEqual(estimate(20000,500)['total_usd'],49.36)
        self.assertAlmostEqual(estimate(20000,2000)['total_usd'],65.89)

    def test_persistent_budget_cannot_be_reset_between_batches(self):
        with tempfile.TemporaryDirectory() as temp:
            p=study_budget(temp,60,10,.01,11450)
            self.assertAlmostEqual(p['request_ledger_ceiling_usd'],49.99)
            self.assertEqual(study_budget(temp,60,10,.01,11450),p)
            with self.assertRaises(StopRun):study_budget(temp,120,10,.01,11450)
            window_policy(temp,0,2,916,8)
            with self.assertRaises(StopRun):window_policy(temp,0,2,916,16)

    def test_global_request_and_cost_ledger_reloads(self):
        prompt=build_stage1_prompt('publicgoods','A',['A','B'],PARAMS)
        with tempfile.TemporaryDirectory() as temp:
            t=MockTransport();j=Journal(temp,t,1,1,mock=True)
            j.ask('checkpoint-000/r1/planning/A','gpt-4o-mini',prompt,1)
            j2=Journal(temp,t,1,1,mock=True)
            with self.assertRaises(StopRun):j2.ask('checkpoint-001/r1/planning/A','gpt-4o-mini',prompt,2)
            self.assertEqual(t.calls,1)

    def test_cumulative_dollar_guard_does_not_reset_on_resume(self):
        prompt=build_stage1_prompt('publicgoods','A',['A','B'],PARAMS)
        with tempfile.TemporaryDirectory() as temp:
            t=MockTransport()  # Fake local responses, accounted at real rates; no network.
            j=Journal(temp,t,10,1,mock=False)
            j.ask('checkpoint-000/r1/planning/A','gpt-4o-mini',prompt,1)
            r=j.records()[0]
            j2=Journal(temp,t,10,r['reserved_usd']+r['cost_usd']/2,mock=False)
            with self.assertRaises(StopRun):j2.ask('checkpoint-001/r1/planning/A','gpt-4o-mini',prompt,1)
            self.assertEqual(t.calls,1)
            self.assertGreater(j2.totals()['accounted_usd'],0)

    def test_verified_prices_and_full_output_limit_match_actual_payload(self):
        from peer_identity.study_costs import pricing_status,FULL_OUTPUT_TOKENS
        self.assertTrue(pricing_status()['prices_live_verified'])
        prompt=build_stage1_prompt('publicgoods','A',['A','B'],PARAMS)
        with tempfile.TemporaryDirectory() as temp:
            t=MockTransport();Journal(temp,t,1,1,mock=True).ask('one','gpt-4o-mini',prompt,1)
            self.assertEqual(t.payloads[0]['max_completion_tokens'],FULL_OUTPUT_TOKENS)
            self.assertEqual(FULL_OUTPUT_TOKENS,2000)

    def test_pilot_refinement_keeps_full_output_even_for_short_fixture_answers(self):
        # Synthetic responses in a disposable ledger test the projection arithmetic;
        # no actual API or persistent research data is used.
        with tempfile.TemporaryDirectory() as temp:
            cfg=Config(checkpoints=2)
            run_study(cfg,temp,Journal(temp,MockTransport(),916,8,mock=False))
            result=refine(temp)
            self.assertFalse(result['projection_withheld'])
            self.assertEqual(result['observed_requests'],916)
            self.assertTrue(all(r['full_output_forecast_output_tokens_per_call']==2000 for r in result['rows']))
            self.assertTrue(all(r['full_output_forecast_input_tokens_per_call']>=20000 for r in result['rows']))
            expected=result['observed_cost_usd']+sum(r['remaining_full_output_forecast_usd'] for r in result['rows'])
            self.assertAlmostEqual(result['primary_full_output_total_including_prior_usd'],expected)
            self.assertGreater(expected,60)

    def test_budget_increase_requires_explicit_flag_and_retains_ledger(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('amender',ROOT/'experiments/amend_peer_budget.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            study_budget(temp,60,10,.01,11450)
            before=(Path(temp)/'budget-policy.json').read_bytes()
            preview=module.amend(temp,80,10,60,False)
            self.assertEqual(preview['status'],'preview_only_no_policy_change')
            self.assertEqual((Path(temp)/'budget-policy.json').read_bytes(),before)
            self.assertFalse((Path(temp)/'budget-history').exists())
            approved=module.amend(temp,80,10,60,True)
            self.assertEqual(approved['proposed_policy']['total_budget_usd'],80)
            self.assertEqual(approved['proposed_policy']['max_requests'],11450)
            self.assertAlmostEqual(approved['proposed_policy']['request_ledger_ceiling_usd'],69.99)
            self.assertEqual(len(list((Path(temp)/'budget-history').glob('*.json'))),1)

    def test_scope_cap_persists_on_resume_and_isolates_other_windows(self):
        prompt=build_stage1_prompt('publicgoods','A',['A','B'],PARAMS)
        with tempfile.TemporaryDirectory() as temp:
            t=MockTransport()
            j=Journal(temp,t,10,1,mock=True,scope_prefixes=['checkpoint-000'],scope_max_requests=1,scope_budget=.1)
            j.ask('checkpoint-000/r1/planning/A','gpt-4o-mini',prompt,1)
            j=Journal(temp,t,10,1,mock=True,scope_prefixes=['checkpoint-000'],scope_max_requests=1,scope_budget=.1)
            with self.assertRaises(StopRun):j.ask('checkpoint-000/r1/planning/B','gpt-4o-mini',prompt,2)
            other=Journal(temp,t,10,1,mock=True,scope_prefixes=['checkpoint-001'],scope_max_requests=1,scope_budget=.1)
            other.ask('checkpoint-001/r1/planning/A','gpt-4o-mini',prompt,2)
            self.assertEqual(t.calls,2)
            with self.assertRaises(StopRun):other.ask('checkpoint-002/r1/planning/A','gpt-4o-mini',prompt,3)

    def test_scope_dollar_guard_precedes_dispatch(self):
        prompt=build_stage1_prompt('publicgoods','A',['A','B'],PARAMS)
        with tempfile.TemporaryDirectory() as temp:
            t=MockTransport();j=Journal(temp,t,10,1,mock=True,scope_prefixes=['checkpoint-000'],scope_max_requests=10,scope_budget=.000001)
            with self.assertRaises(StopRun):j.ask('checkpoint-000/r1/planning/A','gpt-4o-mini',prompt,1)
            self.assertEqual(t.calls,0)

    def test_split_windows_match_unsplit_payloads_without_repeated_checkpoint(self):
        cfg=Config(checkpoints=2,conditions=['C0'],settings=['natural'])
        with tempfile.TemporaryDirectory() as temp:
            split=Path(temp)/'split';whole=Path(temp)/'whole'
            t=MockTransport();j=Journal(split,t,202,10,mock=True)
            run_study(cfg,split,j,0,1);self.assertEqual(t.calls,101)
            j=Journal(split,t,202,10,mock=True)
            run_study(cfg,split,j,1,1);self.assertEqual(t.calls,202)
            run_study(cfg,split,j,0,1);self.assertEqual(t.calls,202)
            run_study(cfg,whole,Journal(whole,MockTransport(),202,10,mock=True))
            def payloads(p):return {r['request_id_local']:r['payload'] for f in (p/'requests').glob('*.json') for r in [json.loads(f.read_text())]}
            self.assertEqual(payloads(split),payloads(whole))
            self.assertFalse(refine(split).get('projection_withheld') is False)

    def test_cli_windows_export_and_resume_without_new_requests(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'study';exports=Path(temp)/'exports'
            base=[sys.executable,str(ROOT/'experiments/run_peer_identity.py'),'--mode','mock','--checkpoints','2',
                '--conditions','C0','--settings','natural','--max-requests','202','--budget-usd','50',
                '--study-total-budget-usd','60','--reserve-usd','10','--prior-spend-usd','.01',
                '--checkpoint-count','1','--batch-max-requests','101','--batch-budget-usd','8',
                '--export-after-batch','--export-root',str(exports),'--output',str(root)]
            first=subprocess.run(base,capture_output=True,text=True,cwd=ROOT)
            self.assertEqual(first.returncode,0,first.stderr)
            self.assertEqual(json.loads((root/'run-status.json').read_text())['status'],'window_complete')
            second=subprocess.run(base+['--checkpoint-start','1','--resume'],capture_output=True,text=True,cwd=ROOT)
            self.assertEqual(second.returncode,0,second.stderr)
            self.assertEqual(json.loads((root/'run-status.json').read_text())['status'],'complete')
            self.assertEqual(len(list((root/'requests').glob('*.json'))),202)
            self.assertEqual(len(list(exports.glob('*/validation.json'))),2)

if __name__=='__main__':unittest.main()
