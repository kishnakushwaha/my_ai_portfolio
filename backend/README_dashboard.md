# AI Portfolio Dashboard (CMS)

This is your private backend to manage your portfolio website.

## 🚀 How to Run

1.  Open your terminal.
2.  Run the following command from your project root:
    ```bash
    streamlit run backend/dashboard.py
    ```
3.  A browser window will open (usually at `http://localhost:8501`).

## 🛠️ Features

### 1. Manage Articles & Projects
*   **Public (Green)**: Visible on the website.
*   **Unlisted (Yellow)**: Hidden from lists/search, but the link still works (good for sharing quietly).
*   **Drafts (Red)**: Moved to `backend/drafts/`. Completely private and safe on your computer.

### 2. Homepage Sections
*   Toggle entire sections like "Guided Projects" or "Latest Articles" on/off with one click.

### 3. Write New Content
*   Create new articles by typing in Markdown.
*   The system auto-generates the HTML and saves it as a draft.

### 4. Deploy & Backup
*   **Backup**: Click "Backup Data" to zip all your private drafts to `backend/backups/`.
*   **Deploy**: Click "Deploy to Website" to push all changes to GitHub.

## 🛡️ Safety Note
*   Files are **NEVER deleted**. They are just moved between `articles/` and `backend/drafts/`.
*   Drafts are **ignored by Git**, so they stay private on your machine.
