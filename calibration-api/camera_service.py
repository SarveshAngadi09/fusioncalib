# Copyright (C) 2026 Sarvesh Angadi
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial licenses available — see LICENSE-COMMERCIAL.md

"""USB camera capture service using OpenCV VideoCapture."""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import cv2

from polycalib_core.session.models import SessionState
from polycalib_core.session.session_manager import SessionManager

logger = logging.getLogger(__name__)

# Capture rate for calibration — 5 fps is more than enough.
_CAPTURE_FPS = 5
_FRAME_INTERVAL = 1.0 / _CAPTURE_FPS


def list_cameras(max_index: int = 6) -> list[dict]:
    """Enumerate available USB camera indices.

    Tries VideoCapture(0) through VideoCapture(max_index-1) and returns
    those that open successfully.

    Args:
        max_index: Maximum camera index to probe.

    Returns:
        List of dicts with ``index`` and ``label`` keys.
    """
    cameras = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # CAP_DSHOW faster on Windows
        if cap.isOpened():
            cameras.append({"index": i, "label": f"Camera {i}"})
            cap.release()
    return cameras


class CameraService:
    """Captures frames from USB cameras and feeds them into a SessionManager.

    Runs a background thread that reads frames at ``_CAPTURE_FPS`` and calls
    ``session.add_frame()`` whenever the session is in COLLECTING state.
    Stops automatically when the session leaves COLLECTING.
    """

    def __init__(
        self,
        session: SessionManager,
        left_index: int = 0,
        right_index: int = 1,
    ) -> None:
        self._session = session
        self._left_index = left_index
        self._right_index = right_index
        self._mode = session._mode
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the background capture thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info(
            "CameraService started | mode=%s | left=%d%s",
            self._mode,
            self._left_index,
            f" | right={self._right_index}" if self._mode == "stereo" else "",
        )

    def stop(self) -> None:
        """Stop the capture thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)

    def _capture_loop(self) -> None:
        """Main capture loop — runs in background thread."""
        cap_left = cv2.VideoCapture(self._left_index, cv2.CAP_DSHOW)
        cap_right = (
            cv2.VideoCapture(self._right_index, cv2.CAP_DSHOW)
            if self._mode == "stereo"
            else None
        )

        if not cap_left.isOpened():
            logger.error("Cannot open left camera (index=%d)", self._left_index)
            return
        if cap_right and not cap_right.isOpened():
            logger.error("Cannot open right camera (index=%d)", self._right_index)
            cap_left.release()
            return

        try:
            while not self._stop_event.is_set():
                t0 = time.monotonic()

                state = self._session.state
                if state not in (SessionState.COLLECTING, SessionState.READY_TO_SOLVE):
                    time.sleep(0.1)
                    continue

                if state != SessionState.COLLECTING:
                    time.sleep(0.1)
                    continue

                ret_l, frame_l = cap_left.read()
                if not ret_l:
                    logger.warning("Left camera read failed.")
                    time.sleep(0.1)
                    continue

                if self._mode == "stereo":
                    ret_r, frame_r = cap_right.read()
                    if not ret_r:
                        logger.warning("Right camera read failed.")
                        time.sleep(0.1)
                        continue
                    result = self._session.add_frame(frame_l, frame_r)
                else:
                    result = self._session.add_frame(frame_l)

                if result.accepted:
                    logger.debug(
                        "Frame accepted: count=%d coverage=%.2f",
                        result.frame_count,
                        result.coverage_score,
                    )

                elapsed = time.monotonic() - t0
                sleep_time = _FRAME_INTERVAL - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
        finally:
            cap_left.release()
            if cap_right:
                cap_right.release()
            logger.info("CameraService stopped.")
