# Copyright (C) 2026 Sarvesh Angadi
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial licenses available — see LICENSE-COMMERCIAL.md

"""Global application state shared between FastAPI endpoints and CameraService."""

from __future__ import annotations

from typing import Optional

from polycalib_core.session.models import BoardConfig
from polycalib_core.session.session_manager import SessionManager

# Populated on first POST /configure and reset on reconfigure.
session: Optional[SessionManager] = None
camera: Optional["CameraService"] = None  # noqa: F821 — imported at runtime

board_config: BoardConfig = BoardConfig()
