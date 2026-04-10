# AI Job Agent - Chrome Extension

One-click job bookmarking with AI-powered job search agent integration.

## Features

- **Job Bookmarking** - Save any job posting from any website with one click
- **Auto-Detection** - Automatically detects job listings on LinkedIn, Indeed, Glassdoor, Greenhouse, Lever, and Workday
- **Quick View** - Popup showing saved jobs with status tracking (saved, applied, interview, offer, rejected)
- **Backend Sync** - Pushes saved jobs to the AI Job Agent API for smart analysis and tracking
- **Dark/Light Mode** - Modern UI with theme support

## Supported Job Boards

| Site | Auto-detect | Data Extracted |
|------|-------------|----------------|
| LinkedIn | Yes | Title, company, location, description, salary, posted date |
| Indeed | Yes | Title, company, location, description, salary, posted date |
| Glassdoor | Yes | Title, company, location, description, salary |
| Greenhouse | Yes | Title, company, location, description |
| Lever | Yes | Title, company, location, description |
| Workday | Yes | Title, company, location, description, posted date |

## Installation

### Load Unpacked (Development)

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right)
3. Click **Load unpacked**
4. Select the `chrome-extension` directory
5. The extension icon should appear in your toolbar

### Generate Icons

Before loading, generate the icon PNG files using one of these methods:

```bash
# Option 1: Python
cd chrome-extension
python generate_icons.py

# Option 2: Node.js
cd chrome-extension
node generate_icons.js

# Option 3: Browser
# Open chrome-extension/generate_icons.html in a browser,
# click "Download All Icons", and save them to the icons/ directory.
```

## Usage

1. **Browse job listings** on any supported site
2. A floating **"Save to JobAgent"** button appears on job posting pages
3. Click it to save the job, or use the **popup** to save the current page
4. View and manage saved jobs in the popup
5. Click the **sync** button to push jobs to the backend API

## Configuration

Click the **gear icon** in the popup or go to the extension's options page:

- **API URL** - Backend server address (default: `http://localhost:8000`)
- **Auto-Detect** - Toggle the floating save button on job sites
- **Sync Interval** - How often to auto-sync with backend (5-120 minutes)
- **Theme** - Dark or Light mode
- **Export/Clear** - Export bookmarks as JSON or clear all data

## Backend Requirements

The extension communicates with the AI Job Agent FastAPI backend. Make sure it is running:

```bash
cd ..
uvicorn api:app --reload --port 8000
```

The extension uses these API endpoints:
- `POST /api/session` - Create a session
- `POST /api/chat` - Sync bookmarked jobs
- `GET /api/health` - Check backend status

## File Structure

```
chrome-extension/
  manifest.json          - Manifest V3 configuration
  package.json           - Build tooling config
  generate_icons.py      - Icon generation script
  icons/                 - Extension icons (16, 48, 128px)
  src/
    popup/               - Extension popup UI
    content/             - Content script for job detection
    background/          - Service worker for sync
    options/             - Settings page
    utils/               - Shared utilities (API client, storage, extractors)
```
