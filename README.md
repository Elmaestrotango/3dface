# Panopticon

Multi-camera synchronized acquisition GUI for 3D pose estimation. Records from 6-12 Basler cameras at 100 fps with hardware-triggered synchronization, raw-to-disk capture, and post-hoc NVENC encoding.

## Quick Start

```bash
git clone https://github.com/Elmaestrotango/3dpose.git
cd 3dpose
uv sync
uv run python gui.py
```

Or double-click `Panopticon.lnk` on the Desktop (created during setup).

## Prerequisites

1. **uv** — Python package manager: https://docs.astral.sh/uv/getting-started/installation/
2. **Basler Pylon SDK** — install from https://www.baslerweb.com/en/downloads/software-downloads/ (needed for GigE camera drivers and the pylon filter driver)
3. **NVIDIA GPU** with driver 550+ (for NVENC H.264 encoding)
4. **Teensy/Arduino** with `campy/campy/trigger/trigger.ino` flashed via Arduino IDE

## Installation

```bash
git clone https://github.com/Elmaestrotango/3dpose.git
cd 3dpose
uv sync
```

This creates a `.venv` with all Python dependencies (pypylon, PyQt5, numpy, etc.). No conda required.

### First-time setup on a new machine

1. **Generate camera settings**: connect cameras, then run:
   ```bash
   uv run python _gen_pfs.py
   ```
   This saves a `.pfs` file matched to your camera model.

2. **Configure camera IPs** (GigE cameras only):
   ```powershell
   # Run as Administrator
   & "C:\Program Files\Basler\pylon\Runtime\x64\PylonGigEConfigurator.exe" auto-all
   ```

3. **Add firewall rule** (GigE cameras only):
   ```powershell
   # Run as Administrator
   New-NetFirewallRule -DisplayName PanopticonGigE -Direction Inbound -Action Allow -Protocol UDP -Program <path-to-.venv\Scripts\python.exe>
   ```

4. **Create a Desktop shortcut** (optional):
   - Right-click Desktop > New > Shortcut
   - Target: `<repo-path>\_launch.bat`
   - Change icon to `<repo-path>\panopticon.ico`

### Rig Profiles

Each camera rig has a YAML profile in `profiles/`:

```yaml
# profiles/3dpose.yaml
name: 3dpose
frame_width: 1920
frame_height: 1200
frame_rate: 100
quality: 21
pfs_path: "C:\\path\\to\\mono8_1920x1200.pfs"
output_dir: "C:\\path\\to\\data"
serial_port: COM3
trigger_pins: [2, 4, 6, 8, 10, 12]
```

The GUI has a profile dropdown to switch between rigs. To add a new rig, copy an existing profile and update the values.

---

## Usage

### Recording

1. Launch the GUI (`uv run python gui.py` or Desktop shortcut)
2. Select the rig profile from the dropdown
3. Fill in session metadata (date, mouse IDs, assay, etc.)
4. Flip **Calibrate** toggle to record calibration videos (ChArUco board)
5. Flip it off — videos encode in the background
6. Click **Solve** to run sleap-anipose calibration
7. Flip **Record** toggle to record behavioral data
8. Flip it off — videos encode, `calibration.toml` copied to recording dir

### Keyboard/Mouse

- **Double-click** a camera view to zoom (fills entire grid area)
- **Double-click** again to return to grid view
- **Brightness/Contrast** sliders adjust display only (not recorded data)

### Output Structure

```
data/
  YYYYMMDD/
    mouse1_mouse2/
      calibration/
        cam1/ ... cam6/     (MP4 videos + frametimes.npy)
        calibration.toml    (camera parameters)
        board.toml          (ChArUco board definition)
      recording/
        cam1/ ... cam6/     (MP4 videos + frametimes.npy)
        calibration.toml    (copied from calibration/)
      session_metadata.json
```

---

## Architecture

### Raw Capture + Post-Hoc Encoding

The GUI bypasses campy and uses pypylon directly. During recording, raw mono8 frames are written to disk at 100 fps. After recording, ffmpeg encodes them to H.264 via NVENC.

**Why not real-time encoding?** At 1920x1200, ffmpeg's CPU-side gray-to-yuv420p pixel conversion bottlenecks at ~80 fps for 6 cameras. At 800x800, real-time encoding works fine (145+ fps proven). Raw-to-disk achieves 100 fps at any resolution.

**Storage**: ~138 GB raw per camera per 10 minutes. 6 cameras = ~830 GB temp. Encodes to ~20-30 GB. Requires a fast NVMe SSD (1.4+ GB/s write speed).

### Camera Modes

- **Idle**: `TriggerMode=Off`, free-run at 30 fps for live preview
- **Acquiring**: `TriggerMode=On`, `TriggerSource=Line1`, hardware triggered at 100 fps
- Mode switching happens in-place via `StopGrabbing() -> reconfigure -> StartGrabbing()`

### Frame Synchronization

All cameras receive the same TTL trigger pulse from the Teensy (~30 ns cross-pin skew). After stopping triggers, all cameras' data is truncated to the minimum frame count to ensure identical counts for triangulation.

### Calibration

Uses [sleap-anipose](https://github.com/talmolab/sleap-anipose) via `uv run` (separate dependency environment). Calibration videos are subsampled to 200 frames before processing to keep solve time under 2 minutes.

---

## Troubleshooting

### Cameras not found

| Symptom | Cause | Fix |
|---|---|---|
| "No cameras found" on launch | Wrong profile selected | Switch profile dropdown to one with a valid `.pfs` path |
| "No cameras found" on launch | GigE cameras not on same subnet | Run `PylonGigEConfigurator auto-ip` as Administrator |
| "No cameras found" on launch | Firewall blocking UDP discovery | Add firewall rule for `.venv\Scripts\python.exe` (see setup) |
| "No cameras found" on launch | Cameras held by another app | Close PylonViewer, kill stale Python processes, restart GUI |
| Cameras found but 0 fps | Teensy not flashed or not connected | Flash `trigger.ino`, check COM port in profile |

### Serial port errors

| Symptom | Cause | Fix |
|---|---|---|
| "Could not open COM3" | Port held by previous run | GUI auto-retries 10 times. If still stuck, restart the GUI. |
| "Could not open COM3" | Arduino Serial Monitor open | Close Serial Monitor before using the GUI |
| "Could not open COM3" | Wrong COM port | Update `serial_port` in the profile YAML |

### Recording issues

| Symptom | Cause | Fix |
|---|---|---|
| Frame counts differ between cameras | Normal (±5 frames from GigE timing) | Data is auto-truncated to min count. No action needed. |
| Very low fps during recording | `AcquisitionFrameRate` too low in `.pfs` | Regenerate `.pfs` with `AcquisitionFrameRate=165` |
| Videos won't open after recording | Encoding failed | Check for ffmpeg errors in the status bar. Verify NVIDIA drivers. |
| Encoding very slow | CPU doing pixel conversion | Expected for 1920x1200 (~2-3 min per 10-min recording). Normal. |

### Calibration issues

| Symptom | Cause | Fix |
|---|---|---|
| "0 boards detected" | Wrong board parameters | Update `BOARD_X`, `BOARD_Y`, `SQUARE_LENGTH`, `MARKER_LENGTH` in `1_calibrate.py` |
| "0 boards detected" | No ChArUco board in video | Record actual calibration footage with the board visible to all cameras |
| Calibration takes forever | Processing all frames | Default subsamples to 200 frames. Use `--max-frames` to adjust. |
| numpy ABI error | Version conflict | `1_calibrate.py` pins `numpy<2`. Run `uv cache clean` and retry. |
| sleap-anipose directory error | Non-camera dirs in calibration/ | Auto-excluded. Delete stale `reprojections/` if issues persist. |

---

## Teensy Wiring

| Teensy Pin | Destination |
|---|---|
| USB | Computer (COM3, 115200 baud) |
| 2, 4, 6, 8, 10, 12 | Camera Line1 trigger inputs (one per camera) |
| 13 | Stim Arduino interrupt pin (optional, for neural sync) |
| GND | Camera GND (shared) |

Serial protocol: `6,2,4,6,8,10,12,100` (start at 100 fps), `6,2,4,6,8,10,12,-1` (stop).

---

## File Structure

```
gui.py                  Entry point (splash screen + main window)
_launch.bat             Batch launcher (uv run pythonw)
panopticon.ico          Application icon
pyproject.toml          Python dependencies (uv sync)
1_calibrate.py          Calibration script (uv run, sleap-anipose)
profiles/               Rig-specific YAML configs
  3dpose.yaml           6x Basler a2A1920-165g5m GigE
  3dface.yaml           6x Basler acA1300-200um USB3
gui_app/
  main_window.py        Layout, theme, state machine, acquisition flow
  camera_manager.py     Camera lifecycle, mode switching, grab threads
  grab_thread.py        Per-camera: grab + raw write + display thumbnail
  encode_worker.py      Background NVENC encoding with progress
  calibration_worker.py Background sleap-anipose calibration
  serial_controller.py  Teensy serial trigger control
  session_config.py     Profiles, session paths, metadata
  widgets/
    camera_grid.py      Dynamic NxM grid, aspect ratio, double-click zoom
    sidebar.py          Metadata fields, profile selector, toggles, sliders
    toggle_switch.py    Animated toggle switch widget
campy/                  Forked campy (submodule, for trigger.ino firmware)
```

---

## Cross-references

- **Campy fork**: https://github.com/Elmaestrotango/campy
- **sleap-anipose**: https://github.com/talmolab/sleap-anipose
- **stac-mjx**: https://github.com/talmolab/stac-mjx
- **Basler Pylon SDK**: https://www.baslerweb.com/en/downloads/software-downloads/
