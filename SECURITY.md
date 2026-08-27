# Security Policy

## Supported versions

| Version | Security fixes |
|---------|---------------|
| 0.x (current) | Yes |

## Reporting a vulnerability

Do not open a public GitHub issue for security vulnerabilities.

Email: [sarvesh.angadi1997@gmail.com](mailto:sarvesh.angadi1997@gmail.com)

Include:
- Description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept
- Your preferred disclosure timeline

You will receive an acknowledgement within 48 hours and a status update
within 7 days. We will coordinate a fix and disclosure date with you before
publishing anything publicly.

## Scope

FusionCalib is a local-network tool intended to run inside a robot's onboard
network or a secured lab network. It is not designed to be exposed to the
public internet. Vulnerabilities in the following areas are in scope:

- The FastAPI server (`calibration-api/`) — injection, auth bypass, path traversal
- The WebSocket bridge — message spoofing, denial of service
- The ROS2 node — malicious topic payloads leading to code execution
- The web UI — XSS, CSRF

Vulnerabilities that require physical access to the robot's network with no
other impact are out of scope.
