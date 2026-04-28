from datetime import datetime
from html import escape
from pathlib import Path
import csv
import subprocess
import threading
import time
from urllib.parse import urlparse


MIN_DURATION_SECONDS = 3

APP_CATEGORIES = {
    "Slack": "Slack",
    "Outlook": "Outlook",
    "Microsoft Outlook": "Outlook",
    "Microsoft Teams": "Meetings",
    "Zoom": "Meetings",
    "Asana": "Project Management",
    "Terminal": "Deep Work",
    "Microsoft Word": "Deep Work",
    "Excel": "Deep Work",
    "PowerPoint": "Deep Work",
    "Google Docs": "Deep Work",
    "Google Chrome": "Web Browsing",
    "Chrome": "Web Browsing",
    "Dia": "DIA Browser",
    "Idle (no input detected)": "Idle",
}

DIA_DEEP_WORK_KEYWORDS = [
    "microsoft",
    "sharepoint",
    "powerpoint",
    "excel",
    "word",
    "salesforce",
    "teams",
    "outlook",
    "office",
    "onedrive",
    "azure",
    "brighttalk",
]

CHROME_PAGE_RULES = [
    {"match": ["docs.google.com/document"], "category": "Deep Work", "page": "Google Docs"},
    {"match": ["docs.google.com/spreadsheets"], "category": "Deep Work", "page": "Google Sheets"},
    {"match": ["docs.google.com/presentation"], "category": "Deep Work", "page": "Google Slides"},
    {"match": ["mail.google.com"], "category": "Email", "page": "Gmail"},
    {"match": ["calendar.google.com"], "category": "Meetings", "page": "Google Calendar"},
    {"match": ["drive.google.com"], "category": "Deep Work", "page": "Google Drive"},
    {"match": ["app.asana.com"], "category": "Project Management", "page": "Asana"},
    {"match": ["salesforce.com"], "category": "Deep Work", "page": "Salesforce"},
    {"match": ["sharepoint.com"], "category": "Deep Work", "page": "SharePoint"},
    {"match": ["office.com", "microsoft.com"], "category": "Deep Work", "page": "Microsoft 365"},
    {"match": ["linkedin.com"], "category": "Web Browsing", "page": "LinkedIn"},
    {"match": ["youtube.com"], "category": "Web Browsing", "page": "YouTube"},
]

BASE_DIR = Path(__file__).resolve().parent
DAILY_SUMMARY_PATH = BASE_DIR / "daily_summary.csv"
REPORT_PATH = BASE_DIR / "activity_report.html"
DAILY_LOG_DIR = BASE_DIR / "daily_logs"
SUMMARY_HEADERS = ["Date", "App", "Category", "Page", "URL", "Minutes"]


def run_osascript(script):
    return subprocess.check_output(["osascript", "-e", script], text=True).strip()


def ensure_log_files():
    today = datetime.now().strftime("%Y-%m-%d")
    DAILY_LOG_DIR.mkdir(exist_ok=True)
    activity_log_path = get_activity_log_path(today)

    if not activity_log_path.exists():
        activity_log_path.write_text(
            "====================\n"
            f"Date: {today}\n"
            "====================\n\n",
            encoding="utf-8",
        )

    if not DAILY_SUMMARY_PATH.exists():
        with DAILY_SUMMARY_PATH.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(SUMMARY_HEADERS)
        return

    with DAILY_SUMMARY_PATH.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    if rows and rows[0] == SUMMARY_HEADERS:
        return

    upgraded_rows = [SUMMARY_HEADERS]
    data_rows = rows[1:] if rows else []
    for row in data_rows:
        date = row[0] if len(row) > 0 else ""
        app = row[1] if len(row) > 1 else ""
        category = row[2] if len(row) > 2 else ""
        minutes = row[3] if len(row) > 3 else ""
        upgraded_rows.append([date, app, category, "", "", minutes])

    with DAILY_SUMMARY_PATH.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(upgraded_rows)


def get_activity_log_path(date_value):
    if isinstance(date_value, datetime):
        date_text = date_value.strftime("%Y-%m-%d")
    else:
        date_text = str(date_value)
    return DAILY_LOG_DIR / f"activity_log_{date_text}.txt"


def read_summary_rows():
    if not DAILY_SUMMARY_PATH.exists():
        return []

    with DAILY_SUMMARY_PATH.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            row["Minutes"] = int(row["Minutes"]) if row.get("Minutes", "").isdigit() else 0
            rows.append(row)
    return rows


def summarize_minutes(rows, key_name):
    totals = {}
    for row in rows:
        key = row.get(key_name, "") or "Unknown"
        totals[key] = totals.get(key, 0) + row["Minutes"]
    return sorted(totals.items(), key=lambda item: (-item[1], item[0].lower()))


def render_table(title, headers, rows):
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{escape(str(cell))}</td>" for cell in row)
        body_rows.append(f"<tr>{cells}</tr>")
    body_html = "".join(body_rows) if body_rows else (
        f"<tr><td colspan=\"{len(headers)}\">No data yet.</td></tr>"
    )
    return (
        f"<section class=\"panel\"><h2>{escape(title)}</h2><div class=\"table-wrap\">"
        f"<table><thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody></table>"
        f"</div></section>"
    )


def generate_report():
    ensure_log_files()
    rows = read_summary_rows()
    today = datetime.now().strftime("%Y-%m-%d")
    today_rows = [row for row in rows if row.get("Date") == today]

    total_minutes = sum(row["Minutes"] for row in rows)
    today_minutes = sum(row["Minutes"] for row in today_rows)
    tracked_days = len({row["Date"] for row in rows if row.get("Date")})

    category_rows = [(name, minutes) for name, minutes in summarize_minutes(rows, "Category")]
    app_rows = [(name, minutes) for name, minutes in summarize_minutes(rows, "App")]
    today_page_rows = [(name, minutes) for name, minutes in summarize_minutes(today_rows, "Page")[:12]]

    daily_totals = {}
    for row in rows:
        date = row.get("Date", "")
        daily_totals[date] = daily_totals.get(date, 0) + row["Minutes"]
    daily_rows = sorted(daily_totals.items(), key=lambda item: item[0], reverse=True)

    recent_rows = []
    for row in reversed(rows[-15:]):
        recent_rows.append(
            (
                row.get("Date", ""),
                row.get("App", ""),
                row.get("Category", ""),
                row.get("Page", ""),
                row.get("Minutes", 0),
            )
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="30">
  <title>Activity Tracker Report</title>
  <style>
    :root {{
      --bg: #f4efe7;
      --panel: #fffaf2;
      --ink: #1f2933;
      --muted: #6b7280;
      --line: #d7cbb8;
      --accent: #b85c38;
      --accent-soft: #f3d7bf;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Avenir Next", "Helvetica Neue", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, #f7dcc8 0, transparent 30%),
        linear-gradient(180deg, #f8f3eb 0%, var(--bg) 100%);
    }}
    main {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 40px 20px 56px;
    }}
    .hero {{
      margin-bottom: 24px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 42px;
      line-height: 1;
    }}
    .sub {{
      margin: 0;
      color: var(--muted);
      font-size: 16px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin: 28px 0;
    }}
    .stat, .panel {{
      background: color-mix(in srgb, var(--panel) 92%, white 8%);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: 0 10px 30px rgba(74, 52, 33, 0.06);
    }}
    .stat {{
      padding: 18px;
    }}
    .label {{
      color: var(--muted);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .value {{
      margin-top: 8px;
      font-size: 32px;
      font-weight: 700;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 18px;
    }}
    .panel {{
      padding: 18px;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 18px;
    }}
    .table-wrap {{
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      padding: 10px 8px;
      text-align: left;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    tr:last-child td {{
      border-bottom: none;
    }}
    .footer {{
      margin-top: 20px;
      color: var(--muted);
      font-size: 13px;
    }}
    .pill {{
      display: inline-block;
      margin-top: 10px;
      background: var(--accent-soft);
      color: var(--accent);
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>Activity Report</h1>
      <p class="sub">Live local report generated from your tracker logs. Refreshes automatically every 30 seconds.</p>
      <div class="pill">Last updated: {escape(datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"))}</div>
    </section>

    <section class="stats">
      <div class="stat"><div class="label">Tracked Days</div><div class="value">{tracked_days}</div></div>
      <div class="stat"><div class="label">Total Logged Minutes</div><div class="value">{total_minutes}</div></div>
      <div class="stat"><div class="label">Today's Logged Minutes</div><div class="value">{today_minutes}</div></div>
      <div class="stat"><div class="label">Today's Sessions</div><div class="value">{len(today_rows)}</div></div>
    </section>

    <section class="grid">
      {render_table("Time by Category", ["Category", "Minutes"], category_rows)}
      {render_table("Time by App", ["App", "Minutes"], app_rows)}
      {render_table("Today by Page", ["Page", "Minutes"], today_page_rows)}
      {render_table("Daily Totals", ["Date", "Minutes"], daily_rows)}
      {render_table("Recent Logged Activity", ["Date", "App", "Category", "Page", "Minutes"], recent_rows)}
    </section>

    <p class="footer">Daily text logs are saved in {escape(str(DAILY_LOG_DIR))} and cumulative summaries stay in {escape(str(DAILY_SUMMARY_PATH))}.</p>
  </main>
</body>
</html>
"""
    REPORT_PATH.write_text(html, encoding="utf-8")


def get_active_window():
    script = """
    global frontAppName, windowTitle
    set windowTitle to ""
    tell application "System Events"
        set frontApp to first application process whose frontmost is true
        set frontAppName to name of frontApp
        try
            tell process frontAppName
                set windowTitle to name of front window
            end tell
        end try
    end tell
    return frontAppName & "||" & windowTitle
    """

    try:
        output = run_osascript(script)
        app, window_title = output.split("||", 1)
        return app.strip(), window_title.strip()
    except Exception:
        return "Idle (no input detected)", ""


def get_google_chrome_tab():
    script = """
    tell application "Google Chrome"
        if not running then
            return "||"
        end if
        if (count of windows) is 0 then
            return "||"
        end if
        set activeTab to active tab of front window
        return (title of activeTab) & "||" & (URL of activeTab)
    end tell
    """

    try:
        output = run_osascript(script)
        title, url = output.split("||", 1)
        return title.strip(), url.strip()
    except Exception:
        return "", ""


def get_activity_snapshot():
    app, window_title = get_active_window()
    page = window_title
    url = ""

    if app == "Google Chrome":
        tab_title, tab_url = get_google_chrome_tab()
        if tab_title:
            page = tab_title
        url = tab_url

    return {
        "app": app,
        "window_title": window_title,
        "page": page,
        "url": url,
    }


def normalize_app_name(app):
    if "Teams" in app:
        return "Microsoft Teams"
    if "Outlook" in app:
        return "Microsoft Outlook"
    if app == "Google Chrome":
        return "Chrome"
    return app


def classify_chrome_page(url, page):
    combined = f"{url} {page}".lower()
    for rule in CHROME_PAGE_RULES:
        if any(match in combined for match in rule["match"]):
            return rule["category"], rule["page"]

    parsed = urlparse(url) if url else None
    domain = parsed.netloc.replace("www.", "") if parsed and parsed.netloc else ""
    if domain:
        return "Web Browsing", domain
    if page:
        return "Web Browsing", page
    return "Web Browsing", "Chrome"


def categorize_activity(snapshot):
    app = normalize_app_name(snapshot["app"])
    page = snapshot["page"] or snapshot["window_title"] or app
    url = snapshot["url"]
    category = APP_CATEGORIES.get(app, "Uncategorized")

    if app == "Dia":
        combined = f"{app} - {snapshot['window_title']}".lower()
        if any(keyword in combined for keyword in DIA_DEEP_WORK_KEYWORDS):
            category = "Deep Work"
        else:
            category = "Web Browsing"
        return app, category, page, url

    if app == "Chrome":
        category, page = classify_chrome_page(url, page)
        return app, category, page, url

    return app, category, page, url


def snapshots_match(left, right):
    return (
        left["app"] == right["app"]
        and left["window_title"] == right["window_title"]
        and left["page"] == right["page"]
        and left["url"] == right["url"]
    )


def log_activity(start_time, end_time, snapshot):
    duration = end_time - start_time
    if duration.total_seconds() < MIN_DURATION_SECONDS:
        return

    app, category, page, url = categorize_activity(snapshot)
    minutes = int(duration.total_seconds() / 60)
    detail = page or snapshot["window_title"] or app
    url_text = f" [{url}]" if url else ""
    activity_log_path = get_activity_log_path(start_time.date())

    if not activity_log_path.exists():
        activity_log_path.write_text(
            "====================\n"
            f"Date: {start_time.strftime('%Y-%m-%d')}\n"
            "====================\n\n",
            encoding="utf-8",
        )

    with activity_log_path.open("a", encoding="utf-8") as handle:
        handle.write(
            f"[{start_time.strftime('%Y-%m-%d %I:%M:%S %p')}] -> "
            f"[{end_time.strftime('%Y-%m-%d %I:%M:%S %p')}] "
            f"Used '{app} - {detail}'{url_text} for {int(duration.total_seconds())} seconds "
            f"(Category: {category})\n"
        )

    with DAILY_SUMMARY_PATH.open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerow([start_time.date(), app, category, page, url, minutes])

    generate_report()


class ActivityTracker:
    def __init__(self, poll_interval=1):
        self.poll_interval = poll_interval
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        ensure_log_files()
        previous_snapshot = get_activity_snapshot()
        start_time = datetime.now()

        while not self.stop_event.is_set():
            time.sleep(self.poll_interval)
            current_snapshot = get_activity_snapshot()
            if snapshots_match(current_snapshot, previous_snapshot):
                continue

            end_time = datetime.now()
            log_activity(start_time, end_time, previous_snapshot)
            previous_snapshot = current_snapshot
            start_time = datetime.now()

        log_activity(start_time, datetime.now(), previous_snapshot)


def main():
    tracker = ActivityTracker()
    try:
        tracker.run()
    except KeyboardInterrupt:
        tracker.stop()
        print("Tracking stopped. Summary saved.")


if __name__ == "__main__":
    main()
