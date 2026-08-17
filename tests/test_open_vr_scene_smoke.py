from __future__ import annotations

from scripts.ebench.open_vr_scene_smoke import _config_contract, _stage_contract


class _Attribute:
    def __init__(self, value: object) -> None:
        self._value = value

    def Get(self) -> object:
        return self._value


class _Prim:
    def __init__(self, path: str = "", type_name: str = "Xform", *, valid: bool = True) -> None:
        self.path = path
        self.type_name = type_name
        self.valid = valid
        self.children: list[_Prim] = []
        self.attributes: dict[str, object] = {}

    def IsValid(self) -> bool:
        return self.valid

    def GetPath(self) -> str:
        return self.path

    def GetName(self) -> str:
        return self.path.rpartition("/")[2]

    def GetChildren(self) -> list[_Prim]:
        return self.children

    def GetTypeName(self) -> str:
        return self.type_name

    def GetAttribute(self, name: str) -> _Attribute:
        return _Attribute(self.attributes.get(name))


class _Stage:
    def __init__(self, *, fluid: bool) -> None:
        self.world = _Prim("/World")
        self.prims = {"/World": self.world}
        for path, type_name in (
            ("/World/background", "Xform"),
            ("/World/table", "Xform"),
            ("/World/obj_beaker", "Xform"),
            ("/World/vr_direct_open_light", "DomeLight"),
        ):
            prim = _Prim(path, type_name)
            self.prims[path] = prim
            self.world.children.append(prim)
        self.prims["/World/vr_direct_open_light"].attributes["inputs:intensity"] = 750.0
        if fluid:
            runtime = _Prim("/World/fluid_runtime")
            self.prims[runtime.path] = runtime
            self.world.children.append(runtime)
            for name in ("Source", "Target", "ParticleSet"):
                self.prims[f"{runtime.path}/{name}"] = _Prim(f"{runtime.path}/{name}")

    def GetDefaultPrim(self) -> _Prim:
        return self.world

    def GetPrimAtPath(self, path: str) -> _Prim:
        return self.prims.get(path, _Prim(valid=False))


def test_direct_root_contract_accepts_non_fluid_task() -> None:
    contract = _stage_contract(_Stage(fluid=False))
    config = {
        "task07": {
            "obj_prim_list": ["/World/_scene/obj_beaker"],
            "layout_randomization": {
                "table": "table",
                "objects": [{
                    "objs": ["obj_beaker"],
                    "mode": "local",
                    "yaw_range_degrees": [0.0, 0.0],
                    "x_offset_range": [-0.01, 0.01],
                    "y_offset_range": [-0.01, 0.01],
                }],
            },
        }
    }
    assert _config_contract(config, contract)["tasks"][0]["obj_prim_count"] == 1


def test_direct_root_contract_groups_fluid_with_randomized_content() -> None:
    contract = _stage_contract(_Stage(fluid=True))
    config = {
        "task02": {
            "obj_prim_list": ["/World/_scene/obj_beaker"],
            "layout_randomization": {
                "table": "table",
                "objects": [{
                    "objs": ["obj_beaker", "fluid_runtime"],
                    "mode": "local",
                    "yaw_range_degrees": [0.0, 0.0],
                    "x_offset_range": [-0.01, 0.01],
                    "y_offset_range": [-0.01, 0.01],
                }],
            },
        }
    }
    assert _config_contract(config, contract)["tasks"][0]["randomized_names"] == [
        "obj_beaker",
        "fluid_runtime",
    ]
