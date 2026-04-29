# activity-tracker

Mac activity tracker with a downloadable desktop app and a Render-hosted landing page.

## Repo Layout

- `activity_tracker.py`: local tracking and report generation
- `tracker_desktop_app.py`: macOS desktop UI
- `requirements.txt`: desktop app runtime dependency list
- `site/`: static marketing and download page for Render
- `render.yaml`: Render static site config

## Deploy The Download Page

1. Push this repo to GitHub.
2. In Render, create a new service from the repo.
3. Render will detect `render.yaml` and deploy the static site from `site/`.
4. Point the download button at the latest GitHub Release asset for your Mac app.

## Download Link

The landing page currently points to:

- `https://github.com/luke-wester/activity-tracker/releases/latest/download/ActivityTracker-mac.zip`

Once you upload a zipped `.app` file named `ActivityTracker-mac.zip` to GitHub Releases, the Render page will download the latest build directly.

## App Icon

The selected macOS icon file is stored here:

- `assets/activity_tracker_icon_minimal.icns`

Use it when packaging the Mac app with PyInstaller:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "Activity Tracker" --icon assets/activity_tracker_icon_minimal.icns tracker_desktop_app.py
```

## Desktop App Notes

- `tracker_desktop_app.py` now uses `PySide6` for the native macOS utility window and trackpad-friendly scrolling.
- `run_tracker.sh` launches the app from the project `.venv`, so local double-click launchers should target that script instead of the system Python.

## Release Refresh

After rebuilding the app, create the release zip with:

```bash
cd dist
zip -r "ActivityTracker-mac.zip" "Activity Tracker.app"
```

Upload that zip to the latest GitHub Release so the landing page button always serves the newest app build.
