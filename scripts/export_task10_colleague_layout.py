"""Relocate task10 scenes and byte-identical producer resources for colleague use."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.export_task09_colleague_layout import semantic_snapshot


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def export_layout(package, out):
    from pxr import Usd, UsdUtils, UsdPhysics, UsdLux
    package, out = Path(package).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError(out)
    producer = package/'assets/composed/producer'
    out.mkdir(parents=True)
    for version in ('41','45'):
        mdl = producer/f'materials/isaac{version}/deps/mdl'
        if mdl.exists():
            shutil.copytree(mdl,out/f'SubUSDs/materials/isaac{version}')

    def localize(path):
        if not path:
            return path
        source = Path(path).resolve()
        relative = source.relative_to(producer)
        parts = relative.parts
        if parts[:3] == ('source','SubUSDs','textures'):
            destination = Path('SubUSDs/textures').joinpath(*parts[3:])
        elif parts[0] == 'materials' and parts[2:4] == ('deps','mdl'):
            destination = Path('SubUSDs/materials')/parts[1]/Path(*parts[4:])
        elif parts[:3] == ('source','SubUSDs','materials'):
            destination = Path('SubUSDs/materials/source').joinpath(*parts[3:])
        else:
            raise ValueError('Unexpected producer dependency: '+str(source))
        target = out/destination
        if target.exists():
            if sha(target) != sha(source):
                raise ValueError('Resource name collision: '+str(destination))
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
        return './'+destination.as_posix()

    entries = {}
    for name, entry in [('main','scene.usd'),('isaac45','scene_isaac45.usda')]:
        source = Usd.Stage.Open(str(package/f'scene/{name}.usda'))
        if any(p.IsA(UsdPhysics.Scene) or p.HasAPI(UsdLux.LightAPI) for p in source.Traverse()):
            raise ValueError('Clean entry contains a PhysicsScene or light')
        expected = semantic_snapshot(source)
        layer = source.Flatten(addSourceFileComment=False)
        UsdUtils.ModifyAssetPaths(layer,localize)
        # Flatten can drop the custom bit from a blocked primvar. Preserve
        # authored attribute metadata as part of exact semantic relocation.
        for prim in source.Traverse():
            for attr in prim.GetAttributes():
                spec = layer.GetAttributeAtPath(attr.GetPath())
                if spec is not None:
                    spec.custom = attr.IsCustom()
        layer.Export(str(out/entry),args={'format':'usdc'} if name == 'main' else {})
        delivered = Usd.Stage.Open(str(out/entry))
        if semantic_snapshot(delivered) != expected:
            raise ValueError('Export changed composed scene semantics')
        layers,assets,missing = UsdUtils.ComputeAllDependencies(str(out/entry))
        dependencies = [Path(p.realPath) for p in layers if p.realPath]+[Path(p) for p in assets]
        if missing or any(not p.resolve().is_relative_to(out) for p in dependencies):
            raise ValueError('Export has unresolved or external dependencies: '+str(missing))
        entries[entry] = {'semantic_parity':True,'missing':[],'sha256':sha(out/entry)}
    return {'status':'pass','scope':'static_export_parity_only','entries':entries,
            'files':{p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args = parser.parse_args()
    report = export_layout(args.package,args.out)
    args.evidence.parent.mkdir(parents=True,exist_ok=True)
    args.evidence.write_text(json.dumps(report,indent=2))
    print(args.out)
