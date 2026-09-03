# Copyright (C) 2026 Sarvesh Angadi
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial licenses available — see LICENSE-COMMERCIAL.md

"""FusionCalib REST API — no ROS2, pure Python + OpenCV."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import io

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import app_state
from camera_service import CameraService, list_cameras
from polycalib_core.session.models import BoardConfig, SessionState
from polycalib_core.session.session_manager import SessionManager
from polycalib_core.session.session_writer import result_to_json, write_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SESSION_DIR = Path("sessions")


@asynccontextmanager
async def lifespan(app: FastAPI):
    SESSION_DIR.mkdir(exist_ok=True)
    logger.info("FusionCalib API ready. Open http://localhost:8000")
    yield
    if app_state.camera:
        app_state.camera.stop()
    logger.info("FusionCalib API shut down.")


app = FastAPI(
    title="FusionCalib API",
    description="Multimodal sensor calibration — no ROS2 required.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ------------------------------------------------------------------
# Response models
# ------------------------------------------------------------------

class ConfigRequest(BaseModel):
    mode: str = "single"          # "single" or "stereo"
    left_index: int = 0
    right_index: int = 1
    min_frames: int = 20


class ActionResponse(BaseModel):
    success: bool
    message: str


class StatusResponse(BaseModel):
    state: str
    session_id: Optional[str]
    frame_count: int
    result: Optional[dict[str, Any]]


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"ok": True}


@app.get("/cameras", tags=["setup"])
def get_cameras() -> list[dict]:
    """List available USB cameras by index."""
    return list_cameras()


@app.post("/configure", response_model=ActionResponse, tags=["setup"])
def configure(req: ConfigRequest) -> ActionResponse:
    """Configure the calibration session — mode, camera indices, min frames.

    Must be called before /start. Can be called again to reconfigure
    (stops any running camera capture first).
    """
    if req.mode not in ("single", "stereo"):
        raise HTTPException(status_code=422, detail="mode must be 'single' or 'stereo'")

    if app_state.camera:
        app_state.camera.stop()

    app_state.session = SessionManager(
        board_config=app_state.board_config,
        mode=req.mode,
        left_camera_id="left" if req.mode == "stereo" else "camera",
        left_topic=f"usb:{req.left_index}",
        right_camera_id="right",
        right_topic=f"usb:{req.right_index}",
        min_frames=req.min_frames,
    )
    app_state.camera = CameraService(
        session=app_state.session,
        left_index=req.left_index,
        right_index=req.right_index,
    )
    return ActionResponse(success=True, message=f"Configured: mode={req.mode}, left={req.left_index}" +
                          (f", right={req.right_index}" if req.mode == "stereo" else ""))


@app.post("/start", response_model=ActionResponse, tags=["calibration"])
def start_collection() -> ActionResponse:
    """Begin frame collection. Camera capture starts automatically."""
    _require_session()
    try:
        app_state.session.start_collection()
        app_state.camera.start()
        return ActionResponse(success=True, message="Collection started.")
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.post("/solve", response_model=ActionResponse, tags=["calibration"])
def trigger_solve() -> ActionResponse:
    """Trigger the calibration solve (must be in ready_to_solve state)."""
    _require_session()
    if app_state.session.state != SessionState.READY_TO_SOLVE:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot solve from state '{app_state.session.state}'. Collect more frames first."
        )
    app_state.camera.stop()

    import threading
    threading.Thread(target=_run_solve, daemon=True).start()
    return ActionResponse(success=True, message="Solve started.")


@app.get("/status", response_model=StatusResponse, tags=["calibration"])
def get_status() -> StatusResponse:
    """Return current session state, frame count, and result if done."""
    if app_state.session is None:
        return StatusResponse(state="unconfigured", session_id=None, frame_count=0, result=None)

    result = None
    if app_state.session.result is not None:
        r = app_state.session.result
        if isinstance(r, tuple):
            intr_l, intr_r, ext = r
            result = {
                "left_rms": round(intr_l.reprojection_error_rms, 4),
                "right_rms": round(intr_r.reprojection_error_rms, 4),
                "stereo_rms": round(ext.reprojection_error_rms, 4),
                "frame_count": ext.frame_count,
            }
        else:
            result = {
                "rms": round(r.reprojection_error_rms, 4),
                "frame_count": r.frame_count,
            }

    return StatusResponse(
        state=app_state.session.state.value,
        session_id=app_state.session.session_id,
        frame_count=app_state.session.frame_count,
        result=result,
    )


@app.post("/upload", response_model=ActionResponse, tags=["calibration"])
async def upload_image(file: UploadFile = File(...)) -> ActionResponse:
    """Upload a single image for single-camera calibration."""
    _require_session()
    _auto_start_collecting()
    image = await _read_upload(file)
    result = app_state.session.add_frame(image)
    if not result.accepted:
        return ActionResponse(success=False, message=result.reason or "Frame rejected.")
    return ActionResponse(
        success=True,
        message=f"Accepted — {result.frame_count} frames collected (coverage {result.coverage_score:.0%}).",
    )


@app.post("/upload/pair", response_model=ActionResponse, tags=["calibration"])
async def upload_image_pair(
    left: UploadFile = File(...),
    right: UploadFile = File(...),
) -> ActionResponse:
    """Upload a synchronised left + right image pair for stereo calibration."""
    _require_session()
    _auto_start_collecting()
    image_left = await _read_upload(left)
    image_right = await _read_upload(right)
    result = app_state.session.add_frame(image_left, image_right)
    if not result.accepted:
        return ActionResponse(success=False, message=result.reason or "Pair rejected.")
    return ActionResponse(
        success=True,
        message=f"Accepted — {result.frame_count} pairs collected (coverage {result.coverage_score:.0%}).",
    )


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

async def _read_upload(file: UploadFile) -> np.ndarray:
    """Decode an uploaded image file into an OpenCV BGR array."""
    data = await file.read()
    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=422, detail=f"Cannot decode image: {file.filename}")
    return image


def _require_session() -> None:
    if app_state.session is None:
        raise HTTPException(status_code=400, detail="Not configured. Call POST /configure first.")


def _auto_start_collecting() -> None:
    """If session is idle, silently start collection so uploads work immediately."""
    if app_state.session.state == SessionState.IDLE:
        app_state.session.start_collection()


def _run_solve() -> None:
    """Run solve in background thread and write results to disk."""
    try:
        solve_result = app_state.session.solve()
    except Exception as exc:
        logger.error(f"Solve failed: {exc}")
        return

    if isinstance(solve_result, tuple):
        intr_left, intr_right, ext = solve_result
        intrinsics = [intr_left, intr_right]
        extrinsics = [ext]
    else:
        intrinsics = [solve_result]
        extrinsics = None

    try:
        output_path = write_session(
            session_id=app_state.session.session_id,
            intrinsics=intrinsics,
            output_dir=SESSION_DIR,
            extrinsics=extrinsics,
        )
        logger.info(f"Calibration written to {output_path}")
    except Exception as exc:
        logger.error(f"Failed to write session: {exc}")
