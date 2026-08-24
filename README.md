
# MotionTask

**Automate Keyboard & Mouse Actions via Real-Time Camera Motion Detection**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8.svg?style=flat-square&logo=opencv&logoColor=white)](https://opencv.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)



MotionTask is a single-file Python application that connects webcams or IP camera streams to system-level macro automation. When computer vision detects movement, MotionTask instantly executes hotkeys or complex input sequences.


```

┌─────────────────┐     Contour Filter     ┌──────────────────┐     Input Engine     ┌──────────────────┐
│ Camera Stream   │ ─────────────────────> │ Motion Detection │ ───────────────────> │ Hotkey / Macro   │
│ (Webcam / RTSP) │                        │ (OpenCV)         │                      │ Execution        │
└─────────────────┘                        └──────────────────┘                      └──────────────────┘

```


**Core Capabilities**

* **Live Feed Processing:** Real-time preview with visual contour highlighting and FPS counters.
* **Tunable Vision Pipeline:** Adjustable sensitivity thresholds and trigger cooldowns.
* **Flexible Actions:** Trigger single hotkey combinations or full multi-input macros.
* **Integrated Recorder:** Capture mouse moves, clicks, scrolling, and keystrokes using `pynput`.
* **Dual JSON Engine:** Auto-detects native multi-input schemas and legacy keyboard-only formats.
* **Auto-Persistence:** Automatically saves and restores UI configurations.

---

**System Requirements**

| Component | Minimum Version | Notes |
| :--- | :--- | :--- |
| **Python** | `3.8+` | Core environment |
| **OpenCV** | `4.5.0+` | Video stream & frame differential processing |
| **Pillow** | `9.0.0+` | Frame conversions for UI rendering |
| **pynput** | `1.7.0+` | Global input recording and emulation |
| **Tkinter** | Standard Library | Graphical interface framework |

---

**Quick Start**

1. **Clone & Install**
   ```bash
   git clone https://github.com/Gaurab-Dhakal/motiontask.git
   cd motiontask
   pip install -r requirements.txt
   ```

2. **Launch Application**
```bash
python motiontask.py

```


3. **Connect Camera**
* Enter `0` for the default local webcam.
* Enter a stream URL (e.g., `rtsp://192.168.1.100:554/stream` or `http://192.168.1.100:8080/video`) for IP cameras.



---

**Macro Data Schemas**

MotionTask auto-detects and processes two JSON schema structures:

```json
{
  "version": 2,
  "created": "2026-08-24T12:00:00",
  "event_count": 3,
  "events": [
    [0.123, "kp", "a"],
    [0.456, "mm", [100, 200]],
    [0.789, "md", [100, 200, "Button.left"]]
  ],
  "format": "native"
}

```

* **Codes:** `kp`/`kr` (Key Press/Release), `mm` (Mouse Move), `md`/`mu` (Mouse Down/Up), `ms` (Mouse Scroll).

```json
{
  "hotkeys": {
    "start": ["ctrl", "shift", "r"],
    "stop": ["ctrl", "shift", "s"],
    "play": ["f9"]
  },
  "events": [
    {"timestamp": 0.0, "key_type": "name", "key_value": "ctrl", "is_press": true},
    {"timestamp": 0.1, "key_type": "char", "key_value": "a", "is_press": false}
  ]
}

```

---

**Troubleshooting**

* **`ImportError: pynput`** $\rightarrow$ Install via `pip install pynput`.
* **Camera Connection Fails** $\rightarrow$ Check stream URL, network accessibility, or device index.
* **Mouse Offset on Playback** $\rightarrow$ Ensure macro was recorded at the current display resolution.
* **Linux Display Errors** $\rightarrow$ Install Tkinter system dependencies (`sudo apt install python3-tk`).

---

**License**

Distributed under the [MIT License](https://www.google.com/search?q=LICENSE).

```

```
