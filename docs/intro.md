---
sidebar_position: 1
title: Introduction
---

# FusionCalib

FusionCalib is a multimodal sensor calibration platform for robotics rigs.
It solves extrinsic and intrinsic calibration across RGB cameras, depth
sensors, thermal cameras, and LiDAR in a single unified workflow.

## Why FusionCalib?

Most calibration tools are built for a single sensor modality. When you are
deploying a robot with four different sensor types, you end up running four
different tools, converting between four output formats, and maintaining
four separate calibration pipelines.

FusionCalib is designed from the ground up for multi-sensor rigs. Every
modality shares the same session model, the same output format, and the
same operator workflow.

## Design principles

- **ROS2-native.** All sensor input arrives as ROS2 topics. Any sensor with
  a ROS2 driver works with FusionCalib without modification.
- **Modality-agnostic pipeline.** Adding a new sensor type (thermal, LiDAR)
  is a plugin, not a rewrite.
- **Reproducible sessions.** Every calibration session is saved with full
  provenance — inputs, detections, solver outputs — and can be re-exported.
- **Browser-based operator UI.** A wizard walks the operator through each
  step. No terminal expertise required after initial setup.

## What is implemented

| Feature | Status |
|---------|--------|
| RGB + Depth calibration | v0 — available |
| Thermal camera support | v1 — planned |
| LiDAR support | v2 — planned |
| Background drift detection | v2 — planned |

## Next steps

- [Installation](getting-started/installation.md)
- [Quickstart](getting-started/quickstart.md)
- [Supported sensors](guides/supported-sensors.md)
