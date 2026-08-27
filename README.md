# FusionCalib

**Multimodal sensor calibration for robotics rigs.**

FusionCalib solves extrinsic and intrinsic calibration across RGB cameras, depth sensors, thermal cameras, and LiDAR — in a single unified workflow. It is ROS2-native, target-based, and designed for engineers who need calibration to be fast, repeatable, and production-ready.

---

## Who this is for

Robotics engineers deploying multi-sensor rigs on legged robots, wheeled platforms, or UAVs. If you are currently running three separate calibration tools and stitching together their outputs by hand, FusionCalib is built for you.

---

## What is supported

### v0 (current)
- RGB + Depth camera pairs (Intel RealSense D-series, Azure Kinect, ZED 2)
- ChArUco board target detection
- Extrinsic calibration between RGB and depth sensors
- Output: YAML/JSON calibration file compatible with ROS2 tf2, RTAB-Map, and ORB-SLAM3

### Roadmap
| Version | Feature |
|---------|---------|
| v1 | Thermal camera support (heated asymmetric circle grid target) |
| v1 | Thermal ↔ RGB and Thermal ↔ LiDAR extrinsics |
| v2 | LiDAR support (Ouster, Velodyne, Livox) |
| v2 | Targetless background drift detection — flags sensor misalignment during normal operation |

---

## How it works

FusionCalib runs as a ROS2 node. Your sensors publish data on standard ROS2 topics. FusionCalib subscribes to those topics, guides you through a calibration session via a browser-based wizard, and writes a calibration file you can import directly into your robot stack.

No USB camera capture. No vendor-specific SDKs. If your sensor has a ROS2 driver, it works with FusionCalib.

---

## Quick start

### Prerequisites
- Docker and Docker Compose
- A ROS2 Humble environment (or use the provided Docker stack)
- A printed ChArUco board (6×8, 200 mm — PDF in `calibration-target/`)

### Run with Docker Compose

```bash
git clone https://github.com/sarveshangadi/fusioncalib.git
cd fusioncalib
cp .env.example .env
docker compose up
```

Open `http://localhost:3000` in your browser. The calibration wizard will guide you through the rest.

### Run the ROS2 node directly

```bash
cd calibration-core
colcon build --packages-select polycalib_core
source install/setup.bash
ros2 run polycalib_core calibration_node
```

Configure your sensor topics in `.env` or via ROS2 parameters.

---

## Output format

FusionCalib writes a YAML calibration file after each session:

```yaml
fusionCalib:
  session_id: "2026-08-27T14:30:00Z"
  sensors:
    - id: rgb_camera
      intrinsics: { ... }
    - id: depth_camera
      intrinsics: { ... }
  extrinsics:
    - pair: [rgb_camera, depth_camera]
      transform: { translation: [...], rotation: [...] }
```

See [docs/reference/output-format.md](docs/reference/output-format.md) for the full schema.

---

## Documentation

- [Introduction](docs/intro.md)
- [Installation](docs/getting-started/installation.md)
- [Supported sensors](docs/guides/supported-sensors.md)
- [Calibration board guide](docs/guides/calibration-board.md)
- [RGB + Depth calibration walkthrough](docs/guides/rgb-depth-calibration.md)
- [Export formats](docs/guides/export-formats.md)
- [ROS2 topic reference](docs/reference/ros2-topics.md)
- [Architecture overview](docs/architecture/overview.md)

---

## License

FusionCalib is dual-licensed:

- **AGPL-3.0** — free for open-source use. See [LICENSE](LICENSE).
- **Commercial license** — for proprietary or embedded deployments. See [LICENSE-COMMERCIAL.md](LICENSE-COMMERCIAL.md) or contact [sarvesh.angadi1997@gmail.com](mailto:sarvesh.angadi1997@gmail.com).

---

## Citation

If you use FusionCalib in academic work, please cite it using [CITATION.cff](CITATION.cff).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security issues: see [SECURITY.md](SECURITY.md).
