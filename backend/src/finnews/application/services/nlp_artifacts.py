from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ArtifactError(ValueError):
    pass


class ModelArtifactManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    task: str = Field(pattern=r"^(event|sentiment)$")
    dataset_id: str
    dataset_version: str
    dataset_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    split_hashes: dict[str, str]
    label_set: list[str]
    provider: str
    model_kind: str
    status: str
    artifact_uri: str
    artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    artifact_size_bytes: int = Field(ge=1, le=25_000_000)
    config_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    created_at: str

    @field_validator("artifact_uri")
    @classmethod
    def validate_relative_uri(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or "://" in value:
            raise ValueError("artifact_uri must be a relative local path")
        if any(part == ".." for part in path.parts):
            raise ValueError("artifact_uri must not traverse outside artifact root")
        return value


@dataclass(frozen=True)
class SavedArtifact:
    manifest: ModelArtifactManifest
    manifest_path: Path
    artifact_path: Path


def save_model_artifact(
    model: object,
    artifact_root: Path,
    *,
    model_id: str,
    task: str,
    dataset_id: str,
    dataset_version: str,
    dataset_sha256: str,
    split_hashes: dict[str, str],
    label_set: list[str],
    provider: str,
    model_kind: str,
    status: str,
    config: dict[str, Any],
) -> SavedArtifact:
    task_dir = artifact_root / task / model_id
    task_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = task_dir / "model.joblib"
    joblib.dump(model, artifact_path, compress=3)
    artifact_hash = sha256_file(artifact_path)
    config_hash = sha256_text(json.dumps(config, sort_keys=True, separators=(",", ":")))
    manifest = ModelArtifactManifest(
        model_id=model_id,
        task=task,
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        dataset_sha256=dataset_sha256,
        split_hashes=split_hashes,
        label_set=label_set,
        provider=provider,
        model_kind=model_kind,
        status=status,
        artifact_uri=f"{task}/{model_id}/model.joblib",
        artifact_sha256=artifact_hash,
        artifact_size_bytes=artifact_path.stat().st_size,
        config_sha256=config_hash,
        created_at=datetime(2026, 6, 22, tzinfo=UTC).isoformat(),
    )
    manifest_path = task_dir / "manifest.json"
    manifest_path.write_text(
        manifest.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return SavedArtifact(manifest, manifest_path, artifact_path)


def load_trusted_artifact(artifact_root: Path, manifest_path: Path, *, task: str) -> object:
    root = artifact_root.resolve()
    manifest_resolved = manifest_path.resolve()
    if not manifest_resolved.is_relative_to(root):
        raise ArtifactError("manifest is outside artifact root")
    manifest = ModelArtifactManifest.model_validate_json(
        manifest_resolved.read_text(encoding="utf-8")
    )
    if manifest.task != task:
        raise ArtifactError("artifact task mismatch")
    artifact_path = (root / manifest.artifact_uri).resolve()
    if not artifact_path.is_relative_to(root):
        raise ArtifactError("artifact path is outside artifact root")
    if not artifact_path.is_file():
        raise ArtifactError("artifact is missing")
    if sha256_file(artifact_path) != manifest.artifact_sha256:
        raise ArtifactError("artifact hash mismatch")
    return joblib.load(artifact_path)


def safe_manifest_summary(manifest: ModelArtifactManifest) -> dict[str, Any]:
    return {
        "model_id": manifest.model_id,
        "task": manifest.task,
        "dataset_id": manifest.dataset_id,
        "dataset_version": manifest.dataset_version,
        "dataset_sha256": manifest.dataset_sha256,
        "split_hashes": manifest.split_hashes,
        "provider": manifest.provider,
        "model_kind": manifest.model_kind,
        "status": manifest.status,
        "artifact_sha256": manifest.artifact_sha256,
        "artifact_size_bytes": manifest.artifact_size_bytes,
        "manifest_sha256": sha256_text(manifest.model_dump_json()),
        "config_sha256": manifest.config_sha256,
        "created_at": manifest.created_at,
    }


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
