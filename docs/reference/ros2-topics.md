---
title: ROS2 Topic Reference
---

# ROS2 Topic Reference

## Subscribed topics

| Topic | Type | Description |
|-------|------|-------------|
| `/camera/color/image_raw` (default) | `sensor_msgs/Image` | RGB camera frames. Configurable via `rgb_topic` parameter. |
| `/camera/depth/image_rect_raw` (default) | `sensor_msgs/Image` | Depth camera frames. Configurable via `depth_topic` parameter. |

## Published topics

| Topic | Type | Description |
|-------|------|-------------|
| `/polycalib/status` | `std_msgs/String` | Node status string: `idle`, `collecting`, `solving`, `done`, `error`. |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rgb_topic` | string | `/camera/color/image_raw` | RGB image topic to subscribe to. |
| `depth_topic` | string | `/camera/depth/image_rect_raw` | Depth image topic to subscribe to. |

## Setting parameters at launch

```bash
ros2 run polycalib_core calibration_node \
  --ros-args \
  -p rgb_topic:=/my_camera/rgb/image_raw \
  -p depth_topic:=/my_camera/depth/image_raw
```

Or via a YAML parameter file:

```yaml
# params.yaml
fusioncalib_node:
  ros__parameters:
    rgb_topic: /my_camera/rgb/image_raw
    depth_topic: /my_camera/depth/image_raw
```

```bash
ros2 run polycalib_core calibration_node --ros-args --params-file params.yaml
```
