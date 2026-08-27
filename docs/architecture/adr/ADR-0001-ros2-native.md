# ADR-0001: ROS2-native sensor input over USB-native capture

**Date:** 2026-08-27
**Status:** Accepted

## Context

FusionCalib needs to ingest data from multiple sensor modalities — RGB cameras,
depth sensors, thermal cameras, and LiDAR. The first design decision is how
sensor data enters the system.

Two approaches were considered:

**Option A — USB-native capture:** The calibration tool opens camera devices
directly via OS-level APIs (V4L2, libusb, vendor SDKs). This is what most
single-modality calibration tools do (e.g., OpenCV's VideoCapture, librealsense).

**Option B — ROS2-native topics:** The calibration tool subscribes to ROS2
topics. Sensors are handled by their own ROS2 drivers, which already exist for
every sensor class we target.

## Decision

FusionCalib uses ROS2-native topic subscription (Option B) for all sensor input.
The calibration node never opens a device directly.

## Reasoning

### Sensor coverage without vendor lock-in

Every serious robotics sensor ships with or has a community ROS2 driver.
By consuming standard ROS2 image and point cloud messages, FusionCalib is
immediately compatible with any sensor that has a driver — without writing
or maintaining vendor-specific capture code.

USB-native capture would require per-vendor integration for each modality:
librealsense for RealSense, Azure Kinect SDK for Kinect, ZED SDK for ZED,
and entirely different APIs for thermal cameras and LiDAR. That is not a
calibration tool; that is a hardware abstraction layer — which ROS2 already
provides.

### Multi-sensor synchronization

ROS2 message_filters provides time-synchronized subscription across multiple
topics out of the box. Achieving the same synchronization with raw USB streams
requires building a custom synchronization layer. For multi-sensor calibration,
synchronization is not optional.

### Deployment model

FusionCalib's target environment is an already-running ROS2 robot stack.
The operator launches FusionCalib alongside their existing sensor nodes.
If sensors were captured via USB, FusionCalib would conflict with existing
drivers for the same device. ROS2 topic subscription has no such conflict:
multiple nodes can subscribe to the same topic.

### Reproducibility

ROS2 bag files are the standard way to record and replay sensor data in
robotics. A ROS2-native tool inherits this for free: record a calibration
session with `ros2 bag record`, replay it later for debugging or re-export.
USB-native tools have no equivalent path to replay.

## Trade-offs accepted

- **ROS2 is required.** Users without a ROS2 environment cannot run FusionCalib
  without Docker. The Docker Compose deployment mitigates this.
- **Network overhead.** Topic messages carry serialization overhead vs. raw
  frame buffers. At calibration frame rates (1–5 fps), this is not a concern.
- **DDS configuration.** Multi-machine ROS2 setups require correct DDS network
  configuration. Documented in installation guide.

## Alternatives rejected

**USB-native (Option A):** Rejected because it requires per-vendor SDK
maintenance, conflicts with existing robot drivers, and provides no path to
multi-sensor time synchronization or session replay.

**Shared memory / zero-copy:** Considered for v2 (LiDAR point clouds at high
rates). Not needed for v0 RGB + Depth at calibration frame rates.
