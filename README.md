# activity-tracker

Mac activity tracker with a downloadable desktop app and a Render-hosted landing page.

## Repo Layout

- `activity_tracker.py`: local tracking and report generation
- `tracker_desktop_app.py`: macOS desktop UI
- `site/`: static marketing and download page for Render
- `render.yaml`: Render static site config

## Deploy The Download Page

1. Push this repo to GitHub.
2. In Render, create a new service from the repo.
3. Render will detect `render.yaml` and deploy the static site from `site/`.
4. Point the download button at the latest GitHub Release asset for your Mac app.

## Download Link

The landing page currently points to:

- `https://github.com/luke-wester/activity-tracker/releases/latest`

Once you upload a zipped `.app` file to GitHub Releases, users can download it from the Render page.
