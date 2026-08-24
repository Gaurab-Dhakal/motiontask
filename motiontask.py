#!/usr/bin/env python3
"""
MotionTask - IP Camera Motion Detection + Macro Automation
Single-file application using tkinter, opencv-python, and pynput.
Supports custom macro/config file upload/download.
Compatible with uploaded example.json macro format.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import cv2
import threading
import time
import queue
import json
import os
from datetime import datetime
from PIL import Image, ImageTk

# pynput imports
try:
    from pynput import keyboard, mouse
    from pynput.keyboard import Key, Controller as KController
    from pynput.mouse import Button, Controller as MController
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

# =============================================================================
# CONFIGURATION & GLOBALS
# =============================================================================
DEFAULT_URL = "0"
PREVIEW_W, PREVIEW_H = 320, 240
BLUR_KERNEL = (21, 21)
FPS_LIMIT = 15
CONFIG_FILENAME = "motiontask_config.json"

class MotionTaskApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MotionTask — Motion Detection + Macro Automation")
        self.root.geometry("950x760")
        self.root.minsize(850, 650)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # --- State ---
        self.running = False
        self.preview_visible = True
        self.capturing = False
        self.recording = False
        self.macro_events = []          # internal format: (timestamp, type, data)
        self.macro_start_time = None
        self.last_trigger_time = 0
        self.current_frame = None
        self.prev_frame = None
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=100, varThreshold=25, detectShadows=False
        )

        # --- Threading ---
        self.video_thread = None
        self.macro_thread = None
        self.lock = threading.Lock()
        self.frame_queue = queue.Queue(maxsize=2)
        self.log_queue = queue.Queue()

        # --- pynput controllers ---
        if PYNPUT_AVAILABLE:
            self.kb_ctrl = KController()
            self.mouse_ctrl = MController()
            self.kb_listener = None
            self.mouse_listener = None

        # --- Custom keybind ---
        self.custom_keybind = tk.StringVar(value="ctrl+shift+m")

        # --- Build UI ---
        self.build_ui()

        # --- Auto-load config ---
        self.load_config_silent()

        # --- Start log updater ---
        self.update_log()

    # =========================================================================
    # UI BUILDER
    # =========================================================================
    def build_ui(self):
        # Main frames
        self.left_frame = ttk.Frame(self.root, padding=5)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.right_frame = ttk.Frame(self.root, padding=5, width=340)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_frame.pack_propagate(False)

        # ---- Preview Area ----
        preview_frame = ttk.LabelFrame(self.left_frame, text="Live Preview", padding=5)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.preview_label = tk.Label(preview_frame, bg="black")
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        # ---- Log Area ----
        log_frame = ttk.LabelFrame(self.left_frame, text="Event Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 5))

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=8, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # ---- Controls (Right Panel) ----
        # Source
        src_frame = ttk.LabelFrame(self.right_frame, text="Camera Source", padding=5)
        src_frame.pack(fill=tk.X, pady=2)

        ttk.Label(src_frame, text="Enter full URL (e.g., http://192.168.1.1/video) or 0 for webcam").pack(anchor=tk.W)
        self.url_var = tk.StringVar(value=DEFAULT_URL)
        ttk.Entry(src_frame, textvariable=self.url_var, width=30).pack(fill=tk.X, pady=2)
        ttk.Button(src_frame, text="Connect", command=self.start_video).pack(fill=tk.X, pady=2)
        ttk.Button(src_frame, text="Disconnect", command=self.stop_video).pack(fill=tk.X, pady=2)

        # Preview toggle
        self.preview_btn = ttk.Button(src_frame, text="Hide Preview", command=self.toggle_preview)
        self.preview_btn.pack(fill=tk.X, pady=2)

        # Motion Settings
        motion_frame = ttk.LabelFrame(self.right_frame, text="Motion Settings", padding=5)
        motion_frame.pack(fill=tk.X, pady=5)

        ttk.Label(motion_frame, text="Sensitivity (min area):").pack(anchor=tk.W)

        # --- FIX: Create label BEFORE the scale ---
        self.sens_val_label = ttk.Label(motion_frame, text="500 px²")
        self.sens_val_label.pack(anchor=tk.E)

        self.sens_scale = ttk.Scale(
            motion_frame, from_=1, to=5000, orient=tk.HORIZONTAL,
            command=lambda v: self.sens_val_label.config(text=f"{int(float(v))} px²")
        )
        self.sens_scale.set(500)
        self.sens_scale.pack(fill=tk.X)

        ttk.Label(motion_frame, text="Cooldown (sec):").pack(anchor=tk.W, pady=(5, 0))

        # --- FIX: Create label BEFORE the scale ---
        self.cool_val_label = ttk.Label(motion_frame, text="2.0 s")
        self.cool_val_label.pack(anchor=tk.E)

        self.cooldown_scale = ttk.Scale(
            motion_frame, from_=0, to=30, orient=tk.HORIZONTAL,
            command=lambda v: self.cool_val_label.config(text=f"{float(v):.1f} s")
        )
        self.cooldown_scale.set(2.0)
        self.cooldown_scale.pack(fill=tk.X)

        self.motion_status = ttk.Label(motion_frame, text="Status: Idle", foreground="gray")
        self.motion_status.pack(anchor=tk.W, pady=(5, 0))

        # Action Selection
        action_frame = ttk.LabelFrame(self.right_frame, text="Trigger Action", padding=5)
        action_frame.pack(fill=tk.X, pady=5)

        self.action_var = tk.StringVar(value="keybind")
        ttk.Radiobutton(action_frame, text="Trigger Custom Keybind", variable=self.action_var,
                        value="keybind").pack(anchor=tk.W)
        ttk.Radiobutton(action_frame, text="Play Recorded Macro", variable=self.action_var,
                        value="macro").pack(anchor=tk.W)

        # Custom Keybind
        kb_frame = ttk.Frame(action_frame)
        kb_frame.pack(fill=tk.X, pady=5)
        ttk.Label(kb_frame, text="Keybind:").pack(side=tk.LEFT)
        ttk.Entry(kb_frame, textvariable=self.custom_keybind, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(kb_frame, text="Test", command=self.test_keybind, width=6).pack(side=tk.LEFT)

        # Macro Controls
        macro_frame = ttk.LabelFrame(self.right_frame, text="Macro Recorder", padding=5)
        macro_frame.pack(fill=tk.X, pady=5)

        self.record_btn = ttk.Button(macro_frame, text="▶ Record", command=self.toggle_record)
        self.record_btn.pack(fill=tk.X, pady=2)

        self.play_btn = ttk.Button(macro_frame, text="⏵ Play Macro", command=self.play_macro)
        self.play_btn.pack(fill=tk.X, pady=2)

        self.clear_btn = ttk.Button(macro_frame, text="Clear Macro", command=self.clear_macro)
        self.clear_btn.pack(fill=tk.X, pady=2)

        # Macro file I/O
        macro_io = ttk.Frame(macro_frame)
        macro_io.pack(fill=tk.X, pady=2)
        ttk.Button(macro_io, text="Save Macro", command=self.save_macro).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        ttk.Button(macro_io, text="Load Macro", command=self.load_macro).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2,0))

        self.macro_info = ttk.Label(macro_frame, text="Events: 0")
        self.macro_info.pack(anchor=tk.W, pady=(3, 0))

        # Config I/O
        cfg_frame = ttk.LabelFrame(self.right_frame, text="Configuration", padding=5)
        cfg_frame.pack(fill=tk.X, pady=5)

        cfg_btns = ttk.Frame(cfg_frame)
        cfg_btns.pack(fill=tk.X)
        ttk.Button(cfg_btns, text="Save Config", command=self.save_config).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        ttk.Button(cfg_btns, text="Load Config", command=self.load_config).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2,0))

        # Stats
        stats_frame = ttk.LabelFrame(self.right_frame, text="Stats", padding=5)
        stats_frame.pack(fill=tk.X, pady=5)

        self.fps_label = ttk.Label(stats_frame, text="FPS: —")
        self.fps_label.pack(anchor=tk.W)
        self.trigger_count = 0
        self.trigger_label = ttk.Label(stats_frame, text="Triggers: 0")
        self.trigger_label.pack(anchor=tk.W)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        ttk.Separator(self.right_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        ttk.Label(self.right_frame, textvariable=self.status_var, foreground="blue",
                  wraplength=320).pack(fill=tk.X)

    # =========================================================================
    # LOGGING
    # =========================================================================
    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_queue.put(f"[{ts}] {msg}")

    def update_log(self):
        while not self.log_queue.empty():
            try:
                line = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, line + "\n")
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
            except queue.Empty:
                break
        self.root.after(100, self.update_log)

    # =========================================================================
    # VIDEO / MOTION DETECTION
    # =========================================================================
    def start_video(self):
        if self.capturing:
            self.log("Already connected. Stop first.")
            return
        self.capturing = True
        self.running = True
        self.video_thread = threading.Thread(target=self.video_loop, daemon=True)
        self.video_thread.start()
        self.log("Video thread started.")
        self.motion_status.config(text="Status: Running", foreground="green")
        self.status_var.set("Capturing...")

    def stop_video(self):
        self.running = False
        self.capturing = False
        self.prev_frame = None
        time.sleep(0.2)
        self.log("Video stopped.")
        self.motion_status.config(text="Status: Idle", foreground="gray")
        self.status_var.set("Stopped")
        self.preview_label.config(image="")

    def toggle_preview(self):
        self.preview_visible = not self.preview_visible
        self.preview_btn.config(text="Show Preview" if not self.preview_visible else "Hide Preview")
        if not self.preview_visible:
            self.preview_label.config(image="")
        self.log(f"Preview {'enabled' if self.preview_visible else 'hidden'}.")

    def video_loop(self):
        url = self.url_var.get().strip()
        if url == "0" or url.lower() == "default":
            cap = cv2.VideoCapture(0)
        else:
            cap = cv2.VideoCapture(url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            # Try to set MJPG format for better performance on IP cameras
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))

        if not cap.isOpened():
            self.log(f"ERROR: Cannot open camera source: {url}")
            self.capturing = False
            self.running = False
            return

        self.log(f"Camera opened: {url}")
        frame_time = 1.0 / FPS_LIMIT
        last_frame_time = 0
        fps_counter = 0
        fps_start = time.time()

        while self.running and self.capturing:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue

            now = time.time()
            if now - last_frame_time < frame_time:
                time.sleep(0.001)
                continue
            last_frame_time = now

            # Downscale, Grayscale, Blur
            small = cv2.resize(frame, (PREVIEW_W, PREVIEW_H))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, BLUR_KERNEL, 0)

            # Motion Detection
            motion_detected = False
            total_area = 0
            if self.prev_frame is not None:
                diff = cv2.absdiff(self.prev_frame, blurred)
                _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                min_area = int(self.sens_scale.get())
                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if area > min_area:
                        total_area += area
                        motion_detected = True
                        if self.preview_visible:
                            x, y, w, h = cv2.boundingRect(cnt)
                            cv2.rectangle(small, (x, y), (x + w, y + h), (0, 255, 0), 2)

                if motion_detected:
                    cv2.putText(small, "MOTION", (10, 25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            self.prev_frame = blurred.copy()

            # Trigger Action
            if motion_detected:
                cooldown = float(self.cooldown_scale.get())
                if now - self.last_trigger_time >= cooldown:
                    self.last_trigger_time = now
                    self.trigger_count += 1
                    self.root.after(0, lambda: self.trigger_label.config(
                        text=f"Triggers: {self.trigger_count}"
                    ))
                    self.log(f"Motion triggered! Area={total_area:.0f}px²")
                    threading.Thread(target=self.execute_action, daemon=True).start()

            # FPS
            fps_counter += 1
            if now - fps_start >= 1.0:
                fps = fps_counter
                fps_counter = 0
                fps_start = now
                self.root.after(0, lambda f=fps: self.fps_label.config(text=f"FPS: {f}"))

            # Preview
            if self.preview_visible:
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                im = Image.fromarray(rgb)
                imgtk = ImageTk.PhotoImage(image=im)
                self.root.after(0, lambda img=imgtk: self._set_preview(img))

        cap.release()
        self.log("Camera released.")

    def _set_preview(self, imgtk):
        self.preview_label.imgtk = imgtk
        self.preview_label.config(image=imgtk)

    # =========================================================================
    # ACTION EXECUTION
    # =========================================================================
    def execute_action(self):
        action = self.action_var.get()
        if action == "keybind":
            self.fire_keybind()
        elif action == "macro":
            self.play_macro()

    def fire_keybind(self):
        if not PYNPUT_AVAILABLE:
            self.log("pynput not installed. Cannot fire keybind.")
            return
        combo = self.custom_keybind.get().strip().lower()
        self.log(f"Firing keybind: {combo}")
        try:
            keys = combo.split("+")
            parsed = []
            for k in keys:
                k = k.strip()
                if k == "ctrl":
                    parsed.append(Key.ctrl)
                elif k == "alt":
                    parsed.append(Key.alt)
                elif k == "shift":
                    parsed.append(Key.shift)
                elif k == "cmd" or k == "win":
                    parsed.append(Key.cmd)
                elif k == "space":
                    parsed.append(Key.space)
                elif k == "enter":
                    parsed.append(Key.enter)
                elif k == "tab":
                    parsed.append(Key.tab)
                elif k == "esc":
                    parsed.append(Key.esc)
                elif k == "up":
                    parsed.append(Key.up)
                elif k == "down":
                    parsed.append(Key.down)
                elif k == "left":
                    parsed.append(Key.left)
                elif k == "right":
                    parsed.append(Key.right)
                elif len(k) == 1:
                    parsed.append(k)
                else:
                    try:
                        parsed.append(getattr(Key, k))
                    except AttributeError:
                        parsed.append(k)

            for key in parsed:
                self.kb_ctrl.press(key)
            for key in reversed(parsed):
                self.kb_ctrl.release(key)
            self.log(f"Keybind '{combo}' executed.")
        except Exception as e:
            self.log(f"Keybind error: {e}")

    def test_keybind(self):
        self.log("Testing keybind...")
        self.fire_keybind()

    # =========================================================================
    # MACRO RECORDER / PLAYER
    # =========================================================================
    def toggle_record(self):
        if not PYNPUT_AVAILABLE:
            messagebox.showerror("Missing Dependency", "pynput is required for macro recording.\nInstall: pip install pynput")
            return

        if self.recording:
            self.stop_record()
        else:
            self.start_record()

    def start_record(self):
        self.macro_events = []
        self.macro_start_time = time.time()
        self.recording = True
        self.record_btn.config(text="⏹ Stop Recording")
        self.log("Macro recording STARTED. Perform actions now...")
        self.status_var.set("Recording macro...")

        self.kb_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.kb_listener.start()

        self.mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self.mouse_listener.start()

    def stop_record(self):
        self.recording = False
        self.record_btn.config(text="▶ Record")
        self.log(f"Macro recording STOPPED. Events captured: {len(self.macro_events)}")
        self.status_var.set(f"Macro saved: {len(self.macro_events)} events")
        self.macro_info.config(text=f"Events: {len(self.macro_events)}")

        if self.kb_listener:
            self.kb_listener.stop()
            self.kb_listener = None
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None

    def _elapsed(self):
        return time.time() - self.macro_start_time

    def _on_key_press(self, key):
        if not self.recording:
            return
        try:
            self.macro_events.append((self._elapsed(), "kp", key.char))
        except AttributeError:
            self.macro_events.append((self._elapsed(), "kp", str(key)))

    def _on_key_release(self, key):
        if not self.recording:
            return
        try:
            self.macro_events.append((self._elapsed(), "kr", key.char))
        except AttributeError:
            self.macro_events.append((self._elapsed(), "kr", str(key)))

    def _on_mouse_move(self, x, y):
        if not self.recording:
            return
        if self.macro_events and self.macro_events[-1][1] == "mm":
            self.macro_events[-1] = (self._elapsed(), "mm", (x, y))
        else:
            self.macro_events.append((self._elapsed(), "mm", (x, y)))

    def _on_mouse_click(self, x, y, button, pressed):
        if not self.recording:
            return
        evt = "md" if pressed else "mu"
        self.macro_events.append((self._elapsed(), evt, (x, y, str(button))))

    def _on_mouse_scroll(self, x, y, dx, dy):
        if not self.recording:
            return
        self.macro_events.append((self._elapsed(), "ms", (x, y, dx, dy)))

    def clear_macro(self):
        self.macro_events = []
        self.macro_info.config(text="Events: 0")
        self.log("Macro cleared.")

    def play_macro(self):
        if not self.macro_events:
            self.log("No macro recorded.")
            return
        if self.macro_thread and self.macro_thread.is_alive():
            self.log("Macro already playing.")
            return
        self.macro_thread = threading.Thread(target=self._macro_player, daemon=True)
        self.macro_thread.start()
        self.log("Macro playback started.")

    def _macro_player(self):
        if not PYNPUT_AVAILABLE:
            return
        start = time.time()
        for evt in self.macro_events:
            delay = evt[0] - (time.time() - start)
            if delay > 0:
                time.sleep(delay)
            typ = evt[1]
            data = evt[2]
            try:
                if typ == "kp":
                    key = self._parse_key(data)
                    self.kb_ctrl.press(key)
                elif typ == "kr":
                    key = self._parse_key(data)
                    self.kb_ctrl.release(key)
                elif typ == "mm":
                    self.mouse_ctrl.position = data
                elif typ == "md":
                    x, y, btn_str = data
                    btn = self._parse_button(btn_str)
                    self.mouse_ctrl.position = (x, y)
                    self.mouse_ctrl.press(btn)
                elif typ == "mu":
                    x, y, btn_str = data
                    btn = self._parse_button(btn_str)
                    self.mouse_ctrl.position = (x, y)
                    self.mouse_ctrl.release(btn)
                elif typ == "ms":
                    x, y, dx, dy = data
                    self.mouse_ctrl.scroll(dx, dy)
            except Exception as e:
                self.log(f"Macro playback error: {e}")
                break
        self.log("Macro playback finished.")

    def _parse_key(self, data):
        if isinstance(data, str) and data.startswith("Key."):
            name = data.split(".", 1)[1]
            return getattr(Key, name, data)
        return data

    def _parse_button(self, btn_str):
        if "left" in btn_str:
            return Button.left
        elif "right" in btn_str:
            return Button.right
        elif "middle" in btn_str:
            return Button.middle
        return Button.left

    # =========================================================================
    # FORMAT CONVERTERS (Internal <-> Uploaded JSON format)
    # =========================================================================
    def _convert_uploaded_to_internal(self, payload):
        """Convert uploaded example.json format to internal (timestamp, type, data)."""
        events = payload.get("events", [])
        internal = []
        for ev in events:
            ts = ev.get("timestamp", 0)
            ktype = ev.get("key_type", "name")
            kval = ev.get("key_value", "")
            is_press = ev.get("is_press", True)

            if ktype == "name":
                key_repr = f"Key.{kval}"
            else:
                key_repr = kval

            if is_press:
                internal.append((ts, "kp", key_repr))
            else:
                internal.append((ts, "kr", key_repr))
        return internal

    def _convert_internal_to_uploaded(self, internal_events):
        """Convert internal format to uploaded example.json format."""
        events = []
        for ev in internal_events:
            ts, typ, data = ev
            if typ not in ("kp", "kr"):
                continue  # skip mouse events for this format
            is_press = typ == "kp"
            if isinstance(data, str) and data.startswith("Key."):
                ktype = "name"
                kval = data.split(".", 1)[1]
            else:
                ktype = "char"
                kval = data
            events.append({
                "timestamp": round(ts, 3),
                "key_type": ktype,
                "key_value": kval,
                "is_press": is_press
            })
        return events

    # =========================================================================
    # MACRO FILE I/O (Save / Load) — with format detection
    # =========================================================================
    def save_macro(self):
        if not self.macro_events:
            messagebox.showinfo("Save Macro", "No macro events to save.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Macro"
        )
        if not path:
            return
        try:
            # Detect if user wants uploaded format by filename hint, or ask
            # Default to native format but support both
            payload = {
                "version": 2,
                "created": datetime.now().isoformat(),
                "event_count": len(self.macro_events),
                "events": self.macro_events,
                "format": "native"
            }
            with open(path, "w") as f:
                json.dump(payload, f, indent=2)
            self.log(f"Macro saved to: {os.path.basename(path)}")
            self.status_var.set(f"Macro saved: {os.path.basename(path)}")
        except Exception as e:
            self.log(f"Failed to save macro: {e}")
            messagebox.showerror("Save Error", str(e))

    def save_macro_uploaded_format(self):
        """Save in the exact uploaded example.json format (keyboard-only)."""
        if not self.macro_events:
            messagebox.showinfo("Save Macro", "No macro events to save.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Macro (Uploaded Format)"
        )
        if not path:
            return
        try:
            events = self._convert_internal_to_uploaded(self.macro_events)
            payload = {
                "hotkeys": {
                    "start": ["ctrl", "shift", "r"],
                    "stop": ["ctrl", "shift", "s"],
                    "play": ["f9"]
                },
                "events": events
            }
            with open(path, "w") as f:
                json.dump(payload, f, indent=2)
            self.log(f"Macro saved (uploaded format) to: {os.path.basename(path)}")
            self.status_var.set(f"Macro saved: {os.path.basename(path)}")
        except Exception as e:
            self.log(f"Failed to save macro: {e}")
            messagebox.showerror("Save Error", str(e))

    def load_macro(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Load Macro"
        )
        if not path:
            return
        try:
            with open(path, "r") as f:
                payload = json.load(f)

            # --- Format detection ---
            if "hotkeys" in payload and "events" in payload and isinstance(payload["events"], list):
                if payload["events"] and isinstance(payload["events"][0], dict) and "key_type" in payload["events"][0]:
                    # Uploaded example.json format
                    self.macro_events = self._convert_uploaded_to_internal(payload)
                    self.log(f"Loaded uploaded-format macro: {os.path.basename(path)} ({len(self.macro_events)} events)")
                else:
                    # Native format with events list
                    loaded = payload.get("events", [])
                    self.macro_events = loaded
                    self.log(f"Loaded native-format macro: {os.path.basename(path)} ({len(self.macro_events)} events)")
            elif "events" in payload and isinstance(payload["events"], list):
                loaded = payload.get("events", [])
                self.macro_events = loaded
                self.log(f"Loaded macro: {os.path.basename(path)} ({len(self.macro_events)} events)")
            else:
                messagebox.showwarning("Load Macro", "Unrecognized file format.")
                return

            self.macro_info.config(text=f"Events: {len(self.macro_events)}")
            self.status_var.set(f"Macro loaded: {os.path.basename(path)}")
        except Exception as e:
            self.log(f"Failed to load macro: {e}")
            messagebox.showerror("Load Error", str(e))

    # =========================================================================
    # CONFIG FILE I/O (Save / Load / Auto-load)
    # =========================================================================
    def build_config(self):
        """Serialize current UI state to a dict."""
        return {
            "version": 1,
            "camera_url": self.url_var.get(),
            "sensitivity": float(self.sens_scale.get()),
            "cooldown": float(self.cooldown_scale.get()),
            "action": self.action_var.get(),
            "keybind": self.custom_keybind.get(),
            "preview_visible": self.preview_visible,
            "macro_events": self.macro_events
        }

    def apply_config(self, cfg):
        """Apply a config dict to the UI."""
        if "camera_url" in cfg:
            self.url_var.set(cfg["camera_url"])
        if "sensitivity" in cfg:
            self.sens_scale.set(cfg["sensitivity"])
            self.sens_val_label.config(text=f"{int(cfg['sensitivity'])} px²")
        if "cooldown" in cfg:
            self.cooldown_scale.set(cfg["cooldown"])
            self.cool_val_label.config(text=f"{float(cfg['cooldown']):.1f} s")
        if "action" in cfg:
            self.action_var.set(cfg["action"])
        if "keybind" in cfg:
            self.custom_keybind.set(cfg["keybind"])
        if "preview_visible" in cfg:
            if cfg["preview_visible"] != self.preview_visible:
                self.toggle_preview()
        if "macro_events" in cfg and cfg["macro_events"]:
            self.macro_events = cfg["macro_events"]
            self.macro_info.config(text=f"Events: {len(self.macro_events)}")

    def save_config(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Configuration"
        )
        if not path:
            return
        try:
            cfg = self.build_config()
            with open(path, "w") as f:
                json.dump(cfg, f, indent=2)
            self.log(f"Config saved to: {os.path.basename(path)}")
            self.status_var.set(f"Config saved: {os.path.basename(path)}")
        except Exception as e:
            self.log(f"Failed to save config: {e}")
            messagebox.showerror("Save Error", str(e))

    def load_config(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Load Configuration"
        )
        if not path:
            return
        try:
            with open(path, "r") as f:
                cfg = json.load(f)
            self.apply_config(cfg)
            self.log(f"Config loaded from: {os.path.basename(path)}")
            self.status_var.set(f"Config loaded: {os.path.basename(path)}")
        except Exception as e:
            self.log(f"Failed to load config: {e}")
            messagebox.showerror("Load Error", str(e))

    def load_config_silent(self):
        """Auto-load config from default filename on startup."""
        if os.path.exists(CONFIG_FILENAME):
            try:
                with open(CONFIG_FILENAME, "r") as f:
                    cfg = json.load(f)
                self.apply_config(cfg)
                self.log(f"Auto-loaded config: {CONFIG_FILENAME}")
            except Exception as e:
                self.log(f"Auto-load config failed: {e}")

    def save_config_silent(self):
        """Auto-save config to default filename on exit."""
        try:
            cfg = self.build_config()
            with open(CONFIG_FILENAME, "w") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    # =========================================================================
    # CLEANUP
    # =========================================================================
    def on_close(self):
        self.log("Shutting down...")
        self.running = False
        self.capturing = False
        self.recording = False

        if self.kb_listener:
            self.kb_listener.stop()
        if self.mouse_listener:
            self.mouse_listener.stop()

        self.save_config_silent()
        time.sleep(0.3)
        self.root.destroy()


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = MotionTaskApp(root)
    root.mainloop()