---
title: RGB + Depth Calibration
---

# RGB + Depth Calibration

This guide covers a full calibration session between an RGB camera and a depth
sensor using FusionCalib v0.

## Prerequisites

- FusionCalib running and connected to your camera topics (see [Quickstart](../getting-started/quickstart.md))
- ChArUco board printed and mounted (see [Calibration Board](calibration-board.md))

## Session overview

1. **Topic check** — confirm both topics are publishing
2. **Frame collection** — capture 20–50 synchronized frame pairs
3. **Detection review** — verify ChArUco corners were detected correctly
4. **Solve** — compute intrinsics and extrinsics
5. **Export** — write the calibration YAML

## Tips for good calibration

- **Lighting:** Avoid direct sunlight or strong shadows on the board. Diffuse
  indoor lighting works best.
- **Distance:** Keep the board at 0.5–2 m from the camera. Avoid distances
  where the board fills the entire frame.
- **Tilt:** Include frames where the board is tilted ±30° in both X and Y axes.
  This is critical for accurate intrinsic estimation.
- **Coverage:** Use the wizard's heatmap to confirm the board appeared across
  the full image area, not just the center.

## Understanding the output

The calibration file includes:
- Intrinsics for each camera (focal length, principal point, distortion coefficients)
- The extrinsic transform from the depth sensor frame to the RGB camera frame
- Reprojection error (RMS) — values below 1.0 px are acceptable; below 0.5 px is good

## Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| No board detected | Board not fully in frame, poor lighting, or wrong ArUco dictionary |
| High reprojection error (> 2 px) | Too few frames, insufficient tilt variety, or board warping |
| Depth frames not synchronized | Clock offset between sensors — check driver time synchronization |
