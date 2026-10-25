"""Offline three-scenario review; no requests or policy mutations."""
from pathlib import Path
import runpy
if __name__=='__main__':runpy.run_path(str(Path(__file__).resolve().parents[1]/'peer_identity/budget_review.py'),run_name='__main__')
