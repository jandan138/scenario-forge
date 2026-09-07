"""Finalize exact-scene cold-start and retained-state rendering evidence."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import zipfile

from scripts.generate_fehlings_water_bath import write_task_documents


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--report',type=Path,action='append',required=True)
    args=parser.parse_args()
    root=args.root.resolve()
    scene_sha=sha256((root/'scene.usd').read_bytes()).hexdigest()
    reports=[json.loads(p.read_text()) for p in args.report]
    if len(reports)!=3 or len({p.resolve() for p in args.report})!=3:
        raise ValueError('three independent report paths required')
    if any(d['status']!='pass' or d['scene_sha256']!=scene_sha for d in reports):
        raise ValueError('three passes must bind to the exact scene')
    producer=root/'deps/objects/obj_sample_tube/evidence/manifest.json'
    if json.loads(producer.read_text())['overall_status']!='pass':
        raise ValueError('producer not qualified')
    evidence=root/'evidence'
    render=json.loads((evidence/'initial_scene/render_manifest.json').read_text())
    if render['status']!='pass' or len(render['images'])<6:
        raise ValueError('render incomplete')
    if render['report_sha256'] not in [sha256(p.read_bytes()).hexdigest() for p in args.report]:
        raise ValueError('renders do not refer to final reports')
    from PIL import Image,ImageDraw,ImageFont
    sheet=Image.new('RGB',(1920,580),'#18232c')
    draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',22)
    for i,(name,label) in enumerate([('outside_no_heating_closeup.png','Before heating | 0 s'),
                                    ('observed_closeup.png','After 120 s | observation')]):
        draw.text((i*960+15,8),label,fill='white',font=font)
        with Image.open(evidence/'initial_scene'/name) as frame:
            sheet.paste(frame.resize((960,540)),(i*960,40))
    sheet.save(evidence/'initial_scene/appearance_before_after.png')
    from pxr import Usd,UsdUtils
    stage=Usd.Stage.Open(str(root/'scene.usd'))
    if stage.GetDefaultPrim().GetPath().pathString!='/World':
        raise ValueError('unexpected default prim')
    write_task_documents(root)
    runtime=evidence/'runtime'
    runtime.mkdir(exist_ok=True)
    for i,p in enumerate(args.report,1):
        shutil.copy2(p,runtime/f'cold_start_{i}.json')
    for p in evidence.glob('diagnostic_*'):
        target=root.parent.parent/'diagnostic_renders'/p.name
        target.parent.mkdir(exist_ok=True)
        if not target.exists():
            shutil.move(str(p),str(target))
    layers,assets,unresolved=UsdUtils.ComputeAllDependencies(str(root/'scene.usd'))
    paths={Path(layer.realPath).resolve() for layer in layers if layer.realPath}|{Path(str(p)).resolve() for p in assets}
    external=[str(p) for p in paths if not p.is_relative_to(root)]
    if unresolved or external:
        raise ValueError(f'closure failed: {unresolved}, {external}')
    closure={'status':'pass','external':[],'unresolved':[],'dependency_count':len(paths)}
    (evidence/'package_closure.json').write_text(json.dumps(closure,indent=2)+'\n')
    path=root/'manifest.json'
    manifest=json.loads(path.read_text())
    manifest.update(status='pass',runtime_cold_starts=3,runtime_reports=[f'evidence/runtime/cold_start_{i}.json' for i in range(1,4)],
                    render_evidence='evidence/initial_scene/render_manifest.json',closure=closure)
    manifest['entrypoints'].update(task='task.yaml',metrics='metrics.yaml')
    manifest['claims'].update(scene_fixture_verified=True,visual_reaction_verified=True,
                            robot_policy_success=False,continuous_robot_grasp_verified=False)
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    if (root/'.fehlings_render.usda').exists():
        raise ValueError('temporary render layer remains')
    archive=Path(shutil.make_archive(str(root),'zip',root_dir=root.parent,base_dir=root.name))
    with zipfile.ZipFile(archive) as handle:
        if handle.testzip() is not None:
            raise ValueError('ZIP CRC failed')
    archive.with_suffix('.zip.sha256').write_text(sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
    print(archive)


if __name__=='__main__':
    main()
