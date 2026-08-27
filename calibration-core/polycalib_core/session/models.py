# Copyright (C) 2026 Sarvesh Angadi
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial licenses available — see LICENSE-COMMERCIAL.md

"""Data models shared across detectors, solvers, and session management."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import cv2
import numpy as np


@dataclass
class BoardConfig:
    """ChArUco board geometry parameters."""

    squares_x: int = 6
    squares_y: int = 8
    square_size_m: float = 0.035
    marker_size_m: float = 0.025
    aruco_dict_id: int = cv2.aruco.DICT_4X4_50

    def make_board(self) -> cv2.aruco.CharucoBoard:
        """Construct and return the OpenCV CharucoBoard object."""
        dictionary = cv2.aruco.getPredefinedDictionary(self.aruco_dict_id)
        board = cv2.aruco.CharucoBoard(
            (self.squares_x, self.squares_y),
            self.square_size_m,
            self.marker_size_m,
            dictionary,
        )
        return board

    def make_detector_params(self) -> cv2.aruco.DetectorParameters:
        """Return default ArUco detector parameters."""
        return cv2.aruco.DetectorParameters()


@dataclass
class DetectionResult:
    """Output of a single ChArUco detection on one image frame."""

    charuco_corners: np.ndarray  # shape (N, 1, 2), float32 — subpixel corner positions
    charuco_ids: np.ndarray      # shape (N, 1), int32 — corner IDs matching board layout
    image_size: tuple[int, int]  # (width, height) of the source image
    coverage_score: float        # 0.0–1.0, fraction of image area spanned by detected corners

    @property
    def corner_count(self) -> int:
        """Number of detected ChArUco corners."""
        return int(self.charuco_corners.shape[0])


@dataclass
class IntrinsicResult:
    """Result of a single-camera intrinsic calibration solve."""

    camera_id: str
    topic: str
    camera_matrix: np.ndarray    # shape (3, 3)
    dist_coeffs: np.ndarray      # shape (1, 5) — plumb_bob: k1 k2 p1 p2 k3
    image_size: tuple[int, int]  # (width, height)
    reprojection_error_rms: float
    frame_count: int


@dataclass
class ExtrinsicResult:
    """Result of a stereo extrinsic calibration solve."""

    camera_id_left: str
    camera_id_right: str
    R: np.ndarray                # shape (3, 3) — rotation from right to left camera frame
    T: np.ndarray                # shape (3, 1) — translation from right to left camera frame
    reprojection_error_rms: float
    frame_count: int

    def rotation_quaternion(self) -> tuple[float, float, float, float]:
        """Return rotation as (qx, qy, qz, qw) quaternion."""
        rvec, _ = cv2.Rodrigues(self.R)
        angle = float(np.linalg.norm(rvec))
        if angle < 1e-10:
            return (0.0, 0.0, 0.0, 1.0)
        axis = rvec.flatten() / angle
        s = np.sin(angle / 2.0)
        qx, qy, qz = axis * s
        qw = float(np.cos(angle / 2.0))
        return (float(qx), float(qy), float(qz), qw)


class SessionState(str, Enum):
    """State machine states for a calibration session."""

    IDLE = "idle"
    COLLECTING = "collecting"
    READY_TO_SOLVE = "ready_to_solve"
    SOLVING = "solving"
    DONE = "done"
    ERROR = "error"


@dataclass
class FrameAddResult:
    """Return value from SessionManager.add_frame / add_frame_pair."""

    accepted: bool
    frame_count: int
    coverage_score: float
    reason: str = ""  # human-readable message when not accepted
