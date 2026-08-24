```markdown
# MotionTask – Motion Detection + Macro Automation

**MotionTask** is a single‑file Python application that combines IP camera motion detection with keyboard/mouse macro automation. It provides a graphical interface (Tkinter) to:

- Connect to any IP camera or local webcam.
- Detect motion with adjustable sensitivity and cooldown.
- Execute a custom key‑binding or play a recorded macro when motion is triggered.
- Record and replay keyboard and mouse macros (using `pynput`).
- Save/load configurations and macro files in JSON format.

![Screenshot](screenshot.png) *(add a screenshot if you like)*

---

## Features

- **Live preview** with motion highlighting.
- **Motion detection** using background subtraction and contour analysis.
- **Two trigger actions**:
  - Simulate a custom key combination (e.g., `Ctrl+Shift+M`).
  - Play a recorded macro (keyboard + mouse).
- **Macro recorder** – capture keyboard presses, mouse clicks, movement, and scrolling.
- **Import/Export** macros in the native format or the uploaded `example.json` format.
- **Persistent configuration** – auto‑saves settings on exit and reloads them on start.
- **Real‑time FPS** and trigger counter.

---

## Requirements

- Python 3.6 or higher
- **Tkinter** (usually bundled with Python)
- **OpenCV** (`opencv-python`)
- **Pillow** (`PIL`)
- **pynput** (for macro recording/playback)

Install all dependencies with:

```bash
pip install -r requirements.txt
```

---

## Installation & Usage

1. **Clone the repository**  
   ```bash
   git clone https://github.com/yourusername/motiontask.git
   cd motiontask
   ```

2. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**  
   ```bash
   python deepseek_motiontask.py
   ```

4. **Connect to a camera**  
   - Enter `0` (or leave default) for the built‑in webcam.  
   - Enter a full URL (e.g., `http://192.168.1.100:8080/video`) for an IP camera.  
   - Click **Connect**.

5. **Adjust motion settings**  
   - **Sensitivity** (minimum contour area in pixels²).  
   - **Cooldown** (seconds to wait after a trigger before allowing another).

6. **Choose an action**  
   - *Trigger Custom Keybind* – enter a combination like `ctrl+shift+m`.  
   - *Play Recorded Macro* – record or load a macro, then motion will replay it.

7. **Record a macro** (optional)  
   - Click **▶ Record**, perform your actions, then click **⏹ Stop Recording**.  
   - You can save/load macros via the buttons below.

8. **Save/Load configuration**  
   - All settings are automatically saved to `motiontask_config.json` on exit.  
   - You can manually save/load configs from the UI.

---

## Macro File Formats

MotionTask supports **two JSON formats**:

### Native Format (full keyboard + mouse events)

```json
{
  "version": 2,
  "created": "2026-08-24T12:00:00",
  "event_count": 42,
  "events": [
    [0.123, "kp", "a"],
    [0.456, "mm", [100, 200]],
    [0.789, "md", [100, 200, "Button.left"]]
  ],
  "format": "native"
}
```

- `"kp"` / `"kr"` – key press / release (data is a character or `Key.*` string).  
- `"mm"` – mouse move (data is `[x, y]`).  
- `"md"` / `"mu"` – mouse button press / release (data is `[x, y, button_name]`).  
- `"ms"` – mouse scroll (data is `[x, y, dx, dy]`).

### Uploaded (Example) Format (keyboard‑only)

This matches the `example.json` provided in the original task:

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

The application **automatically detects** which format you load.

---

## Configuration File

Settings are saved as JSON (e.g., `motiontask_config.json`):

```json
{
  "version": 1,
  "camera_url": "0",
  "sensitivity": 500,
  "cooldown": 2.0,
  "action": "keybind",
  "keybind": "ctrl+shift+m",
  "preview_visible": true,
  "macro_events": [...]
}
```

---

## Troubleshooting

- **`pynput` not available** – Macros will be disabled. Install it with `pip install pynput`.
- **Camera not opening** – Verify the URL and that the camera is accessible.
- **Preview lag** – Lower the resolution (hardcoded to 320x240) or increase the FPS limit.
- **Macro playback fails** – Ensure the macro was recorded with the same screen resolution (absolute mouse coordinates).

---

## Contributing

Feel free to open issues or submit pull requests. Please follow PEP 8 and include docstrings.

---

## License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.
```

---

## 2. `LICENSE` (MIT)

```text
MIT License

Copyright (c) 2026 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 3. `.gitignore`

```gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Virtual environments
venv/
env/
ENV/
.venv

# Local configuration (auto‑saved by the app)
motiontask_config.json

# Logs and temporary files
*.log
*.tmp

# Mac OS metadata
.DS_Store

# IDE settings
.vscode/
.idea/
*.swp
*.swo

# Pytest / coverage
.pytest_cache/
.coverage
htmlcov/
```

---

## 4. `requirements.txt`

```txt
opencv-python>=4.5.0
pillow>=9.0.0
pynput>=1.7.0
```

> **Note:** Tkinter is part of the Python standard library, so it's not listed.

---

## 5. (Optional) GitHub Actions workflow – `.github/workflows/ci.yml`

This runs a basic syntax check on every push, helping to keep the code clean.

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install flake8
      - name: Lint with flake8
        run: |
          # stop the build if there are Python syntax errors or undefined names
          flake8 deepseek_motiontask.py --count --select=E9,F63,F7,F82 --show-source --statistics
          # exit-zero treats all errors as warnings
          flake8 deepseek_motiontask.py --count --exit-zero --max-complexity=10 --statistics
```

---

## How to Add These Files to Your Repository

1. **Create the files** in your local project folder with the content above.
2. **Stage and commit** them:

   ```bash
   git add README.md LICENSE .gitignore requirements.txt .github/workflows/ci.yml
   git commit -m "Add documentation, license, gitignore, and CI workflow"
   git push
   ```

3. **Optionally**, upload a screenshot (rename `screenshot.png` and place it in the repo root) and update the README to display it.
