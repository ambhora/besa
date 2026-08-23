# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_besa_spack_environment_uses_common_local_dev_env() -> None:
    manifest = (ROOT / "spack.yaml").read_text(encoding="utf-8")

    assert "https://github.com/ambhora/amstack.git" in manifest
    assert "branch: main" in manifest
    assert "dev: spack/spack_repo/dev" in manifest
    assert "- besa@main" not in manifest
    dev_env_spec = next(
        line.strip()[2:].replace(" ", "")
        for line in manifest.splitlines()
        if line.strip().startswith("- dev-env@")
    )
    assert dev_env_spec.startswith("dev-env@1.1")
    assert sorted(filter(None, dev_env_spec.removeprefix("dev-env@1.1").split("+"))) == [
        "coverage",
        "docs",
        "tests",
    ]
    assert "develop:" not in manifest

    repo = ROOT / "spack" / "spack_repo" / "dev"
    assert (repo / "repo.yaml").is_file()
    assert "namespace: dev" in (repo / "repo.yaml").read_text(encoding="utf-8")

    environment_package = (
        repo / "packages" / "dev_env" / "package.py"
    ).read_text(encoding="utf-8")
    assert "class DevEnv(BundlePackage):" in environment_package
    assert 'version("1.1")' in environment_package
    for variant in ("docs", "tests", "coverage"):
        assert f'variant("{variant}"' in environment_package
    assert 'depends_on("py-pytest", when="+tests")' in environment_package
    assert 'depends_on("py-exhale", when="+docs")' in environment_package
    assert 'depends_on("py-pydata-sphinx-theme", when="+docs")' in environment_package
    assert 'depends_on("properdocs", when="+docs")' in environment_package

    compile(environment_package, "dev_env/package.py", "exec")
