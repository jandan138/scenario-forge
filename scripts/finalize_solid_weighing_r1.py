"""Package a dual-runtime force-weighing task only after exact-content validation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

from scripts.balance_evidence import scene_content_digest, validate_task_reports


def finalize(root,reports,producer,guide):
    from pxr import UsdUtils
    closure=scene_content_digest(root)
    asset_hash=hashlib.sha256((root/'deps/balance/asset.usda').read_bytes()).hexdigest()
    validate_task_reports([json.loads(p.read_text()) for p in reports],closure,asset_hash)
    source=json.loads((producer/'manifest.json').read_text())
    if source.get('status')!='promoted' or source.get('asset_sha256')!=asset_hash:
        raise ValueError('producer qualification missing or stale')
    closures={}
    for entry in ('scene.usd','scene_isaac41.usda'):
        layers,assets,missing=UsdUtils.ComputeAllDependencies(str(root/entry))
        paths=[*(Path(x.realPath) for x in layers if x.realPath),*(Path(x) for x in assets)]
        if missing or any(not p.resolve().is_relative_to(root.resolve()) for p in paths):
            raise ValueError('task dependency closure failed')
        closures[entry]={'status':'pass','layers':len(layers),'assets':len(assets),'unresolved':[]}
    evidence=root/'evidence'
    evidence.mkdir(exist_ok=True)
    review_path=root.parent.parent/'evidence/visual_review.json'
    review=json.loads(review_path.read_text())
    if review.get('status') not in ('PASS','WARN') or review.get('closure_sha256')!=closure:
        raise ValueError('visual review missing, failed or stale')
    images=[]
    (evidence/'images').mkdir(exist_ok=True)
    for item in review['images']:
        path=Path(item['source'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256'] or item['verdict']=='FAIL':
            raise ValueError('visual evidence changed or failed')
        dest=evidence/'images'/path.name
        shutil.copy2(path,dest)
        images.append({'path':str(dest.relative_to(root)),'sha256':item['sha256']})
    shutil.copy2(review_path,evidence/'visual_review.json')
    records=[]
    for i,path in enumerate(reports,1):
        dest=evidence/f'cold_start_{i}.json'
        shutil.copy2(path,dest)
        records.append({'path':str(dest.relative_to(root)),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
    text=re.sub(r'\[([^]]+)\]\(\.\./standards/[^)]+\)',r'\1（Scenario Forge 仓库 docs/standards）',guide.read_text())
    (root/'README.md').write_text(text)
    manifest=json.loads((root/'manifest.json').read_text())
    manifest.update(status='scene_fixture_verified',runtime_qualification='Isaac Sim 4.1 and 4.5; GPU TGS 120 Hz',
                    closure_sha256=closure,producer_manifest=source,runtime_evidence=records,
                    dependency_closure=closures,
                    visual_evidence={'status':review['status'],'review':'evidence/visual_review.json','images':images},
                    robot_policy_success=False,scope='prescribed live placements, physical force response and tare joint motion')
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2))
    # Refresh producer receipt only; scene and controller bytes stay unchanged.
    shutil.copy2(producer/'manifest.json',root/'deps/balance/manifest.json')
    shutil.copy2(producer/'material_closure.json',root/'deps/balance/material_closure.json')
    shutil.copytree(producer/'evidence',root/'deps/balance/evidence',dirs_exist_ok=True)
    assert scene_content_digest(root)==closure
    archive=root.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(root.rglob('*')):
            if path.is_file():
                z.write(path,str(Path(root.name)/path.relative_to(root)))
    with zipfile.ZipFile(archive) as z:
        if z.testzip():
            raise ValueError('ZIP CRC failure')
    result={'root':str(root),'zip':str(archive),'scene_sha256':manifest['scene_sha256'],
            'closure_sha256':closure,'zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    (root.parent/'delivery_receipt.json').write_text(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--report',type=Path,action='append',required=True)
    p.add_argument('--producer',type=Path,required=True)
    p.add_argument('--guide',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(finalize(a.root,a.report,a.producer,a.guide),indent=2))
