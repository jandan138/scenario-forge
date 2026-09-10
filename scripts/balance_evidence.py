"""Exact-content evidence checks for the force-weighing handoff."""
import hashlib

REQUIRED_CHECKS={'empty','container','tare','target','negative','reset','lifted_invalid',
                 'pressure_responds','pressure_recovers','move_recovers','overload'}


def scene_content_digest(root):
    h=hashlib.sha256()
    extensions={'.usd','.usda','.usdc','.mdl','.png','.jpg','.jpeg','.py'}
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.suffix.lower() in extensions and 'evidence' not in p.relative_to(root).parts:
            h.update(p.relative_to(root).as_posix().encode()+b'\0')
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def validate_task_reports(data,closure_digest,asset_digest):
    if len(data)!=6 or len({r.get('pid') for r in data})!=6 or any(not r.get('pid') for r in data):
        raise ValueError('six independent processes required')
    seen=set()
    for r in data:
        runtime=r.get('runtime','')[:3]
        if (runtime not in ('4.1','4.5') or r.get('status')!='passed'
                or r.get('closure_sha256')!=closure_digest or r.get('asset_sha256')!=asset_digest
                or abs(r.get('physics_dt',0)-1/120)>1e-9
                or not REQUIRED_CHECKS.issubset(r.get('checks',{}))
                or not all(v is True for v in r['checks'].values())):
            raise ValueError('unqualified or stale task evidence')
        seen.add((runtime,r.get('initialization')))
    expected={(v,m) for v in ('4.1','4.5') for m in ('omitted','zero','pressed')}
    if seen!=expected:
        raise ValueError('both runtimes require omitted, zero and nonzero initialization')
