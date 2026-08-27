---
sidebar_position: 1
title: Installation
---

# Installation

## Prerequisites

- Docker 24+ and Docker Compose v2
- A printed ChArUco calibration board (6×8 squares, 200 mm — PDF in `calibration-target/`)
- A supported RGB + Depth camera with a ROS2 driver running

## Option 1 — Docker Compose (recommended)

This runs the full stack: ROS2 calibration node, API server, and web UI.

```bash
git clone https://github.com/sarveshangadi/fusioncalib.git
cd fusioncalib
cp .env.example .env
# Edit .env to set your ROS2 topic names and DDS network interface
docker compose up
```

Open `http://localhost:3000` in your browser.

## Option 2 — Native ROS2 install

Requires ROS2 Humble on Ubuntu 22.04.

```bash
# Clone into your ROS2 workspace
cd ~/ros2_ws/src
git clone https://github.com/sarveshangadi/fusioncalib.git
cd ~/ros2_ws

# Install Python dependencies
pip install -r fusioncalib/calibration-core/requirements.txt

# Build
colcon build --packages-select polycalib_core
source install/setup.bash
```

Run the node:

```bash
ros2 run polycalib_core calibration_node \
  --ros-args \
  -p rgb_topic:=/camera/color/image_raw \
  -p depth_topic:=/camera/depth/image_rect_raw
```

## Verifying the installation

```bash
ros2 topic echo /polycalib/status
```

You should see status messages as the node starts up. With a camera
publishing on the configured topics, you will also see frame receipt logs.

## Next step

[Quickstart — run your first calibration session](quickstart.md)
