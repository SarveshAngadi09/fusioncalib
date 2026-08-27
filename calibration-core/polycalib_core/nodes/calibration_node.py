# Copyright (C) 2026 Sarvesh Angadi
# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial licenses available — see LICENSE-COMMERCIAL.md

"""FusionCalib ROS2 calibration node — single-camera and stereo modes."""

from __future__ import annotations

import threading
from pathlib import Path

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import String
from std_srvs.srv import Trigger
import message_filters

from polycalib_core.session.models import BoardConfig, SessionState
from polycalib_core.session.session_manager import SessionManager
from polycalib_core.session.session_writer import result_to_json, write_session


class CalibrationNode(Node):
    """ROS2 node that ingests camera frames and orchestrates calibration.

    Modes:
        ``single`` — one camera, intrinsic calibration only.
            Subscribes to ``left_topic``.
        ``stereo`` — two cameras, intrinsic + extrinsic calibration.
            Subscribes to ``left_topic`` and ``right_topic``.

    Services:
        ``/polycalib/start`` — begin frame collection (idle → collecting).
        ``/polycalib/solve`` — trigger solve (ready_to_solve → solving → done).

    Topics published:
        ``/polycalib/status`` — current :class:`SessionState` string.
        ``/polycalib/result`` — JSON result summary after a successful solve.
    """

    _SYNC_SLOP_SEC = 0.05

    def __init__(self) -> None:
        super().__init__("fusioncalib_node")
        self._bridge = CvBridge()
        self._declare_parameters()

        mode: str = self.get_parameter("mode").get_parameter_value().string_value
        left_topic: str = self.get_parameter("left_topic").get_parameter_value().string_value
        right_topic: str = self.get_parameter("right_topic").get_parameter_value().string_value
        left_id: str = self.get_parameter("left_camera_id").get_parameter_value().string_value
        right_id: str = self.get_parameter("right_camera_id").get_parameter_value().string_value
        min_frames: int = self.get_parameter("min_frames").get_parameter_value().integer_value
        session_dir: str = self.get_parameter("session_dir").get_parameter_value().string_value
        autostart: bool = self.get_parameter("autostart").get_parameter_value().bool_value

        board_config = BoardConfig()
        self._session_dir = Path(session_dir)
        self._session = SessionManager(
            board_config=board_config,
            mode=mode,
            left_camera_id=left_id,
            left_topic=left_topic,
            right_camera_id=right_id,
            right_topic=right_topic,
            min_frames=min_frames,
        )

        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )

        self._status_pub = self.create_publisher(String, "/polycalib/status", 10)
        self._result_pub = self.create_publisher(String, "/polycalib/result", 10)

        self.create_service(Trigger, "/polycalib/start", self._handle_start)
        self.create_service(Trigger, "/polycalib/solve", self._handle_solve)

        if mode == "single":
            self._left_sub = self.create_subscription(
                Image, left_topic, self._on_single_frame, sensor_qos
            )
        else:
            self._left_filter = message_filters.Subscriber(
                self, Image, left_topic, qos_profile=sensor_qos
            )
            self._right_filter = message_filters.Subscriber(
                self, Image, right_topic, qos_profile=sensor_qos
            )
            self._sync = message_filters.ApproximateTimeSynchronizer(
                [self._left_filter, self._right_filter],
                queue_size=10,
                slop=self._SYNC_SLOP_SEC,
            )
            self._sync.registerCallback(self._on_stereo_pair)

        self.create_timer(1.0, self._publish_status)

        if autostart:
            self._session.start_collection()

        self.get_logger().info(
            "FusionCalib started | mode=%s | left=%s%s",
            mode,
            left_topic,
            f" | right={right_topic}" if mode == "stereo" else "",
        )
        self._publish_status()

    # ------------------------------------------------------------------
    # Parameter declaration
    # ------------------------------------------------------------------

    def _declare_parameters(self) -> None:
        """Declare node parameters with defaults."""
        self.declare_parameter("mode", "single")
        self.declare_parameter("left_topic", "/camera/color/image_raw")
        self.declare_parameter("right_topic", "/camera2/color/image_raw")
        self.declare_parameter("left_camera_id", "left")
        self.declare_parameter("right_camera_id", "right")
        self.declare_parameter("min_frames", 20)
        self.declare_parameter("session_dir", "/sessions")
        self.declare_parameter("autostart", True)

    # ------------------------------------------------------------------
    # Frame callbacks
    # ------------------------------------------------------------------

    def _on_single_frame(self, msg: Image) -> None:
        """Handle a single camera frame (single mode)."""
        image = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        result = self._session.add_frame(image)

        if result.accepted:
            self.get_logger().debug(
                "Frame accepted: count=%d coverage=%.2f",
                result.frame_count,
                result.coverage_score,
            )
            self._publish_status()
        elif result.reason:
            self.get_logger().debug("Frame rejected: %s", result.reason)

    def _on_stereo_pair(self, left_msg: Image, right_msg: Image) -> None:
        """Handle a synchronised stereo frame pair (stereo mode)."""
        image_left = self._bridge.imgmsg_to_cv2(left_msg, desired_encoding="bgr8")
        image_right = self._bridge.imgmsg_to_cv2(right_msg, desired_encoding="bgr8")
        result = self._session.add_frame(image_left, image_right)

        if result.accepted:
            self.get_logger().debug(
                "Stereo pair accepted: count=%d coverage=%.2f",
                result.frame_count,
                result.coverage_score,
            )
            self._publish_status()
        elif result.reason and self._session.state == SessionState.COLLECTING:
            self.get_logger().debug("Pair rejected: %s", result.reason)

    # ------------------------------------------------------------------
    # Service handlers
    # ------------------------------------------------------------------

    def _handle_start(
        self, _request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Handle /polycalib/start service call."""
        try:
            self._session.start_collection()
            response.success = True
            response.message = "Collection started."
            self._publish_status()
        except RuntimeError as exc:
            response.success = False
            response.message = str(exc)
        return response

    def _handle_solve(
        self, _request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        """Handle /polycalib/solve service call — runs the solve in a thread."""
        if self._session.state != SessionState.READY_TO_SOLVE:
            response.success = False
            response.message = (
                f"Cannot solve from state '{self._session.state}'. "
                f"Need {SessionState.READY_TO_SOLVE}."
            )
            return response

        threading.Thread(target=self._run_solve_async, daemon=True).start()
        response.success = True
        response.message = "Solve started asynchronously."
        return response

    def _run_solve_async(self) -> None:
        """Run solve in a background thread and publish the result."""
        self._publish_status()
        try:
            solve_result = self._session.solve()
        except Exception as exc:
            self.get_logger().error("Solve failed: %s", exc)
            self._publish_status()
            return

        # Unpack result based on mode.
        if isinstance(solve_result, tuple):
            intr_left, intr_right, ext = solve_result
            intrinsics = [intr_left, intr_right]
            extrinsics = [ext]
        else:
            intrinsics = [solve_result]
            extrinsics = None

        # Write YAML to disk.
        try:
            output_path = write_session(
                session_id=self._session.session_id,
                intrinsics=intrinsics,
                output_dir=self._session_dir,
                extrinsics=extrinsics,
            )
            self.get_logger().info("Calibration written to %s", output_path)
        except Exception as exc:
            self.get_logger().error("Failed to write session: %s", exc)

        # Publish JSON result summary.
        json_str = result_to_json(
            session_id=self._session.session_id,
            intrinsics=intrinsics,
            extrinsics=extrinsics,
        )
        msg = String()
        msg.data = json_str
        self._result_pub.publish(msg)

        self._publish_status()

    # ------------------------------------------------------------------
    # Status publisher
    # ------------------------------------------------------------------

    def _publish_status(self) -> None:
        """Publish the current session state string to /polycalib/status."""
        msg = String()
        msg.data = self._session.state.value
        self._status_pub.publish(msg)


def main(args: list[str] | None = None) -> None:
    """Entry point for the calibration node."""
    rclpy.init(args=args)
    node = CalibrationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
