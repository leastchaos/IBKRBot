# config.py

from dataclasses import dataclass, fields
import os
import json
from typing import Any, Optional

CONFIG_PATH = os.path.join(os.getcwd(), "credentials", "genai_config.json")

@dataclass(frozen=True)
class ChromeSettings:
    user_data_dir: str
    profile_directory: str
    chrome_driver_path: Optional[str] = None
    download_dir: Optional[str] = None

@dataclass(frozen=True)
class TelegramSettings:
    token: str
    chat_id: str

@dataclass(frozen=True)
class DriveSettings:
    folder_id: Optional[str] = None

@dataclass(frozen=True)
class Settings:
    chrome: ChromeSettings
    telegram: Optional[TelegramSettings]
    drive: Optional[DriveSettings]

    @classmethod
    def from_file(cls, path: str = CONFIG_PATH) -> "Settings":
        """
        Loads settings from a nested JSON file, applying defaults for any missing keys.
        """
        try:
            with open(path, "r") as f:
                user_config = json.load(f)
        except FileNotFoundError:
            user_config = {}
            print(f"Warning: Config file not found at {path}. Using default settings.")

        # --- Process Chrome Settings ---
        user_chrome_settings = user_config.get("chrome", {})
        default_chrome_settings = {
            "user_data_dir": os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "User Data"),
            "profile_directory": "Default",
            "chrome_driver_path": None,
            "download_dir": os.path.join(os.getcwd(), "downloads")
        }
        # User settings override defaults
        final_chrome_config = default_chrome_settings | user_chrome_settings
        chrome_settings = ChromeSettings(**final_chrome_config)


        # --- Process Telegram Settings ---
        telegram_settings = None
        user_telegram_settings = user_config.get("telegram")
        if user_telegram_settings and "token" in user_telegram_settings and "chat_id" in user_telegram_settings:
            telegram_settings = TelegramSettings(**user_telegram_settings)
        else:
            print("Warning: Telegram configuration not found or incomplete. Telegram features will be disabled.")


        # --- Process Drive Settings ---
        drive_settings = None
        user_drive_settings = user_config.get("drive")
        if user_drive_settings:
            drive_settings = DriveSettings(**user_drive_settings)


        # --- Compose the final Settings object ---
        return cls(
            chrome=chrome_settings,
            telegram=telegram_settings,
            drive=drive_settings
        )

# Maintain this function for compatibility with your other scripts
def get_settings() -> Settings:
    """Convenience function to load settings using the class method."""
    return Settings.from_file()

if __name__ == "__main__":
    # This test will now correctly load and print your settings
    settings = get_settings()
    
    print("--- Loaded Settings ---")
    print(f"Chrome Settings : {settings.chrome}")
    print(f"Telegram Settings : {settings.telegram}")
    print(f"Drive Settings : {settings.drive}")