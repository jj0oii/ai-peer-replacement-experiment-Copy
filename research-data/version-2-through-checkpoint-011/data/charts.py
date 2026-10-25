"""Four reproducible teammate-review figures; no credentials or model calls.

Run copied charts.py beside analyze.py, or python -m peer_identity.review_charts.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import statistics
import sys
# Portable analysis must not add cache files inside a sealed sharing bundle.
sys.dont_write_bytecode = True

try:
    from .analyze_shared import analyze, csv_row
except ImportError:
    from analyze import analyze, csv_row


def average(values):
    values=list(values)
    return statistics.mean(values) if values else None


def create_charts(bundle, output):
    bundle=Path(bundle).resolve();output=Path(output).resolve()
    if output.is_relative_to(bundle):raise ValueError('Keep the review output outside the immutable bundle')
    tables,summary=analyze(bundle)  # validates compact-file checksums
    with (bundle/'rounds.csv').open(newline='') as f:rounds=list(csv.DictReader(f))
    metadata=json.loads((bundle/'metadata.json').read_text())
    output.mkdir(parents=True,exist_ok=False)
    os.environ.setdefault('MPLCONFIGDIR',str(output/'.matplotlib'))
    os.environ.setdefault('XDG_CACHE_HOME',str(output/'.cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    banner='SYNTHETIC MOCK DATA — NOT RESEARCH FINDINGS' if summary['mock'] else 'Exploratory pilot data — descriptive means'
    v2=metadata['config'].get('protocol_version')=='publicgoods-peer-identity-v2'
    settings=metadata['config']['settings'];conditions=metadata['config']['conditions'];plot_data=[]
    colors={'C0':'#0072B2','C1':'#009E73','C2':'#E69F00','C3':'#CC79A7'}
    labels={'C0':'C0 no swap','C1':'C1 sham','C2':'C2 same-model reset','C3':'C3 different model'}
    def save(fig,name):
        fig.suptitle(banner,fontsize=11)
        fig.tight_layout(rect=(0,0,1,.93))
        fig.savefig(output/(name+'.png'),dpi=160)
        fig.savefig(output/(name+'.svg'))
        plt.close(fig)
    for field,name,ylabel,limits in [('contribution','contributions','A contribution (tokens)',(-.2,5.2)),
                                     ('trust_score','trust','A trust in B (1–10)' if v2 else 'A trust in B (1–5)',(.8,10.2) if v2 else (.8,5.2))]:
        fig,axes=plt.subplots(1,len(settings),figsize=(6*len(settings),4),squeeze=False)
        for axis,setting in zip(axes[0],settings):
            for condition in conditions:
                values=[]
                for number in range(1,11):
                    group=[r for r in rounds if r['agent']=='A' and int(r['round'])==number and r[field]!='' and
                           (r['phase']=='establishment' if number<=5 else r['setting']==setting and r['condition']==condition)]
                    by_cp={}
                    for row in group:by_cp.setdefault(row['checkpoint_id'],[]).append(float(row[field]))
                    value=average(average(v) for v in by_cp.values())
                    values.append(value if value is not None else float('nan'))
                    plot_data.append({'measure':field,'setting':setting,'condition':condition,'round':number,
                                      'independent_checkpoints':len(by_cp),'mean':value})
                axis.plot(range(1,11),values,marker='o',color=colors[condition],label=labels[condition])
            axis.axvline(5.5,color='gray',linestyle='--',label='Branch point')
            axis.set(title=setting,xlabel='Round',ylabel=ylabel,ylim=limits,xticks=range(1,11))
            axis.legend(fontsize=8)
        save(fig,name)
    fig,axes=plt.subplots(1,len(settings),figsize=(6*len(settings),4),squeeze=False)
    for axis,setting in zip(axes[0],settings):
        for i,condition in enumerate(conditions):
            row=next((r for r in tables['recognition_by_condition'] if r['condition']==condition and r['setting']==setting),None)
            value=row['changed_rate_checkpoint_weighted'] if row else None
            axis.bar(i,value if value is not None else 0,color=colors[condition])
            axis.text(i,(value or 0)+.025,'missing' if value is None else f'{value:.0%}',ha='center',fontsize=8)
            plot_data.append({'measure':'detected_change','setting':setting,'condition':condition,'round':None,
                              'independent_checkpoints':row['independent_checkpoints'] if row else 0,'mean':value})
        axis.set(title=setting,xlabel='Condition',ylabel='Fraction answering CHANGED',ylim=(0,1.12),xticks=range(len(conditions)),xticklabels=conditions)
    save(fig,'detection_rates')
    fig,axes=plt.subplots(1,len(settings),figsize=(6*len(settings),4),squeeze=False)
    for axis,setting in zip(axes[0],settings):
        for i,condition in enumerate(conditions):
            group=[r for r in tables['matched_checkpoint_effects'] if r['setting']==setting and r['condition']==condition]
            value=0. if condition=='C0' else average(r['matched_immediate_change_a'] for r in group)
            axis.bar(i,value if value is not None else 0,color=colors[condition])
            axis.text(i,(value or 0)+.15,'reference' if condition=='C0' else 'missing' if value is None else f'{value:.2f}',ha='center',fontsize=8)
            plot_data.append({'measure':'matched_immediate_change','setting':setting,'condition':condition,'round':6,
                              'independent_checkpoints':len(group) if condition!='C0' else summary['independent_checkpoints_with_results'],'mean':value})
        axis.axhline(0,color='gray',linewidth=.8)
        axis.set(title=setting,xlabel='Condition',ylabel='Round-6 change minus matched C0 change',ylim=(-5.5,5.5),xticks=range(len(conditions)),xticklabels=conditions)
    save(fig,'matched_changes')
    with (output/'plot_data.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(plot_data[0]));writer.writeheader();writer.writerows(plot_data)
    for name,rows in tables.items():
        if rows:
            with (output/(name+'.csv')).open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(csv_row(row) for row in rows)
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (output/'README.md').write_text('# '+banner+'\n\nFour figures and their exact plotting values are saved here. Mean repetitions within each checkpoint first, then mean independent checkpoints. Baseline rounds are shared and shown identically across conditions. Natural and controlled panels are separate. Missing values are not scored as zero; detection missing bars are explicitly labelled. No uncertainty interval or research conclusion is inferred from deterministic mock fixtures.\n')
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle',type=Path,nargs='?',default=Path(__file__).resolve().parent)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();print(json.dumps(create_charts(args.bundle,args.output),indent=2))
if __name__=='__main__':main()
