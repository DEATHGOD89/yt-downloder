import sys
import os
import json
from PIL import Image, ImageEnhance
import customtkinter as ctk

def get_asset_path(filename: str) -> str:
    """Finds asset path reliably whether running as source script or standalone EXE."""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "_internal", "assets", filename),
        os.path.join(getattr(sys, "_MEIPASS", ""), "assets", filename),
        os.path.join(os.path.dirname(sys.executable), "assets", filename),
        os.path.join(os.path.dirname(sys.executable), "_internal", "assets", filename),
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return ""

def get_settings_file_path() -> str:
    """
    Returns writable path for settings.json.
    Prefers directory next to executable or script (portable mode),
    falls back to %APPDATA% if restricted.
    """
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    local_path = os.path.join(base_dir, "settings.json")
    try:
        # Test if local folder is writable
        test_file = local_path + ".tmp"
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return local_path
    except Exception:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        conf_dir = os.path.join(appdata, "YTDownloaderUltra")
        os.makedirs(conf_dir, exist_ok=True)
        return os.path.join(conf_dir, "settings.json")

def get_default_download_folder() -> str:
    """Dynamic resolution of default download folder across any Windows machine."""
    user_downloder = os.path.join(os.path.expanduser("~"), "Downloads", "downloder")
    if os.path.exists(user_downloder):
        return user_downloder
    try:
        os.makedirs(user_downloder, exist_ok=True)
        return user_downloder
    except Exception:
        return os.path.join(os.path.expanduser("~"), "Downloads")

SETTINGS_FILE = get_settings_file_path()

class ThemeManager:
    THEMES = {
        "the_strain": {
            "name": "💀 The Strain (Crimson)",
            "image_file": "theme_the_strain.jpg",
            "primary": "#e60026",
            "primary_hover": "#b8001f",
            "accent": "#ff2a4b",
            "card_bg": "#120508",
            "card_border": "#54121a",
            "card_hover": "#22080d",
            "text_primary": "#ffffff",
            "text_secondary": "#ff9ea8",
            "badge_bg": "#2e080d",
            "darkness": 0.42
        },
        "gothic_rose": {
            "name": "🌹 Gothic Rose (Dark Veil)",
            "image_file": "theme_gothic_rose.jpg",
            "primary": "#e01a4f",
            "primary_hover": "#b0123c",
            "accent": "#ff4d79",
            "card_bg": "#120c13",
            "card_border": "#4a192c",
            "card_hover": "#22111d",
            "text_primary": "#ffffff",
            "text_secondary": "#ffb3c6",
            "badge_bg": "#2b0f1a",
            "darkness": 0.45
        },
        "obsidian": {
            "name": "🌑 Obsidian Dark (Stealth)",
            "image_file": None,
            "primary": "#e60026",
            "primary_hover": "#b8001f",
            "accent": "#ff3b5c",
            "card_bg": "#131317",
            "card_border": "#282832",
            "card_hover": "#1c1c24",
            "text_primary": "#ffffff",
            "text_secondary": "#9fa3af",
            "badge_bg": "#1e1e28",
            "darkness": 1.0
        }
    }

    def __init__(self):
        self.settings_file = get_settings_file_path()
        self.settings = self.load_settings()
        self.current_theme_key = self.settings.get("theme", "the_strain")
        if self.current_theme_key not in self.THEMES:
            self.current_theme_key = "the_strain"
        self._image_cache = {}

    def load_settings(self) -> dict:
        if os.path.isfile(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception:
                pass
        return {
            "theme": "the_strain",
            "quality": "4k",
            "output_dir": get_default_download_folder()
        }

    def save_settings(self, updates: dict):
        self.settings.update(updates)
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception:
            pass

    def get_current_theme(self) -> dict:
        return self.THEMES[self.current_theme_key]

    def set_theme(self, theme_key: str):
        if theme_key in self.THEMES:
            self.current_theme_key = theme_key
            self.save_settings({"theme": theme_key})

    def get_processed_background(self, width: int, height: int) -> ctk.CTkImage:
        """
        Loads the theme image, performs center-crop with aspect ratio preservation,
        and applies a subtle dark contrast filter so UI widgets are crystal clear.
        Guarded against invalid/minimized window dimensions.
        """
        width = max(200, width)
        height = max(150, height)

        cache_key = (self.current_theme_key, width, height)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]

        theme = self.get_current_theme()
        img_name = theme.get("image_file")
        img_path = get_asset_path(img_name) if img_name else ""

        if not img_path or not os.path.isfile(img_path):
            solid = Image.new("RGB", (width, height), color=(12, 12, 16))
            ctk_img = ctk.CTkImage(light_image=solid, dark_image=solid, size=(width, height))
            self._image_cache[cache_key] = ctk_img
            return ctk_img

        try:
            raw = Image.open(img_path).convert("RGB")
            aspect_target = width / max(1, height)
            aspect_img = raw.width / max(1, raw.height)

            if aspect_img > aspect_target:
                new_h = height
                new_w = int(height * aspect_img)
            else:
                new_w = width
                new_h = int(width / aspect_img)

            resized = raw.resize((max(1, new_w), max(1, new_h)), Image.Resampling.LANCZOS)
            left = (new_w - width) // 2
            top = (new_h - height) // 2
            cropped = resized.crop((left, top, left + width, top + height))

            dark_factor = theme.get("darkness", 0.45)
            enhancer = ImageEnhance.Brightness(cropped)
            processed = enhancer.enhance(dark_factor)

            ctk_img = ctk.CTkImage(light_image=processed, dark_image=processed, size=(width, height))
            if len(self._image_cache) > 6:
                self._image_cache.clear()
            self._image_cache[cache_key] = ctk_img
            return ctk_img
        except Exception:
            fallback = Image.new("RGB", (width, height), color=(15, 10, 15))
            return ctk.CTkImage(light_image=fallback, dark_image=fallback, size=(width, height))
