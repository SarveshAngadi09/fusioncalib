# Copyright (C) 2026 Sarvesh Angadi
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial licenses available — see LICENSE-COMMERCIAL.md

"""Writes calibration session results to YAML files on disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np
import yaml

from polycalib_core.session.models import ExtrinsicResult, IntrinsicResult

_SCHEMA_VERSION = "0.1"


def write_session(
    session_id: str,
    intrinsics: list[IntrinsicResult],
    output_dir: Path,
    extrinsics: Optional[list[ExtrinsicResult]] = None,
) -> Path:
    """Write a calibration session result to a YAML file.

    The output schema matches ``docs/reference/output-format.md``.

    Args:
        session_id: ISO-8601 timestamp string identifying the session.
        intrinsics: List of intrinsic results (one per camera).
        output_dir: Directory to write to. Created if it does not exist.
        extrinsics: Optional list of extrinsic results (one per camera pair).

    Returns:
        Absolute path to the written YAML file.
    """
    output_dir = Path(output_dir)
    session_dir = output_dir / session_id.replace(":", "-")
    session_dir.mkdir(parents=True, exist_ok=True)
    output_path = session_dir / "calibration.yaml"

    doc = _build_document(session_id, intrinsics, extrinsics)

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(doc, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return output_path


def result_to_json(
    session_id: str,
    intrinsics: list[IntrinsicResult],
    extrinsics: Optional[list[ExtrinsicResult]] = None,
) -> str:
    """Serialise a calibration result to a compact JSON string.

    Used to publish on the ``/polycalib/result`` ROS2 topic.
    """
    doc = _build_document(session_id, intrinsics, extrinsics)
    return json.dumps(doc, separators=(",", ":"))


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _build_document(
    session_id: str,
    intrinsics: list[IntrinsicResult],
    extrinsics: Optional[list[ExtrinsicResult]],
) -> dict:
    """Construct the output dictionary matching the schema."""
    sensors = [_intrinsic_to_dict(intr) for intr in intrinsics]

    ext_list = []
    if extrinsics:
        for ext in extrinsics:
            ext_list.append(_extrinsic_to_dict(ext))

    quality: dict = {}
    if intrinsics:
        quality["reprojection_error_rms_px"] = round(
            intrinsics[0].reprojection_error_rms, 6
        )
        quality["frame_count"] = intrinsics[0].frame_count
    if extrinsics:
        quality["stereo_reprojection_error_rms_px"] = round(
            extrinsics[0].reprojection_error_rms, 6
        )
        quality["stereo_frame_count"] = extrinsics[0].frame_count

    doc: dict = {
        "fusionCalib": {
            "version": _SCHEMA_VERSION,
            "session_id": session_id,
            "sensors": sensors,
        }
    }
    if ext_list:
        doc["fusionCalib"]["extrinsics"] = ext_list
    doc["fusionCalib"]["quality"] = quality
    return doc


def _intrinsic_to_dict(intr: IntrinsicResult) -> dict:
    """Serialise one IntrinsicResult to a dict."""
    w, h = intr.image_size
    return {
        "id": intr.camera_id,
        "topic": intr.topic,
        "intrinsics": {
            "width": w,
            "height": h,
            "camera_matrix": _mat_to_list(intr.camera_matrix),
            "distortion_model": "plumb_bob",
            "distortion_coefficients": intr.dist_coeffs.flatten().tolist(),
        },
        "reprojection_error_rms_px": round(intr.reprojection_error_rms, 6),
        "frame_count": intr.frame_count,
    }


def _extrinsic_to_dict(ext: ExtrinsicResult) -> dict:
    """Serialise one ExtrinsicResult to a dict."""
    qx, qy, qz, qw = ext.rotation_quaternion()
    return {
        "pair": [ext.camera_id_left, ext.camera_id_right],
        "translation": ext.T.flatten().tolist(),
        "rotation_quaternion": [qx, qy, qz, qw],
        "rotation_matrix": _mat_to_list(ext.R),
        "reprojection_error_rms_px": round(ext.reprojection_error_rms, 6),
        "frame_count": ext.frame_count,
    }


def _mat_to_list(mat: np.ndarray) -> list[float]:
    """Flatten a numpy matrix to a plain Python list of floats."""
    return [round(float(v), 10) for v in mat.flatten()]
