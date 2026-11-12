"""Repackage the qualified task09 into scene.usd + SubUSDs without asset conversion."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def file_inventory(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def source_stage(package, version):
    from pxr import Usd, UsdGeom
    main = Usd.Stage.Open(str(package/'scene/main.usda'))
    # The old runtime-only wrappers omit stage metadata. Match the qualified
    # main/demo coordinate system, using an anonymous layer, never editing input.
    stage = Usd.Stage.CreateInMemory()
    stage.GetRootLayer().subLayerPaths = [str((package/f'scene/runtime{version}.usda').resolve())]
    UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.GetStageMetersPerUnit(main))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.GetStageUpAxis(main))
    stage.SetMetadata('kilogramsPerUnit', main.GetMetadata('kilogramsPerUnit'))
    stage.SetDefaultPrim(stage.GetPrimAtPath('/World'))
    return stage


def resource_destination(source, package):
    relative = source.resolve().relative_to(package.resolve())
    parts = relative.parts
    if parts[:4] == ('assets', 'composed', 'SubUSDs', 'textures'):
        return Path('SubUSDs/textures').joinpath(*parts[4:])
    if parts[:2] == ('assets', 'material_closure') and parts[4:6] == ('deps', 'mdl'):
        return Path('SubUSDs/materials').joinpath(parts[2], parts[3], *parts[6:])
    raise ValueError('Unrecognized dependency: '+str(source))


def normalized(value):
    from pxr import Sdf
    if isinstance(value, Sdf.AssetPath):
        if not value.path:
            return ('asset', '')
        if not value.resolvedPath:
            raise ValueError('Unresolved asset: '+value.path)
        return ('asset_sha256', sha(value.resolvedPath))
    if isinstance(value, Sdf.AssetPathArray):
        return tuple(normalized(v) for v in value)
    return str(value)


def semantic_snapshot(stage):
    """Compare composed task values, metadata, connections and relationships.

    Asset paths are compared by actual resource bytes so relocation is allowed.
    Unknown PhysX schemas are read from authored metadata, not HasAPI alone.
    """
    from pxr import UsdGeom
    result = {'meters': UsdGeom.GetStageMetersPerUnit(stage),
              'up': str(UsdGeom.GetStageUpAxis(stage)),
              'kilograms': stage.GetMetadata('kilogramsPerUnit'),
              'default': str(stage.GetDefaultPrim().GetPath()), 'prims': {}}
    for p in stage.Traverse():
        schemas = p.GetMetadata('apiSchemas')
        attrs = {}
        for a in p.GetAttributes():
            attrs[a.GetName()] = {
                'type': str(a.GetTypeName()), 'custom': a.IsCustom(),
                'value': normalized(a.Get()),
                'samples': [(t, normalized(a.Get(t))) for t in a.GetTimeSamples()],
                'connections': [str(x) for x in a.GetConnections()],
                'interpolation': a.GetMetadata('interpolation'),
                'variability': str(a.GetVariability()),
            }
        result['prims'][str(p.GetPath())] = {
            'type': p.GetTypeName(), 'active': p.IsActive(), 'instanceable': p.IsInstanceable(),
            'schemas': list(schemas.GetAppliedItems()) if schemas else [], 'attrs': attrs,
            'relationships': {r.GetName(): [str(x) for x in r.GetTargets()] for r in p.GetRelationships()},
        }
    return result


def check_layout(out, package):
    from pxr import Usd, UsdPhysics, UsdLux, UsdUtils
    out = out.resolve()
    results = {}
    for version, entry in [('41', 'scene.usd'), ('45', 'scene_isaac45.usda')]:
        stage = Usd.Stage.Open(str(out/entry))
        if any(p.IsA(UsdPhysics.Scene) or p.HasAPI(UsdLux.LightAPI) for p in stage.Traverse()):
            raise ValueError('Delivery must not contain physics scenes or lights')
        actual = semantic_snapshot(stage)
        expected = semantic_snapshot(source_stage(package, version))
        if actual != expected:
            different = [p for p in set(actual['prims']) | set(expected['prims'])
                         if actual['prims'].get(p) != expected['prims'].get(p)]
            raise ValueError('Composed task semantics changed: '+str(different[:10]))
        layers, assets, missing = UsdUtils.ComputeAllDependencies(str(out/entry))
        paths = [*(Path(x.realPath) for x in layers if x.realPath), *(Path(x) for x in assets)]
        if missing or any(not p.resolve().is_relative_to(out) for p in paths):
            raise ValueError('Unresolved or external dependency: '+str(missing))
        results[entry] = {'status': 'pass', 'semantic_parity': True,
                          'layers': len(layers), 'direct_assets': len(assets), 'missing': []}
    return results


def export_layout(package, out):
    from pxr import Usd, Sdf, UsdUtils
    package, out = package.resolve(), out.resolve()
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    # Reuse the already-qualified producer closures in full, preserving recursive
    # MDL imports and copyright notices. No MDL parsing/conversion is duplicated.
    for source in sorted((package/'assets/material_closure').glob('isaac*/task*/deps/mdl')):
        relative = source.relative_to(package/'assets/material_closure')
        shutil.copytree(source, out/'SubUSDs/materials'/relative.parts[0]/relative.parts[1])
    remap = {}

    def localize(path):
        if not path:
            return path
        source = Path(path)
        if not source.is_absolute() or not source.is_file():
            raise ValueError('Flatten did not resolve a dependency: '+path)
        destination = resource_destination(source, package)
        target = out/destination
        if target.exists():
            if sha(target) != sha(source):
                raise ValueError('Resource name collision: '+str(target))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        remap[str(source)] = destination.as_posix()
        return './'+destination.as_posix()

    sources = {v: source_stage(package, v) for v in ('41', '45')}
    layer = sources['41'].Flatten(addSourceFileComment=False)
    UsdUtils.ModifyAssetPaths(layer, localize)
    layer.Export(str(out/'scene.usd'), args={'format': 'usdc'})
    # Only genuinely different attributes are authored in the 4.5 wrapper.
    variant = Usd.Stage.CreateNew(str(out/'scene_isaac45.usda'))
    variant.GetRootLayer().subLayerPaths = ['./scene.usd']
    for key in ('metersPerUnit', 'upAxis', 'kilogramsPerUnit'):
        variant.SetMetadata(key, sources['45'].GetMetadata(key))
    variant.SetDefaultPrim(variant.GetPrimAtPath('/World'))
    overrides = []
    for prim in sources['45'].TraverseAll():
        old = sources['41'].GetPrimAtPath(prim.GetPath())
        for attr in prim.GetAttributes():
            value = attr.Get()
            before = old.GetAttribute(attr.GetName()).Get()
            # Different runtime modules can have equal bytes; keep distinct
            # runtime paths even in that case to preserve closure identity.
            if isinstance(value, Sdf.AssetPath):
                changed = value.resolvedPath != before.resolvedPath
            else:
                changed = value != before
            if not changed:
                continue
            if attr.GetName() not in ('node:type', 'info:mdl:sourceAsset'):
                raise ValueError('Unexpected runtime difference: '+str(attr.GetPath()))
            if isinstance(value, Sdf.AssetPath):
                value = Sdf.AssetPath(localize(value.resolvedPath))
            target = variant.OverridePrim(prim.GetPath())
            target.CreateAttribute(attr.GetName(), attr.GetTypeName(), custom=attr.IsCustom()).Set(value)
            overrides.append(str(attr.GetPath()))
    variant.GetRootLayer().Save()
    result = {'status': 'pass', 'source_package': str(package), 'default_runtime': '4.1',
              'inactive_prims_omitted_by_flatten': [str(p.GetPath()) for p in sources['41'].TraverseAll() if not p.IsActive()],
              'entries': check_layout(out, package), 'asset_path_map': remap,
              'runtime45_overrides': overrides, 'files': file_inventory(out)}
    return result


def make_validation_fixture(exported, package, fixture):
    """Wrap exported bytes in the existing validator's private directory shape."""
    from pxr import Usd, UsdGeom, Sdf
    fixture = fixture.resolve()
    if fixture.exists():
        raise FileExistsError(fixture)
    composed = fixture/'assets/composed'
    shutil.copytree(exported, composed)
    # Existing validator hashes scene.usdc; alias only in this private fixture.
    (composed/'scene.usdc').symlink_to('scene.usd')
    (fixture/'scene').mkdir()
    for version, entry in [('41', 'scene.usd'), ('45', 'scene_isaac45.usda')]:
        stage = Usd.Stage.CreateNew(str(fixture/f'scene/demo{version}.usda'))
        stage.GetRootLayer().subLayerPaths = ['../assets/composed/'+entry]
        UsdGeom.SetStageMetersPerUnit(stage, 1.)
        UsdGeom.SetStageUpAxis(stage, 'Z')
        stage.SetDefaultPrim(stage.GetPrimAtPath('/World'))
        Sdf.CreatePrimInLayer(stage.GetRootLayer(), '/World')
        template = Usd.Stage.Open(str(package/f'scene/demo{version}.usda'))
        Sdf.CopySpec(template.GetRootLayer(), '/World/PhysicsScene', stage.GetRootLayer(), '/World/PhysicsScene')
        stage.GetRootLayer().Save()
    return fixture


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    report = export_layout(args.package, args.out)
    (args.evidence/'export.json').write_text(json.dumps(report, indent=2))
    fixture = make_validation_fixture(args.out, args.package, args.evidence/'runtime_fixture')
    print(json.dumps({'export': str(args.out), 'validation_fixture': str(fixture)}, indent=2))
