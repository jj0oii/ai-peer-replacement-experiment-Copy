"""Free planning/real-pilot cost refinement; never sends API requests."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from peer_identity.study_costs import estimate,refine,PRIMARY_INPUT_TOKENS,FULL_OUTPUT_TOKENS
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pilot',type=Path)
    a=p.parse_args()
    print(json.dumps(refine(a.pilot) if a.pilot else {
        'primary_full_output_scenario':estimate(PRIMARY_INPUT_TOKENS,FULL_OUTPUT_TOKENS),
        'recommended_total_usd':80,'recommended_reserve_usd':10,
        'existing_cumulative_limit_usd':60,'budget_increase_applied':False,
        'reference_scenarios':[estimate(i,o) for i,o in [(2000,150),(10000,300),(20000,500)]]},indent=2))
