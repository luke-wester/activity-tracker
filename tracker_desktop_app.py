import threading
import tkinter as tk
from tkinter import font, messagebox
import webbrowser
from datetime import datetime

from activity_tracker import ActivityTracker, REPORT_PATH, generate_report, read_summary_rows


class PillButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text,
        command,
        width,
        height,
        font_obj,
        theme,
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
        )
        self.command = command
        self.enabled = True
        self.width = width
        self.height = height
        self.font_obj = font_obj
        self.inset = 2
        self.radius = (height - (self.inset * 2)) / 2
        self.theme = theme

        self.left_arc = self.create_oval(
            self.inset,
            self.inset,
            height - self.inset,
            height - self.inset,
            outline="",
            fill="",
        )
        self.right_arc = self.create_oval(
            width - height + self.inset,
            self.inset,
            width - self.inset,
            height - self.inset,
            outline="",
            fill="",
        )
        self.center_rect = self.create_rectangle(
            self.radius + self.inset,
            self.inset,
            width - self.radius - self.inset,
            height - self.inset,
            outline="",
            fill="",
        )
        self.label = self.create_text(width / 2, height / 2, text=text, fill="", font=font_obj)

        for item in (self.left_arc, self.right_arc, self.center_rect, self.label):
            self.tag_bind(item, "<Button-1>", self.on_click)
            self.tag_bind(item, "<Enter>", self.on_enter)
            self.tag_bind(item, "<Leave>", self.on_leave)

        self.configure(cursor="hand2")
        if theme:
            self.apply_theme(theme)

    def apply_theme(self, theme):
        self.theme = theme
        self.configure(bg=self.master.cget("bg"))
        self.draw_base()

    def draw_base(self, hovered=False):
        fill = self.theme["fill_hover"] if hovered and self.enabled else self.theme["fill"]
        if not self.enabled:
            fill = self.theme["disabled_fill"]

        self.itemconfig(self.left_arc, fill=fill, outline=fill)
        self.itemconfig(self.right_arc, fill=fill, outline=fill)
        self.itemconfig(self.center_rect, fill=fill, outline=fill)
        self.itemconfig(
            self.label,
            fill=self.theme["text_color"] if self.enabled else self.theme["disabled_text"],
        )
        self.configure(cursor="hand2" if self.enabled else "arrow")

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.draw_base()

    def on_enter(self, _event):
        if self.enabled:
            self.draw_base(hovered=True)

    def on_leave(self, _event):
        self.draw_base()

    def on_click(self, _event):
        if self.enabled:
            self.command()

    def set_text(self, text):
        self.itemconfig(self.label, text=text)


class RoundedPanel(tk.Canvas):
    def __init__(self, parent, radius=18, padding=(18, 18), **kwargs):
        super().__init__(parent, highlightthickness=0, bd=0, **kwargs)
        self.radius = radius
        self.pad_x, self.pad_y = padding
        self.fill_color = "#ffffff"
        self.border_color = "#d2d2d7"
        self.background_color = parent.cget("bg")

        self.inner = tk.Frame(self, bd=0, highlightthickness=0)
        self.window_id = self.create_window(
            self.pad_x,
            self.pad_y,
            anchor="nw",
            window=self.inner,
        )

        self.bind("<Configure>", self.on_configure)

    def on_configure(self, _event=None):
        width = max(self.winfo_width(), self.radius * 2 + 2)
        height = max(self.winfo_height(), self.radius * 2 + 2)
        self.delete("panel")
        self.draw_rounded_rect(1, 1, width - 1, height - 1, self.radius, self.fill_color, self.border_color)
        self.coords(self.window_id, self.pad_x, self.pad_y)
        self.itemconfigure(
            self.window_id,
            width=max(1, width - (self.pad_x * 2)),
            height=max(1, height - (self.pad_y * 2)),
        )

    def draw_rounded_rect(self, x1, y1, x2, y2, radius, fill, outline):
        self.create_arc(x1, y1, x1 + radius * 2, y1 + radius * 2, start=90, extent=90, fill=fill, outline=fill, tags="panel")
        self.create_arc(x2 - radius * 2, y1, x2, y1 + radius * 2, start=0, extent=90, fill=fill, outline=fill, tags="panel")
        self.create_arc(x1, y2 - radius * 2, x1 + radius * 2, y2, start=180, extent=90, fill=fill, outline=fill, tags="panel")
        self.create_arc(x2 - radius * 2, y2 - radius * 2, x2, y2, start=270, extent=90, fill=fill, outline=fill, tags="panel")
        self.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=fill, outline=fill, tags="panel")
        self.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=fill, outline=fill, tags="panel")

    def apply_theme(self, background_color, fill_color, border_color):
        self.background_color = background_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.configure(bg=background_color)
        self.inner.configure(bg=fill_color)
        self.on_configure()


class StatusChip(tk.Canvas):
    def __init__(self, parent, textvariable, font_obj, **kwargs):
        super().__init__(parent, width=132, height=32, highlightthickness=0, bd=0, **kwargs)
        self.textvariable = textvariable
        self.font_obj = font_obj
        self.fill_color = "#fff2d6"
        self.text_color = "#9a680b"
        self.dot = None
        self.label = self.create_text(48, 16, text=self.textvariable.get(), font=self.font_obj, fill="", anchor="w")
        self.dot = self.create_oval(104, 12, 112, 20, outline="", fill="")

        self.textvariable.trace_add("write", self.on_text_change)
        self.apply_theme(parent.cget("bg"), self.fill_color, self.text_color, "#000000")

    def on_text_change(self, *_args):
        self.itemconfig(self.label, text=self.textvariable.get())
        bbox = self.bbox(self.label)
        if bbox:
            dot_x = bbox[2] + 10
            self.coords(self.dot, dot_x, 12, dot_x + 8, 20)

    def apply_theme(self, background_color, fill_color, text_color, border_color):
        self.configure(bg=background_color)
        self.fill_color = fill_color
        self.text_color = text_color
        self.itemconfig(self.label, fill=text_color)
        self.itemconfig(self.dot, fill=text_color, outline=text_color)
        self.on_text_change()


class TrackerDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Activity Tracker")
        self.root.geometry("1240x760")
        self.root.minsize(1160, 720)
        self.root.resizable(True, True)

        self.tracker = None
        self.tracker_thread = None
        self.session_start_time = None
        self.theme_name = "light"
        self.metric_cards = []

        self.themes = {
            "light": {
                "bg": "#f5f5f7",
                "hero_bg": "#dce9fb",
                "surface": "#ffffff",
                "surface_alt": "#f7f9fc",
                "surface_emphasis": "#eef2f7",
                "ink": "#1d1d1f",
                "muted": "#5f6670",
                "line": "#c6d4ea",
                "accent": "#0071e3",
                "accent_pressed": "#0062c3",
                "accent_soft": "#e8f2ff",
                "accent_soft_pressed": "#d8e8ff",
                "accent_2": "#5e5ce6",
                "accent_3": "#34c759",
                "button_text": "#ffffff",
                "disabled_fill": "#bfdaf7",
                "disabled_text": "#f6fbff",
                "secondary_disabled_fill": "#eef4fb",
                "secondary_disabled_text": "#7ea9d8",
                "badge_bg": "#fff2d6",
                "badge_fg": "#9a680b",
                "badge_line": "#e2c37a",
                "success_bg": "#e8f5ee",
                "success_fg": "#1d7f4f",
                "success_line": "#b7e3c8",
                "shadow": "#dfe8f8",
            },
            "dark": {
                "bg": "#111216",
                "hero_bg": "#151b25",
                "surface": "#1c1d22",
                "surface_alt": "#22252c",
                "surface_emphasis": "#272b34",
                "ink": "#f5f5f7",
                "muted": "#a1a1aa",
                "line": "#343843",
                "accent": "#0a84ff",
                "accent_pressed": "#409cff",
                "accent_soft": "#16324f",
                "accent_soft_pressed": "#20456a",
                "accent_2": "#7d7aff",
                "accent_3": "#30d158",
                "button_text": "#ffffff",
                "disabled_fill": "#27435f",
                "disabled_text": "#9dc9ff",
                "secondary_disabled_fill": "#253241",
                "secondary_disabled_text": "#7aa7d4",
                "badge_bg": "#3d3017",
                "badge_fg": "#ffd27a",
                "badge_line": "#5d4820",
                "success_bg": "#163324",
                "success_fg": "#7ee2a8",
                "success_line": "#27573d",
                "shadow": "#0b0c10",
            },
        }
        self.colors = self.themes[self.theme_name]

        self.status_var = tk.StringVar(value="Stopped")
        self.detail_var = tk.StringVar(
            value="Click Start Tracking, then grant macOS Automation and Accessibility access if prompted."
        )
        self.badge_var = tk.StringVar(value="Ready")
        self.report_path_var = tk.StringVar(value=str(REPORT_PATH))
        self.theme_button_var = tk.StringVar(value="Dark Mode")

        self.configure_fonts()
        self.build_ui()
        self.apply_theme()
        self.root.bind("<Configure>", self.on_resize)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.poll_tracker_thread()

    def configure_fonts(self):
        self.title_font = font.Font(family="SF Pro Display", size=24, weight="bold")
        self.subtitle_font = font.Font(family="SF Pro Text", size=13)
        self.section_font = font.Font(family="SF Pro Text", size=13, weight="bold")
        self.body_font = font.Font(family="SF Pro Text", size=13)
        self.badge_font = font.Font(family="SF Pro Text", size=11, weight="bold")
        self.metric_value_font = font.Font(family="SF Pro Display", size=18, weight="bold")
        self.metric_label_font = font.Font(family="SF Pro Text", size=11)
        self.meta_font = font.Font(family="SF Pro Text", size=12)

    def build_ui(self):
        self.root_container = tk.Frame(self.root, padx=24, pady=22)
        self.root_container.pack(fill="both", expand=True)
        self.root_container.grid_columnconfigure(0, weight=5)
        self.root_container.grid_columnconfigure(1, weight=4)
        self.root_container.grid_rowconfigure(1, weight=1)
        self.root_container.grid_rowconfigure(2, weight=1)

        self.hero = RoundedPanel(self.root_container, radius=22, padding=(22, 20), height=160)
        self.hero.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.hero.inner.grid_columnconfigure(0, weight=1)
        hero_content = self.hero.inner

        self.title_label = tk.Label(
            hero_content,
            text="Activity Tracker",
            font=self.title_font,
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.subtitle_label = tk.Label(
            hero_content,
            text="Track focus, meetings, browsing, and page-level activity in real time.",
            font=self.subtitle_font,
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(6, 0))

        self.top_controls = tk.Frame(hero_content)
        self.top_controls.grid(row=0, column=1, rowspan=2, sticky="e")

        self.theme_toggle_button = PillButton(
            self.top_controls,
            text="Dark Mode",
            command=self.toggle_theme,
            width=132,
            height=38,
            font_obj=self.metric_label_font,
            theme=self.get_button_theme("ghost"),
        )
        self.theme_toggle_button.pack(side="left", padx=(0, 10))

        self.badge_chip = StatusChip(
            self.top_controls,
            textvariable=self.badge_var,
            font_obj=self.badge_font,
            bg=self.colors["hero_bg"],
        )
        self.badge_chip.pack(side="left")

        self.left_panel = RoundedPanel(self.root_container, radius=22, padding=(24, 24), height=420)
        self.left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(18, 0))

        self.right_panel = RoundedPanel(self.root_container, radius=22, padding=(24, 24), height=420)
        self.right_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(18, 0))

        left_content = self.left_panel.inner
        right_content = self.right_panel.inner

        self.status_label = tk.Label(left_content, text="Current Status", font=self.section_font)
        self.status_label.pack(anchor="w")

        self.status_value_label = tk.Label(left_content, textvariable=self.status_var, font=self.title_font)
        self.status_value_label.pack(anchor="w", pady=(8, 2))

        self.detail_label = tk.Label(
            left_content,
            textvariable=self.detail_var,
            justify="left",
            wraplength=360,
            font=self.body_font,
        )
        self.detail_label.pack(anchor="w", pady=(0, 18))

        self.metrics_row = tk.Frame(left_content)
        self.metrics_row.pack(fill="x", pady=(0, 18))

        self.build_metric_card("Session Timer", "00:00:00", 0, key="session_timer")
        self.build_metric_card("Today's Minutes", "0", 1, key="today_minutes")
        self.build_metric_card("Tracked Days", "0", 2, key="tracked_days")

        self.button_row = tk.Frame(left_content)
        self.button_row.pack(anchor="w", fill="x", pady=(14, 16))

        self.tracker_toggle_button = PillButton(
            self.button_row,
            text="Start Tracking",
            command=self.toggle_tracking,
            width=220,
            height=54,
            font_obj=self.body_font,
            theme=self.get_button_theme("primary"),
        )

        self.notes_label = tk.Label(
            left_content,
            text="Tip: leave this window open or minimized while the tracker runs in the background.",
            font=self.metric_label_font,
            wraplength=360,
            justify="left",
        )
        self.notes_label.pack(anchor="w", pady=(18, 0))

        self.report_heading = tk.Label(right_content, text="Live Report", font=self.section_font)
        self.report_heading.pack(anchor="w")

        self.report_copy = tk.Label(
            right_content,
            text=(
                "Open the running dashboard to review category totals, top apps, top pages, "
                "daily history, recent sessions, and the new chart views."
            ),
            font=self.body_font,
            wraplength=300,
            justify="left",
        )
        self.report_copy.pack(anchor="w", pady=(10, 18))

        self.report_button = PillButton(
            right_content,
            text="Open Live Report",
            command=self.open_report,
            width=220,
            height=54,
            font_obj=self.body_font,
            theme=self.get_button_theme("secondary"),
        )
        self.report_button.pack(anchor="w")

        self.path_label = tk.Label(right_content, text="Report file", font=self.metric_label_font)
        self.path_label.pack(anchor="w", pady=(20, 6))

        self.path_value = tk.Label(
            right_content,
            textvariable=self.report_path_var,
            font=self.meta_font,
            wraplength=300,
            justify="left",
        )
        self.path_value.pack(anchor="w")

        self.permissions_box = RoundedPanel(right_content, radius=16, padding=(16, 16), height=210)
        self.permissions_box.pack(fill="x", pady=(22, 0))
        permissions_content = self.permissions_box.inner

        self.permissions_title = tk.Label(
            permissions_content,
            text="macOS Permissions",
            font=self.section_font,
        )
        self.permissions_title.pack(anchor="w")

        self.permissions_text = tk.Label(
            permissions_content,
            text=(
                "If tracking looks blank, confirm Accessibility and Automation access for the app "
                "or Python in System Settings."
            ),
            font=self.metric_label_font,
            wraplength=290,
            justify="left",
        )
        self.permissions_text.pack(anchor="w", pady=(8, 0))

        self.update_layout(self.root.winfo_width())

    def build_metric_card(self, label, value, column, key=None):
        card = RoundedPanel(self.metrics_row, radius=16, padding=(16, 16), height=120)
        card.grid(row=0, column=column, sticky="nsew", padx=(0, 10 if column < 2 else 0))
        self.metrics_row.grid_columnconfigure(column, weight=1)
        content = card.inner

        metric_value = tk.Label(content, text=value, font=self.metric_value_font)
        metric_value.pack(anchor="w")

        metric_label = tk.Label(content, text=label, font=self.metric_label_font)
        metric_label.pack(anchor="w", pady=(4, 0))

        self.metric_cards.append(
            {"card": card, "value": metric_value, "label": metric_label, "key": key or label}
        )

    def get_button_theme(self, kind):
        if kind == "primary":
            return {
                "fill": self.colors["accent"],
                "fill_hover": self.colors["accent_pressed"],
                "text_color": self.colors["button_text"],
                "disabled_fill": self.colors["disabled_fill"],
                "disabled_text": self.colors["disabled_text"],
                "outline": self.colors["accent"],
            }
        if kind == "secondary":
            return {
                "fill": self.colors["accent_soft"],
                "fill_hover": self.colors["accent_soft_pressed"],
                "text_color": self.colors["accent"],
                "disabled_fill": self.colors["secondary_disabled_fill"],
                "disabled_text": self.colors["secondary_disabled_text"],
                "outline": self.colors["accent_soft"],
            }
        return {
            "fill": self.colors["surface_emphasis"],
            "fill_hover": self.colors["surface_alt"],
            "text_color": self.colors["ink"],
            "disabled_fill": self.colors["secondary_disabled_fill"],
            "disabled_text": self.colors["secondary_disabled_text"],
            "outline": self.colors["line"],
        }

    def apply_theme(self):
        self.colors = self.themes[self.theme_name]
        self.root.configure(bg=self.colors["bg"])
        self.root_container.configure(bg=self.colors["bg"])
        self.hero.apply_theme(self.colors["bg"], self.colors["hero_bg"], self.colors["line"])
        self.top_controls.configure(bg=self.colors["hero_bg"])

        for widget in (self.title_label, self.subtitle_label):
            widget.configure(bg=self.colors["hero_bg"])
        self.title_label.configure(fg=self.colors["ink"])
        self.subtitle_label.configure(fg=self.colors["muted"])

        self.badge_chip.apply_theme(
            self.colors["hero_bg"],
            self.colors["badge_bg"],
            self.colors["badge_fg"],
            self.colors["badge_line"],
        )

        self.left_panel.apply_theme(self.colors["bg"], self.colors["surface"], self.colors["line"])
        self.right_panel.apply_theme(self.colors["bg"], self.colors["surface"], self.colors["line"])
        self.metrics_row.configure(bg=self.colors["surface"])
        self.button_row.configure(bg=self.colors["surface"])

        self.status_label.configure(bg=self.colors["surface"], fg=self.colors["ink"])
        self.status_value_label.configure(bg=self.colors["surface"], fg=self.colors["ink"])
        self.detail_label.configure(bg=self.colors["surface"], fg=self.colors["muted"])
        self.notes_label.configure(bg=self.colors["surface"], fg=self.colors["muted"])

        self.report_heading.configure(bg=self.colors["surface"], fg=self.colors["ink"])
        self.report_copy.configure(bg=self.colors["surface"], fg=self.colors["muted"])
        self.path_label.configure(bg=self.colors["surface"], fg=self.colors["muted"])
        self.path_value.configure(bg=self.colors["surface"], fg=self.colors["ink"])

        self.permissions_box.apply_theme(self.colors["surface"], self.colors["surface_alt"], self.colors["line"])
        self.permissions_title.configure(bg=self.colors["surface_alt"], fg=self.colors["ink"])
        self.permissions_text.configure(bg=self.colors["surface_alt"], fg=self.colors["muted"])

        for metric in self.metric_cards:
            metric["card"].apply_theme(self.colors["surface"], self.colors["surface_alt"], self.colors["line"])
            metric["value"].configure(bg=self.colors["surface_alt"], fg=self.colors["accent_2"])
            metric["label"].configure(bg=self.colors["surface_alt"], fg=self.colors["muted"])

        self.theme_toggle_button.itemconfig(self.theme_toggle_button.label, text=self.theme_button_text())
        self.theme_toggle_button.apply_theme(self.get_button_theme("ghost"))
        self.update_tracker_button_appearance()
        self.report_button.apply_theme(self.get_button_theme("secondary"))
        self.refresh_metrics()

    def is_tracking_active(self):
        return bool(self.tracker_thread and self.tracker_thread.is_alive())

    def update_tracker_button_appearance(self):
        if self.is_tracking_active():
            self.tracker_toggle_button.set_text("Stop Tracking")
            self.tracker_toggle_button.apply_theme(self.get_button_theme("secondary"))
        else:
            self.tracker_toggle_button.set_text("Start Tracking")
            self.tracker_toggle_button.apply_theme(self.get_button_theme("primary"))
        self.tracker_toggle_button.set_enabled(True)

    def set_metric_value(self, key, value):
        for metric in self.metric_cards:
            if metric["key"] == key:
                metric["value"].configure(text=value)
                return

    def refresh_metrics(self):
        rows = read_summary_rows()
        today = datetime.now().strftime("%Y-%m-%d")
        today_minutes = sum(row["Minutes"] for row in rows if row.get("Date") == today)
        tracked_days = len({row.get("Date") for row in rows if row.get("Date")})

        elapsed_seconds = 0
        if self.session_start_time and self.tracker_thread and self.tracker_thread.is_alive():
            elapsed_seconds = int((datetime.now() - self.session_start_time).total_seconds())

        hours, remainder = divmod(elapsed_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        self.set_metric_value("session_timer", f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        self.set_metric_value("today_minutes", str(today_minutes))
        self.set_metric_value("tracked_days", str(tracked_days))

    def update_layout(self, width):
        compact = width < 1080

        self.left_panel.grid_forget()
        self.right_panel.grid_forget()
        if compact:
            self.root_container.grid_columnconfigure(0, weight=1)
            self.root_container.grid_columnconfigure(1, weight=0)
            self.left_panel.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=0, pady=(18, 10))
            self.right_panel.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=0, pady=(0, 0))
            self.detail_label.configure(wraplength=max(520, width - 140))
            self.notes_label.configure(wraplength=max(520, width - 140))
            self.report_copy.configure(wraplength=max(520, width - 180))
            self.path_value.configure(wraplength=max(520, width - 180))
            self.permissions_text.configure(wraplength=max(520, width - 190))
        else:
            self.root_container.grid_columnconfigure(0, weight=5)
            self.root_container.grid_columnconfigure(1, weight=4)
            self.left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(18, 0))
            self.right_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(18, 0))
            self.detail_label.configure(wraplength=440)
            self.notes_label.configure(wraplength=440)
            self.report_copy.configure(wraplength=360)
            self.path_value.configure(wraplength=360)
            self.permissions_text.configure(wraplength=350)

        self.tracker_toggle_button.pack_forget()
        if compact:
            self.tracker_toggle_button.pack(anchor="w")
        else:
            self.tracker_toggle_button.pack(side="left")

    def on_resize(self, event):
        if event.widget is self.root:
            self.update_layout(event.width)

    def theme_button_text(self):
        return "Dark Mode" if self.theme_name == "light" else "Light Mode"

    def toggle_theme(self):
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        self.apply_theme()

    def toggle_tracking(self):
        if self.is_tracking_active():
            self.stop_tracking()
        else:
            self.start_tracking()

    def start_tracking(self):
        if self.tracker_thread and self.tracker_thread.is_alive():
            return

        self.tracker = ActivityTracker()
        self.tracker_thread = threading.Thread(target=self.tracker.run, daemon=True)
        self.tracker_thread.start()
        self.session_start_time = datetime.now()
        generate_report()

        self.status_var.set("Running")
        self.badge_var.set("Live")
        self.badge_chip.apply_theme(
            self.colors["hero_bg"],
            self.colors["success_bg"],
            self.colors["success_fg"],
            self.colors["success_line"],
        )
        self.detail_var.set(
            "The tracker is logging your active app, Chrome page titles and URLs, Dia browser activity, and refreshing the report."
        )
        self.update_tracker_button_appearance()
        self.refresh_metrics()

    def stop_tracking(self):
        if self.tracker:
            self.tracker.stop()

        self.status_var.set("Stopping")
        self.badge_var.set("Saving")
        self.badge_chip.apply_theme(
            self.colors["hero_bg"],
            self.colors["badge_bg"],
            self.colors["badge_fg"],
            self.colors["badge_line"],
        )
        self.detail_var.set("Waiting for the current session to be written to the log.")
        self.update_tracker_button_appearance()
        self.refresh_metrics()

    def poll_tracker_thread(self):
        if self.tracker_thread and not self.tracker_thread.is_alive():
            self.tracker_thread = None
            self.tracker = None
            self.session_start_time = None
            self.status_var.set("Stopped")
            self.badge_var.set("Ready")
            self.badge_chip.apply_theme(
                self.colors["hero_bg"],
                self.colors["badge_bg"],
                self.colors["badge_fg"],
                self.colors["badge_line"],
            )
            self.detail_var.set("You can start tracking again at any time.")
            self.update_tracker_button_appearance()

        self.refresh_metrics()
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
