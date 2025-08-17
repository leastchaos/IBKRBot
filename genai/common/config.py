# common/config.py
import logging
import os
import json
from dataclasses import dataclass
import yaml
from yaml.loader import SafeLoader

# The path to your configuration file, now defined centrally
CONFIG_PATH = os.path.join(os.getcwd(), "credentials", "genai_config_v2.json")

# The path to your prompts file
PROMPTS_PATH = os.path.join(os.getcwd(), "genai", "prompts.yml")


def load_prompts() -> dict[str, str]:
    """Loads and returns the prompts from the prompts.yml file."""
    try:
        with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
            return yaml.load(f, Loader=SafeLoader)
    except FileNotFoundError:
        logging.error(f"FATAL: Prompts file not found at {PROMPTS_PATH}.")
        return {}
    except yaml.YAMLError as e:
        logging.error(f"FATAL: Error parsing prompts.yml file: {e}")
        return {}


@dataclass(frozen=True)
class GeminiAccount:
    """Represents a single Gemini account profile."""
    name: str
    profile_directory: str
    user_data_dir: str
    max_concurrent_jobs: int = 1


@dataclass(frozen=True)
class ChromeSettings:
    """Configuration specific to the Selenium Chrome driver."""
    accounts: list[GeminiAccount]
    download_dir: str
    chrome_driver_path: str | None = None


@dataclass(frozen=True)
class TelegramSettings:
    """Configuration for Telegram notifications."""
    token: str
    chat_id: str
    admin_id: str


@dataclass(frozen=True)
class DriveSettings:
    """Configuration for Google Drive integration."""
    portfolio_sheet_url: str
    folder_id: str | None = None


@dataclass(frozen=True)
class Settings:
    """The main, top-level configuration class."""
    chrome: ChromeSettings
    telegram: TelegramSettings
    drive: DriveSettings

    @classmethod
    def from_file(cls, path: str = CONFIG_PATH) -> "Settings":
        """Loads settings from a JSON file."""
        try:
            with open(path, "r") as f:
                user_config = json.load(f)
        except FileNotFoundError:
            logging.error(f"FATAL: Configuration file not found at {path}.")
            raise

        required_sections = ["chrome", "telegram", "drive"]
        for section in required_sections:
            if section not in user_config:
                raise ValueError(f"Missing required section '{section}' in {path}")

        # --- Process Chrome Settings ---
        user_chrome_config = user_config["chrome"]
        
        # 1. Create the list of GeminiAccount objects from the raw data
        accounts_data = user_chrome_config.get("accounts", [])
        accounts_list = [GeminiAccount(**acc_data) for acc_data in accounts_data]

        # 2. *** THE FIX: Remove the raw 'accounts' data before unpacking ***
        if 'accounts' in user_chrome_config:
            del user_chrome_config['accounts']

        # 3. Now, instantiate ChromeSettings safely with no conflicts
        chrome_settings = ChromeSettings(
            accounts=accounts_list,
            **user_chrome_config
        )
        
        telegram_settings = TelegramSettings(**user_config["telegram"])
        drive_settings = DriveSettings(**user_config["drive"])

        return cls(
            chrome=chrome_settings,
            telegram=telegram_settings,
            drive=drive_settings,
        )


def get_settings() -> Settings:
    """A simple convenience function to load the application settings."""
    return Settings.from_file()