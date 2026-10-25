"""Local, credential-free batch identity and allowlisted execution-source snapshots."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import uuid
from .inference import atomic_json


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def ensure_batch(directory, config=None, mock=None, legacy=False):
    directory=Path(directory)
    path=directory/'batch.json'
    if path.exists():
        return json.loads(path.read_text())
    root=Path(__file__).resolve().parents[1]
    def git(*args):
        r=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True)
        return r.stdout.strip() if r.returncode==0 else None
    sources={}
    if not legacy:
        files=[*root.glob('peer_identity/*.py'),*root.glob('experiments/*peer*.py'),
               *root.glob('src/games/*.py'),root/'src/endogenous/core/prompt_builders.py']
        sources={str(p.relative_to(root)):p.read_text() for p in sorted(set(files))}
        atomic_json(directory/'source-snapshot.json',sources)
    data={'schema_version':1,'batch_id':'batch_'+uuid.uuid4().hex,'created_at':utc_now(),
          'identity_origin':'legacy_export_adoption' if legacy else 'execution',
          'execution_git_commit':None if legacy else git('rev-parse','HEAD'),
          'execution_tree_dirty':None if legacy else bool(git('status','--porcelain')),
          'python_version':platform.python_version(),
          'source_sha256':{p:hashlib.sha256(text.encode()).hexdigest() for p,text in sources.items()},
          'config':config,'mock':mock}
    atomic_json(path,data)
    return data
