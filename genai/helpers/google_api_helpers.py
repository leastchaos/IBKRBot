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
from google.auth.external_account_authorized_user import Credentials as ExternalAccountCredentials
# --- Internal imports ---
from genai.constants import GDRIVE_SCOPES


def _load_or_refresh_credentials(account_name: str) -> Credentials | ExternalAccountCredentials | None:
    """
    Private helper to handle loading, refreshing, or creating credentials
    for a specific account.
    """
    # --- MODIFIED: Create a unique token path for each account ---
    token_path = os.path.join(os.getcwd(), "credentials", f"{account_name}_token.json")
    account_specific_creds_path = os.path.join(
        os.getcwd(), "credentials", f"{account_name}_credentials.json"
    )
    if not os.path.exists(account_specific_creds_path):
        logging.error(
            f"Credentials file for account '{account_name}' does not exist: {account_specific_creds_path}"
        )
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

    # Save the new or refreshed token to the account-specific file
    with open(token_path, "w") as token:
        token.write(creds.to_json())
    logging.info(f"Google API credentials saved for account '{account_name}'.")
    return creds


def get_drive_service(account_name: str) -> Resource | None:
    """
    Authenticates with the Google Drive API for a specific account.
    """
    try:
        # --- MODIFIED: Pass the account name down ---
        logging.info(f"Authenticating Google Drive service for account: {account_name}")
        creds = _load_or_refresh_credentials(account_name)
        if not creds:
            raise RuntimeError(f"Failed to obtain valid credentials for {account_name}.")
        return build("drive", "v3", credentials=creds)
    except Exception:
        logging.error(
            f"An unexpected error occurred during Google Drive authentication for {account_name}.",
            exc_info=True,
        )
        return None


def rename_google_doc(service: Resource, doc_id: str, new_title: str) -> bool:
    """Renames a Google Drive file."""
    logging.info(f"Renaming doc {doc_id} to '{new_title}'...")
    try:
        body = {"name": new_title}
        service.files().update(fileId=doc_id, body=body, fields="id, name").execute()
        logging.info("✅ File renamed successfully.")
        return True
    except HttpError as error:
        logging.error(
            f"❌ An API error occurred while renaming the file.", exc_info=True
        )
        return False


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

def get_google_doc_content(service: Resource, document_id: str) -> str | None:
    """
    Fetches the content of a Google Doc by exporting it as plain text.

    Args:
        service: The authenticated Google Drive API service instance.
        document_id: The ID of the Google Document.

    Returns:
        The text content of the document, or None if an error occurs.
    """
    try:
        logging.info(f"Fetching content for Google Doc ID: {document_id}")
        # Request the document to be exported as plain text
        request = service.files().export_media(fileId=document_id, mimeType="text/plain")
        
        # Execute the request and get the content
        response = request.execute()
        
        # The content is in bytes, so decode it to a string
        content = response.decode('utf-8')
        logging.info(f"Successfully fetched and decoded content for Doc ID: {document_id}")
        return content
    except Exception as e:
        logging.error(f"Failed to get content for Google Doc ID {document_id}: {e}", exc_info=True)
        return "Failed to fetch content from the Google Doc. Please check the document ID or your permissions."

if __name__ == "__main__":
    # This block demonstrates a more robust and linear way to use the functions.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    # 1. Get the service object ONCE.
    logging.info("Authenticating and getting Google Drive service...")
    drive_service = get_drive_service("leastchaos")

    # 2. Guard clause: Only proceed if authentication was successful.
    if not drive_service:
        logging.warning(
            "Halting execution because Google Drive service could not be initialized."
        )
        # In a real script, you might use 'sys.exit(1)' here.
        # For this example, we'll just return to stop execution of this block.
        # import sys; sys.exit(1)
        # For now, just return
        # return

    logging.info("Authentication successful.")

    from genai.common.config import get_settings

    config = get_settings()
    reports_folder_id = config.drive.folder_id

    test_url = "https://docs.google.com/document/d/1vjMHr4Kn9Ki_eJ2T19SOMADICEo_uVtmY9r08dkFTlo/edit"

    logging.info(f"\nProcessing URL: {test_url}")
    doc_id = get_doc_id_from_url(test_url)

    # 3. Guard clause: Only proceed if the document ID is valid.
    if not doc_id:
        logging.warning(
            "Halting process for this URL because Document ID could not be determined."
        )
        # return

    logging.info(f"Extracted Document ID: {doc_id}")
    # 4. Fetch the content of the document.
    content = get_google_doc_content(drive_service, doc_id)

    # 5. Guard clause: Only proceed if content was successfully fetched.
    if not content:
        logging.warning(
            "Halting process for this URL because content could not be fetched."
        )
        # return
    logging.info(f"Content fetched successfully for Doc ID: {doc_id}")
    print(f"Document Content:\n{content[:500]}...")  # Print first 500 chars
    # # 4. Chain the operations, using guard clauses to ensure robustness.
    # # First, try to move the file if a folder ID is provided.
    # if reports_folder_id:
    #     if not move_file_to_folder(drive_service, doc_id, reports_folder_id):
    #         logging.error(f"Failed to move file {doc_id}, will not proceed with sharing.")
    #         # return  # Stop here if move fails

    # # If we are here, either move was successful or not required. Proceed to share.
    # share_google_doc_publicly(drive_service, doc_id)


