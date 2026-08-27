---
title: Output Format Reference
---

# Output Format Reference

## File location

Calibration files are written to `sessions/<session-id>/calibration.yaml`
inside the FusionCalib working directory.

## Full schema

```yaml
fusionCalib:
  version: string            # Schema version, e.g. "0.1"
  session_id: string         # ISO 8601 timestamp of session start
  sensors:
    - id: string             # Sensor identifier
      topic: string          # ROS2 topic this sensor was read from
      intrinsics:
        width: integer
        height: integer
        camera_matrix:       # Row-major 3x3 matrix as 9-element list
          - float            # [fx, 0, cx, 0, fy, cy, 0, 0, 1]
        distortion_model: string   # "plumb_bob" | "rational_polynomial"
        distortion_coefficients:
          - float            # [k1, k2, p1, p2, k3] for plumb_bob
  extrinsics:
    - pair: [string, string] # [source_sensor_id, target_sensor_id]
      translation: [float, float, float]         # [tx, ty, tz] in meters
      rotation_quaternion: [float, float, float, float]  # [qx, qy, qz, qw]
      rotation_matrix:     # Row-major 3x3 as 9-element list (redundant, for convenience)
        - float
  quality:
    reprojection_error_rms_px: float  # RMS reprojection error across all frames
    frame_count: integer              # Number of frame pairs used in solve
    coverage_score: float             # 0.0–1.0, board coverage across image area
```

## Versioning

The `version` field will increment when the schema changes in a
backward-incompatible way. Parsers should check this field before reading.
