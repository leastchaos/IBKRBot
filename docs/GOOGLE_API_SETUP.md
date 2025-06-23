# Google Drive API Setup Guide

This guide provides step-by-step instructions on how to create the necessary `credentials.json` file to allow the application to interact with your Google Drive account.

## Phase 1: Google Cloud Project Setup

1.  **Go to the Google Cloud Console:**
    * Open your browser and navigate to: [https://console.cloud.google.com/](https://console.cloud.google.com/)
    * Log in with the Google account you want the bot to use.

2.  **Create a New Project:**
    * At the top of the page, click the project dropdown menu (it might say "Select a project").
    * In the dialog that appears, click **"NEW PROJECT"**.
    * Give your project a name (e.g., `Gemini Automation Bot`) and click **"CREATE"**.
    * Wait for the project to be created, and ensure it is selected in the top dropdown menu.

3.  **Enable the Google Drive API:**
    * Use the search bar at the top of the page and type **"Google Drive API"**.
    * Click on the "Google Drive API" result from the Marketplace.
    * Click the blue **"ENABLE"** button. Wait for the process to complete.

## Phase 2: Configure the OAuth Consent Screen

This screen is what you will see when you grant permission to your own script for the first time.

1.  **Navigate to the Consent Screen:**
    * Using the navigation menu (☰) on the left, go to **APIs & Services > OAuth consent screen**.

2.  **Configure the Screen:**
    * **User Type:** Select **"External"** and click **"CREATE"**.
    * **App Information:**
        * **App name:** Enter a name, e.g., `Gemini Research Worker`.
        * **User support email:** Select your own email address from the dropdown.
        * **Developer contact information:** Scroll to the bottom and enter your own email address again.
    * Click **"SAVE AND CONTINUE"**.
    * **Scopes Page:** You can skip this page completely. Just click **"SAVE AND CONTINUE"**.
    * **Test Users Page:**
        * This is a **critical step** for avoiding a complex app verification process.
        * Click **"+ ADD USERS"**.
        * Enter the same Google email address you are using for this setup.
        * Click **"ADD"**.
    * Click **"SAVE AND CONTINUE"**. You'll see a summary page. You are done here.

## Phase 3: Create and Download the Credentials

This is where you get the actual `credentials.json` file.

1.  **Navigate to Credentials:**
    * Using the navigation menu (☰) on the left, go to **APIs & Services > Credentials**.

2.  **Create New Credentials:**
    * At the top of the page, click **"+ CREATE CREDENTIALS"**.
    * From the dropdown list, select **"OAuth client ID"**.

3.  **Configure the Client ID:**
    * **Application type:** From the dropdown, you **must** select **"Desktop app"**.
    * **Name:** You can leave the default name or call it `Worker Desktop Client`.
    * Click **"CREATE"**.

4.  **Download the JSON File:**
    * A small window will pop up saying "OAuth client created." You can just click **"OK"**.
    * You will now be back on the "Credentials" page. In the "OAuth 2.0 Client IDs" list, find the client you just created.
    * On the far right of that row, click the **download icon (↓)**.
    * This will download a JSON file with a name like `client_secret_...json`.

## Phase 4: Final Project Steps

1.  **Rename and Place the File:**
    * Find the file you just downloaded.
    * Rename it to exactly **`credentials.json`**.
    * Place this file inside the `credentials/` folder in your project directory.

2.  **Delete the Old Token (If it Exists):**
    * Before you run the application for the first time with new credentials, go into your `credentials/` folder.
    * If you see a file named `token.json`, **delete it**.
    * This forces the script to re-run the entire authentication process from the beginning using your new `credentials.json` file.

3.  **Run the Application to Authenticate:**
    * Run `worker.py` or any script that calls `get_drive_service()`.
    * A new browser window will automatically open, asking you to log in and grant the permissions for the app you configured.
    * Follow the login steps and click "Allow". This will only happen once.
    * After you approve, the browser tab will close itself, a new `token.json` file will be created in your `credentials` folder, and your script will proceed.