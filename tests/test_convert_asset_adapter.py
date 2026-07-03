from scenario_forge.adapters.convert_asset import ConvertAssetCommandPlan, NormalizeAssetCommandPlan


def test_convert_asset_plan_builds_command_without_executing_conversion() -> None:
    plan = ConvertAssetCommandPlan(
        convert_asset_root="/tools/ConvertAsset",
        input_usd="/data/raw/beaker.usd",
        output_usd="/data/processed/beaker_noMDL.usd",
        operations=("no-mdl", "mesh-faces"),
    )

    commands = plan.commands()

    assert commands == (
        (
            "/tools/ConvertAsset/scripts/isaac_python.sh",
            "/tools/ConvertAsset/main.py",
            "no-mdl",
            "/data/raw/beaker.usd",
            "--out",
            "/data/processed/beaker_noMDL.usd",
        ),
        (
            "/tools/ConvertAsset/scripts/isaac_python.sh",
            "/tools/ConvertAsset/main.py",
            "mesh-faces",
            "/data/processed/beaker_noMDL.usd",
        ),
    )


def test_normalize_asset_plan_uses_convert_asset_public_cli_boundary() -> None:
    plan = NormalizeAssetCommandPlan(
        convert_asset_root="/tools/ConvertAsset",
        source_usd="/data/raw/beaker.usd",
        package_dir="/tmp/normalized/beaker",
    )

    assert plan.command() == (
        "/tools/ConvertAsset/scripts/isaac_python.sh",
        "/tools/ConvertAsset/main.py",
        "normalize-asset",
        "/data/raw/beaker.usd",
        "--package-dir",
        "/tmp/normalized/beaker",
    )
