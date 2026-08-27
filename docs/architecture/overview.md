---
title: Architecture Overview
---

# Architecture Overview

FusionCalib is composed of three services that communicate over a local network.

```
┌─────────────────────────────────────────────┐
│                Robot / Host                  │
│                                              │
│  Sensor drivers (ROS2 nodes)                │
│    │  /camera/color/image_raw               │
│    │  /camera/depth/image_rect_raw          │
│    ▼                                        │
│  ┌─────────────────────┐                   │
│  │  polycalib_core     │  ROS2 node        │
│  │  (calibration-core) │                   │
│  │                     │                   │
│  │  - Frame ingestion  │                   │
│  │  - Target detection │                   │
│  │  - Solver           │                   │
│  │  - Session state    │                   │
│  └────────┬────────────┘                   │
│           │ WebSocket / REST                │
│           ▼                                 │
│  ┌─────────────────────┐                   │
│  │  calibration-api    │  FastAPI server   │
│  │  (FastAPI + WS)     │                   │
│  └────────┬────────────┘                   │
│           │ HTTP / WebSocket                │
│           ▼                                 │
│  ┌─────────────────────┐                   │
│  │  calibration-webapp │  Browser UI       │
│  │  (React + TS)       │                   │
│  └─────────────────────┘                   │
└─────────────────────────────────────────────┘
```

## Components

### calibration-core (ROS2 Python package)

The core calibration logic runs as a ROS2 node. It subscribes to sensor
topics, detects calibration targets, runs the solver, and manages session
state. It exposes its state and control interface over WebSocket to the API
server.

Sub-packages:
- `nodes/` — ROS2 node entry point
- `detectors/` — target detection plugins (ChArUco v0; circle grid v1)
- `solvers/` — calibration solvers (OpenCV-based v0)
- `session/` — session persistence and replay

### calibration-api (FastAPI)

A thin REST + WebSocket server that bridges the web UI and the ROS2 node.
The ROS2 node is the source of truth; the API server relays commands and
status without duplicating state.

### calibration-webapp (React + TypeScript)

A browser-based wizard that guides the operator through calibration steps:
topic configuration, frame collection, detection review, solve, and export.
Communicates with the API server over WebSocket for real-time frame previews
and status updates.

## Architecture Decision Records

- [ADR-0001: ROS2-native sensor input](adr/ADR-0001-ros2-native.md)
