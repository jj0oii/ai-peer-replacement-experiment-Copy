"""Analyze separately collected held-out calibration JSON, without API calls."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from peer_identity.distance import measure_heldout
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path)
    args=p.parse_args()
    print(json.dumps(measure_heldout(json.loads(args.input.read_text())),indent=2))
