# config.py

from dataclasses import dataclass
import os
import json


CONFIG_PATH = "credentials/genai_config.json"


@dataclass(frozen=True)
class Settings:
    """A frozen dataclass to hold the configuration for the Selenium Chrome driver."""

    user_data_dir: str
    profile_directory: str
    telegram_token: str
    telegram_chat_id: str
    folder_id: str
    chrome_driver_path: str | None = None
    download_dir: str = os.path.join(os.getcwd(), "downloads")

def get_settings() -> Settings:
    """
    Initializes and returns the Chrome settings.
    This is the single source of truth for your configuration.
    """
    # Using os.path.expanduser("~") is a robust way to get the user's home directory
    # on any operating system (Windows, macOS, or Linux).
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    return Settings(
        user_data_dir=config["user_data_dir"],
        profile_directory=config["profile_directory"],
        chrome_driver_path=config.get("chrome_driver_path", None),
        telegram_token=config["telegram_token"],
        telegram_chat_id=config["telegram_chat_id"],
        folder_id=config["folder_id"],
        download_dir=config.get("download_dir", os.path.join(os.getcwd(), "downloads")),
    )


if __name__ == "__main__":
    settings = get_settings()
    print(settings)
