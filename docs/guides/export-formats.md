---
title: Export Formats
---

# Export Formats

FusionCalib exports calibration results in YAML (primary) and JSON (secondary).

## YAML output (default)

```yaml
fusionCalib:
  version: "0.1"
  session_id: "2026-08-27T14:30:00Z"
  sensors:
    - id: rgb_camera
      topic: /camera/color/image_raw
      intrinsics:
        width: 1280
        height: 720
        camera_matrix: [fx, 0, cx, 0, fy, cy, 0, 0, 1]
        distortion_model: plumb_bob
        distortion_coefficients: [k1, k2, p1, p2, k3]
    - id: depth_camera
      topic: /camera/depth/image_rect_raw
      intrinsics:
        width: 1280
        height: 720
        camera_matrix: [fx, 0, cx, 0, fy, cy, 0, 0, 1]
        distortion_model: plumb_bob
        distortion_coefficients: [k1, k2, p1, p2, k3]
  extrinsics:
    - pair: [depth_camera, rgb_camera]
      translation: [tx, ty, tz]
      rotation_quaternion: [qx, qy, qz, qw]
  quality:
    reprojection_error_rms_px: 0.42
    frame_count: 35
```

## Loading in ROS2 tf2

```python
import yaml
from geometry_msgs.msg import TransformStamped

with open("calibration.yaml") as f:
    cal = yaml.safe_load(f)["fusionCalib"]

ext = cal["extrinsics"][0]
t = TransformStamped()
t.transform.translation.x = ext["translation"][0]
# ... (fill remaining fields)
```

## Loading in RTAB-Map

Place the YAML file path in your RTAB-Map launch configuration under
`camera_info_url`. See RTAB-Map documentation for the exact parameter name
for your sensor model.

## Loading in ORB-SLAM3

ORB-SLAM3 uses a custom YAML format. FusionCalib will include an ORB-SLAM3
export option in a future release. For now, extract the camera matrix and
distortion coefficients from the FusionCalib YAML manually.
