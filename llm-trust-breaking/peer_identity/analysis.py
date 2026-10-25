"""Checkpoint-level matched summaries; no behavioral recognition classifier."""
from __future__ import annotations
import csv
import json
import os
from pathlib import Path
import random
import statistics
import math

from .inference import atomic_json

def mean(values):
    values = list(values)
    return statistics.mean(values) if values else None


def branch_metrics(result):
    rounds = result['state']['rounds']
    baseline, post = rounds[2:5], rounds[5:10]
    def avg(rs, agent, field):
        return mean(r['agents'][agent][field] for r in rs)
    base = avg(baseline, 'A', 'actual_contribution')
    trust_base = mean(r['agents']['A']['reflection']['score'] for r in baseline)
    recognition = result['recognition']
    truth = result['metadata']['truth_changed']
    changed = recognition['judgment'] == 'CHANGED'
    by_agent = {}
    for a in ['A', 'B']:
        by_agent[a] = {
            'mean_contribution': avg(post, a, 'actual_contribution'),
            'mean_payoff': mean(r['outcomes']['payoffs'][a] for r in post),
            'actual_commitment_breaking_rate': avg(post, a, 'commitment_breaking'),
            'proposed_commitment_breaking_rate': avg(post, a, 'proposed_commitment_breaking'),
            'promise_deception_rate': avg(post, a, 'promise_deception'),
            'contributions': [r['agents'][a]['actual_contribution'] for r in post]}
    # Descriptive lagged co-movement, NOT a causal reciprocity estimate.
    reciprocity = mean((post[i]['agents']['B']['actual_contribution'] - post[i-1]['agents']['B']['actual_contribution']) *
                      (post[i-1]['agents']['A']['actual_contribution'] - base) for i in range(1, 5))
    return {'checkpoint': result['checkpoint_id'], 'condition': result['metadata']['condition'],
        'setting': result['metadata']['setting'], 'repetition': result['repetition'],
        'category': result['metadata']['category'], 'high_trust': result['qualification']['high_trust'],
        'baseline_contribution_a': base,
        'immediate_change_a': post[0]['agents']['A']['actual_contribution'] - base,
        'post_average_change_a': avg(post, 'A', 'actual_contribution') - base,
        'trust_change_a': mean(r['agents']['A']['reflection']['score'] for r in post) - trust_base,
        'post_trust_a': [r['agents']['A']['reflection']['score'] for r in post],
        'post_contributions_a': [r['agents']['A']['actual_contribution'] for r in post],
        'post_contributions_b': [r['agents']['B']['actual_contribution'] for r in post],
        'contribution_recovery_a': mean(r['agents']['A']['actual_contribution'] for r in post[-2:]) - post[0]['agents']['A']['actual_contribution'],
        'mean_pool_fraction': mean(sum(r['outcomes']['choices'].values()) / 10 for r in post),
        'both_contribute_at_least_three_rate': mean(all(v >= 3 for v in r['outcomes']['choices'].values()) for r in post),
        'same_contribution_rate': mean(r['outcomes']['choices']['A'] == r['outcomes']['choices']['B'] for r in post),
        'recognition': recognition['judgment'], 'confidence': recognition['confidence'],
        'truth_changed': truth, 'correct': changed == truth, 'said_changed': changed,
        'descriptive_b_reciprocity': reciprocity, 'agents': by_agent}


def cluster_interval(values, seed=33):
    """Each value is already an independent checkpoint mean; resample checkpoints only."""
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    means = sorted(mean(rng.choices(values, k=len(values))) for _ in range(2000))
    return [means[49], means[1949]]


def analyze(directory, make_figures=True):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    results = [json.loads(p.read_text()) for p in sorted(directory.glob('checkpoint-*/*/result.json'))]
    rows = [branch_metrics(r) for r in results]
    # Average stochastic repetitions within checkpoint/condition/setting BEFORE inference.
    collapsed = []
    keys = sorted({(r['checkpoint'], r['setting'], r['condition']) for r in rows})
    for cp, setting, condition in keys:
        group = [r for r in rows if (r['checkpoint'], r['setting'], r['condition']) == (cp, setting, condition)]
        fields = ['immediate_change_a', 'post_average_change_a', 'trust_change_a', 'correct', 'said_changed', 'confidence',
                  'mean_pool_fraction', 'both_contribute_at_least_three_rate', 'same_contribution_rate']
        collapsed.append({'checkpoint': cp, 'setting': setting, 'condition': condition,
            'high_trust': group[0]['high_trust'], 'completed_repetitions': len(group),
            **{f: mean(r[f] for r in group) for f in fields}})
    lookup = {(r['checkpoint'], r['setting'], r['condition']): r for r in collapsed}
    # Pair the SAME repetition before averaging; partial runs never mix unmatched repetitions.
    matched = []
    for row in collapsed:
        for reference in ['C0', 'C2']:
            if reference == row['condition']:
                continue
            treatments = {r['repetition']: r for r in rows if r['checkpoint'] == row['checkpoint'] and
                r['setting'] == row['setting'] and r['condition'] == row['condition']}
            controls = {r['repetition']: r for r in rows if r['checkpoint'] == row['checkpoint'] and
                r['setting'] == row['setting'] and r['condition'] == reference}
            shared = sorted(treatments.keys() & controls.keys())
            if shared:
                record = {k: row[k] for k in ['checkpoint', 'setting', 'condition', 'high_trust']}
                record.update(reference=reference, matched_repetitions=len(shared))
                for f in ['immediate_change_a', 'post_average_change_a', 'trust_change_a']:
                    record['matched_' + f] = mean(treatments[i][f] - controls[i][f] for i in shared)
                matched.append(record)
    comparisons = []
    for setting, condition, reference in sorted({(r['setting'], r['condition'], r['reference']) for r in matched}):
        for subset in ['all_valid', 'high_trust']:
            group = [r for r in matched if (r['setting'], r['condition'], r['reference']) == (setting, condition, reference)
                     and (subset == 'all_valid' or r['high_trust'])]
            values = [r['matched_immediate_change_a'] for r in group]
            comparisons.append({'setting': setting, 'condition': condition, 'reference': reference,
                'subset': subset, 'independent_checkpoints': len(values),
                'mean_matched_immediate_change': mean(values),
                'checkpoint_bootstrap_95_interval': cluster_interval(values),
                'mean_matched_post_average_change': mean(r['matched_post_average_change_a'] for r in group),
                'mean_matched_trust_change': mean(r['matched_trust_change_a'] for r in group)})
    recognition = []
    for setting in manifest['config']['settings']:
        group = [r for r in collapsed if r['setting'] == setting]
        negatives = [r for r in group if r['condition'] in ('C0', 'C1')]
        positives = [r for r in group if r['condition'] in ('C2', 'C3')]
        tpr, fpr = mean(r['said_changed'] for r in positives), mean(r['said_changed'] for r in negatives)
        recognition.append({'setting': setting, 'accuracy_checkpoint_weighted': mean(r['correct'] for r in group),
            'true_positive_rate': tpr, 'false_positive_rate': fpr,
            'balanced_accuracy': (tpr + 1-fpr)/2 if tpr is not None and fpr is not None else None,
            'by_condition': {c: {'changed_rate': mean(r['said_changed'] for r in group if r['condition'] == c),
                'confidence_values': [r['confidence'] for r in rows if r['condition'] == c and r['setting'] == setting],
                'independent_checkpoints': sum(r['condition'] == c for r in group),
                'changed_rate_checkpoint_bootstrap_95_interval': cluster_interval([r['said_changed'] for r in group if r['condition'] == c])}
                for c in manifest['config']['conditions']}})
    # Find first descriptive divergence from the matched C0 trajectory (no claim of recognition).
    for row in rows:
        controls = [r for r in rows if r['checkpoint'] == row['checkpoint'] and r['setting'] == row['setting'] and
                    r['repetition'] == row['repetition'] and r['condition'] == 'C0']
        row['first_observed_contribution_divergence_round'] = next((6+i for i,(a,b) in
            enumerate(zip(row['post_contributions_a'], controls[0]['post_contributions_a'])) if a != b), None) if controls else None
    cps = [json.loads(p.read_text()) for p in directory.glob('checkpoint-*/checkpoint.json')]
    target = manifest['config']['checkpoints'] * len(manifest['config']['conditions']) * len(manifest['config']['settings']) * manifest['config']['repetitions']
    summary = {'schema_version': 1, 'mock': manifest['mock'], 'completed_checkpoints': len(cps),
        'expected_continuations': target, 'completed_continuations': len(rows), 'incomplete_continuations': target-len(rows),
        'high_trust_checkpoints': sum(cp['qualification']['high_trust'] for cp in cps),
        'qualification_failure_rate': mean(not cp['qualification']['high_trust'] for cp in cps),
        'matched_comparisons': comparisons, 'recognition': recognition,
        'recognition_behavior_descriptive': [
            {'setting': setting, 'judgment': judgment, 'continuations': len(g),
             'checkpoint_weighted_mean_immediate_change_a': mean(mean(r['immediate_change_a'] for r in g if r['checkpoint']==cp) for cp in {r['checkpoint'] for r in g})}
            for setting in manifest['config']['settings'] for judgment in ['SAME','CHANGED']
            for g in [[r for r in rows if r['setting']==setting and r['recognition']==judgment]]],
        'uncertainty_note': 'Exploratory percentile bootstrap over checkpoint means; fewer than 2 checkpoints yields no interval. Not a power guarantee.'}
    out = directory / 'analysis'
    out.mkdir(exist_ok=True)
    atomic_json(out / 'summary.json', summary)
    atomic_json(out / 'branch-metrics.json', rows)
    atomic_json(out / 'checkpoint-metrics.json', collapsed)
    atomic_json(out / 'matched-metrics.json', matched)
    for name, records in [('comparisons', comparisons), ('checkpoint-metrics', collapsed)]:
        if records:
            with (out / (name + '.csv')).open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(records[0]))
                writer.writeheader()
                writer.writerows(records)
    if make_figures and rows:
        os.environ.setdefault('MPLCONFIGDIR', str(out / '.matplotlib'))
        os.environ.setdefault('XDG_CACHE_HOME', str(out / '.cache'))
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2, 2, figsize=(10, 7))
        for index, setting in enumerate(manifest['config']['settings']):
            for c in manifest['config']['conditions']:
                group = [r for r in rows if r['setting'] == setting and r['condition'] == c]
                # Equal repetitions planned; partial runs may have unequal counts. Collapse by checkpoint per point.
                if group:
                    axes[index, 0].plot(range(6,11), [mean(mean(r['post_contributions_a'][i] for r in group if r['checkpoint']==cp)
                        for cp in {r['checkpoint'] for r in group}) for i in range(5)], marker='o', label=c)
                    axes[index, 1].plot(range(6,11), [mean(mean(r['post_trust_a'][i] for r in group if r['checkpoint']==cp)
                        for cp in {r['checkpoint'] for r in group}) for i in range(5)], marker='o', label=c)
            for col, label in enumerate(['A contribution', 'A trust toward B']):
                axes[index, col].set(title=setting + ': ' + label, xlabel='Round', ylabel=label)
                axes[index, col].legend()
        fig.suptitle(('MOCK DATA — pipeline validation only' if manifest['mock'] else 'Exploratory checkpoint means'))
        fig.tight_layout()
        fig.savefig(out / 'trajectories.png', dpi=150)
        plt.close(fig)
    return summary


def power_plan(directory, meaningful_change):
    """Rough paired-normal sample-size planning from checkpoint-level PILOT differences.

    Not a substitute for simulation, multiplicity adjustment, or bounded-outcome checks.
    No estimate from fewer than 3 checkpoints or a degenerate deterministic mock pilot.
    """
    if meaningful_change <= 0:
        raise ValueError('Meaningful contribution change must be positive')
    path=Path(directory)/'analysis/matched-metrics.json'
    matched=json.loads(path.read_text())
    mock=json.loads((Path(directory)/'manifest.json').read_text())['mock']
    estimates=[]
    for setting,condition,reference in sorted({(r['setting'],r['condition'],r['reference']) for r in matched}):
        values=[r['matched_immediate_change_a'] for r in matched if
                (r['setting'],r['condition'],r['reference'])==(setting,condition,reference)]
        sd=statistics.stdev(values) if len(values)>1 else None
        n=math.ceil(((1.959964+.841621)*sd/meaningful_change)**2) if not mock and len(values)>=3 and sd else None
        estimates.append({'setting':setting,'condition':condition,'reference':reference,
            'pilot_independent_checkpoints':len(values),'paired_sd':sd,
            'approximate_required_checkpoints_80pct_power':max(3,n) if n else None})
    result={'meaningful_change':meaningful_change,'estimates':estimates,
        'limitations':'Two-sided alpha .05, single comparison, paired-normal approximation. No guarantee; choose effect independently, account for co-primary outcomes/multiplicity, pilot variance uncertainty and bounded outcomes. Null for mock, <3 checkpoints or zero variance.'}
    atomic_json(Path(directory)/'analysis/power-plan.json',result)
    return result
