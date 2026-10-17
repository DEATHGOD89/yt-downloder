import os
import sys
import time
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import requests
from io import BytesIO

# Enable per-monitor DPI awareness on Windows for razor-sharp rendering on all 4K/2K/1080p monitors
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from downloader import DownloaderBackend, get_default_download_dir
from theme_manager import ThemeManager, get_asset_path

# Set global CustomTkinter appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Ultra Downloader [Gothic Crimson Edition]")
        self.geometry("1060x820")
        self.minsize(940, 680)

        # Set application icon safely
        icon_path = get_asset_path("app_icon.ico")
        if icon_path and os.path.isfile(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # Center on screen
        self._center_window()

        # Initialize Backend & Theme Manager dynamically
        self.theme_mgr = ThemeManager()
        initial_dir = self.theme_mgr.settings.get("output_dir", get_default_download_dir())
        self.backend = DownloaderBackend(output_dir=initial_dir)

        self.selected_quality = tk.StringVar(value=self.theme_mgr.settings.get("quality", "4k"))
        self.is_downloading = False
        self.last_failed_url = ""
        self.last_failed_quality = ""
        self.latest_completed_file = ""

        # Background resize debounce
        self._resize_timer = None
        self._current_bg_w = 0
        self._current_bg_h = 0

        # Terminal log buffer for smooth 60 FPS rendering
        self._log_buffer = []
        self._log_timer = None

        # Build UI
        self._init_ui()

        # Bind events
        self.bind("<Configure>", self._on_window_configure)
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # Keyboard shortcuts
        self.bind("<Control-v>", lambda e: self._paste_clipboard())
        self.bind("<Control-V>", lambda e: self._paste_clipboard())

    def _center_window(self):
        self.update_idletasks()
        w = 1060
        h = 820
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(0, (screen_w - w) // 2)
        y = max(0, (screen_h - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _on_window_close(self):
        """Clean shutdown handler: stops any active downloads and kills child processes."""
        if self.is_downloading:
            self.backend.cancel_download()
        self.destroy()

    def _init_ui(self):
        theme = self.theme_mgr.get_current_theme()

        # 1. Background image canvas / label
        self.bg_label = ctk.CTkLabel(self, text="")
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self._update_background()

        # 2. Main Scrollable Container for cards
        self.main_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=("#0c0c10", "#0c0c10"),
            corner_radius=18,
            border_width=1,
            border_color=theme["card_border"]
        )
        self.main_scroll.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.92, relheight=0.92)

        # Build sections inside main_scroll
        self._build_header(theme)
        self._build_url_section(theme)
        self._build_video_preview_card(theme)
        self._build_quality_selector(theme)
        self._build_destination_section(theme)
        self._build_action_buttons(theme)
        self._build_progress_card(theme)
        self._build_notification_cards(theme)
        self._build_terminal_drawer(theme)

    # ------------------ UI SECTIONS ------------------

    def _build_header(self, theme):
        header_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        header_frame.pack(fill="x", padx=25, pady=(15, 10))

        # Title & Subtitle
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left")

        app_title = ctk.CTkLabel(
            title_box,
            text="⚡ YT-DLP ULTRA",
            font=("Segoe UI", 26, "bold"),
            text_color=theme["accent"]
        )
        app_title.pack(anchor="w")

        app_subtitle = ctk.CTkLabel(
            title_box,
            text="Silent Background Engine | 4K HDR • 1080p FHD • Crystal Audio",
            font=("Segoe UI", 12),
            text_color=theme["text_secondary"]
        )
        app_subtitle.pack(anchor="w")

        # Right Controls: Theme Selector, Update Engine & Downloads Button
        right_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_box.pack(side="right", pady=5)

        # Update Engine Button
        self.btn_update_engine = ctk.CTkButton(
            right_box,
            text="⚡ Update Engine",
            width=120,
            height=34,
            fg_color="#1a1a24",
            hover_color="#2b2b3a",
            border_width=1,
            border_color="#3c3c52",
            font=("Segoe UI", 11, "bold"),
            command=self._trigger_engine_update
        )
        self.btn_update_engine.pack(side="left", padx=(0, 8))

        # Open Downloads Folder Button
        self.btn_open_folder = ctk.CTkButton(
            right_box,
            text="📂 Downloads",
            width=110,
            height=34,
            fg_color="#1f1f28",
            hover_color="#2b2b38",
            border_width=1,
            border_color="#3c3c4e",
            font=("Segoe UI", 12, "bold"),
            command=self._open_downloads_folder
        )
        self.btn_open_folder.pack(side="left", padx=(0, 10))

        # Theme Switcher Segmented
        theme_names = ["💀 The Strain", "🌹 Gothic Rose", "🌑 Obsidian"]
        curr_idx = 0
        if self.theme_mgr.current_theme_key == "gothic_rose":
            curr_idx = 1
        elif self.theme_mgr.current_theme_key == "obsidian":
            curr_idx = 2

        self.theme_seg = ctk.CTkSegmentedButton(
            right_box,
            values=theme_names,
            height=34,
            selected_color=theme["primary"],
            selected_hover_color=theme["primary_hover"],
            font=("Segoe UI", 11, "bold"),
            command=self._on_theme_changed
        )
        self.theme_seg.set(theme_names[curr_idx])
        self.theme_seg.pack(side="left")

    def _build_url_section(self, theme):
        url_card = ctk.CTkFrame(
            self.main_scroll,
            fg_color=("#14141c", "#14141c"),
            corner_radius=14,
            border_width=1,
            border_color=theme["card_border"]
        )
        url_card.pack(fill="x", padx=25, pady=8)

        lbl = ctk.CTkLabel(
            url_card,
            text="ENTER YOUTUBE VIDEO LINK:",
            font=("Segoe UI", 12, "bold"),
            text_color=theme["text_secondary"]
        )
        lbl.pack(anchor="w", padx=20, pady=(12, 4))

        input_row = ctk.CTkFrame(url_card, fg_color="transparent")
        input_row.pack(fill="x", padx=20, pady=(0, 14))

        self.url_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Paste YouTube URL here (e.g. https://www.youtube.com/watch?v=...)",
            height=42,
            font=("Segoe UI", 13),
            border_width=1,
            border_color="#333344",
            fg_color="#0a0a0e"
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.url_entry.bind("<Return>", lambda e: self._fetch_video_info())

        # Paste Button
        self.btn_paste = ctk.CTkButton(
            input_row,
            text="📋 Paste Link",
            width=110,
            height=42,
            fg_color=theme["primary"],
            hover_color=theme["primary_hover"],
            font=("Segoe UI", 12, "bold"),
            command=self._paste_clipboard
        )
        self.btn_paste.pack(side="left", padx=(0, 8))

        # Inspect Button
        self.btn_inspect = ctk.CTkButton(
            input_row,
            text="🔍 Fetch Info",
            width=100,
            height=42,
            fg_color="#242432",
            hover_color="#343446",
            font=("Segoe UI", 12, "bold"),
            command=self._fetch_video_info
        )
        self.btn_inspect.pack(side="left", padx=(0, 8))

        # Clear Button
        self.btn_clear = ctk.CTkButton(
            input_row,
            text="✖",
            width=42,
            height=42,
            fg_color="#1e1e28",
            hover_color="#2c2c3a",
            font=("Segoe UI", 13, "bold"),
            command=self._clear_input
        )
        self.btn_clear.pack(side="left")

    def _build_video_preview_card(self, theme):
        self.preview_card = ctk.CTkFrame(
            self.main_scroll,
            fg_color=("#151520", "#151520"),
            corner_radius=14,
            border_width=1,
            border_color=theme["card_border"]
        )
        self.preview_card.pack_forget()

        content_row = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        content_row.pack(fill="x", padx=16, pady=12)

        self.thumb_label = ctk.CTkLabel(content_row, text="", width=180, height=105)
        self.thumb_label.pack(side="left", padx=(0, 15))

        details_box = ctk.CTkFrame(content_row, fg_color="transparent")
        details_box.pack(side="left", fill="both", expand=True)

        self.video_title_lbl = ctk.CTkLabel(
            details_box,
            text="Video Title Here",
            font=("Segoe UI", 14, "bold"),
            text_color="#ffffff",
            anchor="w",
            wraplength=620,
            justify="left"
        )
        self.video_title_lbl.pack(anchor="w", pady=(2, 4))

        self.video_channel_lbl = ctk.CTkLabel(
            details_box,
            text="Channel Name",
            font=("Segoe UI", 12),
            text_color="#ff9ea8",
            anchor="w"
        )
        self.video_channel_lbl.pack(anchor="w", pady=(0, 6))

        badge_row = ctk.CTkFrame(details_box, fg_color="transparent")
        badge_row.pack(anchor="w")

        self.badge_duration = ctk.CTkLabel(
            badge_row,
            text="⏱️ 00:00",
            fg_color=theme["badge_bg"],
            corner_radius=6,
            font=("Segoe UI", 11, "bold"),
            padx=8,
            pady=3
        )
        self.badge_duration.pack(side="left", padx=(0, 8))

        self.badge_quality = ctk.CTkLabel(
            badge_row,
            text="🎬 4K Ultra HD Supported",
            fg_color="#182a18",
            text_color="#4ade80",
            corner_radius=6,
            font=("Segoe UI", 11, "bold"),
            padx=8,
            pady=3
        )
        self.badge_quality.pack(side="left", padx=(0, 8))

    def _build_quality_selector(self, theme):
        card = ctk.CTkFrame(
            self.main_scroll,
            fg_color=("#14141c", "#14141c"),
            corner_radius=14,
            border_width=1,
            border_color=theme["card_border"]
        )
        card.pack(fill="x", padx=25, pady=8)

        lbl = ctk.CTkLabel(
            card,
            text="SELECT DOWNLOAD RESOLUTION & FORMAT:",
            font=("Segoe UI", 12, "bold"),
            text_color=theme["text_secondary"]
        )
        lbl.pack(anchor="w", padx=20, pady=(12, 8))

        modes_frame = ctk.CTkFrame(card, fg_color="transparent")
        modes_frame.pack(fill="x", padx=16, pady=(0, 14))

        self.quality_cards = {}
        formats_data = [
            ("4k", "🌟 4K / Max Quality", "Best Video + Best Audio\nMerged to MP4 (Ultra HD)", "-f bv*+ba/b"),
            ("1080p", "🖥️ 1080p Full HD", "Best 1080p Video + Audio\nMerged to MP4 (1080p FHD)", "-f bestvideo[height<=1080]+..."),
            ("720p", "📱 720p HD", "Fast download HD 720p\nMerged to MP4 (720p HD)", "-f bestvideo[height<=720]+..."),
            ("audio", "🎵 Audio Only (MP3)", "Crystal clear best audio\nExtracted to MP3 format", "-f bestaudio/best -x"),
        ]

        for idx, (key, title, desc, tag) in enumerate(formats_data):
            f_card = ctk.CTkFrame(
                modes_frame,
                fg_color="#1b1b24",
                corner_radius=12,
                border_width=1,
                border_color="#333346"
            )
            f_card.grid(row=0, column=idx, padx=6, pady=4, sticky="nsew")
            modes_frame.columnconfigure(idx, weight=1)

            rb = ctk.CTkRadioButton(
                f_card,
                text=title,
                value=key,
                variable=self.selected_quality,
                font=("Segoe UI", 13, "bold"),
                fg_color=theme["primary"],
                hover_color=theme["primary_hover"],
                command=self._on_quality_changed
            )
            rb.pack(anchor="w", padx=12, pady=(10, 4))

            desc_lbl = ctk.CTkLabel(
                f_card,
                text=desc,
                font=("Segoe UI", 10),
                text_color="#9ea3b0",
                justify="left"
            )
            desc_lbl.pack(anchor="w", padx=14, pady=(0, 10))

            def make_click_handler(k=key):
                return lambda event: self._select_quality(k)
            f_card.bind("<Button-1>", make_click_handler(key))
            desc_lbl.bind("<Button-1>", make_click_handler(key))

            self.quality_cards[key] = f_card

        self._highlight_selected_quality()

    def _select_quality(self, key):
        self.selected_quality.set(key)
        self._on_quality_changed()

    def _on_quality_changed(self):
        self.theme_mgr.save_settings({"quality": self.selected_quality.get()})
        self._highlight_selected_quality()

    def _highlight_selected_quality(self):
        theme = self.theme_mgr.get_current_theme()
        curr = self.selected_quality.get()
        for key, card in self.quality_cards.items():
            if key == curr:
                card.configure(
                    border_color=theme["accent"],
                    border_width=2,
                    fg_color=theme.get("card_hover", "#22080d")
                )
            else:
                card.configure(
                    border_color="#333346",
                    border_width=1,
                    fg_color="#1b1b24"
                )

    def _build_destination_section(self, theme):
        dest_card = ctk.CTkFrame(
            self.main_scroll,
            fg_color=("#14141c", "#14141c"),
            corner_radius=14,
            border_width=1,
            border_color=theme["card_border"]
        )
        dest_card.pack(fill="x", padx=25, pady=8)

        row = ctk.CTkFrame(dest_card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=10)

        lbl = ctk.CTkLabel(
            row,
            text="SAVE FOLDER:",
            font=("Segoe UI", 12, "bold"),
            text_color=theme["text_secondary"]
        )
        lbl.pack(side="left", padx=(0, 10))

        self.dest_lbl = ctk.CTkLabel(
            row,
            text=self.backend.output_dir,
            font=("Segoe UI", 12),
            text_color="#ffffff",
            anchor="w"
        )
        self.dest_lbl.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_change_dest = ctk.CTkButton(
            row,
            text="Change Folder",
            width=115,
            height=32,
            fg_color="#242432",
            hover_color="#343446",
            font=("Segoe UI", 11, "bold"),
            command=self._change_output_directory
        )
        self.btn_change_dest.pack(side="right")

    def _build_action_buttons(self, theme):
        action_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        action_frame.pack(fill="x", padx=25, pady=(10, 8))

        self.btn_download = ctk.CTkButton(
            action_frame,
            text="⬇️  START DOWNLOAD (SILENT BACKGROUND)",
            height=50,
            fg_color=theme["primary"],
            hover_color=theme["primary_hover"],
            font=("Segoe UI", 15, "bold"),
            corner_radius=14,
            command=self._start_download_action
        )
        self.btn_download.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_cancel = ctk.CTkButton(
            action_frame,
            text="⏹️ Stop",
            width=100,
            height=50,
            fg_color="#331418",
            hover_color="#521d24",
            text_color="#ff7b8c",
            font=("Segoe UI", 13, "bold"),
            corner_radius=14,
            state="disabled",
            command=self._cancel_download_action
        )
        self.btn_cancel.pack(side="left")

    def _build_progress_card(self, theme):
        self.progress_card = ctk.CTkFrame(
            self.main_scroll,
            fg_color=("#14141c", "#14141c"),
            corner_radius=14,
            border_width=1,
            border_color=theme["card_border"]
        )
        self.progress_card.pack_forget()

        self.progress_status_lbl = ctk.CTkLabel(
            self.progress_card,
            text="Preparing download engine...",
            font=("Segoe UI", 13, "bold"),
            text_color="#ffffff",
            anchor="w"
        )
        self.progress_status_lbl.pack(fill="x", padx=20, pady=(14, 6))

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_card,
            height=14,
            corner_radius=7,
            progress_color=theme["accent"],
            fg_color="#222230"
        )
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 10))
        self.progress_bar.set(0.0)

        metrics_frame = ctk.CTkFrame(self.progress_card, fg_color="transparent")
        metrics_frame.pack(fill="x", padx=20, pady=(0, 14))

        self.metric_pct = self._create_metric_badge(metrics_frame, "📊 Progress", "0.0%", theme)
        self.metric_speed = self._create_metric_badge(metrics_frame, "⚡ Speed", "0.0 MB/s", theme)
        self.metric_size = self._create_metric_badge(metrics_frame, "📦 Size", "-- / --", theme)
        self.metric_eta = self._create_metric_badge(metrics_frame, "⏱️ ETA", "--:--", theme)

    def _create_metric_badge(self, parent, label_text, init_val, theme):
        badge = ctk.CTkFrame(
            parent,
            fg_color="#1d1d28",
            corner_radius=8,
            border_width=1,
            border_color="#2e2e40"
        )
        badge.pack(side="left", fill="x", expand=True, padx=4)

        title = ctk.CTkLabel(badge, text=label_text, font=("Segoe UI", 10), text_color="#a0a5b8")
        title.pack(anchor="center", pady=(4, 0))

        val = ctk.CTkLabel(badge, text=init_val, font=("Segoe UI", 12, "bold"), text_color="#ffffff")
        val.pack(anchor="center", pady=(0, 4))
        return val

    def _build_notification_cards(self, theme):
        # 1. Error Banner
        self.error_card = ctk.CTkFrame(
            self.main_scroll,
            fg_color="#2b0a10",
            corner_radius=14,
            border_width=2,
            border_color="#ff2247"
        )
        self.error_card.pack_forget()

        err_header = ctk.CTkFrame(self.error_card, fg_color="transparent")
        err_header.pack(fill="x", padx=16, pady=(12, 6))

        err_title = ctk.CTkLabel(
            err_header,
            text="⚠️  DOWNLOAD ERROR ENCOUNTERED",
            font=("Segoe UI", 14, "bold"),
            text_color="#ff4d6d"
        )
        err_title.pack(side="left")

        self.btn_try_again = ctk.CTkButton(
            err_header,
            text="🔄  Try Again",
            width=120,
            height=32,
            fg_color="#e60026",
            hover_color="#ff1a40",
            font=("Segoe UI", 12, "bold"),
            command=self._retry_download
        )
        self.btn_try_again.pack(side="right", padx=(0, 8))

        btn_dismiss_err = ctk.CTkButton(
            err_header,
            text="✖",
            width=32,
            height=32,
            fg_color="#3e131b",
            hover_color="#541b26",
            command=lambda: self.error_card.pack_forget()
        )
        btn_dismiss_err.pack(side="right")

        self.error_msg_lbl = ctk.CTkLabel(
            self.error_card,
            text="Error description here",
            font=("Segoe UI", 11),
            text_color="#ffccd3",
            justify="left",
            wraplength=880,
            anchor="w"
        )
        self.error_msg_lbl.pack(fill="x", padx=18, pady=(0, 14))

        # 2. Success Banner
        self.success_card = ctk.CTkFrame(
            self.main_scroll,
            fg_color="#0e2316",
            corner_radius=14,
            border_width=2,
            border_color="#22c55e"
        )
        self.success_card.pack_forget()

        succ_row = ctk.CTkFrame(self.success_card, fg_color="transparent")
        succ_row.pack(fill="x", padx=16, pady=12)

        succ_info = ctk.CTkFrame(succ_row, fg_color="transparent")
        succ_info.pack(side="left", fill="both", expand=True)

        succ_title = ctk.CTkLabel(
            succ_info,
            text="✅  DOWNLOAD COMPLETED SUCCESSFULLY!",
            font=("Segoe UI", 14, "bold"),
            text_color="#4ade80",
            anchor="w"
        )
        succ_title.pack(anchor="w")

        self.succ_file_lbl = ctk.CTkLabel(
            succ_info,
            text="File saved to folder",
            font=("Segoe UI", 11),
            text_color="#bbf7d0",
            anchor="w",
            wraplength=600
        )
        self.succ_file_lbl.pack(anchor="w")

        succ_actions = ctk.CTkFrame(succ_row, fg_color="transparent")
        succ_actions.pack(side="right")

        self.btn_play_file = ctk.CTkButton(
            succ_actions,
            text="▶️ Play Video",
            width=110,
            height=34,
            fg_color="#16a34a",
            hover_color="#15803d",
            font=("Segoe UI", 12, "bold"),
            command=self._play_completed_file
        )
        self.btn_play_file.pack(side="left", padx=(0, 8))

        btn_show_folder = ctk.CTkButton(
            succ_actions,
            text="📂 Open Folder",
            width=110,
            height=34,
            fg_color="#1f2937",
            hover_color="#374151",
            font=("Segoe UI", 12, "bold"),
            command=self._open_downloads_folder
        )
        btn_show_folder.pack(side="left")

    def _build_terminal_drawer(self, theme):
        drawer_frame = ctk.CTkFrame(self.main_scroll, fg_color="transparent")
        drawer_frame.pack(fill="x", padx=25, pady=(12, 20))

        toggle_bar = ctk.CTkFrame(drawer_frame, fg_color="transparent")
        toggle_bar.pack(fill="x")

        self.is_terminal_open = False
        self.btn_toggle_terminal = ctk.CTkButton(
            toggle_bar,
            text="▶  Show Live Terminal Logs (yt-dlp output)",
            height=28,
            fg_color="transparent",
            hover_color="#1f1f28",
            text_color="#9ea3b0",
            font=("Segoe UI", 11, "bold"),
            anchor="w",
            command=self._toggle_terminal_drawer
        )
        self.btn_toggle_terminal.pack(side="left")

        self.btn_clear_terminal = ctk.CTkButton(
            toggle_bar,
            text="Clear Logs",
            width=80,
            height=26,
            fg_color="#1a1a24",
            hover_color="#2a2a38",
            font=("Segoe UI", 10),
            command=self._clear_terminal_logs
        )

        self.terminal_box = ctk.CTkTextbox(
            drawer_frame,
            height=160,
            font=("Consolas", 11),
            fg_color="#07070a",
            text_color="#00ff66",
            border_width=1,
            border_color="#222230"
        )
        self.terminal_box.pack_forget()

    # ------------------ EVENT HANDLERS & LOGIC ------------------

    def _on_window_configure(self, event):
        """Debounced background resize on window change with minimize guard."""
        if event.widget == self:
            w, h = self.winfo_width(), self.winfo_height()
            if w < 200 or h < 200:
                return  # Skip minimized states
            if abs(w - self._current_bg_w) > 20 or abs(h - self._current_bg_h) > 20:
                if self._resize_timer:
                    self.after_cancel(self._resize_timer)
                self._resize_timer = self.after(120, self._update_background)

    def _update_background(self):
        if not self.winfo_exists():
            return
        w = max(400, self.winfo_width())
        h = max(300, self.winfo_height())
        self._current_bg_w = w
        self._current_bg_h = h
        bg_img = self.theme_mgr.get_processed_background(w, h)
        self.bg_label.configure(image=bg_img)

    def _on_theme_changed(self, value):
        if "Strain" in value:
            self.theme_mgr.set_theme("the_strain")
        elif "Rose" in value:
            self.theme_mgr.set_theme("gothic_rose")
        else:
            self.theme_mgr.set_theme("obsidian")

        theme = self.theme_mgr.get_current_theme()
        self._update_background()

        self.main_scroll.configure(border_color=theme["card_border"])
        self.btn_download.configure(fg_color=theme["primary"], hover_color=theme["primary_hover"])
        self.btn_paste.configure(fg_color=theme["primary"], hover_color=theme["primary_hover"])
        self.progress_bar.configure(progress_color=theme["accent"])
        self._highlight_selected_quality()

    def _trigger_engine_update(self):
        """Runs yt-dlp -U in the background so the tool stays compatible with YouTube forever."""
        self.btn_update_engine.configure(state="disabled", text="⏳ Updating...")
        self._log_to_terminal("[*] Checking for yt-dlp engine updates...\n")

        def on_done(success, msg):
            if not self.winfo_exists():
                return
            self.after(0, lambda: self._handle_update_done(success, msg))

        self.backend.update_engine(
            on_log=lambda l: self.after(0, lambda: self._log_to_terminal(l)),
            on_done=on_done
        )

    def _handle_update_done(self, success, msg):
        self.btn_update_engine.configure(state="normal", text="⚡ Update Engine")
        if success:
            messagebox.showinfo("Engine Update", f"yt-dlp Engine Status:\n\n{msg}")
        else:
            messagebox.showwarning("Engine Update", f"Could not update engine:\n\n{msg}")

    def _paste_clipboard(self):
        """Explicit privacy-first clipboard reading on button click or Ctrl+V."""
        try:
            cb = self.clipboard_get().strip()
            if cb:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, cb)
                self._fetch_video_info()
        except Exception:
            messagebox.showwarning("Clipboard", "No readable text found on your clipboard.")

    def _clear_input(self):
        self.url_entry.delete(0, "end")
        self.preview_card.pack_forget()

    def _fetch_video_info(self):
        url = self.url_entry.get().strip()
        if not url:
            return

        self.btn_inspect.configure(state="disabled", text="Fetching...")

        def worker():
            try:
                info = self.backend.extract_info(url)
                thumb_img = None
                thumb_url = info.get("thumbnail")
                if thumb_url:
                    try:
                        resp = requests.get(thumb_url, timeout=5)
                        if resp.status_code == 200:
                            raw = Image.open(BytesIO(resp.content))
                            raw = raw.resize((180, 105), Image.Resampling.LANCZOS)
                            thumb_img = ctk.CTkImage(light_image=raw, dark_image=raw, size=(180, 105))
                    except Exception:
                        pass
                if self.winfo_exists():
                    self.after(0, lambda: self._apply_video_info(info, thumb_img))
            except Exception as e:
                if self.winfo_exists():
                    self.after(0, lambda: self._on_info_fetch_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_video_info(self, info, thumb_img):
        if not self.winfo_exists():
            return
        self.btn_inspect.configure(state="normal", text="🔍 Fetch Info")
        self.video_title_lbl.configure(text=info.get("title", "YouTube Video"))
        self.video_channel_lbl.configure(text=f"📺 {info.get('uploader', 'Channel')}")
        self.badge_duration.configure(text=f"⏱️ {info.get('duration', '00:00')}")

        has_4k = info.get("has_4k", False)
        if has_4k:
            self.badge_quality.configure(
                text="🎬 4K Ultra HD Supported",
                fg_color="#182a18",
                text_color="#4ade80"
            )
        else:
            self.badge_quality.configure(
                text="🖥️ 1080p FHD Supported",
                fg_color="#1a2536",
                text_color="#60a5fa"
            )

        if thumb_img:
            self.thumb_label.configure(image=thumb_img)

        self.preview_card.pack(fill="x", padx=25, pady=6, after=self.url_entry.master.master)

    def _on_info_fetch_error(self, err_text):
        if not self.winfo_exists():
            return
        self.btn_inspect.configure(state="normal", text="🔍 Fetch Info")
        self._log_to_terminal(f"[!] Warning: Could not pre-fetch video info: {err_text}\n")

    def _change_output_directory(self):
        new_dir = filedialog.askdirectory(initialdir=self.backend.output_dir, title="Select Download Folder")
        if new_dir:
            self.backend.output_dir = new_dir
            self.dest_lbl.configure(text=new_dir)
            self.theme_mgr.save_settings({"output_dir": new_dir})

    def _open_downloads_folder(self):
        folder = self.backend.output_dir
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(folder)
        else:
            subprocess.Popen(["xdg-open", folder])

    def _toggle_terminal_drawer(self):
        self.is_terminal_open = not self.is_terminal_open
        if self.is_terminal_open:
            self.btn_toggle_terminal.configure(text="▼  Hide Live Terminal Logs")
            self.btn_clear_terminal.pack(side="right")
            self.terminal_box.pack(fill="x", pady=(8, 0))
        else:
            self.btn_toggle_terminal.configure(text="▶  Show Live Terminal Logs (yt-dlp output)")
            self.btn_clear_terminal.pack_forget()
            self.terminal_box.pack_forget()

    def _clear_terminal_logs(self):
        self.terminal_box.delete("1.0", "end")

    def _log_to_terminal(self, text):
        """Batched terminal log updater for smooth performance."""
        self._log_buffer.append(text)
        if not self._log_timer:
            self._log_timer = self.after(80, self._flush_log_buffer)

    def _flush_log_buffer(self):
        self._log_timer = None
        if not self.winfo_exists() or not self._log_buffer:
            return
        combined = "\n".join(self._log_buffer) + "\n"
        self._log_buffer.clear()
        self.terminal_box.insert("end", combined)
        self.terminal_box.see("end")

    # ------------------ DOWNLOAD LIFECYCLE ------------------

    def _start_download_action(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter or paste a valid YouTube video URL first!")
            return

        if self.is_downloading:
            return

        self.is_downloading = True
        quality = self.selected_quality.get()

        # Reset notifications
        self.error_card.pack_forget()
        self.success_card.pack_forget()

        # Show progress card
        self.progress_card.pack(fill="x", padx=25, pady=8, after=self.btn_download.master)
        self.progress_bar.set(0.0)
        self.progress_status_lbl.configure(text=f"Launching silent background process for [{quality.upper()}]...")
        self.metric_pct.configure(text="0.0%")
        self.metric_speed.configure(text="Starting...")
        self.metric_size.configure(text="Connecting...")
        self.metric_eta.configure(text="--:--")

        self.btn_download.configure(state="disabled", text="⏳  DOWNLOADING IN BACKGROUND...")
        self.btn_cancel.configure(state="normal")

        self.backend.start_download(
            url=url,
            quality_mode=quality,
            on_progress=lambda p: self.after(0, lambda: self._handle_progress(p)),
            on_log=lambda l: self.after(0, lambda: self._log_to_terminal(l)),
            on_success=lambda f: self.after(0, lambda: self._handle_success(f)),
            on_error=lambda e: self.after(0, lambda: self._handle_error(e, url, quality)),
        )

    def _cancel_download_action(self):
        self.backend.cancel_download()
        self.btn_cancel.configure(state="disabled")
        self.progress_status_lbl.configure(text="Stopping download...")

    def _handle_progress(self, p):
        if not self.winfo_exists():
            return
        pct = p.get("percent", 0.0)
        self.progress_bar.set(min(1.0, max(0.0, pct / 100.0)))
        self.metric_pct.configure(text=f"{pct:.1f}%")

        if p.get("speed"):
            self.metric_speed.configure(text=p["speed"])
        if p.get("size"):
            self.metric_size.configure(text=p["size"])
        if p.get("eta"):
            self.metric_eta.configure(text=p["eta"])
        if p.get("status"):
            self.progress_status_lbl.configure(text=p["status"])

    def _handle_success(self, file_path):
        if not self.winfo_exists():
            return
        self.is_downloading = False
        self.latest_completed_file = file_path
        self.btn_download.configure(state="normal", text="⬇️  START DOWNLOAD (SILENT BACKGROUND)")
        self.btn_cancel.configure(state="disabled")

        self.progress_bar.set(1.0)
        self.progress_status_lbl.configure(text="Download finished! Saved successfully.")

        filename = os.path.basename(file_path) if file_path else "Media file"
        self.succ_file_lbl.configure(text=f"Saved: {filename}\nDirectory: {self.backend.output_dir}")
        self.success_card.pack(fill="x", padx=25, pady=8, after=self.progress_card)

    def _handle_error(self, err_text, url, quality):
        if not self.winfo_exists():
            return
        self.is_downloading = False
        self.last_failed_url = url
        self.last_failed_quality = quality

        self.btn_download.configure(state="normal", text="⬇️  START DOWNLOAD (SILENT BACKGROUND)")
        self.btn_cancel.configure(state="disabled")

        self.progress_status_lbl.configure(text="Download failed or was interrupted.")
        self.progress_bar.set(0.0)

        clean_err = err_text.strip()
        if len(clean_err) > 300:
            clean_err = clean_err[:300] + "... (Check Terminal Logs below for full trace)"

        self.error_msg_lbl.configure(text=clean_err)
        self.error_card.pack(fill="x", padx=25, pady=8, after=self.progress_card)

    def _retry_download(self):
        if self.last_failed_url:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, self.last_failed_url)
            if self.last_failed_quality:
                self.selected_quality.set(self.last_failed_quality)
                self._on_quality_changed()
            self._start_download_action()

    def _play_completed_file(self):
        target = self.latest_completed_file
        if target and os.path.isfile(target):
            try:
                if sys.platform == "win32":
                    os.startfile(target)
                else:
                    subprocess.Popen(["xdg-open", target])
            except Exception:
                self._open_downloads_folder()
        else:
            self._open_downloads_folder()

if __name__ == "__main__":
    import traceback
    try:
        app = YouTubeDownloaderApp()
        app.mainloop()
    except Exception as e:
        err = traceback.format_exc()
        try:
            with open("crash_log.txt", "w", encoding="utf-8") as f:
                f.write(err)
        except Exception:
            pass
        try:
            import tkinter.messagebox as mb
            mb.showerror("Fatal Error Starting Downloader", f"An error occurred while launching:\n\n{err}")
        except Exception:
            pass
