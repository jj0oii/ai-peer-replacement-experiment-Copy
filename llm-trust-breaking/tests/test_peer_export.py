"""Sharing tests: deterministic local mocks, no network access."""
import copy
import csv
import fcntl
import gzip
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from peer_identity.export import (ExportError, export_bundle, verify_bundle, build_datasets,
    validate_datasets, sources, scan, file_sha)
from peer_identity.inference import Journal, MockTransport, StopRun, HTTPFailure, atomic_json, digest
from peer_identity.protocol import Config, run_study

ROOT=Path(__file__).resolve().parents[1]

class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.parent=Path(cls.tmp.name)
        cls.source=cls.parent/'batch'
        cls.cfg=Config(checkpoints=1)
        cls.socket_patch=patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK FORBIDDEN'))
        cls.socket_patch.start()
        cls.transport=MockTransport()
        run_study(cls.cfg,cls.source,Journal(cls.source,cls.transport,458,20,mock=True))
        cls.bundle,cls.report=export_bundle(cls.source,cls.parent/'bundle')
    @classmethod
    def tearDownClass(cls):
        cls.socket_patch.stop();cls.tmp.cleanup()
    def clone(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        path=Path(temp.name)/'batch';shutil.copytree(self.source,path)
        return path
    def tables(self):
        manifest=json.loads((self.source/'manifest.json').read_text())
        batch=json.loads((self.source/'batch.json').read_text())
        tables,_,_=build_datasets(self.source,sources(self.source),manifest,batch)
        return tables,batch

    def test_complete_export_counts_and_baseline_not_duplicated(self):
        self.assertEqual(self.report['row_counts'],{'rounds':90,'detections':8,'trials':8,'checkpoints':1,'run_metrics':8})
        tables,batch=self.tables()
        self.assertEqual(sum(r['phase']=='establishment' for r in tables['rounds']),10)
        self.assertEqual(len({r['run_id'] for r in tables['trials']}),8)
        self.assertEqual(sum(r['api_requests'] for r in tables['trials']),408)
        self.assertEqual(tables['checkpoints'][0]['api_requests'],50)
        self.assertEqual(sum(r['known_cost_usd'] for r in tables['trials']),0)

    def test_downloaded_analysis_uses_only_compact_files(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle=Path(temp)/'download';shutil.copytree(self.bundle,bundle)
            (bundle/'raw.jsonl.gz').unlink()  # compact-only download works without LFS
            out=Path(temp)/'analysis'
            result=subprocess.run([sys.executable,str(bundle/'analyze.py'),str(bundle),'--output',str(out)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            summary=json.loads((out/'summary.json').read_text())
            self.assertEqual(summary['complete_continuations'],8)
            self.assertTrue(summary['mock'])
            self.assertEqual(summary['independent_checkpoints_with_results'],1)
            self.assertEqual(len(summary['recognition_by_condition']),8)
            with (out/'matched_checkpoint_effects.csv').open() as f:effects=list(csv.DictReader(f))
            self.assertEqual(len(effects),6)
            self.assertTrue(all(float(r['matched_immediate_change_a'])==0 for r in effects))

    def test_requested_run_metrics_fields_and_nonzero_formulas(self):
        from peer_identity.analyze_shared import compute_run_metrics, RUN_METRIC_FIELDS
        tables,batch=self.tables()
        self.assertEqual(len(tables['run_metrics']),8)
        self.assertEqual(list(tables['run_metrics'][0]),RUN_METRIC_FIELDS)
        run=tables['trials'][0]['run_id']
        row=next(r for r in tables['rounds'] if r['run_id']==run and r['agent']=='A' and r['round']==6)
        row['contribution']=2;row['trust_score']=3
        metric=next(r for r in compute_run_metrics(tables) if r['run_id']==run)
        self.assertEqual(metric['baseline_a_contribution'],4)
        self.assertEqual(metric['round6_a_contribution'],2)
        self.assertEqual(metric['immediate_contribution_change'],-2)
        self.assertAlmostEqual(metric['sustained_contribution_change'],-.4)
        self.assertAlmostEqual(metric['trust_rating_change'],-.2)

    def test_incomplete_run_metrics_do_not_zero_fill(self):
        from peer_identity.analyze_shared import compute_run_metrics
        tables,batch=self.tables();run=tables['trials'][0]['run_id']
        tables['rounds']=[r for r in tables['rounds'] if r['run_id']!=run or r['round']==6]
        tables['detections'][0]['judgment']=None
        metric=next(r for r in compute_run_metrics(tables) if r['run_id']==run)
        self.assertIsNone(metric['sustained_contribution_change'])
        self.assertIsNone(metric['post_a_trust_in_b'])
        self.assertIsNone(metric['detected_change'])

    def test_derived_metric_tampering_rejected(self):
        tables,batch=self.tables();tables['run_metrics'][0]['immediate_contribution_change']=99
        with self.assertRaises(ExportError):validate_datasets(tables,self.cfg,batch['batch_id'])

    def test_four_teammate_charts_generated(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'charts'
            run=subprocess.run([sys.executable,str(self.bundle/'charts.py'),str(self.bundle),'--output',str(out)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            for name in ['contributions','trust','detection_rates','matched_changes']:
                self.assertGreater((out/(name+'.png')).stat().st_size,1000)
                self.assertIn('SYNTHETIC MOCK DATA',(out/(name+'.svg')).read_text())
            with (out/'run_metrics.csv').open() as f:self.assertEqual(len(list(csv.DictReader(f))),8)
            self.assertIn('NOT RESEARCH FINDINGS',(out/'README.md').read_text())

    def test_metadata_actual_code_and_prompts(self):
        m=json.loads((self.bundle/'metadata.json').read_text())
        self.assertEqual(len(m['execution_commit_sha']),40)
        self.assertTrue(m['prompt_versions'])
        self.assertIn('src/endogenous/core/prompt_builders.py',m['prompt_versions'])
        self.assertEqual(m['config']['controlled_contribution'],3)
        self.assertTrue(m['batch']['created_at'])
        self.assertEqual(m['usage']['api_requests'],458)
        self.assertEqual(m['usage']['input_tokens'],45800)
        self.assertEqual(m['usage']['known_cost_usd'],0)

    def test_bundle_revalidates_independently(self):
        self.assertTrue(verify_bundle(self.bundle)['valid'])
        self.assertEqual(self.transport.calls,458)

    def test_export_never_overwrites_completed_bundle(self):
        sha=file_sha(self.bundle/'metadata.json')
        with self.assertRaises(ExportError):export_bundle(self.source,self.bundle)
        self.assertEqual(sha,file_sha(self.bundle/'metadata.json'))

    def test_separate_batches_have_unique_join_ids(self):
        path=self.parent/'second'
        cfg=Config(checkpoints=1,conditions=['C0'],settings=['natural'])
        run_study(cfg,path,Journal(path,MockTransport(),101,20,mock=True))
        second,_=export_bundle(path,self.parent/'second-bundle')
        m1=json.loads((self.bundle/'metadata.json').read_text());m2=json.loads((second/'metadata.json').read_text())
        self.assertNotEqual(m1['batch']['batch_id'],m2['batch']['batch_id'])

    def test_incomplete_establishment_preserves_missingness(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'partial';cfg=Config(checkpoints=1)
            with self.assertRaises(StopRun):run_study(cfg,path,Journal(path,MockTransport(),3,20,mock=True))
            out,report=export_bundle(path,Path(temp)/'export')
            self.assertEqual(report['row_counts']['rounds'],2)
            self.assertEqual(report['incomplete_trials'],8)
            with (out/'rounds.csv').open() as f:rows=list(csv.DictReader(f))
            self.assertTrue(all(r['contribution']=='' and r['payoff']=='' for r in rows))
            with (out/'trials.csv').open() as f:trials=list(csv.DictReader(f))
            self.assertTrue(all(r['status']=='not_started' for r in trials))

    def test_partial_continuation_error_and_pending_are_preserved(self):
        for pending in [False,True]:
            with self.subTest(pending=pending), tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'partial';cfg=Config(checkpoints=1,conditions=['C0'],settings=['natural'])
                transport=MockTransport()
                class Abrupt(BaseException):pass
                def fail(payload):
                    if transport.calls==51:
                        if pending:raise Abrupt()
                        raise TimeoutError('must not export exception message')
                    return transport(payload)
                j=Journal(path,fail,101,20,mock=True)
                with self.assertRaises(Abrupt if pending else StopRun):run_study(cfg,path,j)
                out,report=export_bundle(path,Path(temp)/'export')
                with (out/'trials.csv').open() as f:trial=next(csv.DictReader(f))
                self.assertEqual(trial['status'],'incomplete' if pending else 'error')
                self.assertEqual(trial['pending_requests'],'1' if pending else '0')
                self.assertFalse(trial['usage_complete']=='true')
                with gzip.open(out/'raw.jsonl.gz','rt') as f:raw=f.read()
                self.assertIn('pending' if pending else 'blocked',raw)
                self.assertNotIn('must not export exception message',raw)

    def test_missing_final_result_recovers_from_journal(self):
        path=self.clone();next(path.glob('checkpoint-*/*/result.json')).unlink()
        out,_=export_bundle(path,path.parent/'recovered')
        with (out/'trials.csv').open() as f:rows=list(csv.DictReader(f))
        self.assertEqual(sum(r['status']=='recovered_complete' for r in rows),1)

    def test_missing_field_fails_validation(self):
        tables,batch=self.tables();del tables['rounds'][0]['payoff']
        with self.assertRaises(ExportError):validate_datasets(tables,self.cfg,batch['batch_id'])

    def test_duplicate_run_and_round_ids_rejected(self):
        tables,batch=self.tables();tables['trials'][1]['run_id']=tables['trials'][0]['run_id']
        with self.assertRaises(ExportError):validate_datasets(tables,self.cfg,batch['batch_id'])
        tables,batch=self.tables();tables['rounds'].append(tables['rounds'][0].copy())
        with self.assertRaises(ExportError):validate_datasets(tables,self.cfg,batch['batch_id'])

    def test_wrong_condition_and_correctness_rejected(self):
        tables,batch=self.tables();tables['detections'][0]['condition']='C4'
        with self.assertRaises(ExportError):validate_datasets(tables,self.cfg,batch['batch_id'])
        tables,batch=self.tables();tables['detections'][0]['correct']=not tables['detections'][0]['correct']
        with self.assertRaises(ExportError):validate_datasets(tables,self.cfg,batch['batch_id'])

    def test_out_of_range_and_missing_complete_output_rejected(self):
        tables,batch=self.tables();tables['rounds'][0]['contribution']=6
        with self.assertRaises(ExportError):validate_datasets(tables,self.cfg,batch['batch_id'])
        tables,batch=self.tables();tables['rounds'][0]['trust_score']=None
        with self.assertRaises(ExportError):validate_datasets(tables,self.cfg,batch['batch_id'])

    def test_saved_result_labels_and_payoffs_cannot_disagree(self):
        for field in ['condition','payoff']:
            with self.subTest(field=field):
                path=self.clone();p=next(path.glob('checkpoint-*/*/result.json'));r=json.loads(p.read_text())
                if field=='condition':r['metadata']['condition']='C4'
                else:r['state']['rounds'][6]['outcomes']['payoffs']['A']=999
                atomic_json(p,r)
                with self.assertRaises(ExportError):export_bundle(path,path.parent/'invalid')

    def test_corrupt_or_missing_journal_rejected(self):
        path=self.clone();next((path/'requests').glob('*.json')).unlink()
        with self.assertRaises(ExportError):export_bundle(path,path.parent/'invalid')

    def test_environment_files_are_not_exported(self):
        path=self.clone();(path/'compute.env').write_text('NEVER_EXPORT_THIS_LOCAL_FILE')
        (path/'unrelated.log').write_text('NEVER_EXPORT_THIS_LOCAL_FILE')
        out,_=export_bundle(path,path.parent/'clean')
        with gzip.open(out/'raw.jsonl.gz','rt') as f:self.assertNotIn('NEVER_EXPORT_THIS_LOCAL_FILE',f.read())

    def test_pattern_known_value_and_sensitive_field_scans(self):
        fixtures=[{'text':'sk-proj-'+'X'*30},{'text':'ghp_'+'X'*30},{'authorization':'anything'},
                  {'text':'Bearer '+'X'*30},{'text':'-----BEGIN PRIVATE KEY-----'}]
        for value in fixtures:
            with self.assertRaises(ExportError):scan(value)
        with self.assertRaises(ExportError):scan({'text':'very-private-local-value'},['very-private-local-value'])

    def test_secret_in_model_output_blocks_export_without_leak(self):
        path=self.clone();p=next((path/'requests').glob('*.json'));r=json.loads(p.read_text())
        r['note']='sk-proj-'+'X'*30;atomic_json(p,r)
        destination=path.parent/'unsafe'
        with self.assertRaises(ExportError) as error:export_bundle(path,destination)
        self.assertNotIn(r['note'],str(error.exception));self.assertFalse(destination.exists())

    def test_safe_http_error_diagnostics_are_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'error';cfg=Config(checkpoints=1)
            def rejected(payload):raise HTTPFailure(429,'insufficient_quota')
            with self.assertRaises(StopRun):run_study(cfg,path,Journal(path,rejected,458,20,mock=True))
            out,_=export_bundle(path,Path(temp)/'export')
            with gzip.open(out/'raw.jsonl.gz','rt') as f:records=[json.loads(line) for line in f]
            failure=next(r['record'] for r in records if r['path'].startswith('requests/'))
            self.assertEqual(failure['http_status'],429)
            self.assertEqual(failure['error_code'],'insufficient_quota')
            self.assertEqual(HTTPFailure(401,'sk-proj-'+'X'*30).code,'unknown')

    def test_checksum_and_extra_file_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'bundle';shutil.copytree(self.bundle,path)
            (path/'rounds.csv').write_text('tampered')
            with self.assertRaises(ExportError):verify_bundle(path)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'bundle';shutil.copytree(self.bundle,path)
            (path/'compute.env').write_text('not a bundle member')
            with self.assertRaises(ExportError):verify_bundle(path)

    def test_symlink_sources_rejected(self):
        path=self.clone();p=next((path/'requests').glob('*.json'));target=path.parent/'external.json';shutil.move(p,target);p.symlink_to(target)
        with self.assertRaises(ExportError):export_bundle(path,path.parent/'unsafe')

    def test_live_writer_lock_blocks_export(self):
        with (self.source/'.run.lock').open('a') as f:
            fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(ExportError):export_bundle(self.source,self.parent/'locked')

    def test_legacy_unknown_commit_is_not_fabricated(self):
        path=self.clone();(path/'batch.json').unlink();(path/'source-snapshot.json').unlink()
        out,_=export_bundle(path,path.parent/'legacy')
        m=json.loads((out/'metadata.json').read_text())
        self.assertIsNone(m['execution_commit_sha'])
        self.assertEqual(m['batch']['identity_origin'],'legacy_export_adoption')

    def test_cli_completed_batch_is_not_overwritten(self):
        path=self.parent/'cli'
        command=[sys.executable,str(ROOT/'experiments/run_peer_identity.py'),'--mode','mock','--checkpoints','1',
                 '--conditions','C0','--settings','natural','--output',str(path)]
        first=subprocess.run(command,capture_output=True,text=True,cwd=ROOT)
        self.assertEqual(first.returncode,0,first.stderr)
        sha=file_sha(path/'run-status.json')
        second=subprocess.run(command,capture_output=True,text=True,cwd=ROOT)
        self.assertNotEqual(second.returncode,0)
        third=subprocess.run(command+['--resume'],capture_output=True,text=True,cwd=ROOT)
        self.assertEqual(third.returncode,0,third.stderr)
        self.assertEqual(sha,file_sha(path/'run-status.json'))

    def test_cli_stopped_attempt_is_retained_and_exportable(self):
        path=self.parent/'cli-stopped'
        command=[sys.executable,str(ROOT/'experiments/run_peer_identity.py'),'--mode','mock','--checkpoints','1',
                 '--max-requests','3','--output',str(path)]
        run=subprocess.run(command,capture_output=True,text=True,cwd=ROOT)
        self.assertNotEqual(run.returncode,0)
        attempts=list((path/'attempts').glob('*.json'));self.assertEqual(len(attempts),1)
        self.assertEqual(json.loads(attempts[0].read_text())['status'],'error')
        out,report=export_bundle(path,path.parent/'stopped-export')
        self.assertEqual(report['row_counts']['rounds'],2)

if __name__=='__main__':unittest.main()
