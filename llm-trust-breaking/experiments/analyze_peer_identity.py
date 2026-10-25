"""Rebuild tables and figures from saved (possibly partial) peer-identity results."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from peer_identity.analysis import analyze, power_plan
if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--meaningful-change',type=float,help='Optional prespecified effect size in contribution tokens for rough power planning')
    args=parser.parse_args()
    print(json.dumps(analyze(args.directory),indent=2))

    if args.meaningful_change is not None:
        print(json.dumps(power_plan(args.directory,args.meaningful_change),indent=2))
