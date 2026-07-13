from __future__ import annotations

from importlib import resources
from pathlib import Path


def repo_root() -> Path | None:
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "pyproject.toml").exists():
        return candidate
    return None


def registry_path(name: str) -> Path:
    root = repo_root()
    if root is not None:
        return root / "data" / "registries" / name
    return Path(resources.files("anibench").joinpath("data", "registries", name))


def schema_path(name: str = "study_manifest.schema.json") -> Path:
    root = repo_root()
    if root is not None:
        return root / "schemas" / name
    return Path(resources.files("anibench").joinpath("schemas", name))


def default_reference_path() -> Path:
    root = repo_root()
    if root is not None:
        return root / "data" / "studies" / "reference_trial.json"
    return Path(
        resources.files("anibench").joinpath(
            "data", "studies", "reference_trial.json"
        )
    )


def reference_design_path(name: str) -> Path:
    root = repo_root()
    if root is not None:
        return root / "spec" / "v1" / "reference_design" / name
    return Path(
        resources.files("anibench").joinpath(
            "spec", "v1", "reference_design", name
        )
    )
