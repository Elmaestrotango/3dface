# 3D Pose — Freely-Moving Social Behavior

This document describes the 3D full-body pose arm of the Despotism project. Mice are recorded during social interaction in open arenas using multi-view synchronized cameras, yielding 3D skeletal pose trajectories via SLEAP + stac-mjx. The goal is to capture detailed body kinematics during naturalistic and structured social behaviors — open field interaction, tube test, and any future assay — to complement the homecage-monitoring and head-fixed facial-expression arms.

For the project-level overview, see `~/.claude/despotism.md`. For the homecage-monitoring arm, see `~/notebooks-kay/despotism/id_switch/README.md`. For the head-fixed facial-expression arm, see `~/notebooks-kay/despotism/3dface/README.md`.

---

## Behavioral Contexts

| Assay | Description |
|-------|-------------|
| **Open field** | Two mice freely interacting in an open arena; captures approach, investigation, aggression, mounting, allogrooming, etc. |
| **Tube test** | Standardized dominance assay; two mice enter opposite ends of a tube, dominant mouse pushes subordinate out |
| **Other** | Pipeline is designed to generalize to any social or solitary behavior captured with this camera rig |

---

## Recording Setup

- **Cameras**: 6x Basler mono8 (initial), expandable to 12
- **Resolution**: 1920x1200
- **Frame rate**: 100 fps
- **Synchronization**: Hardware trigger via Arduino/Teensy — Campy sends serial start command, microcontroller generates synchronized TTL pulses to all cameras on rising edge
- **Acquisition software**: [Campy](https://github.com/ksseverson57/campy) — multi-camera GPU-accelerated video acquisition
- **Encoding**: H.264 via Nvidia GPU, same as 3dface arm
- **Arena**: 3 ft x 3 ft platform with transparent walls and floor (enables below-platform camera views)
- **Identity**: Mice have headplates; identifying markers attached to headplates. Multi-view coverage further reduces ID swaps

### Campy trigger protocol

Campy communicates with the Arduino/Teensy over serial (115200 baud). A single comma-separated ASCII string configures and starts triggering:

- **Start**: `<num_pins>,<pin0>,<pin1>,...,<pinN>,<frame_rate>` (e.g. `6,2,4,6,8,10,12,100`)
- **Stop**: same format with frame rate set to `-1`

The microcontroller generates a 50% duty cycle square wave on all configured pins simultaneously (~30 ns cross-pin synchronicity). Each rising edge triggers one frame capture on all cameras via their hardware trigger input line.

In the acquisition notebook, `startArduino` is set to `False`. Campy launches and initializes all cameras first, then the notebook sends the serial start command when the user presses Enter — ensuring all cameras are grabbing from frame 1. Pressing Enter again sends the stop command.

### Teensy wiring

| Teensy Pin | Destination |
|---|---|
| **USB** | Computer (COM3) |
| **2** | cam1 Line1 (trigger input) |
| **4** | cam2 Line1 |
| **6** | cam3 Line1 |
| **8** | cam4 Line1 |
| **10** | cam5 Line1 |
| **12** | cam6 Line1 |
| **13** | Stim Arduino interrupt (optional, for neural sync) |
| **GND** | Camera GND (shared) |

Flash `campy/campy/trigger/trigger.ino` to the Teensy via the Arduino IDE.

### Campy config

Production config: `data/configs/3dpose_6cams.yaml`. Camera settings: `data/configs/mono8_1920x1200.pfs`.

Key settings:
- **Pixel format**: Mono8 (gray in, gray out) — IR illumination, no color needed
- **Compression**: H.264 via NVENC (`h264_nvenc`), quality 21, on GPU 0
- **Trigger**: `startArduino: False` — cameras initialize first, then the notebook sends a serial start command to the Teensy when the user presses Enter. This ensures all cameras are ready before the first frame.
- **Serial**: COM3 at 115200 baud, digital pins 2,4,6,8,10,12

When expanding to 12 cameras, update `numCams`, `cameraSelection`, `cameraNames`, `gpuID`, and add digital pins as needed (Teensy has many digital output pins available).

---

## Calibration

Multi-view calibration is required before each session (or whenever the camera geometry changes). A ChArUco board is slowly moved through the shared field of view to compute per-camera intrinsics and extrinsics.

### Recording calibration videos

Use the calibration section of `0a_acquire.ipynb` (optional — skip if cameras haven't moved). This records ChArUco board videos into `<session>/calibration/cam1/`, `cam2/`, etc.

### Running calibration

Calibration is processed post-hoc using `1_calibrate.py`, which uses [sleap-anipose](https://github.com/talmolab/sleap-anipose). Dependencies are managed inline via `uv` — no conda env needed:

```bash
uv run 1_calibrate.py <session_dir>
# e.g. uv run 1_calibrate.py data/20260511/slmc001_slmc002
```

**Board**: ChArUco 5x5, ArUco 4x4_1000 dictionary, square_length=24.0 mm, marker_length=18.75 mm.

**Outputs**: `calibration.toml` (camera parameters), `calibration_metadata.h5`, reprojection error histogram, reprojection images — all written to the `calibration/` subdirectory.

---

## Camera Geometry (6-camera configuration)

```
            Top view (looking down)
        ┌─────────────────────────┐
        │                         │
        │     ③        ②          │
        │       ╲    ╱            │
        │        ╲  ╱             │
        │    ④────①────          │
        │        (↓)              │
        │     3ft × 3ft arena     │
        │   transparent walls     │
        │   + transparent floor   │
        │                         │
        └─────────────────────────┘

            Side view (cross-section)
                ②  ①  ③
               ╱   ↓   ╲         ← above: 45° angled (②③④)
              ╱    ↓    ╲                  + 1 straight down (①)
    ─────────┼──────────┼─────── ← transparent platform
              ╲         ╱
               ⑤       ⑥         ← below: 45° angled upward
```

**Above the arena (4 cameras):**
| Camera | Position | Angle |
|--------|----------|-------|
| **①** | Directly above center | Straight down (0°) — matches existing top-down behavioral data in the lab |
| **②** | Above, offset | 45° down, positioned at 0° azimuth |
| **③** | Above, offset | 45° down, positioned at 120° azimuth |
| **④** | Above, offset | 45° down, positioned at 240° azimuth |

**Below the arena (2 cameras):**
| Camera | Position | Angle |
|--------|----------|-------|
| **⑤** | Below, offset | 45° up, positioned at 0° azimuth |
| **⑥** | Below, offset | 45° up, positioned at 180° azimuth |

This geometry guarantees at least 3 cameras viewing each mouse at all times, even during close social interaction. The transparent floor enables the below-platform views, which capture paw placement and ventral body features that top-down views miss.

The top-down camera (①) provides continuity with existing lab datasets that use overhead-only recording for behavioral classification.

### Illumination

5 IR panels, offset similarly to the angled cameras (rotated slightly to avoid direct reflection into lenses):
- 3 panels above the arena
- 2 panels below the arena (illuminating through transparent floor)

IR illumination is invisible to the mice and provides even lighting across all camera views without interfering with behavioral protocols.

---

## Pipeline

```
Multi-view video (6-12 cameras, 1920x1200, 100 fps)
    │
    ▼
SLEAP — 2D pose estimation per camera view
    │
    ▼
stac-mjx — 3D skeletal pose reconstruction
    │       (physics-informed MuJoCo model,
    │        fits skeleton to multi-view 2D detections)
    │
    ▼
3D pose trajectories (per-frame 3D joint positions + body model state)
    │
    ▼
Behavioral analysis
```

### SLEAP (2D pose estimation)

Per-camera 2D keypoint detection. Train on labeled frames exported from a multi-view labeling tool (e.g., LUC3D or per-view SLEAP GUI). One model per camera view or a shared model across views, depending on view similarity.

**Skeleton**: Custom high-granularity skeleton (not the standard SLEAP mouse body skeleton). The multi-view coverage supports tracking finer landmarks that would be unreliable from a single view:
- Standard body landmarks (nose, ears, head, spine, tail base/mid/tip)
- Paws (4x)
- Elbows/wrists, knees/ankles
- Additional landmarks TBD based on labeling feasibility and stac-mjx model requirements

### stac-mjx (3D skeletal reconstruction)

[stac-mjx](https://github.com/talmolab/stac-mjx) fits a physics-based MuJoCo skeleton model to multi-view 2D pose detections. Unlike pure triangulation (used in the 3dface arm), stac-mjx enforces skeletal constraints (bone lengths, joint limits, collision avoidance), producing physically plausible 3D body configurations even under occlusion. This is critical for freely-moving social behavior where animals frequently occlude each other.

### Behavioral analysis

Downstream analyses TBD. Potential directions:
- Social interaction classification from 3D pose features
- Integration with VQ tokenization / motif pipeline from the HCM arm
- Cross-assay comparison (open field vs. tube test kinematics)

---

## Data Layout

```
C:\Users\isaac\Desktop\3dpose\data\
└── YYYYMMDD/
    └── <mouse1>_<mouse2>/
        ├── calibration/
        │   ├── cam1/
        │   │   └── YYYYMMDD-<session>-cam1-calibration.mp4
        │   ├── cam2/ ... cam6/
        │   ├── board.toml              (generated by 1_calibrate.py)
        │   ├── calibration.toml        (generated by 1_calibrate.py)
        │   └── calibration_metadata.h5
        ├── recording/
        │   ├── cam1/
        │   │   └── YYYYMMDD-<session>-cam1-recording.mp4
        │   ├── cam2/ ... cam6/
        │   └── _campy_config_recording.yaml
        └── session_metadata.json
```

---

## Differences from 3dface Arm

| | 3dface | 3dpose |
|---|--------|--------|
| **Subject state** | Head-fixed | Freely moving |
| **Body part** | Face only | Full body |
| **Social context** | Dyadic task (subject + target on platform) | Dyadic free interaction (open field, tube test) |
| **Resolution** | 800x800 | 1920x1200 |
| **3D method** | Triangulation (rigid head, no occlusion) | stac-mjx (skeletal model, handles occlusion) |
| **Cameras** | 6 (all above, face-level) | 6 (4 above + 2 below; expanding to 12) |
| **Frame rate** | 100 fps | 100 fps |
| **Skeleton** | Facial landmarks only | Custom high-granularity full-body (paws, joints, etc.) |
| **Identity** | Single animal (head-fixed) | Headplate markers + multi-view disambiguation |

---

## Neural Recording / Stimulation

Mice undergo optogenetic stimulation (and potentially miniscope recording) during free social interaction. A standalone pulse generator drives stim; the recording modality is TBD.

### Trial structure

- Fixed schedule with fixed intervals between stimulation events
- Jitter applied to inter-stim intervals
- Trial structure (stim times, intervals, jitter params) defined in the acquisition notebook and uploaded to a dedicated stim Arduino (separate from the camera trigger Teensy)

### Synchronization (two-Arduino architecture)

```
Camera Teensy                     Stim Arduino
─────────────                     ────────────
Digital pins 2,4,6,8,10,12 ──→ Basler cameras (TTL trigger)
Digital pin 13 (copy) ─────────→ Interrupt pin (frame counter)
                                  Digital pin N ──→ Pulse generator (stim TTL)
                                  Digital pin M ──→ IR LED (visual sync)
                                  Logs: frame_number, event_type → serial
```

**Frame-count sync**: the camera Teensy sends a copy of the frame trigger TTL to the stim Arduino, which counts rising edges on an interrupt pin. All stim events are logged as `(frame_number, event_type)`, giving exact frame-level alignment with zero clock drift.

**IR LED backup**: the stim Arduino drives an IR LED visible to one camera (LED ON = stim active). Provides visual ground truth for verifying sync.

Post-session outputs:
- `frametimes.npy` from Campy (per-camera frame timestamps)
- `session_events.csv` from stim Arduino (`frame_number, event_type, event_code`)
- IR LED visible in video (verification)

---

## Status

- **Rig**: Not yet built. Camera count, placement, and arena geometry TBD.
- **Campy config**: Done. `data/configs/3dpose_6cams.yaml` (6-camera, mono8, 1920x1200, 100 fps, NVENC H.264) and `data/configs/mono8_1920x1200.pfs` (Basler camera settings with hardware trigger on Line1).
- **Acquisition notebook**: Done. `0a_acquire.ipynb` — keyboard-triggered start/stop via Teensy serial. Runs in the `3dpose` conda environment.
- **Calibration script**: Done. `1_calibrate.py` — runs via `uv run`, self-contained dependencies (sleap-anipose). No conda env needed.
- **SLEAP model**: Not yet trained. Skeleton definition (keypoint set) TBD.
- **stac-mjx**: Not yet configured. Mouse body model and fitting parameters TBD.
- **Pipeline scripts**: Will follow the `id_switch/`-style numeric-prefix convention (`{N}{letter}_*.py`, companion notebooks `{N}{letter}n_*.ipynb`).

---

## Environment

### Acquisition (`3dpose` conda env)

Used by `0a_acquire.ipynb`. Python 3.11, key packages:

- campy 2.0.1 (editable install from `campy/`)
- pypylon 26.4.1 (Basler Pylon SDK)
- imageio-ffmpeg 0.6.0 (bundles ffmpeg 7.1 with h264_nvenc)
- PyQt5, numpy, pyyaml, pyserial, jupyter

```bash
conda activate 3dpose
jupyter notebook 0a_acquire.ipynb
```

### Calibration (uv-managed, no env needed)

Used by `1_calibrate.py`. Dependencies declared inline (PEP 723):

- sleap-anipose >=0.1.8 (includes aniposelib, opencv-contrib-python, numba)

```bash
uv run 1_calibrate.py <session_dir>
```

---

## Cross-references

- **Project overview (all arms)**: `~/.claude/despotism.md`
- **Homecage-monitoring arm**: `~/notebooks-kay/despotism/id_switch/README.md`
- **Head-fixed facial-expression arm**: `~/notebooks-kay/despotism/3dface/README.md`
- **Campy (acquisition software)**: https://github.com/ksseverson57/campy
- **sleap-anipose (calibration)**: https://github.com/talmolab/sleap-anipose
- **stac-mjx (3D reconstruction)**: https://github.com/talmolab/stac-mjx
- **F31 grant proposal**: `~/minor_prop/`
