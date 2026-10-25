"""Validate/export local Experiment 3.3 data, or verify a sealed sharing bundle. No network."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from peer_identity.export import ExportError, export_bundle, known_secrets, verify_bundle
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('--output',type=Path,help='New export directory; existing destinations are never overwritten')
    p.add_argument('--verify-export',action='store_true',help='Verify an existing bundle instead of creating one')
    a=p.parse_args()
    secrets=known_secrets(Path(__file__).resolve().parents[2]/'compute.env')
    try:
        if a.verify_export:
            if a.output:p.error('--output is not used with --verify-export')
            print(json.dumps(verify_bundle(a.source,secrets),indent=2))
        else:
            bundle,report=export_bundle(a.source,a.output,secrets)
            print(json.dumps({'bundle':str(bundle),'validation':report},indent=2))
    except (ExportError,ValueError,KeyError,TypeError) as e:
        # Validation messages identify structure/rule, never echo input values.
        raise SystemExit('Export validation failed ('+type(e).__name__+'); no bundle published.') from None
