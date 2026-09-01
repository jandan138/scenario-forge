#!/usr/bin/env python3
"""Register Task08 r13's embedded graph through Isaac 4.1 OmniGraph APIs."""

from __future__ import annotations

import argparse
from hashlib import sha256
import os
from pathlib import Path
import sys
import traceback


GRAPH_PATH = "/World/TaskRuntime/AssistedThreadGraph"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--controller", type=Path, required=True)
    args = parser.parse_args()
    original = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp

    app = SimulationApp({"headless": True, "multi_gpu": False})
    sys.argv = original
    code = 3
    try:
        import omni.graph.core as og
        import omni.usd
        from pxr import Sdf

        context = omni.usd.get_context()
        if not context.open_stage(str(args.scene.resolve())):
            raise RuntimeError("could not open Task08 r13 scene")
        while context.get_stage_loading_status()[2] > 0:
            app.update()
        for _ in range(30):
            app.update()
        stage = context.get_stage()
        stage.SetEditTarget(stage.GetRootLayer())
        if stage.GetPrimAtPath(GRAPH_PATH):
            stage.RemovePrim(GRAPH_PATH)
        script = args.controller.read_text()
        keys = og.Controller.Keys
        og.Controller.edit(
            {
                "graph_path": GRAPH_PATH,
                "pipeline_stage": og.GraphPipelineStage.GRAPH_PIPELINE_STAGE_ONDEMAND,
            },
            {
                keys.CREATE_NODES: [
                    ("OnPhysicsStep", "omni.isaac.core_nodes.OnPhysicsStep"),
                    ("Controller", "omni.graph.scriptnode.ScriptNode"),
                ],
                keys.SET_VALUES: [("Controller.inputs:script", script)],
                keys.CONNECT: [
                    ("OnPhysicsStep.outputs:step", "Controller.inputs:execIn"),
                ],
            },
        )
        graph = stage.GetPrimAtPath(GRAPH_PATH)
        graph.CreateAttribute("runtime:execution", Sdf.ValueTypeNames.Token).Set(
            "on_playback_tick"
        )
        graph.CreateAttribute("runtime:graphRole", Sdf.ValueTypeNames.Token).Set(
            "task08_one_turn_assisted_thread"
        )
        controller = stage.GetPrimAtPath(GRAPH_PATH + "/Controller")
        controller.CreateAttribute(
            "runtime:inlineScriptSha256", Sdf.ValueTypeNames.String
        ).Set(sha256(script.encode()).hexdigest())
        stage.GetRootLayer().Save()
        print(args.scene.resolve(), flush=True)
        code = 0
    except BaseException:
        traceback.print_exc()
        code = 3
    finally:
        app.close()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


if __name__ == "__main__":
    raise SystemExit(main())
