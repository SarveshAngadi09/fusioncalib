# Contributing to FusionCalib

Thank you for your interest in contributing.

## Before you start

- Check open issues and pull requests to avoid duplicating work.
- For significant changes, open an issue first to discuss the approach.
- FusionCalib uses a dual license (AGPL-3.0 + commercial). By submitting a
  pull request, you agree that your contribution is licensed under AGPL-3.0-or-later
  and that Sarvesh Angadi may offer it under commercial terms as well.

## Development setup

```bash
git clone https://github.com/sarveshangadi/fusioncalib.git
cd fusioncalib
cp .env.example .env
```

For the ROS2 node:

```bash
cd calibration-core
pip install -e ".[dev]"
```

## Code style

- Python: type hints on all function signatures, docstrings on public functions.
- Follow ROS2 rclpy node conventions.
- Run `flake8` and `mypy` before submitting.
- No calibration math in scaffold files — keep core logic in `detectors/` and `solvers/`.

## Commit messages

Use the conventional commits format:

```
feat(core): add ChArUco detector skeleton
fix(api): correct WebSocket disconnect handling
docs(adr): add ADR-0002 for session persistence
```

## Pull request checklist

- [ ] Type hints on all new functions
- [ ] Docstring on all new public functions
- [ ] AGPL license header on all new `.py` files
- [ ] Tests for new logic in `calibration-core/test/`
- [ ] Documentation updated if public API changed

## Reporting bugs

Open a GitHub issue with:
- ROS2 distribution and OS
- Sensor model and ROS2 driver version
- Minimal steps to reproduce
- Relevant log output from `ros2 run polycalib_core calibration_node`
