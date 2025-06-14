# config.py

from dataclasses import dataclass
import os
import json


CONFIG_PATH = "credentials/genai_chrome_config.json"


@dataclass(frozen=True)
class ChromeSettings:
    """A frozen dataclass to hold the configuration for the Selenium Chrome driver."""

    user_data_dir: str
    profile_directory: str
    chrome_driver_path: str | None = None
    download_dir: str | None = None


def get_settings() -> ChromeSettings:
    """
    Initializes and returns the Chrome settings.
    This is the single source of truth for your configuration.
    """
    # Using os.path.expanduser("~") is a robust way to get the user's home directory
    # on any operating system (Windows, macOS, or Linux).
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    user_home_dir = os.path.expanduser("~")

    # --- EDIT THE PATH FOR YOUR OPERATING SYSTEM BELOW ---

    # For Windows:
    user_data_path = config.get(
        "user_data_dir",
        os.path.join(
            user_home_dir, "AppData", "Local", "Google", "Chrome", "User Data"
        ),
    )
    profile_dir = config.get(
        "profile_directory",
        os.path.join(
            user_home_dir,
            "AppData",
            "Local",
            "Google",
            "Chrome",
            "User Data",
            "Default",
        ),
    )
    chrome_driver_path = config.get("chrome_driver_path", None)
    download_dir = config.get("download_dir", os.path.join(os.getcwd(), "downloads"))

    if not os.path.exists(user_data_path):
        os.makedirs(user_data_path)
    return ChromeSettings(
        user_data_dir=user_data_path,
        profile_directory=profile_dir,
        chrome_driver_path=chrome_driver_path,
        download_dir=download_dir,
    )


if __name__ == "__main__":
    settings = get_settings()
    print(settings)
