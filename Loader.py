import ui
import os
import io
import re
import time
import threading
import numpy as np
from PIL import Image
import sound

# ===============================
# CONFIGURATION
# ===============================
FRAME_DIR = os.path.expanduser('~/Documents/badapple_frames/frames')
TARGET_FPS = 30
FRAME_TIME = 1.0 / TARGET_FPS
PRE_CONVERT_TO_UI = True          # Pre‐convert frames for smooth playback
TARGET_SIZE = None                # e.g., (480, 360) to save memory
SOUND_ENABLED = False             # Start with sound OFF

# Audio file location (MP3)
BASE_DIR = os.path.expanduser('~/Documents/badapple_frames')
AUDIO_PATH = os.path.join(BASE_DIR, 'bad_apple.mp3')

# ===============================
# Helper: PIL → ui.Image
# ===============================
def pil_to_ui(pil_image):
    with io.BytesIO() as buffer:
        pil_image.save(buffer, format='PNG')
        return ui.Image.from_data(buffer.getvalue())

# ===============================
# Frame loading
# ===============================
def get_sorted_frame_files(directory):
    pattern = re.compile(r'output_(\d+)\.jpg', re.IGNORECASE)
    files = []
    for f in os.listdir(directory):
        m = pattern.match(f)
        if m:
            files.append((int(m.group(1)), f))
    if not files:
        raise FileNotFoundError(f"No 'output_XXXX.jpg' frames in {directory}")
    files.sort(key=lambda x: x[0])
    return [os.path.join(directory, fname) for _, fname in files]

def load_frames():
    paths = get_sorted_frame_files(FRAME_DIR)
    total = len(paths)
    print(f"📀 Found {total} frames")
    frames = []
    for i, path in enumerate(paths):
        pil = Image.open(path).convert('L')
        if TARGET_SIZE:
            pil = pil.resize(TARGET_SIZE, Image.LANCZOS)
        if PRE_CONVERT_TO_UI:
            frames.append(pil_to_ui(pil))
        else:
            frames.append(np.array(pil, dtype=np.uint8))
        if (i+1) % 500 == 0:
            print(f"  Loaded {i+1}/{total}")
    print(f"✅ Loaded {total} frames")
    return frames

# ===============================
# Player View
# ===============================
class BadApplePlayer(ui.View):
    def __init__(self, frames, pre_converted):
        self.frames = frames
        self.pre_converted = pre_converted
        self.frame_index = 0
        self.playing = False
        self.background_color = 'black'
        self.sound_enabled = SOUND_ENABLED
        self.audio_player = None

        # Load audio (MP3)
        if os.path.exists(AUDIO_PATH):
            try:
                self.audio_player = sound.Player(AUDIO_PATH)
                self.audio_player.volume = 1.0 if self.sound_enabled else 0.0
                print(f"✅ Audio loaded: {os.path.basename(AUDIO_PATH)}")
            except Exception as e:
                print(f"⚠️ Could not load audio: {e}")
        else:
            print(f"⚠️ MP3 not found at: {AUDIO_PATH}")

        # UI elements
        self.image_view = ui.ImageView(frame=self.bounds, flex='WH')
        self.image_view.content_mode = ui.CONTENT_SCALE_ASPECT_FIT
        self.add_subview(self.image_view)

        self.fps_label = ui.Label(frame=(10, 10, 100, 30))
        self.fps_label.text_color = 'white'
        self.fps_label.background_color = 'rgba(0,0,0,0.5)'
        self.fps_label.alignment = ui.ALIGN_CENTER
        self.fps_label.font = ('Menlo', 12)
        self.add_subview(self.fps_label)

        self.sound_button = ui.Button(frame=(self.bounds.width-80, self.bounds.height-50, 70, 40))
        self.sound_button.flex = 'LB'
        self.sound_button.background_color = 'rgba(0,0,0,0.6)'
        self.sound_button.corner_radius = 5
        self.sound_button.title = '🔇 Sound OFF' if not self.sound_enabled else '🔊 Sound ON'
        self.sound_button.tint_color = 'white'
        self.sound_button.action = self.toggle_sound
        self.add_subview(self.sound_button)

    def toggle_sound(self, sender):
        self.sound_enabled = not self.sound_enabled
        if self.audio_player:
            self.audio_player.volume = 1.0 if self.sound_enabled else 0.0
        sender.title = '🔇 Sound OFF' if not self.sound_enabled else '🔊 Sound ON'
        print(f"Sound {'enabled' if self.sound_enabled else 'disabled'}")

    def will_close(self):
        self.playing = False
        if self.audio_player:
            self.audio_player.stop()

    def numpy_to_ui_image(self, np_frame):
        pil = Image.fromarray(np_frame, mode='L')
        return pil_to_ui(pil)

    def play(self):
        self.playing = True
        total = len(self.frames)
        frame_times = []

        if self.audio_player:
            self.audio_player.play()
            print("🎵 Audio started (looping will keep playing, press stop to end).")

        print(f"▶️ Playing at {TARGET_FPS} fps (sound = {'ON' if self.sound_enabled else 'OFF'})")

        while self.playing and self.frame_index < total:
            start = time.perf_counter()

            if self.pre_converted:
                self.image_view.image = self.frames[self.frame_index]
            else:
                self.image_view.image = self.numpy_to_ui_image(self.frames[self.frame_index])

            self.frame_index += 1

            elapsed = time.perf_counter() - start
            sleep_time = FRAME_TIME - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

            # Update FPS display
            frame_times.append(time.perf_counter())
            cutoff = time.perf_counter() - 2.0
            frame_times = [t for t in frame_times if t > cutoff]
            if len(frame_times) >= 2:
                fps = (len(frame_times)-1) / (frame_times[-1] - frame_times[0])
                self.fps_label.text = f"{fps:.1f} fps"

        print("✅ Playback finished.")
        if self.audio_player:
            self.audio_player.stop()

# ===============================
# Main
# ===============================
if __name__ == '__main__':
    if not os.path.exists(FRAME_DIR):
        print(f"ERROR: Frame directory not found: {FRAME_DIR}")
        print("Please put your frames in ~/Documents/badapple_frames/frames/")
    else:
        frames = load_frames()
        player = BadApplePlayer(frames, pre_converted=PRE_CONVERT_TO_UI)
        player.present('fullscreen')
        threading.Thread(target=player.play, daemon=True).start()
