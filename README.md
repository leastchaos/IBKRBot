# Gemini Financial Research Bot

## 1. Overview

This project is a sophisticated, automated financial research platform that leverages Google's Gemini for AI-powered analysis. It operates as a robust, 24/7 service that can perform multiple types of research tasks, manage a queue of requests, and deliver detailed reports through Telegram.

The system is designed with a professional-grade architecture, separating concerns into distinct modules for orchestration, browser automation, and notifications. It is built to be resilient, featuring automatic retries for failed tasks and intelligent concurrency management.

## 2. Key Features

* **Multi-Modal Task Handling:** The bot can perform three distinct types of research tasks:
    * **Ad-hoc Research:** Users can request analysis of any company ticker directly through Telegram.
    * **Scheduled Daily Monitoring:** Automatically runs a daily analysis on a predefined list of companies.
    * **Undervalued Stock Screener:** Periodically runs a broad discovery prompt to find and queue potentially undervalued companies for analysis.
* **Intelligent Task Queuing:** All requests are added to a central SQLite database queue. A single worker process picks up tasks, ensuring orderly execution.
* **Concurrent Processing:** The worker can perform up to 2 "Deep Research" tasks in parallel using a multi-tab browser instance, maximizing efficiency.
* **Automated Report Generation & Delivery:**
    * Exports full, detailed reports to Google Docs.
    * Uses the Google Drive API to automatically set public sharing permissions ("anyone with the link") and move reports to a specified folder.
    * Generates a concise, AI-powered summary for each report.
    * Sends a notification to Telegram with the summary and a link to the full Google Doc.
* **Dynamic Watchlist Management:** The list of stocks for daily monitoring can be managed entirely through Telegram commands (`/add`, `/remove`, `/listdaily`).
* **Robust & Resilient:**
    * The system automatically retries tasks that fail due to temporary network or website errors.
    * Runs Chrome in **headless mode**, requiring no visible screen or active desktop session.
    * The worker is designed to run continuously and recover from individual task failures without crashing.

## 3. Architecture Overview

The system is built on a **Producer-Queue-Worker** architecture, which is a standard pattern for building robust, scalable automation systems.

* **Producers:** Scripts that create tasks (e.g., `telegram_bot.py`, `schedule_daily_tasks.py`).
* **Queue:** A central **SQLite database** (`research_queue.db`) that stores all tasks.
* **Worker:** The `worker.py` script is the heart of the application, processing tasks from the queue.

## 5. Setup and Installation

1.  **Clone/Download:** Place the project files in a folder on your Windows machine.

2.  **Install Dependencies:** Open a terminal or command prompt in your project's root directory and run:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up Google Cloud API Credentials:** This is the most complex step. Follow the detailed, step-by-step guide here:
    * **[Google Drive API Setup Guide](docs/GOOGLE_API_SETUP.md)**

4.  **Create Your Configuration File:** Rename `credentials/genai_config.json.template` to `credentials/genai_config.json` and fill in your specific values.

    | Key (`"key": "value"`) | Required? | Description |
    | :--- | :--- | :--- |
    | `user_data_dir` | Yes | Full path to your Chrome User Data folder. |
    | `profile_directory`| Yes | The Chrome profile to use (usually `"Default"`). |
    | `token` | Yes | Your Telegram Bot token from BotFather. |
    | `chat_id` | Yes | The ID for the main channel for all reports. |
    | `folder_id` | Yes | The ID of the Google Drive folder for reports. |

5.  **Initialize the Database:** Run the setup script **once** to create the database file and tables.
    ```bash
    python database/database_setup.py
    ```

## 6. How to Run the System

1.  **Start the Worker:** Open a terminal and run the main worker process. It will run continuously.
    ```bash
    python worker.py
    ```

2.  **Start the Telegram Bot:** Open a **second, separate terminal** and run the bot.
    ```bash
    python telegram_bot.py
    ```

3.  **Schedule the Producer Scripts:** Use **Windows Task Scheduler** to run `schedule_daily_tasks.py` and `schedule_undervalued_scan.py` at your desired daily times.

## 7. Usage: Telegram Bot Commands

* `/start`: Displays a welcome message and lists commands.
* `/research <EXCHANGE:TICKER>`: Requests an immediate analysis.
* `/add <TICKER>`: Adds a company to the daily monitoring list.
* `/remove <TICKER>`: Removes a company from the daily list.
* `/listdaily`: Shows all companies on the daily list.