---
title: Supported Sensors
---

# Supported Sensors

FusionCalib works with any sensor that has a ROS2 driver publishing standard
`sensor_msgs/Image` messages. The sensors below have been tested.

## v0 — RGB + Depth (current)

| Sensor | ROS2 driver | RGB topic | Depth topic |
|--------|------------|-----------|-------------|
| Intel RealSense D435/D455 | `realsense2_camera` | `/camera/color/image_raw` | `/camera/depth/image_rect_raw` |
| Azure Kinect | `azure_kinect_ros_driver` | `/rgb/image_raw` | `/depth/image_raw` |
| ZED 2 / ZED 2i | `zed-ros2-wrapper` | `/zed/zed_node/rgb/image_rect_color` | `/zed/zed_node/depth/depth_registered` |

Topic names are configurable via `.env` or ROS2 parameters.

## v1 — Thermal (planned)

| Sensor | Notes |
|--------|-------|
| FLIR Boson | 320×256 or 640×512 — ROS2 driver in development |
| Seek Mosaic | High-resolution thermal |

## v2 — LiDAR (planned)

| Sensor | Notes |
|--------|-------|
| Ouster OS0 / OS1 | `ros2_ouster` driver |
| Velodyne VLP-16 | `velodyne` ROS2 driver |
| Livox Mid-360 | `livox_ros_driver2` |

## Adding an untested sensor

If your sensor publishes `sensor_msgs/Image` on ROS2 topics, it should work.
Set the topic names in `.env`:

```bash
RGB_TOPIC=/your/rgb/topic
DEPTH_TOPIC=/your/depth/topic
```

Open an issue if you test a sensor not listed here — we will add it.
