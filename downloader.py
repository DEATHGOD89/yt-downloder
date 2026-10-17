import os
import re
import sys
import time
import shutil
import subprocess
import threading
from typing import Callable, Optional, Dict, Any

def get_default_download_dir() -> str:
    """
    Dynamically resolves the default download directory.
    Works seamlessly across any Windows user profile or future updates.
    """
    user_downloads_downloder = os.path.join(os.path.expanduser("~"), "Downloads", "downloder")
    if os.path.exists(user_downloads_downloder):
        return user_downloads_downloder

    known_fixed = r"C:\Users\Death_God\Downloads\downloder"
    if os.path.exists(known_fixed):
        return known_fixed

    try:
        os.makedirs(user_downloads_downloder, exist_ok=True)
        return user_downloads_downloder
    except Exception:
        fallback = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(fallback, exist_ok=True)
        return fallback

class DownloaderBackend:
    """
    Professional backend service to locate tools (yt-dlp, ffmpeg) and execute downloads
    silently in the background with real-time progress metrics and zero orphaned processes.
    """

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or get_default_download_dir()
        self.active_process: Optional[subprocess.Popen] = None
        self._is_cancelled = False
        self._lock = threading.Lock()
        
        # Locate yt-dlp and ffmpeg dynamically
        self.ytdlp_path, self.ffmpeg_dir = self.discover_tools()

    def discover_tools(self) -> tuple[str, Optional[str]]:
        """
        Locates yt-dlp executable and ffmpeg directory dynamically.
        Checks user directory, app bundle, PATH, and falls back to python module.
        """
        candidate_dirs = [
            os.path.join(os.path.expanduser("~"), "Downloads", "downloder"),
            r"C:\Users\Death_God\Downloads\downloder",
            os.path.dirname(os.path.abspath(__file__)),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin"),
            os.path.dirname(sys.executable),
            os.path.join(os.path.dirname(sys.executable), "bin"),
            os.path.join(os.path.dirname(sys.executable), "_internal"),
            os.getcwd(),
        ]
        
        ytdlp_bin = None
        for d in candidate_dirs:
            if not d:
                continue
            exe = os.path.join(d, "yt-dlp.exe")
            if os.path.isfile(exe):
                ytdlp_bin = exe
                break
                
        if not ytdlp_bin:
            ytdlp_bin = shutil.which("yt-dlp")
            
        if not ytdlp_bin:
            # Fallback to python module execution if standalone binary not found
            ytdlp_bin = f'"{sys.executable}" -m yt_dlp'

        # Locate ffmpeg
        ffmpeg_dir = None
        for d in candidate_dirs:
            if not d:
                continue
            ffmpeg_exe = os.path.join(d, "ffmpeg.exe")
            if os.path.isfile(ffmpeg_exe):
                ffmpeg_dir = d
                break
                
        if not ffmpeg_dir:
            which_ffmpeg = shutil.which("ffmpeg")
            if which_ffmpeg:
                ffmpeg_dir = os.path.dirname(which_ffmpeg)

        # Prepend ffmpeg_dir to PATH if found
        if ffmpeg_dir and ffmpeg_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

        return ytdlp_bin, ffmpeg_dir

    def update_engine(self, on_log: Callable[[str], None], on_done: Callable[[bool, str], None]):
        """
        Updates yt-dlp to the latest version in the background.
        Ensures the software never breaks when YouTube changes their video algorithms!
        """
        def worker():
            if not self.ytdlp_path or not os.path.isfile(self.ytdlp_path):
                on_done(False, "yt-dlp binary not found for self-update.")
                return

            on_log(f"[*] Checking for engine updates using: {self.ytdlp_path} -U\n")
            try:
                startupinfo = None
                creationflags = 0
                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    creationflags = subprocess.CREATE_NO_WINDOW

                proc = subprocess.Popen(
                    [self.ytdlp_path, "-U"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
                output_lines = []
                for line in iter(proc.stdout.readline, ""):
                    clean = line.strip()
                    if clean:
                        output_lines.append(clean)
                        on_log(clean)
                proc.stdout.close()
                proc.wait()

                summary = output_lines[-1] if output_lines else "Update complete."
                on_done(True, summary)
            except Exception as e:
                on_done(False, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def extract_info(self, url: str) -> Dict[str, Any]:
        """
        Extracts video metadata (title, thumbnail, duration, author) without downloading.
        Runs with privacy-first options (no tracking, no cache).
        """
        import yt_dlp
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'playlist_items': '1',     # Only extract single target video
            'no_cache_dir': True,       # Privacy: no cached tracking data
            'windows_filenames': True,  # Safe Windows naming
        }
        if self.ffmpeg_dir:
            ydl_opts['ffmpeg_location'] = self.ffmpeg_dir

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        # Clean thumbnail URL
        thumbnail = info.get('thumbnail', '')
        if not thumbnail and 'thumbnails' in info and info['thumbnails']:
            thumbnail = info['thumbnails'][-1].get('url', '')

        duration_sec = info.get('duration', 0) or 0
        mins, secs = divmod(int(duration_sec), 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            duration_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
        else:
            duration_str = f"{mins:02d}:{secs:02d}"

        formats = info.get('formats', [])
        has_4k = any(f.get('height') and f.get('height') >= 2160 for f in formats)
        has_1080 = any(f.get('height') and f.get('height') >= 1080 for f in formats)

        return {
            'title': info.get('title', 'Unknown Title'),
            'thumbnail': thumbnail,
            'duration': duration_str,
            'uploader': info.get('uploader') or info.get('channel') or 'Unknown Channel',
            'view_count': info.get('view_count', 0),
            'has_4k': has_4k,
            'has_1080': has_1080,
            'url': url
        }

    def start_download(
        self,
        url: str,
        quality_mode: str,
        on_progress: Callable[[Dict[str, Any]], None],
        on_log: Callable[[str], None],
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ):
        """
        Starts the download in a dedicated worker thread.
        Runs yt-dlp completely silently in the background with zero terminal window.
        """
        thread = threading.Thread(
            target=self._download_worker,
            args=(url, quality_mode, on_progress, on_log, on_success, on_error),
            daemon=True
        )
        thread.start()
        return thread

    def cancel_download(self):
        """Cancels running process and all child processes cleanly without leaving orphans."""
        with self._lock:
            self._is_cancelled = True
            if self.active_process:
                pid = self.active_process.pid
                try:
                    # On Windows, kill entire process tree including ffmpeg child processes
                    if sys.platform == "win32":
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(pid)],
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            capture_output=True
                        )
                    else:
                        self.active_process.terminate()
                except Exception:
                    pass

    def _build_command(self, url: str, quality_mode: str) -> list[str]:
        """
        Builds the yt-dlp command line arguments based on user's exact specification.
        Includes Windows-safe and privacy-friendly flags.
        """
        if self.ytdlp_path.startswith('"'):
            cmd = [sys.executable, "-m", "yt_dlp"]
        elif self.ytdlp_path.startswith("python -m"):
            cmd = [sys.executable, "-m", "yt_dlp"]
        else:
            cmd = [self.ytdlp_path]

        # Add ffmpeg location if available
        if self.ffmpeg_dir:
            cmd.extend(["--ffmpeg-location", self.ffmpeg_dir])

        # Output template in output directory with Windows-safe characters
        out_tmpl = os.path.join(self.output_dir, "%(title)s [%(id)s].%(ext)s")
        cmd.extend(["-o", out_tmpl])

        # Core professional flags
        cmd.extend([
            "--newline",             # Line-by-line progress parsing
            "--windows-filenames",   # Sanitize characters strictly for Windows NTFS
            "--no-playlist",         # Prevent accidentally downloading entire 500-video playlists
            "--no-mtime",            # Do not touch modification timestamps
            "--no-cache-dir",        # Privacy: don't retain cookies/tracking cache
        ])

        # Format flags corresponding to user's specification:
        if quality_mode == "4k":
            # yt-dlp -f "bv*+ba/b" --merge-output-format mp4 "URL"
            cmd.extend(["-f", "bv*+ba/b", "--merge-output-format", "mp4"])
        elif quality_mode == "1080p":
            # yt-dlp -f "bestvideo*[height<=1080]+bestaudio/best[height<=1080]" --merge-output-format mp4 "URL"
            cmd.extend(["-f", "bestvideo*[height<=1080]+bestaudio/best[height<=1080]", "--merge-output-format", "mp4"])
        elif quality_mode == "720p":
            # 720p HD option
            cmd.extend(["-f", "bestvideo*[height<=720]+bestaudio/best[height<=720]", "--merge-output-format", "mp4"])
        elif quality_mode == "audio":
            # yt-dlp -f "bestaudio" "URL" with mp3 extraction
            cmd.extend(["-f", "bestaudio/best", "-x", "--audio-format", "mp3"])
        else:
            cmd.extend(["-f", "bv*+ba/b", "--merge-output-format", "mp4"])

        cmd.append(url)
        return cmd

    def _download_worker(
        self,
        url: str,
        quality_mode: str,
        on_progress: Callable[[Dict[str, Any]], None],
        on_log: Callable[[str], None],
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ):
        self._is_cancelled = False
        cmd = self._build_command(url, quality_mode)

        on_log(f"[*] Starting download in silent background process...")
        on_log(f"[*] Target URL: {url}")
        on_log(f"[*] Quality Mode: {quality_mode.upper()}")
        on_log(f"[*] Save Directory: {self.output_dir}\n")

        # Ensure output directory exists
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except Exception as e:
            on_error(f"Cannot write to output folder: {e}")
            return

        # Silent Windows process configuration (NO console window!)
        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW

        destination_file = ""
        error_lines = []
        stream_index = 1
        last_stream_pct = 0.0
        last_progress_time = 0.0

        # Safe environment passing UTF-8 encoding
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
                creationflags=creationflags,
                bufsize=1,
                env=env
            )
            with self._lock:
                self.active_process = process

            # Read stdout line by line
            for line in iter(process.stdout.readline, ""):
                if self._is_cancelled:
                    break

                clean_line = line.strip()
                if not clean_line:
                    continue

                on_log(clean_line)

                # Capture error lines
                if "ERROR:" in clean_line:
                    error_lines.append(clean_line)

                # Capture destination file name and detect stream switch
                if "Destination:" in clean_line:
                    dest_cand = clean_line.split("Destination:")[-1].strip()
                    if dest_cand and not dest_cand.endswith((".part", ".ytdl")):
                        destination_file = dest_cand
                    if last_stream_pct >= 90.0:
                        stream_index += 1
                        last_stream_pct = 0.0
                elif "[Merger] Merging formats into" in clean_line:
                    m = re.search(r'Merging formats into\s+"?([^"]+)"?', clean_line)
                    if m:
                        destination_file = m.group(1)

                # Parse progress with throttling (max once per 75ms) to keep UI 60 FPS smooth
                progress_info = self._parse_progress_line(clean_line, stream_index, quality_mode)
                if progress_info:
                    raw_p = progress_info.get("raw_percent", 0.0)
                    if raw_p > last_stream_pct:
                        last_stream_pct = raw_p

                    now = time.time()
                    if (now - last_progress_time > 0.075) or raw_p >= 99.0 or progress_info.get("status", "").startswith("Merging"):
                        last_progress_time = now
                        on_progress(progress_info)

            process.stdout.close()
            ret_code = process.wait()

            with self._lock:
                self.active_process = None

            if self._is_cancelled:
                on_log("\n[!] Download was stopped by user.")
                on_error("Download cancelled by user.")
                return

            if ret_code == 0:
                on_log("\n[+] Download completed successfully!")
                on_progress({
                    "percent": 100.0,
                    "speed": "",
                    "size": "Complete",
                    "eta": "00:00",
                    "status": "Download Complete! Ready to watch."
                })
                # If destination file is relative, prepend output dir
                if destination_file and not os.path.isabs(destination_file):
                    destination_file = os.path.join(self.output_dir, destination_file)
                on_success(destination_file or self.output_dir)
            else:
                err_msg = "Download interrupted or video unavailable."
                if error_lines:
                    err_msg = "\n".join(error_lines)
                on_log(f"\n[-] Process finished with exit code {ret_code}")
                on_error(err_msg)

        except Exception as e:
            with self._lock:
                self.active_process = None
            on_log(f"\n[-] Fatal exception: {str(e)}")
            on_error(str(e))

    def _parse_progress_line(self, line: str, stream_index: int, quality_mode: str) -> Optional[Dict[str, Any]]:
        """
        Parses download lines like:
        [download]  45.2% of  540.25MiB at  12.45MiB/s ETA 00:23
        [download] 100% of  124.50MiB in 00:10 at 12.45MiB/s
        [Merger] Merging formats into ...
        """
        if "[Merger]" in line or "Merging formats" in line:
            return {
                "percent": 98.5,
                "raw_percent": 100.0,
                "speed": "FFmpeg",
                "size": "Merging...",
                "eta": "Finishing",
                "status": "Merging video & audio streams into MP4 with FFmpeg..."
            }
        if "[ExtractAudio]" in line or "Extracting audio" in line:
            return {
                "percent": 98.5,
                "raw_percent": 100.0,
                "speed": "FFmpeg",
                "size": "Extracting...",
                "eta": "Finishing",
                "status": "Extracting high-quality MP3 audio track..."
            }

        pct_match = re.search(r'\[download\]\s+([\d\.]+)%', line)
        if pct_match:
            raw_pct = float(pct_match.group(1))
            size_match = re.search(r'of\s+~?\s*([\d\.]+\s*[a-zA-Z]+)', line)
            speed_match = re.search(r'at\s+([\d\.]+\s*[a-zA-Z]+/s)', line)
            eta_match = re.search(r'ETA\s+([\d:]+)', line)

            size_str = size_match.group(1) if size_match else ""
            speed_str = speed_match.group(1) if speed_match else ""
            eta_str = eta_match.group(1) if eta_match else ""

            # Scale progress gracefully
            if quality_mode == "audio":
                scaled_pct = raw_pct * 0.98
                status_text = f"Downloading Audio Stream... {raw_pct:.1f}%"
            elif stream_index == 1:
                scaled_pct = raw_pct * 0.85
                status_text = f"Downloading Video Stream... {raw_pct:.1f}%"
            else:
                scaled_pct = 85.0 + (raw_pct * 0.13)
                status_text = f"Downloading Audio Stream... {raw_pct:.1f}%"

            return {
                "percent": round(scaled_pct, 1),
                "raw_percent": raw_pct,
                "speed": speed_str,
                "size": size_str,
                "eta": eta_str,
                "status": status_text
            }

        return None
