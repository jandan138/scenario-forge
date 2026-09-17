#!/usr/bin/env python3
"""Static contract checker for a single-root Isaac USD articulation.

Run this script with the Python shipped by Isaac Sim/Kit.  The local system
Python is intentionally supported only for argument/help inspection because
the ``pxr`` package is normally provided by Isaac Kit.
"""

from __future__ import print_function

import argparse
import json
import math
import sys
from collections import defaultdict, deque
from pathlib import Path


SUPPORTED_JOINT_TYPES = {"fixed", "revolute", "prismatic", "spherical"}
JOINT_TYPE_NAMES = {
    "PhysicsFixedJoint": "fixed",
    "PhysicsRevoluteJoint": "revolute",
    "PhysicsPrismaticJoint": "prismatic",
    "PhysicsSphericalJoint": "spherical",
}
ROOT_API_TOKEN = "PhysicsArticulationRootAPI"
RIGID_BODY_TOKEN = "PhysicsRigidBodyAPI"
MASS_TOKEN = "PhysicsMassAPI"
COLLISION_TOKEN = "PhysicsCollisionAPI"
EXCEPTION_ATTRS = (
    "asset:articulationExceptionReason",
    "articulation:exceptionReason",
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Check the single-root articulation contract of an Isaac USD asset."
    )
    parser.add_argument("--usd", required=True, help="Path to the USD/USDA asset")
    parser.add_argument(
        "--asset-root",
        required=True,
        help="Asset prim scope, for example /World/Oven125",
    )
    parser.add_argument(
        "--mode",
        choices=("fixed", "floating"),
        default="fixed",
        help="Expected articulation base mode (default: fixed)",
    )
    parser.add_argument(
        "--json-out",
        help="Optional path for the JSON report; stdout always receives the report",
    )
    return parser.parse_args(argv)


def new_report(asset_root, mode):
    return {
        "status": "FAIL",
        "asset_root": asset_root,
        "mode": mode,
        "articulation_root_count": 0,
        "articulation_root": None,
        "checks": [],
        "metrics": {},
    }


def add_check(report, check_id, status, details, **extra):
    item = {"id": check_id, "status": status, "details": details}
    item.update(extra)
    report["checks"].append(item)


def finish_report(report, json_out=None, exit_code=None):
    has_fail = any(item.get("status") == "FAIL" for item in report["checks"])
    report["status"] = "FAIL" if has_fail else "PASS"
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(payload)
    if json_out:
        try:
            output_path = Path(json_out)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(payload + "\n", encoding="utf-8")
        except Exception as exc:  # pragma: no cover - environment-specific
            print("Unable to write --json-out: {}".format(exc), file=sys.stderr)
            if exit_code in (None, 0):
                exit_code = 2
    if exit_code is None:
        exit_code = 1 if has_fail else 0
    return exit_code


def fail_environment(report, message, json_out=None):
    add_check(report, "environment", "FAIL", message)
    return finish_report(report, json_out=json_out, exit_code=2)


def applied_schemas(prim):
    try:
        return {str(value) for value in prim.GetAppliedSchemas()}
    except Exception:
        return set()


def has_api(prim, schema_cls, token):
    try:
        if prim.HasAPI(schema_cls):
            return True
    except Exception:
        pass
    return token in applied_schemas(prim)


def is_rigid_body(prim, usd_physics):
    return has_api(prim, usd_physics.RigidBodyAPI, RIGID_BODY_TOKEN)


def is_mass_api(prim, usd_physics):
    return has_api(prim, usd_physics.MassAPI, MASS_TOKEN)


def is_collision(prim, usd_physics):
    return has_api(prim, usd_physics.CollisionAPI, COLLISION_TOKEN)


def joint_type(prim, usd_physics):
    type_name = str(prim.GetTypeName())
    if type_name in JOINT_TYPE_NAMES:
        return JOINT_TYPE_NAMES[type_name]
    schema_candidates = (
        ("fixed", getattr(usd_physics, "FixedJoint", None)),
        ("revolute", getattr(usd_physics, "RevoluteJoint", None)),
        ("prismatic", getattr(usd_physics, "PrismaticJoint", None)),
        ("spherical", getattr(usd_physics, "SphericalJoint", None)),
    )
    for name, schema_cls in schema_candidates:
        if schema_cls is None:
            continue
        try:
            if prim.IsA(schema_cls):
                return name
        except Exception:
            continue
    if type_name.startswith("Physics") and type_name.endswith("Joint"):
        return "unsupported"
    return None


def relation_targets(relation):
    try:
        return [str(value) for value in relation.GetTargets()]
    except Exception:
        return []


def get_joint_relations(prim, usd_physics):
    joint = usd_physics.Joint(prim)
    try:
        body0 = relation_targets(joint.GetBody0Rel())
    except Exception:
        body0 = []
    try:
        body1 = relation_targets(joint.GetBody1Rel())
    except Exception:
        body1 = []
    return body0, body1


def get_bool_attr(prim, name, default=False):
    try:
        attr = prim.GetAttribute(name)
        if attr and attr.IsValid():
            value = attr.Get()
            if value is not None:
                return bool(value)
    except Exception:
        pass
    return default


def is_excluded_from_articulation(prim, usd_physics):
    """Read the schema accessor first, then fall back to the raw USD name."""
    try:
        value = usd_physics.Joint(prim).GetExcludeFromArticulationAttr().Get()
        if value is not None:
            return bool(value)
    except Exception:
        pass
    return get_bool_attr(prim, "physics:excludeFromArticulation", False)


def get_string_attr(prim, names):
    for name in names:
        try:
            attr = prim.GetAttribute(name)
            if attr and attr.IsValid():
                value = attr.Get()
                if value is not None and str(value).strip():
                    return str(value).strip()
        except Exception:
            continue
    return ""


def within_scope(path, root_path):
    root = root_path.rstrip("/")
    return path == root or path.startswith(root + "/")


def is_ancestor_or_same(ancestor, descendant):
    return descendant == ancestor or descendant.startswith(ancestor.rstrip("/") + "/")


def prim_path(prim):
    return str(prim.GetPath())


def nearest_rigid_ancestor(prim, body_paths, root_path):
    current = prim
    while current and current.IsValid():
        path = prim_path(current)
        if path in body_paths:
            return path
        if path == root_path:
            break
        current = current.GetParent()
    return None


def scalar_components(value):
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return []
    try:
        return [float(component) for component in value]
    except Exception:
        try:
            return [float(value)]
        except Exception:
            return []


def has_negative_scale(prim, root_path):
    """Detect explicit negative scale on a collider or any parent in scope."""
    current = prim
    while current and current.IsValid():
        for attribute in current.GetAttributes():
            name = str(attribute.GetName())
            if not name.startswith("xformOp:scale"):
                continue
            try:
                values = scalar_components(attribute.Get())
            except Exception:
                values = []
            if any(value < -1.0e-8 for value in values):
                return True
        if prim_path(current) == root_path:
            break
        current = current.GetParent()
    return False


def mass_properties_ok(prim, usd_physics):
    if not is_mass_api(prim, usd_physics):
        return False, "MassAPI is not applied"
    attrs = {str(attribute.GetName()): attribute for attribute in prim.GetAttributes()}
    mass_value = None
    density_value = None
    for name, attribute in attrs.items():
        if name == "physics:mass":
            try:
                mass_value = attribute.Get()
            except Exception:
                pass
        elif name == "physics:density":
            try:
                density_value = attribute.Get()
            except Exception:
                pass
    try:
        if mass_value is not None and float(mass_value) > 0.0:
            return True, "explicit mass"
    except Exception:
        pass
    try:
        if density_value is not None and float(density_value) > 0.0:
            return True, "explicit density (inertia may be auto-computed)"
    except Exception:
        pass
    return False, "MassAPI has neither a positive mass nor density"


def stage_units(stage, usd_geom):
    try:
        meters = float(usd_geom.GetStageMetersPerUnit(stage))
    except Exception:
        meters = None
    try:
        up_axis = str(usd_geom.GetStageUpAxis(stage)).upper()
    except Exception:
        up_axis = ""
    return meters, up_axis


def detect_cycle(nodes, children):
    state = {}
    cycle_nodes = []

    def visit(node):
        state[node] = 1
        for child in children.get(node, []):
            child_state = state.get(child, 0)
            if child_state == 1:
                cycle_nodes.append(child)
                return True
            if child_state == 0 and visit(child):
                return True
        state[node] = 2
        return False

    for node in nodes:
        if state.get(node, 0) == 0 and visit(node):
            return True, cycle_nodes
    return False, cycle_nodes


def reachable_from(root_body, children):
    if not root_body:
        return set()
    visited = set()
    queue = deque([root_body])
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        queue.extend(children.get(node, []))
    return visited


def check_stage(stage, root, args, usd, usd_geom):
    report = new_report(args.asset_root, args.mode)
    root_path = args.asset_root.rstrip("/") or "/"
    prims = [root]
    try:
        # USD 0.22 bundled with Isaac Sim 4.5 does not expose
        # Usd.Prim.GetDescendants(); PrimRange is equivalent and works across
        # both older and newer USD Python bindings.
        if hasattr(root, "GetDescendants"):
            prims.extend(list(root.GetDescendants()))
        else:
            # ``usd`` is the UsdPhysics module in this function, so use the
            # stage traversal API rather than looking up PrimRange on it.
            root_path = str(root.GetPath())
            prims.extend(
                [prim for prim in stage.Traverse()
                 if prim != root and (str(prim.GetPath()) == root_path
                                      or str(prim.GetPath()).startswith(root_path + "/"))]
            )
    except Exception as exc:
        add_check(report, "traversal", "FAIL", "Unable to traverse asset scope: {}".format(exc))
        return report

    # Basic stage contract.
    meters, up_axis = stage_units(stage, usd_geom)
    report["metrics"]["meters_per_unit"] = meters
    report["metrics"]["up_axis"] = up_axis
    if meters is None or not math.isclose(meters, 1.0, rel_tol=0.0, abs_tol=1.0e-6):
        add_check(
            report,
            "stage_units",
            "FAIL",
            "Expected explicit metersPerUnit=1.0, got {!r}".format(meters),
        )
    else:
        add_check(report, "stage_units", "PASS", "metersPerUnit=1.0")
    if up_axis != "Z":
        add_check(report, "up_axis", "FAIL", "Expected Z-up, got {!r}".format(up_axis))
    else:
        add_check(report, "up_axis", "PASS", "Z-up")

    try:
        default_prim = stage.GetDefaultPrim()
        default_path = prim_path(default_prim) if default_prim and default_prim.IsValid() else ""
    except Exception:
        default_path = ""
    report["metrics"]["default_prim"] = default_path or None
    if not default_path:
        add_check(report, "default_prim", "FAIL", "Stage has no valid default prim")
    elif not is_ancestor_or_same(default_path, root_path):
        add_check(
            report,
            "default_prim",
            "FAIL",
            "Default prim {} does not contain asset root {}".format(default_path, root_path),
        )
    elif default_path != root_path:
        add_check(
            report,
            "default_prim",
            "WARN",
            "Default prim {} is an ancestor of asset root {}".format(default_path, root_path),
        )
    else:
        add_check(report, "default_prim", "PASS", "Default prim is the asset root")

    # Identify bodies, colliders, joints, and root APIs.
    body_prims = {}
    collider_prims = []
    root_api_prims = []
    joint_records = []
    for prim in prims:
        path = prim_path(prim)
        if is_rigid_body(prim, usd):
            body_prims[path] = prim
        if is_collision(prim, usd):
            collider_prims.append(prim)
        if has_api(prim, usd.ArticulationRootAPI, ROOT_API_TOKEN):
            root_api_prims.append(prim)
        jtype = joint_type(prim, usd)
        if jtype is not None:
            body0, body1 = get_joint_relations(prim, usd)
            excluded = is_excluded_from_articulation(prim, usd)
            reason = get_string_attr(prim, EXCEPTION_ATTRS)
            joint_records.append(
                {
                    "path": path,
                    "type": jtype,
                    "body0": body0,
                    "body1": body1,
                    "excluded": excluded,
                    "reason": reason,
                }
            )

    report["articulation_root_count"] = len(root_api_prims)
    if len(root_api_prims) != 1:
        add_check(
            report,
            "single_root_api",
            "FAIL",
            "Expected exactly one ArticulationRootAPI in scope, found {}".format(
                len(root_api_prims)
            ),
        )
    else:
        report["articulation_root"] = prim_path(root_api_prims[0])
        add_check(
            report,
            "single_root_api",
            "PASS",
            "Exactly one root API at {}".format(report["articulation_root"]),
        )

    report["metrics"].update(
        {
            "rigid_body_count": len(body_prims),
            "collider_count": len(collider_prims),
            "joint_count": len(joint_records),
            "included_joint_count": sum(1 for item in joint_records if not item["excluded"]),
            "excluded_joint_count": sum(1 for item in joint_records if item["excluded"]),
        }
    )

    if not body_prims:
        add_check(report, "rigid_bodies", "FAIL", "No rigid-body links found in asset scope")
    else:
        add_check(report, "rigid_bodies", "PASS", "Found {} rigid-body links".format(len(body_prims)))

    # Validate joint relationship cardinality and exception annotations.
    malformed_joints = []
    excluded_without_reason = []
    unsupported_included = []
    unsupported_excluded = []
    for item in joint_records:
        body0 = item["body0"]
        body1 = item["body1"]
        if len(body0) > 1 or len(body1) > 1 or (not body0 and not body1):
            malformed_joints.append(item["path"])
        for target in body0 + body1:
            if not within_scope(target, root_path):
                malformed_joints.append(
                    "{} target {} outside asset scope".format(item["path"], target)
                )
        if item["excluded"] and not item["reason"]:
            excluded_without_reason.append(item["path"])
        if item["type"] not in SUPPORTED_JOINT_TYPES:
            if item["excluded"]:
                unsupported_excluded.append(item["path"])
            else:
                unsupported_included.append(item["path"])

    if malformed_joints:
        add_check(
            report,
            "joint_relationships",
            "FAIL",
            "Malformed or out-of-scope body relationships",
            paths=malformed_joints,
        )
    else:
        add_check(report, "joint_relationships", "PASS", "Joint body relationships are cardinality-safe")
    if excluded_without_reason:
        add_check(
            report,
            "exception_reasons",
            "FAIL",
            "Excluded joints require asset:articulationExceptionReason",
            paths=excluded_without_reason,
        )
    else:
        add_check(report, "exception_reasons", "PASS", "All excluded joints have a reason")
    if unsupported_included:
        add_check(
            report,
            "supported_joint_types",
            "FAIL",
            "Unsupported included joint types",
            paths=unsupported_included,
        )
    else:
        add_check(report, "supported_joint_types", "PASS", "Included joint types are supported")
    if unsupported_excluded:
        add_check(
            report,
            "excluded_joint_types",
            "WARN",
            "Excluded joints use types outside the default supported set",
            paths=unsupported_excluded,
        )

    # Build the included articulation graph.
    included = [item for item in joint_records if not item["excluded"]]
    world_joints = []
    regular_joints = []
    parent_of = {}
    children = defaultdict(list)
    duplicate_parent_paths = []
    for item in included:
        body0 = item["body0"][0] if len(item["body0"]) == 1 else None
        body1 = item["body1"][0] if len(item["body1"]) == 1 else None
        # A fixed joint with exactly one body relation is the conventional world anchor.
        if (body0 and not body1) or (body1 and not body0):
            world_joints.append({"record": item, "body": body0 or body1})
            continue
        if body0 and body1:
            regular_joints.append(item)
            if body1 in parent_of:
                duplicate_parent_paths.append(body1)
            else:
                parent_of[body1] = body0
                children[body0].append(body1)

    report["metrics"]["included_world_joint_count"] = len(world_joints)
    if args.mode == "fixed":
        if len(world_joints) != 1:
            add_check(
                report,
                "fixed_world_joint",
                "FAIL",
                "Fixed mode requires exactly one included world joint, found {}".format(
                    len(world_joints)
                ),
            )
        elif world_joints[0]["record"]["type"] != "fixed":
            add_check(
                report,
                "fixed_world_joint",
                "FAIL",
                "The sole fixed-base world joint must be a FixedJoint",
                path=world_joints[0]["record"]["path"],
            )
        else:
            add_check(
                report,
                "fixed_world_joint",
                "PASS",
                "One FixedJoint anchors the base to the world",
                path=world_joints[0]["record"]["path"],
            )
    else:
        if world_joints:
            add_check(
                report,
                "floating_world_joint",
                "FAIL",
                "Floating mode cannot contain included world joints",
                paths=[item["record"]["path"] for item in world_joints],
            )
        else:
            add_check(report, "floating_world_joint", "PASS", "No included world joint")

    if duplicate_parent_paths:
        add_check(
            report,
            "one_parent_per_link",
            "FAIL",
            "A link is the child of more than one included joint",
            paths=sorted(set(duplicate_parent_paths)),
        )
    else:
        add_check(report, "one_parent_per_link", "PASS", "Each included child link has at most one parent")

    cycle, cycle_nodes = detect_cycle(set(body_prims), children)
    if cycle:
        add_check(
            report,
            "acyclic_graph",
            "FAIL",
            "Included articulation graph contains a cycle",
            paths=cycle_nodes,
        )
    else:
        add_check(report, "acyclic_graph", "PASS", "Included articulation graph is acyclic")

    if args.mode == "fixed" and world_joints:
        root_body = world_joints[0]["body"]
    else:
        indegree = {path: 0 for path in body_prims}
        for child in parent_of:
            if child in indegree:
                indegree[child] += 1
        roots = sorted(path for path, degree in indegree.items() if degree == 0)
        root_body = roots[0] if len(roots) == 1 else None
        report["metrics"]["candidate_root_bodies"] = roots
        if len(roots) != 1:
            add_check(
                report,
                "graph_root",
                "FAIL",
                "Expected one graph root body, found {}".format(len(roots)),
                paths=roots,
            )
        else:
            add_check(report, "graph_root", "PASS", "Graph root body is {}".format(root_body))

    if root_body and root_body not in body_prims:
        add_check(
            report,
            "root_body_is_rigid",
            "FAIL",
            "Root body {} is not a rigid-body link".format(root_body),
        )
    elif root_body:
        add_check(report, "root_body_is_rigid", "PASS", "Root body is a rigid-body link")

    reachable = reachable_from(root_body, children)
    report["metrics"]["reachable_body_count"] = len(reachable)
    unreachable = sorted(set(body_prims) - reachable) if root_body else sorted(body_prims)
    if unreachable:
        add_check(
            report,
            "connected_graph",
            "FAIL",
            "Rigid-body links are disconnected from the selected root",
            paths=unreachable,
        )
    else:
        add_check(report, "connected_graph", "PASS", "All rigid-body links are reachable from the root")

    # World-anchor policy: excluded world joints are allowed only as documented exceptions.
    all_world_joints = []
    for item in joint_records:
        body_count = len(item["body0"]) + len(item["body1"])
        if body_count == 1:
            all_world_joints.append(item)
    extra_world = [item for item in all_world_joints if item not in [entry["record"] for entry in world_joints]]
    undocumented_extra_world = [item["path"] for item in extra_world if not item["excluded"]]
    if undocumented_extra_world:
        add_check(
            report,
            "no_child_world_anchor",
            "FAIL",
            "Non-root world joints are not allowed",
            paths=undocumented_extra_world,
        )
    elif extra_world:
        add_check(
            report,
            "no_child_world_anchor",
            "WARN",
            "Excluded world joints are documented exceptions",
            paths=[item["path"] for item in extra_world],
        )
    else:
        add_check(report, "no_child_world_anchor", "PASS", "No extra world anchors")

    # Root API placement is deterministic for the new skill, while allowing the
    # USD-standard ancestor placement as a warning for imported assets.
    if len(root_api_prims) == 1:
        root_api_path = prim_path(root_api_prims[0])
        if args.mode == "fixed" and world_joints:
            world_path = world_joints[0]["record"]["path"]
            if root_api_path == world_path:
                add_check(report, "root_placement", "PASS", "Root API is on the root FixedJoint")
            elif is_ancestor_or_same(root_api_path, world_path):
                add_check(
                    report,
                    "root_placement",
                    "WARN",
                    "Root API is on an ancestor of the root FixedJoint; canonical placement is the joint",
                )
            else:
                add_check(
                    report,
                    "root_placement",
                    "FAIL",
                    "Root API is not on or above the fixed-base root joint",
                )
        elif args.mode == "floating" and root_body:
            if root_api_path == root_body:
                add_check(report, "root_placement", "PASS", "Root API is on the floating root body")
            elif is_ancestor_or_same(root_api_path, root_body):
                add_check(
                    report,
                    "root_placement",
                    "WARN",
                    "Root API is on an ancestor of the floating root body",
                )
            else:
                add_check(
                    report,
                    "root_placement",
                    "FAIL",
                    "Root API is not on or above the floating root body",
                )

    # Mass and collision contract for every dynamic link.
    missing_mass = []
    missing_collision = []
    negative_collision = []
    collider_to_body = {}
    body_path_set = set(body_prims)
    for body_path, body_prim in body_prims.items():
        mass_ok, mass_details = mass_properties_ok(body_prim, usd)
        if not mass_ok:
            missing_mass.append({"path": body_path, "details": mass_details})
        else:
            add_check(report, "mass:" + body_path, "PASS", mass_details)
        body_colliders = []
        for collider in collider_prims:
            owner = nearest_rigid_ancestor(collider, body_path_set, root_path)
            if owner == body_path:
                body_colliders.append(collider)
                collider_to_body[prim_path(collider)] = body_path
                if has_negative_scale(collider, root_path):
                    negative_collision.append(prim_path(collider))
        if not body_colliders:
            missing_collision.append(body_path)

    if missing_mass:
        add_check(report, "mass_properties", "FAIL", "Rigid-body links need explicit mass or density", paths=missing_mass)
    else:
        add_check(report, "mass_properties", "PASS", "All rigid-body links have mass/density")
    if missing_collision:
        add_check(
            report,
            "collision_per_link",
            "FAIL",
            "Every rigid-body link needs an intentional collider",
            paths=missing_collision,
        )
    else:
        add_check(report, "collision_per_link", "PASS", "Every rigid-body link has a collider")
    if negative_collision:
        add_check(
            report,
            "positive_collision_scale",
            "FAIL",
            "Collision geometry or an ancestor uses negative scale",
            paths=negative_collision,
        )
    else:
        add_check(report, "positive_collision_scale", "PASS", "Collision geometry uses positive scale")

    report["metrics"]["colliders_mapped_to_links"] = len(collider_to_body)
    report["metrics"]["excluded_exception_count"] = sum(
        1 for item in joint_records if item["excluded"] and item["reason"]
    )
    return report


def main(argv=None):
    args = parse_args(argv)
    report = new_report(args.asset_root, args.mode)

    try:
        from pxr import Usd, UsdGeom, UsdPhysics
    except Exception as exc:
        return fail_environment(
            report,
            "Isaac Kit pxr modules are unavailable; run this script with Isaac's python.sh: {}".format(exc),
            json_out=args.json_out,
        )

    usd_path = Path(args.usd)
    if not usd_path.is_file():
        return fail_environment(report, "USD file does not exist: {}".format(usd_path), args.json_out)

    try:
        stage = Usd.Stage.Open(str(usd_path))
    except Exception as exc:
        return fail_environment(report, "Unable to open USD stage: {}".format(exc), args.json_out)
    if stage is None:
        return fail_environment(report, "Usd.Stage.Open returned no stage", args.json_out)

    try:
        root = stage.GetPrimAtPath(args.asset_root)
    except Exception as exc:
        return fail_environment(report, "Unable to resolve asset root: {}".format(exc), args.json_out)
    if not root or not root.IsValid():
        return fail_environment(
            report,
            "Asset root prim does not exist: {}".format(args.asset_root),
            args.json_out,
        )

    report = check_stage(stage, root, args, UsdPhysics, UsdGeom)
    return finish_report(report, json_out=args.json_out)


if __name__ == "__main__":
    sys.exit(main())
