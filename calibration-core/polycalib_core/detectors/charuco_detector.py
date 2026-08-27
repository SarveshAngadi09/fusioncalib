# Copyright (C) 2026 Sarvesh Angadi
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial licenses available — see LICENSE-COMMERCIAL.md

"""ChArUco board detector using OpenCV's aruco module."""

from __future__ import annotations

import cv2
import numpy as np

from polycalib_core.session.models import BoardConfig, DetectionResult


class ChArUcoDetector:
    """Detects ChArUco corners in a single image frame.

    Detection pipeline:
      1. Detect ArUco markers in the image.
      2. Interpolate ChArUco corners from the marker detections.
      3. Reject frames with fewer than ``min_corners`` corners.
      4. Compute a coverage score from the bounding box of detected corners.
    """

    def __init__(
        self,
        board_config: BoardConfig,
        min_corners: int = 6,
        coverage_threshold: float = 0.05,
    ) -> None:
        """Initialise the detector.

        Args:
            board_config: Board geometry and ArUco dictionary settings.
            min_corners: Minimum number of detected ChArUco corners required
                for a detection to be considered valid.
            coverage_threshold: Minimum coverage score (0–1) for a frame to
                be considered usable. Frames below this threshold are rejected.
        """
        self._board = board_config.make_board()
        self._detector_params = board_config.make_detector_params()
        self._dictionary = cv2.aruco.getPredefinedDictionary(board_config.aruco_dict_id)
        self._min_corners = min_corners
        self._coverage_threshold = coverage_threshold
        self._aruco_detector = cv2.aruco.ArucoDetector(
            self._dictionary, self._detector_params
        )

    def detect(self, image: np.ndarray) -> DetectionResult | None:
        """Detect ChArUco corners in ``image``.

        Args:
            image: BGR or grayscale image as a numpy array (H×W or H×W×C).

        Returns:
            A :class:`DetectionResult` if detection succeeded and the frame
            passes quality thresholds, otherwise ``None``.
        """
        gray = self._to_gray(image)
        h, w = gray.shape[:2]
        image_size = (w, h)

        marker_corners, marker_ids, _ = self._aruco_detector.detectMarkers(gray)

        if marker_ids is None or len(marker_ids) < 2:
            return None

        charuco_retval, charuco_corners, charuco_ids = (
            cv2.aruco.interpolateCornersCharuco(
                marker_corners, marker_ids, gray, self._board
            )
        )

        if charuco_retval < self._min_corners:
            return None

        # Refine corner positions to subpixel accuracy.
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        charuco_corners = cv2.cornerSubPix(
            gray,
            charuco_corners,
            winSize=(5, 5),
            zeroZone=(-1, -1),
            criteria=criteria,
        )

        coverage = self._compute_coverage(charuco_corners, image_size)
        if coverage < self._coverage_threshold:
            return None

        return DetectionResult(
            charuco_corners=charuco_corners,
            charuco_ids=charuco_ids,
            image_size=image_size,
            coverage_score=coverage,
        )

    @staticmethod
    def _to_gray(image: np.ndarray) -> np.ndarray:
        """Convert image to grayscale if needed."""
        if image.ndim == 3 and image.shape[2] == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if image.ndim == 3 and image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        return image

    @staticmethod
    def _compute_coverage(
        corners: np.ndarray,
        image_size: tuple[int, int],
    ) -> float:
        """Compute coverage score as bounding-box area fraction of the image.

        Args:
            corners: Detected corners, shape (N, 1, 2).
            image_size: (width, height) of the image.

        Returns:
            Coverage score in [0, 1].
        """
        pts = corners.reshape(-1, 2)
        x_min, y_min = pts.min(axis=0)
        x_max, y_max = pts.max(axis=0)
        w, h = image_size
        bbox_area = (x_max - x_min) * (y_max - y_min)
        image_area = float(w * h)
        return float(np.clip(bbox_area / image_area, 0.0, 1.0))
