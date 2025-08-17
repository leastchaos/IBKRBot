# genai/helpers/google_api_helpers.py
import logging
import os
import re

# --- Third-party imports ---
from google.auth import exceptions
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from google.auth.external_account_authorized_user import \
    Credentials as ExternalAccountCredentials
# --- Internal imports ---
from genai.constants import GDRIVE_SCOPES


def _load_or_refresh_credentials(account_name: str) -> Credentials | ExternalAccountCredentials | None:
    """
    Private helper to handle loading, refreshing, or creating credentials
    for a specific account.
    """
    token_path = os.path.join(os.getcwd(), "credentials", f"{account_name}_token.json")
    account_specific_creds_path = os.path.join(
        os.getcwd(), "credentials", f"{account_name}_credentials.json"
    )
    if not os.path.exists(account_specific_creds_path):
        logging.error(f"Credentials file for account '{account_name}' not found.")
        return None
    
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, GDRIVE_SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except exceptions.RefreshError:
            if os.path.exists(token_path):
                os.remove(token_path)
            creds = None # Force re-authentication

    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(
            account_specific_creds_path, GDRIVE_SCOPES
        )
        creds = flow.run_local_server(port=0)

    with open(token_path, "w") as token:
        token.write(creds.to_json())
    logging.info(f"Google API credentials saved for account '{account_name}'.")
    return creds


def get_drive_service(account_name: str) -> Resource | None:
    """Authenticates with the Google Drive API for a specific account."""
    try:
        logging.info(f"Authenticating Google Drive service for account: {account_name}")
        creds = _load_or_refresh_credentials(account_name)
        if not creds:
            raise RuntimeError(f"Failed to obtain valid credentials for {account_name}.")
        return build("drive", "v3", credentials=creds)
    except Exception:
        logging.error(f"Error during Google Drive authentication for {account_name}.", exc_info=True)
        return None


def rename_google_doc(service: Resource, doc_id: str, new_title: str) -> bool:
    """Renames a Google Drive file."""
    logging.info(f"Renaming doc {doc_id} to '{new_title}'...")
    try:
        body = {"name": new_title}
        service.files().update(fileId=doc_id, body=body, fields="id, name").execute() # type: ignore
        logging.info("✅ File renamed successfully.")
        return True
    except HttpError:
        logging.error(f"❌ An API error occurred while renaming the file.", exc_info=True)
        return False


def share_google_doc_publicly(service: Resource, doc_id: str) -> bool:
    """Sets a Google Drive file's permission to "anyone with the link can view"."""
    logging.info(f"Setting public 'viewer' permissions for doc ID: {doc_id}...")
    try:
        permission = {"type": "anyone", "role": "reader"}
        service.permissions().create(fileId=doc_id, body=permission, fields="id").execute() # type: ignore
        logging.info("✅ Permissions updated successfully.")
        return True
    except HttpError:
        logging.error(f"❌ An API error occurred while setting permissions.", exc_info=True)
        return False


def move_file_to_folder(service: Resource, file_id: str, folder_id: str) -> bool:
    """Moves a file to a specific folder in Google Drive."""
    logging.info(f"Moving file {file_id} to folder {folder_id}...")
    try:
        file = service.files().get(fileId=file_id, fields="parents").execute() # type: ignore
        previous_parents = ",".join(file.get("parents", []))

        service.files().update( # type: ignore
            fileId=file_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields="id, parents",
        ).execute()
        logging.info("✅ File moved successfully.")
        return True
    except HttpError:
        logging.error(f"❌ An API error occurred while moving the file.", exc_info=True)
        return False


def get_doc_id_from_url(url: str) -> str | None:
    """Extracts the Google Doc ID from a URL using a regular expression."""
    if not isinstance(url, str):
        return None
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    if match:
        return match.group(1)
    logging.warning(f"Could not extract a valid document ID from URL: {url}")
    return None

def get_google_doc_content(service: Resource, document_id: str) -> str | None:
    """Fetches the content of a Google Doc by exporting it as plain text."""
    try:
        logging.info(f"Fetching content for Google Doc ID: {document_id}")
        request = service.files().export_media(fileId=document_id, mimeType="text/plain") # type: ignore
        
        response = request.execute()
        
        content = response.decode('utf-8')
        logging.info(f"Successfully fetched content for Doc ID: {document_id}")
        return content
    except Exception:
        logging.error(f"Failed to get content for Google Doc ID {document_id}", exc_info=True)
        return None


if __name__ == "__main__":
    # This block is for testing purposes.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    logging.info("Authenticating and getting Google Drive service...")
    drive_service = get_drive_service("leastchaos")

    # --- FIX: Add guard clauses to handle None values ---
    if not drive_service:
        logging.critical("Halting execution: Google Drive service could not be initialized.")
    else:
        logging.info("Authentication successful.")
        
        # This import is only needed for the test block
        from genai.common.config import get_settings

        config = get_settings()
        # --- FIX: Safely access drive settings ---
        reports_folder_id = config.drive.folder_id if config.drive else None

        test_url = "https://docs.google.com/document/d/1vjMHr4Kn9Ki_eJ2T19SOMADICEo_uVtmY9r08dkFTlo/edit"
        logging.info(f"\nProcessing URL: {test_url}")
        doc_id = get_doc_id_from_url(test_url)

        if not doc_id:
            logging.warning("Halting process: Document ID could not be determined.")
        else:
            logging.info(f"Extracted Document ID: {doc_id}")
            content = get_google_doc_content(drive_service, doc_id)

            if not content:
                logging.warning("Halting process: content could not be fetched.")
            else:
                logging.info(f"Content fetched successfully for Doc ID: {doc_id} \n{content[:100]}...")  # Print first 100 chars