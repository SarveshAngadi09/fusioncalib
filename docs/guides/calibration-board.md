---
title: Calibration Board
---

# Calibration Board

FusionCalib uses a ChArUco board as the calibration target. ChArUco combines
a checkerboard with ArUco markers, which allows partial detection — the board
does not need to be fully visible in every frame.

## Board specification (v0)

| Parameter | Value |
|-----------|-------|
| Type | ChArUco |
| Squares X | 6 |
| Squares Y | 8 |
| Square size | 35 mm |
| Marker size | 25 mm |
| ArUco dictionary | DICT_4X4_50 |
| Printed size | 200 mm × 280 mm |

## Printing the board

Download the PDF from `calibration-target/charuco_6x8_200mm.pdf`. Print at
100% scale (no "fit to page") on A4 or US Letter paper. Verify the printed
square size with a ruler — it must be 35 mm ± 0.5 mm.

Mount the printed board on a rigid, flat surface. Warped boards degrade
detection accuracy.

## Board handling during calibration

- Hold the board steady during each capture — motion blur degrades corner detection.
- Cover the full field of view across all collected frames. Move the board to
  corners, edges, and the center. Tilt it at ±30° in both axes.
- Minimum recommended captures: 20 frame pairs with good board coverage.
- The wizard shows a coverage heatmap to guide you.

## Custom board sizes

If your sensor field of view requires a different board size, you can generate
a custom board using OpenCV:

```python
import cv2
import cv2.aruco as aruco

dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
board = aruco.CharucoBoard((6, 8), 0.035, 0.025, dictionary)
image = board.generateImage((2480, 3508))  # A4 at 300 DPI
cv2.imwrite("charuco_custom.png", image)
```
