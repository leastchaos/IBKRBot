import logging
import os
import re

# --- Third-party imports ---
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

# --- Internal imports ---
from genai.constants import GDRIVE_SCOPES, GDRIVE_TOKEN_PATH, GDRIVE_CREDENTIALS_PATH


def _load_or_refresh_credentials() -> Credentials | None:
    """
    Private helper to handle the logic of loading, refreshing, or creating credentials.
    This function contains the nested logic and returns a valid credential object or None.
    """
    creds = None
    # 1. Try to load existing token
    if os.path.exists(GDRIVE_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GDRIVE_TOKEN_PATH, GDRIVE_SCOPES)

    # 2. If credentials are valid, we're done. Return early.
    if creds and creds.valid:
        return creds

    # 3. If credentials have expired, refresh them.
    if creds and creds.expired and creds.refresh_token:
        logging.info("Refreshing expired Google API credentials...")
        creds.refresh(Request())
        # After refreshing, save the new token and return
        with open(GDRIVE_TOKEN_PATH, "w") as token:
            token.write(creds.to_json())
        logging.info("Google API credentials refreshed and saved.")
        return creds

    # 4. If we get here, we need to perform the full, first-time authentication.
    logging.info("Performing first-time authentication for Google Drive API...")
    flow = InstalledAppFlow.from_client_secrets_file(
        GDRIVE_CREDENTIALS_PATH, GDRIVE_SCOPES
    )
    creds = flow.run_local_server(port=0)
    # Save the new credentials for the next run
    with open(GDRIVE_TOKEN_PATH, "w") as token:
        token.write(creds.to_json())
    logging.info("Google API credentials created and saved.")
    return creds


def get_drive_service() -> Resource | None:
    """
    Authenticates with the Google Drive API. This is the main public function.
    It's now simpler, delegating the complex credential logic to a helper.
    """
    try:
        creds = _load_or_refresh_credentials()
        # Guard clause: If we couldn't get credentials, we can't proceed.
        if not creds:
            raise RuntimeError("Failed to obtain valid Google API credentials.")

        return build("drive", "v3", credentials=creds)

    except FileNotFoundError:
        logging.error(
            f"FATAL: Google Drive credentials file not found at '{GDRIVE_CREDENTIALS_PATH}'."
        )
        logging.error(
            "Please ensure you have set up Google Cloud API access and placed the file correctly."
        )
        return None
    except Exception as e:
        logging.error(
            "An unexpected error occurred during Google Drive authentication.",
            exc_info=True,
        )
        return None


def share_google_doc_publicly(service: Resource, doc_id: str) -> bool:
    """Sets a Google Drive file's permission to "anyone with the link can view"."""
    logging.info(f"Setting public 'viewer' permissions for doc ID: {doc_id}...")
    try:
        permission = {"type": "anyone", "role": "reader"}
        service.permissions().create(
            fileId=doc_id, body=permission, fields="id"
        ).execute()
        logging.info(
            "✅ Permissions updated successfully. Anyone with the link can now view."
        )
        return True
    except HttpError as error:
        logging.error(
            f"❌ An API error occurred while setting permissions.", exc_info=True
        )
        return False


def move_file_to_folder(service: Resource, file_id: str, folder_id: str) -> bool:
    """Moves a file to a specific folder in Google Drive."""
    logging.info(f"Moving file {file_id} to folder {folder_id}...")
    try:
        file = service.files().get(fileId=file_id, fields="parents").execute()
        previous_parents = ",".join(file.get("parents", []))

        service.files().update(
            fileId=file_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields="id, parents",
        ).execute()
        logging.info("✅ File moved successfully.")
        return True
    except HttpError as error:
        logging.error(f"❌ An API error occurred while moving the file.", exc_info=True)
        return False


def get_doc_id_from_url(url: str) -> str | None:
    """Extracts the Google Doc ID from a URL using a regular expression."""
    if not isinstance(url, str):
        return None
    # This regex looks for the string of characters between /d/ and the next /
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    if match:
        return match.group(1)
    logging.warning(f"Could not extract a valid document ID from URL: {url}")
    return None


if __name__ == "__main__":
    # This block demonstrates the new, more robust, and efficient way to use the functions.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    # 1. Get the service object ONCE.
    logging.info("Authenticating and getting Google Drive service...")
    drive_service = get_drive_service()

    # 2. Only proceed if authentication was successful.
    if drive_service:
        logging.info("Authentication successful.")

        # NOTE: You must get your folder ID from your config object.
        # This is just an example.
        from genai.helpers.config import get_settings

        config = get_settings()
        reports_folder_id = config.drive.folder_id

        test_url = "https://docs.google.com/document/d/1vjMHr4Kn9Ki_eJ2T19SOMADICEo_uVtmY9r08dkFTlo/edit"

        logging.info(f"\nProcessing URL: {test_url}")
        doc_id = get_doc_id_from_url(test_url)

        # 3. Only proceed if the document ID is valid.
        if doc_id:
            logging.info(f"Extracted Document ID: {doc_id}")

            # 4. Chain the operations, checking for success at each step.
            if move_file_to_folder(drive_service, doc_id, reports_folder_id):
                share_google_doc_publicly(drive_service, doc_id)
        else:
            logging.warning(
                "Halting process for this URL because Document ID could not be determined."
            )
    else:
        logging.warning(
            "Halting execution because Google Drive service could not be initialized."
        )
