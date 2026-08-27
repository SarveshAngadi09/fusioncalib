# Copyright (C) 2026 Sarvesh Angadi
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial licenses available — see LICENSE-COMMERCIAL.md

"""Session state machine that coordinates detectors and solvers."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Union

from polycalib_core.detectors.charuco_detector import ChArUcoDetector
from polycalib_core.session.models import (
    BoardConfig,
    DetectionResult,
    ExtrinsicResult,
    FrameAddResult,
    IntrinsicResult,
    SessionState,
)
from polycalib_core.solvers.extrinsic_solver import ExtrinsicSolver
from polycalib_core.solvers.intrinsic_solver import IntrinsicSolver

logger = logging.getLogger(__name__)

SolveResult = Union[
    IntrinsicResult,
    tuple[IntrinsicResult, IntrinsicResult, ExtrinsicResult],
]


class SessionManager:
    """Controls the calibration workflow as a thread-safe state machine.

    Modes:
        ``"single"`` — collects frames from one camera, solves intrinsics only.
        ``"stereo"`` — collects synchronised pairs from two cameras, solves
            per-camera intrinsics and the stereo extrinsic transform.

    State transitions:
        IDLE → COLLECTING (via :meth:`start_collection`)
        COLLECTING → READY_TO_SOLVE (automatic, when min_frames reached)
        READY_TO_SOLVE → SOLVING (via :meth:`solve`)
        SOLVING → DONE (on success)
        any → ERROR (on exception)
    """

    def __init__(
        self,
        board_config: BoardConfig,
        mode: str,
        left_camera_id: str,
        left_topic: str,
        right_camera_id: str = "",
        right_topic: str = "",
        min_frames: int = 20,
    ) -> None:
        """Initialise the session manager.

        Args:
            board_config: Board geometry shared by detector and solvers.
            mode: ``"single"`` or ``"stereo"``.
            left_camera_id: Identifier for the primary (or only) camera.
            left_topic: ROS2 topic for the primary camera.
            right_camera_id: Identifier for the right camera (stereo only).
            right_topic: ROS2 topic for the right camera (stereo only).
            min_frames: Minimum frames before :attr:`state` advances to
                ``READY_TO_SOLVE``.
        """
        if mode not in ("single", "stereo"):
            raise ValueError(f"mode must be 'single' or 'stereo', got '{mode}'")

        self._mode = mode
        self._min_frames = min_frames
        self._lock = threading.Lock()
        self._state = SessionState.IDLE
        self._session_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._result: Optional[SolveResult] = None
        self._error: Optional[str] = None

        self._detector = ChArUcoDetector(board_config)

        self._solver_left = IntrinsicSolver(
            board_config, left_camera_id, left_topic, min_frames=min_frames
        )

        if mode == "stereo":
            self._solver_right = IntrinsicSolver(
                board_config, right_camera_id, right_topic, min_frames=min_frames
            )
            self._solver_extrinsic = ExtrinsicSolver(
                board_config, left_camera_id, right_camera_id, min_frames=min_frames
            )
        else:
            self._solver_right = None
            self._solver_extrinsic = None

    # ------------------------------------------------------------------
    # Public state API
    # ------------------------------------------------------------------

    @property
    def state(self) -> SessionState:
        """Current state of the session."""
        with self._lock:
            return self._state

    @property
    def session_id(self) -> str:
        """ISO-8601 timestamp string identifying this session."""
        return self._session_id

    @property
    def frame_count(self) -> int:
        """Number of accepted frames (or frame pairs in stereo mode)."""
        with self._lock:
            if self._mode == "stereo":
                return self._solver_extrinsic.frame_count if self._solver_extrinsic else 0
            return self._solver_left.frame_count

    @property
    def result(self) -> Optional[SolveResult]:
        """Calibration result, available after :attr:`state` is ``DONE``."""
        with self._lock:
            return self._result

    @property
    def error(self) -> Optional[str]:
        """Error message, set when :attr:`state` is ``ERROR``."""
        with self._lock:
            return self._error

    # ------------------------------------------------------------------
    # Control API
    # ------------------------------------------------------------------

    def start_collection(self) -> None:
        """Transition from IDLE to COLLECTING.

        Raises:
            RuntimeError: If the session is not in the IDLE state.
        """
        with self._lock:
            if self._state != SessionState.IDLE:
                raise RuntimeError(
                    f"Cannot start collection from state '{self._state}'."
                )
            self._state = SessionState.COLLECTING
            logger.info("Session %s: collection started.", self._session_id)

    def add_frame(self, image_left, image_right=None) -> FrameAddResult:
        """Detect and add a frame (or frame pair in stereo mode).

        This method accepts raw numpy images (BGR), runs detection internally,
        and updates solver state. Call this from the ROS2 node's frame callback.

        Args:
            image_left: Left (or only) camera image as a numpy array.
            image_right: Right camera image (required in stereo mode).

        Returns:
            A :class:`FrameAddResult` describing whether the frame was accepted.
        """
        with self._lock:
            if self._state != SessionState.COLLECTING:
                return FrameAddResult(
                    accepted=False,
                    frame_count=self.frame_count,
                    coverage_score=0.0,
                    reason=f"not collecting (state={self._state})",
                )

            if self._mode == "single":
                return self._add_single_frame(image_left)
            else:
                if image_right is None:
                    return FrameAddResult(
                        accepted=False,
                        frame_count=self.frame_count,
                        coverage_score=0.0,
                        reason="stereo mode requires image_right",
                    )
                return self._add_stereo_pair(image_left, image_right)

    def solve(self) -> SolveResult:
        """Run the calibration solve.

        Must be called when :attr:`state` is ``READY_TO_SOLVE``. Blocks until
        the solve completes.

        Returns:
            ``IntrinsicResult`` in single mode, or a tuple of
            ``(IntrinsicResult, IntrinsicResult, ExtrinsicResult)`` in stereo mode.

        Raises:
            RuntimeError: If called in the wrong state or if the solve fails.
        """
        with self._lock:
            if self._state != SessionState.READY_TO_SOLVE:
                raise RuntimeError(
                    f"Cannot solve from state '{self._state}'. "
                    "Collect enough frames first."
                )
            self._state = SessionState.SOLVING

        try:
            result = self._run_solve()
            with self._lock:
                self._result = result
                self._state = SessionState.DONE
            logger.info("Session %s: solve complete.", self._session_id)
            return result
        except Exception as exc:
            with self._lock:
                self._state = SessionState.ERROR
                self._error = str(exc)
            logger.error("Session %s: solve failed: %s", self._session_id, exc)
            raise

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _add_single_frame(self, image) -> FrameAddResult:
        """Detect and add a single-camera frame. Called with lock held."""
        detection = self._detector.detect(image)
        if detection is None:
            return FrameAddResult(
                accepted=False,
                frame_count=self._solver_left.frame_count,
                coverage_score=0.0,
                reason="detection failed",
            )

        accepted = self._solver_left.add_frame(detection)
        if accepted:
            self._maybe_advance_to_ready()

        return FrameAddResult(
            accepted=accepted,
            frame_count=self._solver_left.frame_count,
            coverage_score=detection.coverage_score,
            reason="" if accepted else "insufficient new coverage",
        )

    def _add_stereo_pair(self, image_left, image_right) -> FrameAddResult:
        """Detect and add a stereo frame pair. Called with lock held."""
        det_left = self._detector.detect(image_left)
        det_right = self._detector.detect(image_right)

        if det_left is None or det_right is None:
            return FrameAddResult(
                accepted=False,
                frame_count=self._solver_extrinsic.frame_count,
                coverage_score=0.0,
                reason="detection failed on one or both images",
            )

        accepted_ext = self._solver_extrinsic.add_frame_pair(det_left, det_right)
        if accepted_ext:
            self._solver_left.add_frame(det_left)
            self._solver_right.add_frame(det_right)
            self._maybe_advance_to_ready()

        coverage = (det_left.coverage_score + det_right.coverage_score) / 2.0
        return FrameAddResult(
            accepted=accepted_ext,
            frame_count=self._solver_extrinsic.frame_count,
            coverage_score=coverage,
            reason="" if accepted_ext else "insufficient shared corners",
        )

    def _maybe_advance_to_ready(self) -> None:
        """Advance state to READY_TO_SOLVE if min_frames is reached. Lock held."""
        ready = (
            self._solver_left.is_ready
            if self._mode == "single"
            else (
                self._solver_extrinsic.is_ready
                and self._solver_left.is_ready
                and self._solver_right.is_ready
            )
        )
        if ready and self._state == SessionState.COLLECTING:
            self._state = SessionState.READY_TO_SOLVE
            logger.info(
                "Session %s: ready to solve (%d frames).",
                self._session_id,
                self.frame_count,
            )

    def _run_solve(self) -> SolveResult:
        """Execute the actual solve. Called without lock."""
        if self._mode == "single":
            return self._solver_left.solve()

        intrinsics_left = self._solver_left.solve()
        intrinsics_right = self._solver_right.solve()
        extrinsics = self._solver_extrinsic.solve(intrinsics_left, intrinsics_right)
        return (intrinsics_left, intrinsics_right, extrinsics)
