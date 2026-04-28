import threading
import tkinter as tk
from tkinter import messagebox
import webbrowser

from activity_tracker import ActivityTracker, REPORT_PATH, generate_report


class TrackerDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Activity Tracker")
        self.root.geometry("460x270")
        self.root.resizable(False, False)

        self.tracker = None
        self.tracker_thread = None

        self.status_var = tk.StringVar(value="Tracker is stopped.")
        self.detail_var = tk.StringVar(
            value="Click Start Tracking, then grant macOS Automation and Accessibility access if prompted."
        )

        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.poll_tracker_thread()

    def build_ui(self):
        container = tk.Frame(self.root, padx=24, pady=24)
        container.pack(fill="both", expand=True)

        title = tk.Label(container, text="Mac Activity Tracker", font=("Helvetica", 18, "bold"))
        title.pack(anchor="w")

        status = tk.Label(container, textvariable=self.status_var, font=("Helvetica", 12))
        status.pack(anchor="w", pady=(16, 8))

        detail = tk.Label(
            container,
            textvariable=self.detail_var,
            justify="left",
            wraplength=360,
            fg="#555555",
        )
        detail.pack(anchor="w")

        button_row = tk.Frame(container, pady=20)
        button_row.pack(anchor="w")

        self.start_button = tk.Button(
            button_row,
            text="Start Tracking",
            width=16,
            command=self.start_tracking,
        )
        self.start_button.pack(side="left", padx=(0, 12))

        self.stop_button = tk.Button(
            button_row,
            text="Stop Tracking",
            width=16,
            command=self.stop_tracking,
            state="disabled",
        )
        self.stop_button.pack(side="left")

        report_button = tk.Button(
            container,
            text="Open Live Report",
            width=16,
            command=self.open_report,
        )
        report_button.pack(anchor="w")

    def start_tracking(self):
        if self.tracker_thread and self.tracker_thread.is_alive():
            return

        self.tracker = ActivityTracker()
        self.tracker_thread = threading.Thread(target=self.tracker.run, daemon=True)
        self.tracker_thread.start()
        generate_report()

        self.status_var.set("Tracker is running.")
        self.detail_var.set(
            "The app is now logging your active app, Chrome page titles and URLs, Dia browser activity, and updating the report."
        )
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

    def stop_tracking(self):
        if self.tracker:
            self.tracker.stop()

        self.status_var.set("Stopping tracker...")
        self.detail_var.set("Waiting for the current session to be written to the log.")
        self.stop_button.config(state="disabled")

    def poll_tracker_thread(self):
        if self.tracker_thread and not self.tracker_thread.is_alive():
            self.tracker_thread = None
            self.tracker = None
            self.status_var.set("Tracker is stopped.")
            self.detail_var.set("You can start tracking again at any time.")
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")

        self.root.after(500, self.poll_tracker_thread)

    def on_close(self):
        if self.tracker_thread and self.tracker_thread.is_alive():
            if not messagebox.askyesno(
                "Stop tracking?",
                "Tracking is still running. Do you want to stop it and close the app?",
            ):
                return
            self.stop_tracking()
            self.root.after(700, self.root.destroy)
            return

        self.root.destroy()

    def open_report(self):
        generate_report()
        webbrowser.open(REPORT_PATH.as_uri())


def main():
    root = tk.Tk()
    TrackerDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
