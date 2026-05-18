import os
import sys
import subprocess
import zipfile
import requests
import numpy as np
from PIL import Image
from pathlib import Path

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
FRAME_DIR = os.path.expanduser('~/Documents/badapple_frames')
VIDEO_URL = "https://www.youtube.com/watch?v=FtutLA63Cp8"          # Original Bad Apple video
OUTPUT_VIDEO_NAME = "badapple_temp.mp4"
FPS = 60

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def ensure_ffmpeg():
    """Check if ffmpeg is installed; if not, exit with instructions."""
    if subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode != 0:
        print("❌ ffmpeg not found. Please install it first:")
        print("   - macOS: brew install ffmpeg")
        print("   - Linux: sudo apt install ffmpeg")
        print("   - Windows: download from https://ffmpeg.org")
        sys.exit(1)

def download_file(url, dest):
    """Download a file with progress indication."""
    response = requests.get(url, stream=True)
    total = int(response.headers.get('content-length', 0))
    with open(dest, 'wb') as f:
        for i, chunk in enumerate(response.iter_content(chunk_size=8192)):
            f.write(chunk)
            if total and (i+1) % 100 == 0:
                print(f"Downloaded {int((i*8192/total)*100)}%", end='\r')
    print("\nDownload complete.")

def extract_frames_with_ffmpeg(video_path, out_dir, fps=FPS):
    """Extract frames from a video file using ffmpeg."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps={fps}",
        os.path.join(out_dir, "frame_%04d.png")
    ]
    subprocess.run(cmd, check=True)
    print(f"✅ Extracted frames to {out_dir}")

# ----------------------------------------------------------------------
# Method 1: Download pre‑extracted frames from GitHub repo
# ----------------------------------------------------------------------
def download_from_github_repo():
    print("[*] Trying to download pre‑extracted frames from GitHub...")
    repo_url = "https://github.com/Felixoofed/badapple-frames"
    zip_url = "https://github.com/Felixoofed/badapple-frames/raw/main/frames.zip"
    zip_path = os.path.join(FRAME_DIR, "frames.zip")

    try:
        # Attempt to clone the repo and get the zip file directly
        download_file(zip_url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(FRAME_DIR)
        os.remove(zip_path)
        return True
    except Exception as e:
        print(f"⚠️ GitHub download failed: {e}")
        return False

# ----------------------------------------------------------------------
# Method 2: Download video from YouTube and extract frames (fallback)
# ----------------------------------------------------------------------
def download_video_and_extract():
    """Download the Bad Apple video from YouTube and extract 60 fps frames."""
    print("[*] Falling back to downloading video from YouTube...")
    ensure_ffmpeg()

    # Use yt-dlp for reliable YouTube downloads
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
    except FileNotFoundError:
        print("❌ yt-dlp not found. Install it with: pip install yt-dlp")
        return False

    video_path = os.path.join(FRAME_DIR, OUTPUT_VIDEO_NAME)
    # Download the video
    subprocess.run([
        "yt-dlp", "-f", "best[height<=1080]", "-o", video_path, VIDEO_URL
    ], check=True)
    # Extract frames
    extract_frames_with_ffmpeg(video_path, FRAME_DIR, FPS)
    # Remove the temporary video file
    os.remove(video_path)
    return True

# ----------------------------------------------------------------------
# Main downloader
# ----------------------------------------------------------------------
def download_frames():
    if os.path.exists(FRAME_DIR) and any(f.endswith('.png') for f in os.listdir(FRAME_DIR)):
        print("✅ Frames already exist – skipping download.")
        return
    os.makedirs(FRAME_DIR, exist_ok=True)

    if download_from_github_repo():
        print("✅ Frames downloaded from GitHub successfully.")
    elif download_video_and_extract():
        print("✅ Frames extracted from video successfully.")
    else:
        raise RuntimeError("Could not obtain frames. Please check your internet connection and install ffmpeg/yt-dlp.")

# ----------------------------------------------------------------------
# Load frames into numpy arrays (in RAM)
# ----------------------------------------------------------------------
def load_frames_into_ram(frame_dir, target_size=None):
    """
    Load all PNG frames from frame_dir into a list of numpy arrays.
    If target_size is given (e.g., (480, 640)), all frames are resized.
    """
    frame_files = sorted([f for f in os.listdir(frame_dir) if f.endswith('.png')])
    if not frame_files:
        raise FileNotFoundError(f"No PNG frames found in {frame_dir}")
    frames = []
    total = len(frame_files)
    print(f"📀 Loading {total} frames into RAM...")
    for i, filename in enumerate(frame_files):
        path = os.path.join(frame_dir, filename)
        img = Image.open(path).convert("L")           # Convert to grayscale
        if target_size:
            img = img.resize(target_size, Image.LANCZOS)
        frames.append(np.array(img, dtype=np.uint8))
        if (i+1) % 500 == 0:
            print(f"  Loaded {i+1}/{total} frames")
    print(f"✅ Loaded {len(frames)} frames into RAM (shape: {frames[0].shape})")
    return frames

# ----------------------------------------------------------------------
# Example usage
# ----------------------------------------------------------------------
if __name__ == "__main__":
    download_frames()                     # Step 1: get the frames
    frames_in_ram = load_frames_into_ram(FRAME_DIR, target_size=(640, 480))
    # Now frames_in_ram is a list of numpy arrays – ready for your player!
    print(frames_in_ram[0].shape)         # Example output: (480, 640)
