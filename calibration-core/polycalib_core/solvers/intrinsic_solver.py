# Copyright (C) 2026 Sarvesh Angadi
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial licenses available — see LICENSE-COMMERCIAL.md

"""Single-camera intrinsic calibration solver using ChArUco detections."""

from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np

from polycalib_core.session.models import BoardConfig, DetectionResult, IntrinsicResult

logger = logging.getLogger(__name__)

# Image plane divided into a grid for spatial coverage tracking.
_GRID_ROWS = 4
_GRID_COLS = 4


class IntrinsicSolver:
    """Accumulates ChArUco detections and solves for camera intrinsics.

    Auto-collection policy:
      - A frame is accepted if its coverage_score exceeds ``min_coverage``.
      - A frame is additionally accepted only when it contributes corners in
        a grid cell that is currently under-represented (fewer than
        ``_GRID_TARGET`` frames covering it). This encourages spatial diversity
        and prevents collecting many nearly-identical frames.
      - Once ``min_frames`` frames are accepted, :attr:`is_ready` becomes True
        and the operator can trigger :meth:`solve`.
    """

    _GRID_TARGET = 3  # desired frames per grid cell before a cell is "full"

    def __init__(
        self,
        board_config: BoardConfig,
        camera_id: str,
        topic: str,
        min_frames: int = 20,
        min_coverage: float = 0.05,
    ) -> None:
        """Initialise the solver.

        Args:
            board_config: Board geometry used during detection.
            camera_id: Identifier string for the camera (used in output).
            topic: ROS2 topic this camera streams on (used in output).
            min_frames: Minimum accepted frames required before :meth:`solve`
                may be called.
            min_coverage: Minimum per-frame coverage score to accept a frame.
        """
        self._board = board_config.make_board()
        self._camera_id = camera_id
        self._topic = topic
        self._min_frames = min_frames
        self._min_coverage = min_coverage

        self._corners_list: list[np.ndarray] = []
        self._ids_list: list[np.ndarray] = []
        self._image_size: Optional[tuple[int, int]] = None
        self._grid_counts = np.zeros((_GRID_ROWS, _GRID_COLS), dtype=int)

    @property
    def frame_count(self) -> int:
        """Number of accepted frames."""
        return len(self._corners_list)

    @property
    def is_ready(self) -> bool:
        """True when enough frames have been collected to attempt a solve."""
        return self.frame_count >= self._min_frames

    def add_frame(self, detection: DetectionResult) -> bool:
        """Attempt to accept a detected frame into the accumulator.

        Args:
            detection: A valid :class:`DetectionResult` from the detector.

        Returns:
            True if the frame was accepted, False if rejected.
        """
        if detection.coverage_score < self._min_coverage:
            return False

        if not self._contributes_new_coverage(detection):
            return False

        self._corners_list.append(detection.charuco_corners)
        self._ids_list.append(detection.charuco_ids)
        self._image_size = detection.image_size
        self._update_grid(detection)

        logger.debug(
            "Intrinsic [%s]: frame accepted (%d/%d), coverage=%.2f",
            self._camera_id,
            self.frame_count,
            self._min_frames,
            detection.coverage_score,
        )
        return True

    def solve(self) -> IntrinsicResult:
        """Solve for camera intrinsics from accumulated frames.

        Returns:
            An :class:`IntrinsicResult` with the calibrated camera matrix,
            distortion coefficients, and reprojection error.

        Raises:
            RuntimeError: If fewer than ``min_frames`` frames have been accepted
                or if OpenCV's calibration routine fails.
        """
        if not self.is_ready:
            raise RuntimeError(
                f"Not enough frames: {self.frame_count}/{self._min_frames}. "
                "Collect more frames before calling solve()."
            )
        if self._image_size is None:
            raise RuntimeError("No image size recorded. Add frames before solving.")

        flags = (
            cv2.CALIB_ZERO_TANGENT_DIST  # start with p1=p2=0, let them refine
        )

        rms, camera_matrix, dist_coeffs, _rvecs, _tvecs = cv2.calibrateCameraCharuco(
            charucoCorners=self._corners_list,
            charucoIds=self._ids_list,
            board=self._board,
            imageSize=self._image_size,
            cameraMatrix=None,
            distCoeffs=None,
            flags=flags,
        )

        logger.info(
            "Intrinsic solve [%s]: RMS=%.4f px, frames=%d",
            self._camera_id,
            rms,
            self.frame_count,
        )

        return IntrinsicResult(
            camera_id=self._camera_id,
            topic=self._topic,
            camera_matrix=camera_matrix,
            dist_coeffs=dist_coeffs,
            image_size=self._image_size,
            reprojection_error_rms=float(rms),
            frame_count=self.frame_count,
        )

    def _contributes_new_coverage(self, detection: DetectionResult) -> bool:
        """Return True if the detection covers at least one under-represented grid cell."""
        w, h = detection.image_size
        pts = detection.charuco_corners.reshape(-1, 2)
        for pt in pts:
            col = min(int(pt[0] / w * _GRID_COLS), _GRID_COLS - 1)
            row = min(int(pt[1] / h * _GRID_ROWS), _GRID_ROWS - 1)
            if self._grid_counts[row, col] < self._GRID_TARGET:
                return True
        return False

    def _update_grid(self, detection: DetectionResult) -> None:
        """Increment grid cell counts for all corners in the detection."""
        w, h = detection.image_size
        pts = detection.charuco_corners.reshape(-1, 2)
        for pt in pts:
            col = min(int(pt[0] / w * _GRID_COLS), _GRID_COLS - 1)
            row = min(int(pt[1] / h * _GRID_ROWS), _GRID_ROWS - 1)
            self._grid_counts[row, col] += 1
