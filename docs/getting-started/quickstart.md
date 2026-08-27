---
sidebar_position: 2
title: Quickstart
---

# Quickstart

This guide runs your first RGB + Depth calibration session in under 10 minutes.

## What you need

- FusionCalib running (see [Installation](installation.md))
- A camera publishing on the configured ROS2 topics
- A printed ChArUco board (6×8, 200 mm — PDF in `calibration-target/`)

## Steps

### 1. Verify topics are publishing

```bash
ros2 topic hz /camera/color/image_raw
ros2 topic hz /camera/depth/image_rect_raw
```

Both should show a non-zero publish rate.

### 2. Open the calibration wizard

Navigate to `http://localhost:3000` in your browser.

### 3. Follow the wizard

The wizard will guide you through:
1. Confirming topic configuration
2. Collecting frame pairs (move the board to cover the field of view)
3. Reviewing detection quality
4. Running the solver
5. Exporting the calibration file

### 4. Export the calibration

The wizard exports a YAML file to the `sessions/` directory. Copy it to your
robot stack:

```bash
cp sessions/<session-id>/calibration.yaml ~/ros2_ws/src/your_robot/config/
```

See [Export formats](../guides/export-formats.md) for how to load this file
into tf2, RTAB-Map, or ORB-SLAM3.
