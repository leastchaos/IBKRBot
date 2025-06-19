import logging
import os
from typing import Any

# --- Google API Imports ---
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

# --- Constants ---
SCOPES = ["https://www.googleapis.com/auth/drive"]
TOKEN_PATH = "credentials/token.json"
CREDENTIALS_PATH = "credentials/google_oauth_cred.json"


def get_drive_service() -> Resource | None:
    """
    Authenticates with the user's Google Account and returns a Drive API service object.
    On the first run, this will open a browser window for user consent.

    Returns:
        An authorized Google Drive API service object (Resource), or None if authentication fails.
    """
    creds: Credentials | None = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logging.error(f"Could not refresh token: {e}. Please re-authenticate.")
                if os.path.exists(TOKEN_PATH):
                    os.remove(TOKEN_PATH)
                creds = None
        
        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            except FileNotFoundError:
                logging.error(f"❌ FATAL ERROR: Credentials file not found at '{CREDENTIALS_PATH}'.")
                logging.error("   Please download it from the Google Cloud Console for your OAuth 2.0 Client ID.")
                return None

        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)


def move_file_to_folder(service: Resource, doc_id: str, folder_id: str) -> bool:
    """
    Moves a file to a specific folder in Google Drive using an existing service object.

    Args:
        service: An authorized Google Drive API service object.
        doc_id: The ID of the file to move.
        folder_id: The ID of the destination folder.

    Returns:
        True if the file was moved successfully, False otherwise.
    """
    logging.info(f"Attempting to move doc ID: {doc_id} to folder ID: {folder_id}...")
    try:
        # Retrieve the file to get its original parents
        file: dict[str, Any] = service.files().get(fileId=doc_id, fields='parents').execute()
        # Use .get(key, []) for safety in case 'parents' key is missing
        previous_parents = ",".join(file.get('parents', []))
        
        service.files().update(
            fileId=doc_id, 
            addParents=folder_id, 
            removeParents=previous_parents, 
            fields='id, parents'
        ).execute()
        
        logging.info("✅ File moved successfully to the designated reports folder.")
        return True
    except HttpError as error:
        logging.exception(f"❌ An error occurred while moving the file: {error}")
        return False


def share_google_doc_publicly(service: Resource, doc_id: str) -> bool:
    """
    Sets the permission of a file to "anyone with the link can view" using an existing service object.

    Args:
        service: An authorized Google Drive API service object.
        doc_id: The ID of the Google Drive file.

    Returns:
        True if permissions were updated successfully, False otherwise.
    """
    logging.info(f"Attempting to set public read permissions for doc ID: {doc_id}...")
    try:
        permission: dict[str, str] = {'type': 'anyone', 'role': 'reader'}
        service.permissions().create(fileId=doc_id, body=permission, fields='id').execute()
        
        logging.info("✅ Permissions updated successfully. Anyone with the link can now view.")
        return True
    except HttpError as error:
        logging.exception(f"❌ An error occurred while setting permissions: {error}")
        return False


def get_doc_id_from_url(url: str) -> str | None:
    """
    Extracts the document ID from a Google Drive document URL.

    Args:
        url: The URL of the Google Drive document.

    Returns:
        The document ID if extracted successfully, None otherwise.
    """
    try:
        return url.split('/d/')[1].split('/')[0]
    except IndexError:
        logging.exception(f"Could not extract Document ID from URL: {url}")
        return None


if __name__ == "__main__":
    # This block demonstrates the new, more robust, and efficient way to use the functions.
    
    # 1. Get the service object ONCE.
    logging.info("Authenticating and getting Google Drive service...")
    drive_service = get_drive_service()
    
    # 2. Only proceed if authentication was successful.
    if drive_service:
        logging.info("Authentication successful.")
        
        # NOTE: You must get your folder ID from your config object.
        # This is just an example.
        from genai.config import get_settings
        config = get_settings()
        reports_folder_id = config.folder_id

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
            logging.warning("Halting process for this URL because Document ID could not be determined.")
    else:
        logging.warning("Halting execution because Google Drive service could not be initialized.")