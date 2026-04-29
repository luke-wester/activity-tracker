import sys
import threading
import webbrowser
from datetime import datetime

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from activity_tracker import ActivityTracker, REPORT_PATH, generate_report, read_summary_rows


class MetricCard(QFrame):
    def __init__(self, label_text, value_text, value_font, label_font):
        super().__init__()
        self.setObjectName("metricCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        self.value_label = QLabel(value_text)
        self.value_label.setObjectName("metricValue")
        self.value_label.setFont(value_font)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.caption_label = QLabel(label_text)
        self.caption_label.setObjectName("metricCaption")
        self.caption_label.setFont(label_font)
        self.caption_label.setWordWrap(True)

        layout.addWidget(self.value_label)
        layout.addWidget(self.caption_label)

    def set_value(self, value):
        self.value_label.setText(value)


class StatusDot(QFrame):
    def __init__(self, font_obj):
        super().__init__()
        self.setObjectName("statusWrap")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.text_label = QLabel("Ready")
        self.text_label.setObjectName("statusText")
        self.text_label.setFont(font_obj)

        self.dot = QLabel()
        self.dot.setObjectName("statusDot")
        self.dot.setFixedSize(10, 10)

        layout.addWidget(self.text_label)
        layout.addWidget(self.dot)
        layout.addStretch(1)

    def set_status(self, text, color):
        self.text_label.setText(text)
        self.text_label.setStyleSheet(f"color: {color};")
        self.dot.setStyleSheet(
            f"background: {color}; border-radius: 5px; min-width: 10px; max-width: 10px; min-height: 10px; max-height: 10px;"
        )


class TrackerDesktopApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Activity Tracker")
        self.resize(900, 760)
        self.setMinimumSize(820, 680)

        self.tracker = None
        self.tracker_thread = None
        self.session_start_time = None
        self.theme_name = "light"

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
                "success_fg": "#1d7f4f",
                "badge_fg": "#9a680b",
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
                "success_fg": "#7ee2a8",
                "badge_fg": "#ffd27a",
            },
        }
        self.colors = self.themes[self.theme_name]

        self.status_text = "Stopped"
        self.detail_text = (
            "Click Start Tracking, then grant macOS Automation and Accessibility access if prompted."
        )
        self.badge_text = "Ready"

        self.configure_fonts()
        self.build_ui()
        self.apply_theme()

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_tracker_thread)
        self.poll_timer.start(500)

    def configure_fonts(self):
        self.title_font = QFont("SF Pro Display", 24, QFont.Weight.Bold)
        self.subtitle_font = QFont("SF Pro Text", 13)
        self.section_font = QFont("SF Pro Text", 13, QFont.Weight.Bold)
        self.body_font = QFont("SF Pro Text", 13)
        self.badge_font = QFont("SF Pro Text", 12, QFont.Weight.DemiBold)
        self.metric_value_font = QFont("SF Pro Display", 18, QFont.Weight.Bold)
        self.metric_label_font = QFont("SF Pro Text", 11)
        self.meta_font = QFont("SF Pro Text", 12)
        self.status_value_font = QFont("SF Pro Display", 30, QFont.Weight.Bold)

    def build_ui(self):
        self.root_widget = QWidget()
        self.root_widget.setObjectName("rootWidget")
        self.setCentralWidget(self.root_widget)

        root_layout = QVBoxLayout(self.root_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setObjectName("scrollArea")
        root_layout.addWidget(self.scroll_area)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scrollContent")
        self.scroll_area.setWidget(self.scroll_content)

        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setContentsMargins(24, 22, 24, 22)
        self.content_layout.setSpacing(18)

        self.hero_panel = self.build_hero_panel()
        self.content_layout.addWidget(self.hero_panel)

        self.status_panel = self.build_status_panel()
        self.content_layout.addWidget(self.status_panel)

        self.report_panel = self.build_report_panel()
        self.content_layout.addWidget(self.report_panel)

        self.content_layout.addStretch(0)

    def build_hero_panel(self):
        panel = QFrame()
        panel.setObjectName("heroPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        self.title_label = QLabel("Activity Tracker")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setFont(self.title_font)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(16)

        self.theme_toggle_button = QPushButton("Dark Mode")
        self.theme_toggle_button.setObjectName("themeButton")
        self.theme_toggle_button.setFont(self.body_font)
        self.theme_toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_toggle_button.clicked.connect(self.toggle_theme)

        self.badge_chip = StatusDot(self.badge_font)

        controls_layout.addWidget(self.theme_toggle_button)
        controls_layout.addWidget(self.badge_chip)

        top_row.addWidget(self.title_label)
        top_row.addStretch(1)
        top_row.addLayout(controls_layout)

        self.subtitle_label = QLabel(
            "Track focus, meetings, browsing, and page-level activity in real time."
        )
        self.subtitle_label.setObjectName("subtitleLabel")
        self.subtitle_label.setFont(self.subtitle_font)
        self.subtitle_label.setWordWrap(True)

        layout.addLayout(top_row)
        layout.addWidget(self.subtitle_label)
        return panel

    def build_status_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        self.status_label = QLabel("Current Status")
        self.status_label.setObjectName("sectionLabel")
        self.status_label.setFont(self.section_font)

        self.status_value_label = QLabel(self.status_text)
        self.status_value_label.setObjectName("statusValue")
        self.status_value_label.setFont(self.status_value_font)

        self.detail_label = QLabel(self.detail_text)
        self.detail_label.setObjectName("bodyLabel")
        self.detail_label.setFont(self.body_font)
        self.detail_label.setWordWrap(True)

        self.tracker_toggle_button = QPushButton("Start Tracking")
        self.tracker_toggle_button.setObjectName("trackerButton")
        self.tracker_toggle_button.setFont(self.body_font)
        self.tracker_toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tracker_toggle_button.clicked.connect(self.toggle_tracking)
        self.tracker_toggle_button.setFixedHeight(54)
        self.tracker_toggle_button.setMinimumWidth(220)
        self.tracker_toggle_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

        self.metrics_grid = QGridLayout()
        self.metrics_grid.setContentsMargins(0, 0, 0, 0)
        self.metrics_grid.setHorizontalSpacing(12)
        self.metrics_grid.setVerticalSpacing(12)

        self.metric_cards = {
            "session_timer": MetricCard(
                "Session Timer", "00:00:00", self.metric_value_font, self.metric_label_font
            ),
            "today_minutes": MetricCard(
                "Today's Minutes", "0", self.metric_value_font, self.metric_label_font
            ),
            "tracked_days": MetricCard(
                "Tracked Days", "0", self.metric_value_font, self.metric_label_font
            ),
        }

        self.metrics_grid.addWidget(self.metric_cards["session_timer"], 0, 0)
        self.metrics_grid.addWidget(self.metric_cards["today_minutes"], 0, 1)
        self.metrics_grid.addWidget(self.metric_cards["tracked_days"], 0, 2)
        self.metrics_grid.setColumnStretch(0, 1)
        self.metrics_grid.setColumnStretch(1, 1)
        self.metrics_grid.setColumnStretch(2, 1)

        self.notes_label = QLabel(
            "Tip: leave this window open or minimized while the tracker runs in the background."
        )
        self.notes_label.setObjectName("metaLabel")
        self.notes_label.setFont(self.metric_label_font)
        self.notes_label.setWordWrap(True)

        layout.addWidget(self.status_label)
        layout.addWidget(self.status_value_label)
        layout.addWidget(self.detail_label)
        layout.addWidget(self.tracker_toggle_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(self.metrics_grid)
        layout.addWidget(self.notes_label)
        return panel

    def build_report_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.report_heading = QLabel("Live Report")
        self.report_heading.setObjectName("sectionLabel")
        self.report_heading.setFont(self.section_font)

        self.report_copy = QLabel(
            "Open the running dashboard to review category totals, top apps, top pages, daily history, recent sessions, and the new chart views."
        )
        self.report_copy.setObjectName("bodyLabel")
        self.report_copy.setFont(self.body_font)
        self.report_copy.setWordWrap(True)

        self.report_button = QPushButton("Open Live Report")
        self.report_button.setObjectName("reportButton")
        self.report_button.setFont(self.body_font)
        self.report_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.report_button.clicked.connect(self.open_report)
        self.report_button.setFixedHeight(54)
        self.report_button.setMinimumWidth(220)
        self.report_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

        self.path_label = QLabel("Report file")
        self.path_label.setObjectName("metaLabel")
        self.path_label.setFont(self.metric_label_font)

        self.path_value = QLabel(str(REPORT_PATH))
        self.path_value.setObjectName("pathValue")
        self.path_value.setFont(self.meta_font)
        self.path_value.setWordWrap(True)
        self.path_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.permissions_panel = QFrame()
        self.permissions_panel.setObjectName("subPanel")
        permissions_layout = QVBoxLayout(self.permissions_panel)
        permissions_layout.setContentsMargins(18, 18, 18, 18)
        permissions_layout.setSpacing(8)

        self.permissions_title = QLabel("macOS Permissions")
        self.permissions_title.setObjectName("sectionLabel")
        self.permissions_title.setFont(self.section_font)

        self.permissions_text = QLabel(
            "If tracking looks blank, confirm Accessibility and Automation access for the app or Python in System Settings."
        )
        self.permissions_text.setObjectName("metaLabel")
        self.permissions_text.setFont(self.metric_label_font)
        self.permissions_text.setWordWrap(True)

        permissions_layout.addWidget(self.permissions_title)
        permissions_layout.addWidget(self.permissions_text)

        layout.addWidget(self.report_heading)
        layout.addWidget(self.report_copy)
        layout.addWidget(self.report_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.path_label)
        layout.addWidget(self.path_value)
        layout.addWidget(self.permissions_panel)
        return panel

    def stylesheet(self):
        c = self.colors
        return f"""
        QMainWindow, QWidget#rootWidget, QWidget#scrollContent {{
            background: {c["bg"]};
            color: {c["ink"]};
        }}
        QScrollArea {{
            background: {c["bg"]};
            border: none;
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 12px;
            margin: 6px 4px 6px 0;
        }}
        QScrollBar::handle:vertical {{
            background: {c["line"]};
            border-radius: 6px;
            min-height: 36px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
            background: transparent;
            border: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}
        QFrame#heroPanel {{
            background: {c["hero_bg"]};
            border: 1px solid {c["line"]};
            border-radius: 22px;
        }}
        QFrame#panel {{
            background: {c["surface"]};
            border: 1px solid {c["line"]};
            border-radius: 22px;
        }}
        QFrame#subPanel, QFrame#metricCard {{
            background: {c["surface_alt"]};
            border: 1px solid {c["line"]};
            border-radius: 16px;
        }}
        QLabel#titleLabel {{
            color: {c["ink"]};
        }}
        QLabel#subtitleLabel, QLabel#bodyLabel, QLabel#metaLabel, QLabel#metricCaption {{
            color: {c["muted"]};
        }}
        QLabel#sectionLabel, QLabel#statusValue, QLabel#pathValue {{
            color: {c["ink"]};
        }}
        QLabel#metricValue {{
            color: {c["accent_2"]};
        }}
        QPushButton#themeButton {{
            background: {c["surface_emphasis"]};
            color: {c["ink"]};
            border: 1px solid {c["line"]};
            border-radius: 19px;
            padding: 9px 18px;
        }}
        QPushButton#themeButton:hover {{
            background: {c["surface_alt"]};
        }}
        QPushButton#reportButton {{
            background: {c["accent_soft"]};
            color: {c["accent"]};
            border: none;
            border-radius: 27px;
            padding: 14px 22px;
        }}
        QPushButton#reportButton:hover {{
            background: {c["accent_soft_pressed"]};
        }}
        """

    def apply_theme(self):
        self.colors = self.themes[self.theme_name]
        self.setStyleSheet(self.stylesheet())
        self.theme_toggle_button.setText(
            "Dark Mode" if self.theme_name == "light" else "Light Mode"
        )
        self.update_badge()
        self.update_tracker_button_appearance()

    def update_tracker_button_appearance(self):
        c = self.colors
        active = self.is_tracking_active()
        text = "Stop Tracking" if active else "Start Tracking"
        self.tracker_toggle_button.setText(text)

        if active:
            fill = c["accent_soft"]
            hover = c["accent_soft_pressed"]
            text_color = c["accent"]
        else:
            fill = c["accent"]
            hover = c["accent_pressed"]
            text_color = "#ffffff"

        self.tracker_toggle_button.setStyleSheet(
            f"""
            QPushButton#trackerButton {{
                background: {fill};
                color: {text_color};
                border: none;
                border-radius: 27px;
                padding: 14px 22px;
            }}
            QPushButton#trackerButton:hover {{
                background: {hover};
            }}
            """
        )

    def is_tracking_active(self):
        return bool(self.tracker_thread and self.tracker_thread.is_alive())

    def set_status_texts(self, status, detail, badge):
        self.status_text = status
        self.detail_text = detail
        self.badge_text = badge
        self.status_value_label.setText(status)
        self.detail_label.setText(detail)
        self.update_badge()

    def update_badge(self):
        if self.badge_text == "Live":
            color = self.colors["success_fg"]
        else:
            color = self.colors["badge_fg"]
        self.badge_chip.set_status(self.badge_text, color)

    def set_metric_value(self, key, value):
        self.metric_cards[key].set_value(value)

    def refresh_metrics(self):
        rows = read_summary_rows()
        today = datetime.now().strftime("%Y-%m-%d")
        today_minutes = sum(row["Minutes"] for row in rows if row.get("Date") == today)
        tracked_days = len({row.get("Date") for row in rows if row.get("Date")})

        elapsed_seconds = 0
        if self.session_start_time and self.is_tracking_active():
            elapsed_seconds = int((datetime.now() - self.session_start_time).total_seconds())

        hours, remainder = divmod(elapsed_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        self.set_metric_value("session_timer", f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        self.set_metric_value("today_minutes", str(today_minutes))
        self.set_metric_value("tracked_days", str(tracked_days))

    def toggle_theme(self):
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        self.apply_theme()

    def toggle_tracking(self):
        if self.is_tracking_active():
            self.stop_tracking()
        else:
            self.start_tracking()

    def start_tracking(self):
        if self.is_tracking_active():
            return

        self.tracker = ActivityTracker()
        self.tracker_thread = threading.Thread(target=self.tracker.run, daemon=True)
        self.tracker_thread.start()
        self.session_start_time = datetime.now()
        generate_report()

        self.set_status_texts(
            "Running",
            "The tracker is logging your active app, Chrome page titles and URLs, Dia browser activity, and refreshing the report.",
            "Live",
        )
        self.update_tracker_button_appearance()
        self.refresh_metrics()

    def stop_tracking(self):
        if self.tracker:
            self.tracker.stop()

        self.set_status_texts(
            "Stopping",
            "Waiting for the current session to be written to the log.",
            "Saving",
        )
        self.update_tracker_button_appearance()
        self.refresh_metrics()

    def poll_tracker_thread(self):
        if self.tracker_thread and not self.tracker_thread.is_alive():
            self.tracker_thread = None
            self.tracker = None
            self.session_start_time = None
            self.set_status_texts(
                "Stopped",
                "You can start tracking again at any time.",
                "Ready",
            )
            self.update_tracker_button_appearance()

        self.refresh_metrics()

    def open_report(self):
        generate_report()
        webbrowser.open(REPORT_PATH.as_uri())

    def closeEvent(self, event: QCloseEvent):
        if not self.is_tracking_active():
            event.accept()
            return

        response = QMessageBox.question(
            self,
            "Stop tracking?",
            "Tracking is still running. Do you want to stop it and close the app?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if response != QMessageBox.StandardButton.Yes:
            event.ignore()
            return

        self.stop_tracking()
        if self.tracker_thread:
            self.tracker_thread.join(timeout=1.5)
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = TrackerDesktopApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
