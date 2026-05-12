# /// script
# requires-python = ">=3.10,<3.12"
# dependencies = [
#     "sleap-anipose>=0.1.8",
# ]
# ///
"""Multi-view camera calibration using sleap-anipose.

Run with: uv run 1_calibrate.py <session_dir>

The session directory should contain a calibration/ subfolder with per-camera
video subdirectories (cam1/, cam2/, ...) produced by 0a_acquire.ipynb.

Outputs calibration.toml into the calibration directory.
"""
import argparse
from pathlib import Path

import sleap_anipose as slap


# -- Board parameters (ChArUco 5x5, ArUco 4x4_1000) -----------------------
BOARD_X = 5
BOARD_Y = 5
SQUARE_LENGTH = 24.0  # mm
MARKER_LENGTH = 18.75  # mm
MARKER_BITS = 4
DICT_SIZE = 1000


def main():
    parser = argparse.ArgumentParser(
        description="Run multi-view calibration on a session's calibration videos.",
    )
    parser.add_argument(
        "session_dir",
        type=Path,
        help="Path to session directory (contains calibration/ with cam1/, cam2/, ...)",
    )
    parser.add_argument(
        "--excluded-views",
        nargs="*",
        default=[],
        help="Camera names to exclude from calibration (e.g. cam5 cam6)",
    )
    args = parser.parse_args()

    calib_dir = args.session_dir / "calibration"
    if not calib_dir.exists():
        raise FileNotFoundError(f"Calibration directory not found: {calib_dir}")

    # Generate board config
    board_toml = calib_dir / "board.toml"
    board_img = calib_dir / "board.jpg"
    slap.draw_board(
        board_name=str(board_img),
        board_x=BOARD_X,
        board_y=BOARD_Y,
        square_length=SQUARE_LENGTH,
        marker_length=MARKER_LENGTH,
        marker_bits=MARKER_BITS,
        dict_size=DICT_SIZE,
        img_width=1440,
        img_height=1440,
        save=str(board_toml),
    )
    print(f"Board config: {board_toml}")

    # Run calibration
    calib_fname = calib_dir / "calibration.toml"
    metadata_fname = calib_dir / "calibration_metadata.h5"
    histogram_path = calib_dir / "reprojection_error_histogram.png"
    reproj_path = calib_dir / "reprojections"

    excluded = tuple(args.excluded_views)

    cgroup, metadata = slap.calibrate(
        session=str(calib_dir),
        board=str(board_toml),
        excluded_views=excluded,
        calib_fname=str(calib_fname),
        metadata_fname=str(metadata_fname),
        histogram_path=str(histogram_path),
        reproj_path=str(reproj_path),
    )

    print(f"\nCalibration complete.")
    print(f"  calibration.toml:  {calib_fname}")
    print(f"  metadata:          {metadata_fname}")
    print(f"  histogram:         {histogram_path}")
    print(f"  reprojections:     {reproj_path}")


if __name__ == "__main__":
    main()
