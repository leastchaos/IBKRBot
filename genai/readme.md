# GenAI Core for Financial Research Bot

## 1\. Overview

This directory, `genai`, contains the core logic for the automated financial research platform. It leverages Google's Gemini for AI-powered analysis, managing a queue of research tasks, and delivering detailed reports. The system is built with a professional-grade architecture, separating concerns into distinct modules for orchestration, browser automation, and notifications. It is designed to be a resilient, 24/7 service with features like automatic retries for failed tasks and intelligent concurrency management.

## 2\. Key Features

  * **Multi-Modal Task Handling**: The bot can perform several distinct types of research tasks, including ad-hoc research, scheduled daily monitoring, and an undervalued stock screener.
  * **Intelligent Task Queuing**: All research requests are managed through a central SQLite database queue, ensuring orderly execution.
  * **Concurrent Processing**: The worker can perform multiple "Deep Research" tasks in parallel using a multi-tab browser instance to maximize efficiency.
  * **Automated Report Generation & Delivery**:
      * Exports detailed reports to Google Docs.
      * Utilizes the Google Drive API for automatic public sharing and folder management.
      * Generates concise, AI-powered summaries for each report.
      * Sends notifications to Telegram with the summary and a link to the full Google Doc.
  * **Dynamic Watchlist Management**: The list of stocks for daily monitoring can be managed entirely through Telegram commands.
  * **Robust & Resilient**: The system is designed for continuous operation, with automatic retries for failed tasks and the ability to recover from individual task failures without crashing.

## 3\. Architecture Overview

The system is built on a **Producer-Queue-Worker** architecture, a standard pattern for robust and scalable automation systems.

  * **Producers**: These are the scripts that create tasks. `telegram_bot.py` and scheduled scripts that trigger daily tasks are examples of producers.
  * **Queue**: A central **SQLite database** (`research_queue.db`) stores all the tasks. The `database/` subdirectory contains the logic for interacting with this queue.
  * **Worker**: The `worker.py` script is the core of the application. It continuously polls the queue for new tasks and processes them.

## 4\. Module Breakdown

  * `worker.py`: The main entry point for the worker process. It manages the task queue, browser instances, and the overall lifecycle of research jobs.
  * `telegram_bot.py`: Handles all user interactions through Telegram, including command parsing and queuing new tasks.
  * `browser_actions.py`: A crucial module that encapsulates all Selenium-based browser automation logic. This includes navigating to Gemini, entering prompts, and extracting responses.
  * `workflows.py`: Defines the high-level steps for each type of research task. It orchestrates the browser actions and other components to execute a complete research workflow.
  * `database/`: Contains all the logic for interacting with the SQLite database, including creating, retrieving, and updating tasks.
  * `helpers/`: A collection of utility functions, including helpers for interacting with the Google Drive API (`google_api_helpers.py`) and for sending notifications (`notifications.py`).
  * `common/`: This subdirectory contains shared modules for configuration (`config.py`), logging (`logging_setup.py`), and general utilities (`utils.py`).
  * `constants.py`: Defines application-wide constants, such as URLs, CSS selectors, and task types.
  * `models.py`: Contains the data models for the application, such as `ResearchJob` and `WorkerState`, which help in maintaining a clean and organized state.
  * `post_processing.py`: This module handles all the tasks that need to be performed after the AI has generated a report. This includes exporting the report to Google Docs, extracting summaries, and sending notifications.
  * `prompts.yml`: A YAML file that stores all the prompts used for the different research tasks. This separation of prompts from the code makes them easier to manage and modify.

## 5\. Workflows

The `workflows.py` module defines several distinct research workflows that can be executed by the worker:

  * **Company Deep Dive**: A comprehensive analysis of a single company.
  * **Tactical Review**: A follow-up analysis on a company that has already been the subject of a deep dive.
  * **Undervalued Screener**: A broad discovery prompt to find and queue potentially undervalued companies for analysis.
  * **Portfolio Review**: A comprehensive analysis of a portfolio of stocks.
  * **Short Company Deep Dive**: A deep dive with a focus on identifying short-selling opportunities.
  * **Buy The Dip**: An analysis of a stock that has recently experienced a significant price drop.
  * **Covered Call Review**: A review of a portfolio to identify opportunities for selling covered calls.

## 6\. Configuration

The application's behavior is primarily configured through the `credentials/genai_config_v2.json` file. This file contains settings for Chrome, Telegram, and Google Drive. The `prompts.yml` file is also a key part of the configuration, as it defines the prompts for the different research tasks.

## 7\. Usage

To run the system, you need to start the worker and the Telegram bot in separate terminals.

1.  **Start the Worker**:
    ```bash
    python -m genai.worker
    ```
2.  **Start the Telegram Bot**:
    ```bash
    python -m genai.telegram_bot
    ```