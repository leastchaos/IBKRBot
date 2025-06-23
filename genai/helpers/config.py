import logging
import os
import json
from dataclasses import dataclass

# The path to your configuration file
CONFIG_PATH = os.path.join(os.getcwd(), "credentials", "genai_config.json")


@dataclass(frozen=True)
class ChromeSettings:
    """Configuration specific to the Selenium Chrome driver."""
    user_data_dir: str
    profile_directory: str
    chrome_driver_path: str | None = None
    download_dir: str | None = None


@dataclass(frozen=True)
class TelegramSettings:
    """Configuration for Telegram notifications."""
    token: str
    chat_id: str
    admin_id: str


@dataclass(frozen=True)
class DriveSettings:
    """Configuration for Google Drive integration."""
    folder_id: str | None = None


@dataclass(frozen=True)
class Settings:
    """The main, top-level configuration class."""
    chrome: ChromeSettings
    telegram: TelegramSettings
    drive: DriveSettings

    @classmethod
    def from_file(cls, path: str = CONFIG_PATH) -> "Settings":
        """
        Loads settings from a nested JSON file, applying defaults and
        enforcing that required sections exist.
        """
        try:
            with open(path, "r") as f:
                user_config = json.load(f)
        except FileNotFoundError:
            logging.error(f"FATAL: Configuration file not found at {path}. The application cannot start.")
            raise

        # Check for all required top-level keys in the JSON
        required_sections = ["chrome", "telegram", "drive"]
        for section in required_sections:
            if section not in user_config:
                logging.error(f"FATAL: Missing required section '{section}' in config file.")
                raise ValueError(f"Missing required section '{section}' in {path}")

        # --- Process Chrome Settings ---
        user_chrome_settings = user_config.get("chrome", {})
        
        # Define the default path directly for a Windows environment.
        default_chrome_settings = {
            "user_data_dir": os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "User Data"),
            "profile_directory": "Default",
            "chrome_driver_path": None,
            "download_dir": os.path.join(os.getcwd(), "downloads")
        }
        # User-provided settings will override the defaults
        final_chrome_config = default_chrome_settings | user_chrome_settings
        chrome_settings = ChromeSettings(**final_chrome_config)

        # --- Process mandatory settings ---
        telegram_settings = TelegramSettings(**user_config["telegram"])
        drive_settings = DriveSettings(**user_config["drive"])

        # --- Compose the final Settings object ---
        return cls(
            chrome=chrome_settings,
            telegram=telegram_settings,
            drive=drive_settings
        )


def get_settings() -> Settings:
    """A simple convenience function to load the application settings."""
    return Settings.from_file()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    try:
        settings = get_settings()
        print("\n--- ✅ Configuration Loaded Successfully ---")
        print(f"Chrome Settings : {settings.chrome}")
        print(f"Telegram Settings : {settings.telegram}")
        print(f"Drive Settings : {settings.drive}")
    except (FileNotFoundError, ValueError, TypeError) as e:
        print(f"\n--- ❌ Failed to load configuration ---")
        print(e)