from setuptools import setup, find_packages
import os
from glob import glob

package_name = "polycalib_core"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
    ],
    install_requires=[
        "setuptools",
        "opencv-contrib-python>=4.8",
        "numpy>=1.24",
        "pyyaml>=6.0",
    ],
    zip_safe=True,
    maintainer="Sarvesh Angadi",
    maintainer_email="sarvesh.angadi1997@gmail.com",
    description=(
        "FusionCalib core calibration node — ROS2-native multimodal sensor calibration."
    ),
    license="AGPL-3.0-or-later",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "calibration_node = polycalib_core.nodes.calibration_node:main",
        ],
    },
)
