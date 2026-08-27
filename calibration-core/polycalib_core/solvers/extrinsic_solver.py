# Copyright (C) 2026 Sarvesh Angadi
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial licenses available — see LICENSE-COMMERCIAL.md

"""Stereo extrinsic calibration solver using paired ChArUco detections."""

from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np

from polycalib_core.session.models import (
    BoardConfig,
    DetectionResult,
    ExtrinsicResult,
    IntrinsicResult,
)

logger = logging.getLogger(__name__)

# Minimum number of ChArUco corners that must appear in BOTH images of a pair.
_MIN_SHARED_CORNERS = 6


class ExtrinsicSolver:
    """Accumulates synchronised left/right ChArUco detections and solves
    for the rigid transform between the two camera frames.

    Intrinsics for both cameras must be supplied at solve time. The solver
    uses ``cv2.stereoCalibrate`` with ``CALIB_FIX_INTRINSIC`` so only the
    extrinsic parameters (R, T) are optimised.
    """

    def __init__(
        self,
        board_config: BoardConfig,
        camera_id_left: str,
        camera_id_right: str,
        min_frames: int = 20,
    ) -> None:
        """Initialise the solver.

        Args:
            board_config: Board geometry matching that used during detection.
            camera_id_left: Identifier for the left camera.
            camera_id_right: Identifier for the right camera.
            min_frames: Minimum accepted frame pairs before :meth:`solve` may
                be called.
        """
        self._board = board_config.make_board()
        self._camera_id_left = camera_id_left
        self._camera_id_right = camera_id_right
        self._min_frames = min_frames

        # Accumulated object points and image points for stereo calibration.
        self._obj_points: list[np.ndarray] = []    # 3-D board corner positions
        self._img_points_left: list[np.ndarray] = []
        self._img_points_right: list[np.ndarray] = []
        self._image_size: Optional[tuple[int, int]] = None

    @property
    def frame_count(self) -> int:
        """Number of accepted frame pairs."""
        return len(self._obj_points)

    @property
    def is_ready(self) -> bool:
        """True when enough frame pairs are available to attempt a solve."""
        return self.frame_count >= self._min_frames

    def add_frame_pair(
        self,
        det_left: DetectionResult,
        det_right: DetectionResult,
    ) -> bool:
        """Attempt to accept a synchronised detection pair.

        Both detections must share at least ``_MIN_SHARED_CORNERS`` common
        corner IDs. Only the shared corners are kept so that both views have
        the same set of 2-D↔3-D correspondences.

        Args:
            det_left: Detection from the left camera.
            det_right: Detection from the right camera.

        Returns:
            True if the pair was accepted, False if it was rejected.
        """
        shared_ids, idx_l, idx_r = self._shared_corner_indices(det_left, det_right)

        if len(shared_ids) < _MIN_SHARED_CORNERS:
            return False

        corners_l = det_left.charuco_corners[idx_l]   # (M, 1, 2)
        corners_r = det_right.charuco_corners[idx_r]  # (M, 1, 2)

        obj_pts = self._board_object_points(shared_ids)  # (M, 1, 3)

        self._obj_points.append(obj_pts)
        self._img_points_left.append(corners_l)
        self._img_points_right.append(corners_r)
        self._image_size = det_left.image_size

        logger.debug(
            "Extrinsic: pair accepted (%d/%d), shared_corners=%d",
            self.frame_count,
            self._min_frames,
            len(shared_ids),
        )
        return True

    def solve(
        self,
        intrinsics_left: IntrinsicResult,
        intrinsics_right: IntrinsicResult,
    ) -> ExtrinsicResult:
        """Solve for the stereo extrinsic transform.

        Intrinsics are fixed during the stereo solve (``CALIB_FIX_INTRINSIC``).
        Only R and T are optimised.

        Args:
            intrinsics_left: Solved intrinsics for the left camera.
            intrinsics_right: Solved intrinsics for the right camera.

        Returns:
            An :class:`ExtrinsicResult` containing R, T, and reprojection error.

        Raises:
            RuntimeError: If fewer than ``min_frames`` pairs are available or
                if OpenCV's stereo calibration fails.
        """
        if not self.is_ready:
            raise RuntimeError(
                f"Not enough frame pairs: {self.frame_count}/{self._min_frames}."
            )
        if self._image_size is None:
            raise RuntimeError("No image size recorded.")

        flags = cv2.CALIB_FIX_INTRINSIC

        rms, *_, R, T, _E, _F = cv2.stereoCalibrate(
            objectPoints=self._obj_points,
            imagePoints1=self._img_points_left,
            imagePoints2=self._img_points_right,
            cameraMatrix1=intrinsics_left.camera_matrix,
            distCoeffs1=intrinsics_left.dist_coeffs,
            cameraMatrix2=intrinsics_right.camera_matrix,
            distCoeffs2=intrinsics_right.dist_coeffs,
            imageSize=self._image_size,
            flags=flags,
            criteria=(cv2.TERM_CRITERIA_MAX_ITER + cv2.TERM_CRITERIA_EPS, 100, 1e-5),
        )

        logger.info(
            "Extrinsic solve [%s↔%s]: RMS=%.4f px, pairs=%d",
            self._camera_id_left,
            self._camera_id_right,
            rms,
            self.frame_count,
        )

        return ExtrinsicResult(
            camera_id_left=self._camera_id_left,
            camera_id_right=self._camera_id_right,
            R=R,
            T=T,
            reprojection_error_rms=float(rms),
            frame_count=self.frame_count,
        )

    @staticmethod
    def _shared_corner_indices(
        det_l: DetectionResult,
        det_r: DetectionResult,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Find corner IDs present in both detections.

        Returns:
            Tuple of (shared_ids, indices_in_left, indices_in_right).
        """
        ids_l = det_l.charuco_ids.flatten()
        ids_r = det_r.charuco_ids.flatten()
        shared = np.intersect1d(ids_l, ids_r)
        idx_l = np.array([np.where(ids_l == i)[0][0] for i in shared])
        idx_r = np.array([np.where(ids_r == i)[0][0] for i in shared])
        return shared, idx_l, idx_r

    def _board_object_points(self, corner_ids: np.ndarray) -> np.ndarray:
        """Return 3-D object points for the given corner IDs from the board.

        Args:
            corner_ids: 1-D array of ChArUco corner IDs.

        Returns:
            Array of shape (N, 1, 3) with the 3-D world positions.
        """
        all_obj_pts = self._board.getChessboardCorners()  # (total_corners, 3)
        selected = all_obj_pts[corner_ids].reshape(-1, 1, 3).astype(np.float32)
        return selected
