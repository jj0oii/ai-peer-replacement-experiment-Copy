"""Offline scientific-analysis regressions: matching, independent units and honest uncertainty."""
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import socket
import statistics
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from peer_identity.matched_statistics import interval,exact_binomial,analyze_rows,BOUNDS,run,load_bundle
from peer_identity.budget_review import groups,scenarios


def row(cp,condition,repetition=0,contribution=2):
 r=dict(checkpoint_id=cp,run_id=f'{cp}:{condition}:{repetition}',setting='natural',condition=condition,agent='A',repetition=repetition)
 r.update({k:(lo+hi)/2 for k,(lo,hi) in BOUNDS.items()});r.update(mean_contribution=contribution,
  sustained_contribution_change=contribution-2,recognition_changed=0,recognition_correct=int(condition in ['C0','C1']))
 return r

class IntervalTests(unittest.TestCase):
 def test_no_population_precision_claim_from_two_equal_values(self):
  result=interval([0,0],(-5,5));self.assertEqual(result['ci_low'],-5);self.assertEqual(result['ci_high'],5)
 def test_one_checkpoint_interval_withheld(self):
  result=interval([1],(-5,5));self.assertIsNone(result['ci_low']);self.assertEqual(result['n_checkpoints'],1)
 def test_large_sample_interval_shrinks(self):
  self.assertGreater(interval([0]*25,(-5,5))['ci_low'],-5)
 def test_invalid_values_refused(self):
  for values in [[float('nan'),0],[6,0]]:
   with self.assertRaises(ValueError):interval(values,(-5,5))
 def test_exact_small_n_binary_intervals(self):
  lo,hi=exact_binomial(0,2);self.assertEqual(lo,0);self.assertAlmostEqual(hi,1-math.sqrt(.025))
  lo,hi=exact_binomial(2,2);self.assertAlmostEqual(lo,math.sqrt(.025));self.assertEqual(hi,1)
  lo,hi=exact_binomial(1,2);self.assertAlmostEqual(lo,1-math.sqrt(.975));self.assertAlmostEqual(hi,math.sqrt(.975))
 def test_unpaired_repetitions_are_not_mixed(self):
  rows=[row('p0','C0',0,0),row('p0','C0',1,5),row('p0','C1',0,1),row('p1','C0',0,5),row('p1','C1',0,4)]
  matched,summary,_,_=analyze_rows(rows)
  selected=[r for r in matched if r['treatment']=='C1' and r['metric']=='mean_contribution']
  self.assertEqual([r['difference'] for r in selected],[1,-1]);self.assertTrue(all(r['matched_repetitions']==1 for r in selected))
  estimate=next(r for r in summary if r['treatment']=='C1' and r['metric']=='mean_contribution');self.assertEqual(estimate['n_checkpoints'],2);self.assertEqual(estimate['estimate'],0)
 def test_repetitions_collapsed_before_uncertainty(self):
  rows=[row(cp,c,rep,2+int(c=='C1')) for cp in ['p0','p1'] for c in ['C0','C1'] for rep in range(3)]
  _,summary,_,_=analyze_rows(rows)
  estimate=next(r for r in summary if r['treatment']=='C1' and r['metric']=='mean_contribution');self.assertEqual(estimate['n_checkpoints'],2)
 def test_duplicate_identity_rejected(self):
  r=row('p','C0')
  with self.assertRaises(ValueError):analyze_rows([r,r])
 def test_missing_pairs_reported_without_imputation(self):
  _,_,_,missing=analyze_rows([row('p','C1')]);self.assertTrue(any(r['reference']=='C0' for r in missing))

class BudgetTests(unittest.TestCase):
 def records(self):
  result=[]
  for (phase,model),n in groups(2).items():
   for k in range(n):result.append(dict(phase=phase,model=model,cost_usd=.001,usage={'prompt_tokens':3000 if k==0 else 1000,'completion_tokens':350 if k==0 else 100}))
  return result
 def test_request_schedule_exact_and_judges_not_double_counted(self):
  self.assertEqual(sum(groups(2).values()),916);self.assertEqual(sum(groups(5).values()),2290);self.assertEqual(sum(groups(23).values()),10534)
 def test_scenarios_preserve_sample_and_full_output_limit(self):
  prices={'gpt-4o-mini':(.15,.075,.6),'gpt-4.1-mini':(.4,.1,1.6),'gpt-5-mini':(.25,.025,2)}
  records=self.records();result=scenarios(records,2,prices)
  for name in ['observed_usage','higher_usage','full_output_stress']:
   rows=[r for r in result if r['scenario']==name];self.assertEqual(sum(r['remaining_requests'] for r in rows),10534);self.assertEqual(sum(r['next_batch_requests'] for r in rows),2290)
  self.assertTrue(all(r['output_tokens_per_call']==2000 for r in result if r['scenario']=='full_output_stress'))
  self.assertTrue(all(r['cache_assumption']=='No cache discount' for r in result if r['scenario']=='higher_usage'))
 def test_observed_cost_reference_uses_paid_cost_not_uncached_reprice(self):
  prices={'gpt-4o-mini':(.15,.075,.6),'gpt-4.1-mini':(.4,.1,1.6),'gpt-5-mini':(.25,.025,2)}
  rows=scenarios(self.records(),2,prices);obs=[r for r in rows if r['scenario']=='observed_usage']
  self.assertAlmostEqual(sum(r['remaining_checkpoint_cost_usd'] for r in obs),10.534)

class SevenCheckpointBudgetTests(unittest.TestCase):
 def test_review_after_seven_checkpoints_has_eighteen_remaining(self):
  from peer_identity.budget_review import run as review
  prices={'gpt-4o-mini':(.15,.075,.6),'gpt-4.1-mini':(.4,.1,1.6),'gpt-5-mini':(.25,.025,2)}
  records=[dict(phase=phase,model=model,cost_usd=.001,usage={'prompt_tokens':1000,'completion_tokens':100}) for (phase,model),count in groups(7).items() for _ in range(count)]
  meta={'config':{'protocol_version':'publicgoods-peer-identity-v2'},'price_assumptions_usd_per_million':prices,'spending_policy':{'prior_spend_allowance_usd':.4954921,'total_budget_usd':60,'safety_reserve_usd':10}}
  with tempfile.TemporaryDirectory() as tmp,patch('peer_identity.budget_review.load',return_value=(meta,records,7)):
   summary=review(Path(tmp)/'input',Path(tmp)/'output')
   self.assertEqual(summary['remaining_checkpoints'],18);self.assertEqual(summary['remaining_continuations'],144);self.assertEqual(summary['remaining_planned_requests'],8244)
   self.assertEqual(summary['next_batch']['checkpoint_start'],7);self.assertEqual(summary['next_batch']['new_cumulative_request_total_after_batch'],5496)

class ExportAnalysisTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from peer_identity.protocol import Config,run_study
  from peer_identity.inference import Journal,MockTransport
  from peer_identity.export import export_bundle
  cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.raw=cls.root/'raw'
  cls.network=patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK FORBIDDEN'));cls.network.start()
  run_study(Config(checkpoints=2,protocol_version='publicgoods-peer-identity-v2',trust_threshold=8),cls.raw,Journal(cls.raw,MockTransport(),916,8,mock=True))
  cls.bundle,_=export_bundle(cls.raw,cls.root/'bundle')
 @classmethod
 def tearDownClass(cls):cls.network.stop();cls.tmp.cleanup()
 def test_complete_mock_export_statistics_have_two_units(self):
  out=self.root/'stats';summary=run(self.bundle,out);self.assertEqual(summary['independent_completed_checkpoints'],2);self.assertEqual(summary['completed_continuations'],16)
  with (out/'matched_contrasts.csv').open() as f:rows=list(csv.DictReader(f))
  self.assertTrue(all(r['n_checkpoints']=='2' for r in rows));self.assertEqual({r['treatment']+'-'+r['reference'] for r in rows},{'C3-C2','C2-C1','C1-C0'})
 def test_compact_download_and_standalone_script(self):
  local=self.root/'compact';local.mkdir()
  for name in ['metadata.json','rounds.csv','trials.csv','detections.csv','checkpoints.csv','checksums.json']:shutil.copy2(self.bundle/name,local/name)
  script=self.root/'stats.py';script.write_bytes(Path(__file__).resolve().parents[1].joinpath('peer_identity/matched_statistics.py').read_bytes())
  result=subprocess.run([sys.executable,str(script),str(local),'--output',str(self.root/'standalone-output')],capture_output=True)
  self.assertEqual(result.returncode,0,result.stderr)
 def test_version1_not_pooled(self):
  folder=self.root/'v1';shutil.copytree(self.bundle,folder)
  p=folder/'metadata.json';meta=json.loads(p.read_text());meta['config']['protocol_version']='publicgoods-peer-identity-v1';p.write_text(json.dumps(meta))
  checks=json.loads((folder/'checksums.json').read_text());checks['metadata.json']=hashlib.sha256(p.read_bytes()).hexdigest();(folder/'checksums.json').write_text(json.dumps(checks))
  with self.assertRaises(ValueError):load_bundle(folder)
 def test_checksum_tampering_rejected(self):
  folder=self.root/'tampered';shutil.copytree(self.bundle,folder);(folder/'rounds.csv').write_text('tampered')
  with self.assertRaises(ValueError):load_bundle(folder)
 def test_mock_budget_data_never_represented_as_actual(self):
  from peer_identity.budget_review import load
  with self.assertRaises(ValueError):load(self.bundle)
