# FH6-Painter Frontend

This is the Tauri and Vanilla HTML/CSS/JS frontend for FH6-Painter. It provides a real-time canvas preview of geometry fitting, live HUD metrics, interactive Region of Interest (ROI) painting, and History Rewind capabilities for generating Forza Horizon 6 liveries.

## Architecture

* **Tauri Framework:** Provides the native desktop window and system integration.
* **Vite + Vanilla Web:** Fast development server and vanilla HTML/CSS/JS for the user interface.
* **WebSocket Integration:** Communicates with the Python backend (`backend/server.py`) to stream real-time geometry drawing progress and log updates without blocking the UI thread.

## Development

Make sure you have Node.js and Rust installed.

### Setup and Build

1. Install dependencies:
   ```bash
   npm install
   # Or from repository root: npm --prefix frontend install
   ```

2. Start the development server (runs Vite):
   ```bash
   npm run dev
   ```

3. Build for production:
   ```bash
   npm run build
   # Or from repository root: npm --prefix frontend run build
   ```

For desktop integration commands, see `package.json` for Tauri-specific scripts.