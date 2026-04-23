# Yazio Insights Exporter & Dashboard

A comprehensive tool to export your full Yazio history into a local SQLite database and visualize it through a web dashboard. It supports standard product logs, AI-generated "Smart Food" entries, and detailed macro tracking.

## Features

- **Auto-Discovery**: Automatically finds all historical dates with data in your Yazio account.
- **Full Macro Tracking**: Tracks Calories, Protein, Carbs, and Fat (Total and per-dish).
- **AI Entry Support**: Correctly resolves and labels items logged via Yazio's AI feature.
- **SQLite Storage**: Saves everything locally for permanent access and fast retrieval.
- **Dashboard**:
  - **Overview**: Daily charts for Energy, Steps, Water, and Macros against your goals.
  - **Analysis**: Historical table showing Actual vs. Goal ratios for every day.
  - **Journal**: A categorized daily food log with per-item macro breakdowns.
- **LLM-Ready Export**: One-click CSV export of your entire food history, optimized for analysis by LLMs.

## Prerequisites

- Python 3.x
- `uv` (recommended) or `pip`

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
# OR if using uv
uv pip install -r requirements.txt
```

### 2. Configure Credentials

Copy the example environment file and enter your Yazio login details:

```bash
cp .env.example .env
```

Edit `.env` and fill in:

- `YAZIO_EMAIL`
- `YAZIO_PASSWORD`

## Usage Guide

### Step 1: Export Data from Yazio

Run the main exporter script to fetch your history and build the SQLite database.

```bash
uv run yazio_export.py
```

_This will create `yazio_data.db`._

### Step 2: Prepare Dashboard Data

Extract the database content into a JSON format for the web interface:

```bash
python export_dashboard_data.py
```

_This will create `dashboard_data.json`._

### Step 3: Launch the Dashboard

Start a local web server to view your insights:

```bash
python -m http.server 8000
```

Open your browser and navigate to:
**`http://localhost:8000`**

## Technical Details

- **Backend**: Python with `requests` for API interaction and `sqlite3` for storage.
- **Frontend**: Tailwind CSS and Chart.js for visualizations.
- **API**: Uses Yazio's internal mobile API (v15). Standard product macros are fetched and cached locally to ensure accuracy.
