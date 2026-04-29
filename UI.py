# Copyright (c) 2025 Y.MF
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

"""基于 PyQt5 的 UI 层（Edge 风格重构版）。"""

from __future__ import annotations

import csv
import logging
import os
import time
from datetime import datetime
from typing import Any

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QRect, QTimer, Qt, QUrl, QObject, QThread, pyqtSignal
from PyQt5.QtGui import QCursor, QDesktopServices, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QShortcut,
    QSplitter,
    QStatusBar,
    QToolButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from Core import KeyItem, PasswordNotebook


logger = logging.getLogger(__name__)


def _compute_lock_seconds(failed_attempts: int, threshold: int = 5, base: int = 30, max_seconds: int = 120) -> int:
    """根据失败次数计算指数退避冷却秒数。"""
    if failed_attempts < threshold:
        return 0
    exponent = failed_attempts - threshold
    return min(max_seconds, base * (2 ** exponent))


class DuplicateWarmupWorker(QObject):
    """后台预热重复密码数据，避免主线程卡顿。"""

    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, password_book: PasswordNotebook):
        super().__init__()
        self.password_book = password_book

    def run(self):
        try:
            data = self.password_book.list_duplicate_password_items()
            self.finished.emit(data)
        except Exception as e:
            self.failed.emit(str(e))


EDGE_LIGHT_STYLESHEET = """
QMainWindow {
    background: #f3f6fb;
}
QWidget {
    color: #1f2937;
    font-family: "Segoe UI", "Microsoft YaHei UI", Arial, sans-serif;
    font-size: 13px;
}
QFrame#TopBar {
    background: #ffffff;
    border: 1px solid #e5eaf2;
    border-radius: 10px;
}
QFrame#SegmentTrack {
    background: #eef2f7;
    border: 1px solid #d7dde8;
    border-radius: 16px;
}
QFrame#SegmentIndicator {
    background: #1a73e8;
    border: none;
    border-radius: 14px;
}
QFrame#Card {
    background: #ffffff;
    border: 1px solid #e5eaf2;
    border-radius: 10px;
}
QLabel#TitleLabel {
    font-size: 16px;
    font-weight: 700;
    color: #0f172a;
}
QLabel#MutedText {
    color: #64748b;
}
QLineEdit {
    background: #ffffff;
    border: 1px solid #d7dde8;
    border-radius: 8px;
    padding: 8px 10px;
}
QLineEdit:focus {
    border: 1px solid #1a73e8;
}
QComboBox {
    background: #ffffff;
    border: 1px solid #d7dde8;
    border-radius: 8px;
    padding: 6px 8px;
}
QTableWidget {
    background: #ffffff;
    border: 1px solid #e5eaf2;
    border-radius: 10px;
    gridline-color: #edf1f7;
    selection-background-color: #e8f0fe;
    selection-color: #0f172a;
}
QHeaderView::section {
    background: #f8fafc;
    color: #334155;
    border: none;
    border-bottom: 1px solid #e5eaf2;
    padding: 8px;
    font-weight: 600;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #d7dde8;
    border-radius: 8px;
    padding: 7px 12px;
    color: #0f172a;
}
QPushButton:hover {
    background: #f8fafc;
    border-color: #b9c3d3;
}
QPushButton#SegmentBtn {
    background: transparent;
    border: none;
    border-radius: 14px;
    min-height: 30px;
    padding: 4px 14px;
    color: #334155;
    font-weight: 600;
}
QPushButton#SegmentBtn:hover {
    background: rgba(26, 115, 232, 0.08);
    border: none;
}
QPushButton#SegmentBtn:checked {
    color: #ffffff;
    background: transparent;
}
QPushButton#SegmentBtn:focus {
    border: 1px solid #93c5fd;
}
QPushButton#PrimaryBtn {
    background: #1a73e8;
    border: 1px solid #1a73e8;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#PrimaryBtn:hover {
    background: #1669d3;
}
QPushButton#DangerBtn {
    background: #ffffff;
    border: 1px solid #ef4444;
    color: #b91c1c;
}
QPushButton#DangerBtn:hover {
    background: #fff1f2;
}
QToolButton#CopyIconBtn {
    background: transparent;
    border: 1px solid #d7dde8;
    border-radius: 11px;
    min-width: 24px;
    min-height: 24px;
    color: #475569;
    font-size: 12px;
}
QToolButton#CopyIconBtn:hover {
    background: #f1f5f9;
    border-color: #b9c3d3;
}
QStatusBar {
    background: #ffffff;
    border-top: 1px solid #e5eaf2;
    color: #475569;
}
"""


class RelativeTimeItem(QTableWidgetItem):
    """用于时间列排序的表格项（按原始时间戳排序，展示相对时间文本）。"""

    def __init__(self, display_text: str, raw_time_text: str):
        super().__init__(display_text)
        self.raw_time_text = raw_time_text
        self.setToolTip(raw_time_text if raw_time_text else "-")

    @staticmethod
    def _to_timestamp(value: str) -> float:
        if not value:
            return 0.0
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").timestamp()
        except ValueError:
            return 0.0

    def __lt__(self, other):
        if isinstance(other, RelativeTimeItem):
            return self._to_timestamp(self.raw_time_text) < self._to_timestamp(other.raw_time_text)
        return super().__lt__(other)


class ErrorDialog(QDialog):
    """统一错误提示对话框。"""

    def __init__(self, parent=None, msg="", button="确认"):
        super().__init__(parent)
        self.setWindowTitle("提示")
        self.setModal(True)
        self.setFixedSize(360, 170)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        title = QLabel("操作提示")
        title.setObjectName("TitleLabel")
        root.addWidget(title)

        text = QLabel(msg)
        text.setWordWrap(True)
        root.addWidget(text)

        line = QHBoxLayout()
        line.addStretch()

        ok_btn = QPushButton(button)
        ok_btn.setObjectName("PrimaryBtn")
        ok_btn.setCursor(QCursor(Qt.PointingHandCursor))
        ok_btn.clicked.connect(self.accept)
        line.addWidget(ok_btn)

        root.addLayout(line)


class ConfirmDialog(QDialog):
    """统一确认对话框。"""

    def __init__(self, parent=None, msg="", button1="确认", button2="取消"):
        super().__init__(parent)
        self.setWindowTitle("请确认")
        self.setModal(True)
        self.setFixedSize(420, 190)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        title = QLabel("确认操作")
        title.setObjectName("TitleLabel")
        root.addWidget(title)

        text = QLabel(msg)
        text.setWordWrap(True)
        root.addWidget(text)

        line = QHBoxLayout()
        line.addStretch()

        ok_btn = QPushButton(button1)
        ok_btn.setObjectName("PrimaryBtn")
        ok_btn.setCursor(QCursor(Qt.PointingHandCursor))
        ok_btn.clicked.connect(self.accept)
        line.addWidget(ok_btn)

        cancel_btn = QPushButton(button2)
        cancel_btn.setCursor(QCursor(Qt.PointingHandCursor))
        cancel_btn.clicked.connect(self.reject)
        line.addWidget(cancel_btn)

        root.addLayout(line)


class LoginDialog(QDialog):
    """登录对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_key = None
        self.failed_attempts = 0
        self.lock_until_ts = 0.0
        self.setWindowTitle("密码本登录")
        self.setFixedSize(480, 280)
        self.setStyleSheet(EDGE_LIGHT_STYLESHEET)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(18)

        title = QLabel("本地密码本")
        title.setObjectName("TitleLabel")
        root.addWidget(title)

        sub = QLabel("请输入主密码以解锁本地密码库。")
        sub.setObjectName("MutedText")
        root.addWidget(sub)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignLeft)
        form.setSpacing(12)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("输入主密码")
        self.password_input.returnPressed.connect(self._on_login_click)
        password_row = QHBoxLayout()
        password_row.setSpacing(6)
        password_row.addWidget(self.password_input)

        self.toggle_pwd_btn = QToolButton()
        self.toggle_pwd_btn.setText("显示")
        self.toggle_pwd_btn.setCheckable(True)
        self.toggle_pwd_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.toggle_pwd_btn.toggled.connect(self._toggle_password_echo)
        password_row.addWidget(self.toggle_pwd_btn)

        form.addRow("主密码", password_row)

        root.addLayout(form)
        root.addStretch()

        btns = QHBoxLayout()
        btns.addStretch()

        quit_btn = QPushButton("退出")
        quit_btn.clicked.connect(self.reject)
        btns.addWidget(quit_btn)

        login_btn = QPushButton("登录")
        login_btn.setObjectName("PrimaryBtn")
        login_btn.clicked.connect(self._on_login_click)
        btns.addWidget(login_btn)

        root.addLayout(btns)

        self.password_input.setFocus()

    def _on_login_click(self):
        now = time.time()
        if now < self.lock_until_ts:
            wait_sec = int(self.lock_until_ts - now + 0.999)
            ErrorDialog(self, f"尝试过于频繁，请在 {wait_sec} 秒后重试").exec_()
            return

        password = self.password_input.text().strip()
        if not password:
            ErrorDialog(self, "请输入登录密码，不能为空").exec_()
            return
        self.main_key = password
        self.accept()

    def register_failed_attempt(self):
        self.failed_attempts += 1
        lock_sec = _compute_lock_seconds(self.failed_attempts)
        if lock_sec > 0:
            self.lock_until_ts = time.time() + lock_sec
            logger.warning("登录失败触发冷却，failed_attempts=%s, lock_seconds=%s", self.failed_attempts, lock_sec)

    def register_success(self):
        self.failed_attempts = 0
        self.lock_until_ts = 0.0

    def _toggle_password_echo(self, checked: bool):
        self.password_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        self.toggle_pwd_btn.setText("隐藏" if checked else "显示")


class SecondaryVerifyDialog(QDialog):
    """敏感操作二次验证对话框。"""

    def __init__(self, action_name: str, parent=None):
        super().__init__(parent)
        self.input_password = None
        self.setWindowTitle("身份确认")
        self.setFixedSize(420, 200)
        self.setStyleSheet(EDGE_LIGHT_STYLESHEET)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        title = QLabel("执行敏感操作需要再次验证")
        title.setObjectName("TitleLabel")
        root.addWidget(title)

        info = QLabel(f"将执行操作：{action_name}")
        info.setObjectName("MutedText")
        root.addWidget(info)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("再次输入主密码")
        self.password_input.returnPressed.connect(self._verify_password)
        root.addWidget(self.password_input)

        btns = QHBoxLayout()
        btns.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        verify_btn = QPushButton("确认验证")
        verify_btn.setObjectName("PrimaryBtn")
        verify_btn.clicked.connect(self._verify_password)
        btns.addWidget(verify_btn)

        root.addLayout(btns)
        self.password_input.setFocus()

    def _verify_password(self):
        password = self.password_input.text().strip()
        if not password:
            ErrorDialog(self, "请输入密码").exec_()
            return
        self.input_password = password
        self.accept()


class ItemEditDialog(QDialog):
    """条目编辑对话框（新增/修改共用）。"""

    def __init__(self, item_data: dict | None = None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(EDGE_LIGHT_STYLESHEET)
        self.setFixedSize(520, 360)
        self.setWindowTitle("修改条目" if item_data else "新增条目")
        self.item_data = KeyItem(item_data) if item_data else KeyItem()

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        title = QLabel("编辑密码条目")
        title.setObjectName("TitleLabel")
        root.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self.url_input = QLineEdit(self.item_data.get("URL", ""))
        self.url_input.setPlaceholderText("例如：https://example.com")
        form.addRow("网址", self.url_input)

        self.username_input = QLineEdit(self.item_data.get("UserName", ""))
        self.username_input.setPlaceholderText("登录用户名")
        form.addRow("用户名", self.username_input)

        self.password_input = QLineEdit(self.item_data.get("Password", ""))
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("密码")
        form.addRow("密码", self.password_input)

        self.password_check = QLineEdit()
        self.password_check.setEchoMode(QLineEdit.Password)
        self.password_check.setPlaceholderText("重复输入密码")
        form.addRow("重复密码", self.password_check)

        self.link_input = QLineEdit(self.item_data.get("LinkURL", ""))
        self.link_input.setPlaceholderText("关联网址（可选）")
        form.addRow("关联地址", self.link_input)

        self.note_input = QLineEdit(self.item_data.get("Note", ""))
        self.note_input.setPlaceholderText("备注（可选）")
        form.addRow("备注", self.note_input)

        root.addLayout(form)
        root.addStretch()

        btns = QHBoxLayout()
        btns.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setObjectName("PrimaryBtn")
        save_btn.clicked.connect(self._save_item)
        btns.addWidget(save_btn)

        root.addLayout(btns)

    def _save_item(self):
        self.item_data = {
            "URL": self.url_input.text().strip(),
            "UserName": self.username_input.text().strip(),
            "Password": self.password_input.text().strip(),
            "LinkURL": self.link_input.text().strip(),
            "Note": self.note_input.text().strip(),
        }
        if not self.item_data["URL"]:
            ErrorDialog(self, "网址不能为空").exec_()
            return
        if not self.item_data["UserName"]:
            ErrorDialog(self, "用户名不能为空").exec_()
            return
        if self.item_data["Password"] != self.password_check.text().strip():
            ErrorDialog(self, "两次输入密码不一致").exec_()
            return
        self.accept()


class MainWindow(QMainWindow):
    """密码本主界面（Edge 风格双栏视图）。"""

    LIST_COLUMNS = [
        "条目ID",
        "网址",
        "用户名",
        "密码等级",
        "最近使用时间",
        "最后修改时间",
        "备注",
    ]
    VERIFY_FAIL_THRESHOLD = 5
    VERIFY_LOCK_BASE_SECONDS = 30
    VERIFY_LOCK_MAX_SECONDS = 120
    CLIPBOARD_CLEAR_MS = int(os.getenv("KEYWORD_NOTEBOOK_CLIPBOARD_CLEAR_MS", "20000"))
    CLIPBOARD_FORCE_CLEAR = os.getenv("KEYWORD_NOTEBOOK_CLIPBOARD_FORCE_CLEAR", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    def __init__(self, password_book: PasswordNotebook):
        super().__init__()
        self.password_book = password_book

        self.all_items: list[dict[str, Any]] = []
        self.filtered_items: list[dict[str, Any]] = []
        self.duplicate_items_cache: list[dict[str, Any]] = []
        self.duplicate_cache_valid = False
        self.current_item_id: str | None = None
        self.current_plain_password: str | None = None
        self.current_segment = "all"
        self._verify_failed_attempts = 0
        self._verify_lock_until_ts = 0.0

        self.reveal_timer = QTimer(self)
        self.reveal_timer.setInterval(15000)
        self.reveal_timer.timeout.connect(self._hide_password)

        self.filter_debounce_timer = QTimer(self)
        self.filter_debounce_timer.setSingleShot(True)
        self.filter_debounce_timer.setInterval(200)
        self.filter_debounce_timer.timeout.connect(self._apply_filters)

        self.deferred_flush_timer = QTimer(self)
        self.deferred_flush_timer.setInterval(3000)
        self.deferred_flush_timer.timeout.connect(self._flush_deferred_sync)

        self.clipboard_clear_timer = QTimer(self)
        self.clipboard_clear_timer.setSingleShot(True)
        self.clipboard_clear_timer.setInterval(self.CLIPBOARD_CLEAR_MS)
        self.clipboard_clear_timer.timeout.connect(self._clear_clipboard_sensitive_content)
        self._last_copied_sensitive_text: str | None = None

        self.item_table: QTableWidget | None = None
        self.status_bar: QStatusBar | None = None
        self.search_input: QLineEdit | None = None
        self.level_filter: QComboBox | None = None
        self.count_label: QLabel | None = None
        self.weak_label: QLabel | None = None
        self.strong_label: QLabel | None = None

        self.detail_url: QLabel | None = None
        self.detail_username: QLabel | None = None
        self.detail_password: QLabel | None = None
        self.detail_link: QLabel | None = None
        self.detail_level: QLabel | None = None
        self.detail_note: QLabel | None = None
        self.copy_tip_label: QLabel | None = None
        self.segment_all_btn: QPushButton | None = None
        self.segment_weak_btn: QPushButton | None = None
        self.segment_dup_btn: QPushButton | None = None
        self.segment_track: QFrame | None = None
        self.segment_indicator: QFrame | None = None
        self.segment_anim: QPropertyAnimation | None = None
        self._duplicate_warmup_thread: QThread | None = None
        self._duplicate_warmup_worker: DuplicateWarmupWorker | None = None
        self._duplicate_warmup_in_progress = False

        self.setWindowTitle("密码本管理器")
        self.setMinimumSize(1100, 680)
        self.resize(1280, 820)
        self.setStyleSheet(EDGE_LIGHT_STYLESHEET)

        self.init_ui()
        self.deferred_flush_timer.start()
        QTimer.singleShot(0, self._load_initial_items)

    def init_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(14, 12, 14, 12)
        root_layout.setSpacing(10)
        self.setCentralWidget(root)

        root_layout.addWidget(self._build_top_bar())
        root_layout.addWidget(self._build_content_splitter(), 1)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪")

        self._install_shortcuts()

    def _build_top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("TopBar")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        title = QLabel("密码")
        title.setObjectName("TitleLabel")
        title.setMinimumWidth(60)
        layout.addWidget(title)

        self.segment_track = QFrame()
        self.segment_track.setObjectName("SegmentTrack")
        self.segment_track.setFixedHeight(34)
        segment_layout = QHBoxLayout(self.segment_track)
        segment_layout.setContentsMargins(2, 2, 2, 2)
        segment_layout.setSpacing(2)

        self.segment_indicator = QFrame(self.segment_track)
        self.segment_indicator.setObjectName("SegmentIndicator")
        self.segment_indicator.setGeometry(0, 0, 0, 0)

        self.segment_anim = QPropertyAnimation(self.segment_indicator, b"geometry", self)
        self.segment_anim.setDuration(200)
        self.segment_anim.setEasingCurve(QEasingCurve.OutCubic)

        self.segment_all_btn = QPushButton("全部")
        self.segment_all_btn.setCheckable(True)
        self.segment_all_btn.setObjectName("SegmentBtn")
        self.segment_all_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.segment_all_btn.clicked.connect(lambda: self._set_segment("all"))
        segment_layout.addWidget(self.segment_all_btn)

        self.segment_weak_btn = QPushButton("弱密码")
        self.segment_weak_btn.setCheckable(True)
        self.segment_weak_btn.setObjectName("SegmentBtn")
        self.segment_weak_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.segment_weak_btn.clicked.connect(lambda: self._set_segment("weak"))
        segment_layout.addWidget(self.segment_weak_btn)

        self.segment_dup_btn = QPushButton("重复密码")
        self.segment_dup_btn.setCheckable(True)
        self.segment_dup_btn.setObjectName("SegmentBtn")
        self.segment_dup_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.segment_dup_btn.clicked.connect(lambda: self._set_segment("duplicate"))
        segment_layout.addWidget(self.segment_dup_btn)

        layout.addWidget(self.segment_track)

        self._refresh_segment_buttons()
        QTimer.singleShot(0, lambda: self._sync_segment_indicator(animate=False))

        self.count_label = QLabel("总数 0")
        self.count_label.setObjectName("MutedText")
        layout.addWidget(self.count_label)

        self.weak_label = QLabel("弱 0")
        self.weak_label.setObjectName("MutedText")
        layout.addWidget(self.weak_label)

        self.strong_label = QLabel("强 0")
        self.strong_label.setObjectName("MutedText")
        layout.addWidget(self.strong_label)

        layout.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索网址 / 用户名 / 备注")
        self.search_input.setMinimumWidth(320)
        self.search_input.textChanged.connect(self._schedule_apply_filters)
        layout.addWidget(self.search_input)

        self.level_filter = QComboBox()
        self.level_filter.addItems(["全部等级", "弱密码(0-1)", "中等(2-3)", "强密码(4-5)"])
        self.level_filter.currentIndexChanged.connect(self._schedule_apply_filters)
        layout.addWidget(self.level_filter)

        add_btn = QPushButton("新增")
        add_btn.setObjectName("PrimaryBtn")
        add_btn.setCursor(QCursor(Qt.PointingHandCursor))
        add_btn.clicked.connect(self._on_add_item_click)
        layout.addWidget(add_btn)

        import_btn = QPushButton("导入")
        import_btn.setCursor(QCursor(Qt.PointingHandCursor))
        import_btn.clicked.connect(self._on_import_browser_passwords)
        layout.addWidget(import_btn)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        refresh_btn.clicked.connect(self._refresh_items)
        layout.addWidget(refresh_btn)

        return bar

    def _build_content_splitter(self) -> QSplitter:
        splitter = QSplitter(Qt.Horizontal)

        left_panel = QFrame()
        left_panel.setObjectName("Card")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        self.item_table = QTableWidget()
        self.item_table.setColumnCount(len(self.LIST_COLUMNS))
        self.item_table.setHorizontalHeaderLabels(self.LIST_COLUMNS)
        self.item_table.verticalHeader().setVisible(False)
        self.item_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.item_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.item_table.setSortingEnabled(True)
        self.item_table.setColumnHidden(0, True)
        self.item_table.setAlternatingRowColors(False)
        self.item_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.item_table.customContextMenuRequested.connect(self._show_table_context_menu)
        self.item_table.itemSelectionChanged.connect(self._on_table_selection_changed)

        header = self.item_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.resizeSection(3, 90)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)

        left_layout.addWidget(self.item_table)

        right_panel = self._build_detail_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([760, 420])
        return splitter

    def _build_detail_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")

        root = QVBoxLayout(card)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        title = QLabel("详情")
        title.setObjectName("TitleLabel")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setVerticalSpacing(10)
        grid.setHorizontalSpacing(8)

        def make_value_label() -> QLabel:
            lab = QLabel("-")
            lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lab.setWordWrap(True)
            return lab

        self.detail_url = make_value_label()
        self.detail_username = make_value_label()
        self.detail_password = make_value_label()
        self.detail_link = make_value_label()
        self.detail_level = make_value_label()
        self.detail_note = make_value_label()

        grid.addWidget(QLabel("网址"), 0, 0)
        grid.addWidget(self.detail_url, 0, 1)
        grid.addWidget(self._create_detail_copy_button(self.detail_url, "网址"), 0, 2)

        grid.addWidget(QLabel("用户名"), 1, 0)
        grid.addWidget(self.detail_username, 1, 1)
        grid.addWidget(self._create_detail_copy_button(self.detail_username, "用户名"), 1, 2)

        grid.addWidget(QLabel("密码"), 2, 0)
        grid.addWidget(self.detail_password, 2, 1)

        grid.addWidget(QLabel("关联地址"), 3, 0)
        grid.addWidget(self.detail_link, 3, 1)
        grid.addWidget(self._create_detail_copy_button(self.detail_link, "关联地址"), 3, 2)

        grid.addWidget(QLabel("密码等级"), 4, 0)
        grid.addWidget(self.detail_level, 4, 1)

        grid.addWidget(QLabel("备注"), 5, 0)
        grid.addWidget(self.detail_note, 5, 1)
        grid.addWidget(self._create_detail_copy_button(self.detail_note, "备注"), 5, 2)

        root.addLayout(grid)

        row1 = QHBoxLayout()
        reveal_btn = QPushButton("显示密码")
        reveal_btn.setObjectName("PrimaryBtn")
        reveal_btn.clicked.connect(self._on_show_password_click)
        row1.addWidget(reveal_btn)

        copy_pwd_btn = QPushButton("复制密码")
        copy_pwd_btn.clicked.connect(self._on_copy_password_click)
        row1.addWidget(copy_pwd_btn)

        root.addLayout(row1)

        row2 = QHBoxLayout()
        copy_user_btn = QPushButton("复制用户名")
        copy_user_btn.clicked.connect(self._on_copy_username_click)
        row2.addWidget(copy_user_btn)

        open_url_btn = QPushButton("打开网址")
        open_url_btn.clicked.connect(self._on_open_url_click)
        row2.addWidget(open_url_btn)

        root.addLayout(row2)

        row3 = QHBoxLayout()
        edit_btn = QPushButton("修改")
        edit_btn.clicked.connect(self._on_edit_item_click)
        row3.addWidget(edit_btn)

        delete_btn = QPushButton("删除")
        delete_btn.setObjectName("DangerBtn")
        delete_btn.clicked.connect(self._on_delete_item_click)
        row3.addWidget(delete_btn)

        root.addLayout(row3)
        root.addStretch()

        hint = QLabel("提示：明文密码将自动在 15 秒后隐藏。")
        hint.setObjectName("MutedText")
        root.addWidget(hint)

        self.copy_tip_label = QLabel("")
        self.copy_tip_label.setObjectName("MutedText")
        self.copy_tip_label.setVisible(False)
        root.addWidget(self.copy_tip_label)

        return card

    def _set_segment(self, segment: str):
        if self.current_segment == segment:
            return
        self.current_segment = segment
        self._refresh_segment_buttons()
        self._sync_segment_indicator(animate=True)
        self._apply_filters()

    def _refresh_segment_buttons(self):
        if not self.segment_all_btn:
            return
        self.segment_all_btn.setChecked(self.current_segment == "all")
        self.segment_weak_btn.setChecked(self.current_segment == "weak")
        self.segment_dup_btn.setChecked(self.current_segment == "duplicate")

    def _current_segment_button(self) -> QPushButton | None:
        if self.current_segment == "weak":
            return self.segment_weak_btn
        if self.current_segment == "duplicate":
            return self.segment_dup_btn
        return self.segment_all_btn

    def _sync_segment_indicator(self, animate: bool):
        if not self.segment_track or not self.segment_indicator:
            return

        button = self._current_segment_button()
        if not button:
            return

        target = QRect(button.x(), button.y(), button.width(), button.height())
        current = self.segment_indicator.geometry()

        self.segment_indicator.show()
        self.segment_indicator.lower()
        self.segment_all_btn.raise_()
        self.segment_weak_btn.raise_()
        self.segment_dup_btn.raise_()

        can_animate = (
            animate
            and self.segment_anim is not None
            and current.width() > 0
            and current.height() > 0
        )

        if can_animate:
            self.segment_anim.stop()
            self.segment_anim.setStartValue(current)
            self.segment_anim.setEndValue(target)
            self.segment_anim.start()
            return

        self.segment_indicator.setGeometry(target)

    def _install_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._focus_search)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._on_add_item_click)
        QShortcut(QKeySequence("F5"), self, activated=self._refresh_items)

        copy_user_action = QAction(self)
        copy_user_action.setShortcut(QKeySequence("Ctrl+Shift+U"))
        copy_user_action.triggered.connect(self._on_copy_username_click)
        self.addAction(copy_user_action)

    def _focus_search(self):
        if self.search_input:
            self.search_input.setFocus()
            self.search_input.selectAll()

    def _refresh_items(self):
        self._hide_password()
        self._load_items_from_core()
        self._apply_filters()
        self.status_bar.showMessage("已刷新")

    def _load_initial_items(self):
        self._load_items_from_core()
        self._apply_filters()
        # 稍后再做后台预热，避免挤占刚进入主界面的响应时间
        QTimer.singleShot(1200, self._start_duplicate_warmup)

    def _load_items_from_core(self):
        self.all_items = self.password_book.list_items()
        self.duplicate_cache_valid = False
        total = len(self.all_items)
        weak = len([x for x in self.all_items if int(x.get("PasswordLevel", 0)) <= 1])
        strong = len([x for x in self.all_items if int(x.get("PasswordLevel", 0)) >= 4])

        self.count_label.setText(f"总数 {total}")
        self.weak_label.setText(f"弱 {weak}")
        self.strong_label.setText(f"强 {strong}")

    def _schedule_apply_filters(self):
        self.filter_debounce_timer.start()

    def _refresh_duplicate_cache(self):
        self.duplicate_items_cache = self.password_book.list_duplicate_password_items()
        self.duplicate_cache_valid = True

    def _start_duplicate_warmup(self):
        if self.duplicate_cache_valid or self._duplicate_warmup_in_progress:
            return

        self._duplicate_warmup_in_progress = True
        self._duplicate_warmup_thread = QThread(self)
        self._duplicate_warmup_worker = DuplicateWarmupWorker(self.password_book)
        self._duplicate_warmup_worker.moveToThread(self._duplicate_warmup_thread)

        self._duplicate_warmup_thread.started.connect(self._duplicate_warmup_worker.run)
        self._duplicate_warmup_worker.finished.connect(self._on_duplicate_warmup_finished)
        self._duplicate_warmup_worker.failed.connect(self._on_duplicate_warmup_failed)
        self._duplicate_warmup_worker.finished.connect(self._duplicate_warmup_thread.quit)
        self._duplicate_warmup_worker.failed.connect(self._duplicate_warmup_thread.quit)
        self._duplicate_warmup_thread.finished.connect(self._cleanup_duplicate_warmup)

        self._duplicate_warmup_thread.start()

    def _on_duplicate_warmup_finished(self, data: list):
        self.duplicate_items_cache = data
        self.duplicate_cache_valid = True
        self._duplicate_warmup_in_progress = False
        logger.debug("重复密码后台预热完成，count=%s", len(data))
        if self.current_segment == "duplicate":
            self._apply_filters()

    def _on_duplicate_warmup_failed(self, message: str):
        self._duplicate_warmup_in_progress = False
        logger.warning("重复密码后台预热失败: %s", message)

    def _cleanup_duplicate_warmup(self):
        if self._duplicate_warmup_worker:
            self._duplicate_warmup_worker.deleteLater()
            self._duplicate_warmup_worker = None
        if self._duplicate_warmup_thread:
            self._duplicate_warmup_thread.deleteLater()
            self._duplicate_warmup_thread = None

    def _apply_filters(self):
        keyword = (self.search_input.text().strip().lower() if self.search_input else "")
        level_mode = self.level_filter.currentIndex() if self.level_filter else 0

        def pass_level(level: int) -> bool:
            if level_mode == 1:
                return level <= 1
            if level_mode == 2:
                return 2 <= level <= 3
            if level_mode == 3:
                return level >= 4
            return True

        source_items = self.all_items
        if self.current_segment == "duplicate":
            if not self.duplicate_cache_valid:
                self._start_duplicate_warmup()
                if self._duplicate_warmup_in_progress:
                    source_items = []
                else:
                    self._refresh_duplicate_cache()
                    source_items = self.duplicate_items_cache
            else:
                source_items = self.duplicate_items_cache

        result: list[dict[str, Any]] = []
        for item in source_items:
            text = " ".join(
                [
                    str(item.get("URL", "")),
                    str(item.get("UserName", "")),
                    str(item.get("Note", "")),
                    str(item.get("LinkURL", "")),
                ]
            ).lower()
            level = int(item.get("PasswordLevel", 0))

            if keyword and keyword not in text:
                continue
            if self.current_segment == "weak" and level > 1:
                continue
            if not pass_level(level):
                continue
            result.append(item)

        self.filtered_items = result
        self._render_table()

    def _render_table(self):
        self.item_table.setSortingEnabled(False)
        self.item_table.setRowCount(0)

        for row, item in enumerate(self.filtered_items):
            self.item_table.insertRow(row)
            self.item_table.setRowHeight(row, 34)

            self.item_table.setItem(row, 0, QTableWidgetItem(str(item.get("Index", ""))))
            self.item_table.setItem(row, 1, QTableWidgetItem(str(item.get("URL", ""))))
            self.item_table.setItem(row, 2, QTableWidgetItem(str(item.get("UserName", ""))))
            self.item_table.setItem(row, 3, QTableWidgetItem(str(item.get("PasswordLevel", ""))))

            last_used_at = str(item.get("LastUsedAt", ""))
            updated_at = str(item.get("UpdatedAt", ""))
            self.item_table.setItem(
                row,
                4,
                RelativeTimeItem(self._format_relative_time(last_used_at), last_used_at),
            )
            self.item_table.setItem(
                row,
                5,
                RelativeTimeItem(self._format_relative_time(updated_at), updated_at),
            )
            self.item_table.setItem(row, 6, QTableWidgetItem(str(item.get("Note", ""))))

        self.item_table.setSortingEnabled(True)

        if self.filtered_items:
            self.item_table.selectRow(0)
        else:
            self.current_item_id = None
            self._render_detail(None)

        self.status_bar.showMessage(f"显示 {len(self.filtered_items)} / {len(self.all_items)} 条")

    def _show_table_context_menu(self, pos):
        row = self.item_table.rowAt(pos.y())
        if row < 0:
            return

        self.item_table.selectRow(row)
        menu = QMenu(self)

        act_show = menu.addAction("显示密码")
        act_copy_user = menu.addAction("复制用户名")
        act_copy_pwd = menu.addAction("复制密码")
        menu.addSeparator()
        act_edit = menu.addAction("修改")
        act_del = menu.addAction("删除")

        chosen = menu.exec_(self.item_table.viewport().mapToGlobal(pos))
        if chosen == act_show:
            self._on_show_password_click()
        elif chosen == act_copy_user:
            self._on_copy_username_click()
        elif chosen == act_copy_pwd:
            self._on_copy_password_click()
        elif chosen == act_edit:
            self._on_edit_item_click()
        elif chosen == act_del:
            self._on_delete_item_click()

    def _on_table_selection_changed(self):
        row = self._selected_row()
        if row < 0 or row >= len(self.filtered_items):
            self.current_item_id = None
            self._render_detail(None)
            return

        item = self.filtered_items[row]
        self.current_item_id = str(item.get("Index", ""))
        self._hide_password()
        self._render_detail(item)

    def _selected_row(self) -> int:
        indexes = self.item_table.selectionModel().selectedRows()
        if not indexes:
            return -1
        return indexes[0].row()

    def _selected_item(self) -> dict[str, Any] | None:
        row = self._selected_row()
        if row < 0 or row >= len(self.filtered_items):
            return None
        return self.filtered_items[row]

    def _render_detail(self, item: dict[str, Any] | None):
        if not item:
            self.detail_url.setText("-")
            self.detail_username.setText("-")
            self.detail_password.setText("-")
            self.detail_link.setText("-")
            self.detail_level.setText("-")
            self.detail_note.setText("-")
            return

        self.detail_url.setText(str(item.get("URL", "")))
        self.detail_username.setText(str(item.get("UserName", "")))
        self.detail_password.setText("********")
        self.detail_link.setText(str(item.get("LinkURL", "")) or "-")
        self.detail_level.setText(str(item.get("PasswordLevel", "")))
        self.detail_note.setText(str(item.get("Note", "")) or "-")

    def _ensure_item_selected(self) -> dict[str, Any] | None:
        item = self._selected_item()
        if not item:
            ErrorDialog(self, "请先从左侧列表选择一个条目").exec_()
            return None
        return item

    def _verify_action(self, action_name: str) -> str | None:
        now = time.time()
        if now < self._verify_lock_until_ts:
            wait_sec = int(self._verify_lock_until_ts - now + 0.999)
            ErrorDialog(self, f"验证尝试过于频繁，请在 {wait_sec} 秒后重试").exec_()
            return None

        verify_dialog = SecondaryVerifyDialog(action_name, self)
        if verify_dialog.exec_() != QDialog.Accepted:
            return None
        password = verify_dialog.input_password
        if not self.password_book.verify_master_key(password):
            self._verify_failed_attempts += 1
            lock_sec = _compute_lock_seconds(
                self._verify_failed_attempts,
                threshold=self.VERIFY_FAIL_THRESHOLD,
                base=self.VERIFY_LOCK_BASE_SECONDS,
                max_seconds=self.VERIFY_LOCK_MAX_SECONDS,
            )
            if lock_sec > 0:
                self._verify_lock_until_ts = time.time() + lock_sec
                logger.warning(
                    "二次验证失败触发冷却，action=%s, failed_attempts=%s, lock_seconds=%s",
                    action_name,
                    self._verify_failed_attempts,
                    lock_sec,
                )
            ErrorDialog(self, "密码验证失败").exec_()
            return None
        self._verify_failed_attempts = 0
        self._verify_lock_until_ts = 0.0
        return password

    def _on_add_item_click(self):
        user_password = self._verify_action("新增密码条目")
        if not user_password:
            return

        dlg = ItemEditDialog(parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return

        result = self.password_book.create_item(dlg.item_data, user_password=user_password)
        if result != "-1":
            self.status_bar.showMessage(f"新增成功：条目 {result}", 3000)
            self._refresh_items()
            return
        ErrorDialog(self, "新增失败，请重试").exec_()

    def _on_import_browser_passwords(self):
        user_password = self._verify_action("导入浏览器密码")
        if not user_password:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择浏览器导出的密码 CSV 文件",
            "",
            "CSV 文件 (*.csv)",
        )
        if not file_path:
            return

        items_to_import: list[dict[str, str]] = []
        skipped = 0
        try:
            with open(file_path, "r", encoding="utf-8-sig", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                if not reader.fieldnames:
                    ErrorDialog(self, "CSV 文件缺少表头，无法导入").exec_()
                    return
                for row in reader:
                    item_data = self._build_item_from_browser_row(row)
                    if not item_data:
                        skipped += 1
                        continue
                    items_to_import.append(item_data)
        except Exception as exc:
            ErrorDialog(self, f"读取 CSV 失败：{str(exc)}").exec_()
            return

        if not items_to_import:
            ErrorDialog(self, "没有可导入的有效密码条目").exec_()
            return

        confirm = ConfirmDialog(
            self,
            f"将导入 {len(items_to_import)} 条浏览器密码记录，是否继续？",
            "导入",
            "取消",
        )
        if confirm.exec_() != QDialog.Accepted:
            return

        created_ids = self.password_book.create_items_batch(items_to_import, user_password=user_password)
        if created_ids is None:
            ErrorDialog(self, "导入失败：密码验证未通过").exec_()
            return

        success = len(created_ids)
        failed = len(items_to_import) - success

        self._refresh_items()
        summary = f"导入完成：成功 {success} 条"
        if skipped:
            summary += f"，跳过 {skipped} 条"
        if failed:
            summary += f"，失败 {failed} 条"
        self.status_bar.showMessage(summary, 5000)
        ErrorDialog(self, summary, "知道了").exec_()

    @staticmethod
    def _normalize_csv_key(raw_key: str) -> str:
        key = str(raw_key or "").strip().lower()
        key = key.replace(" ", "").replace("_", "").replace("-", "")
        return key

    @staticmethod
    def _pick_csv_value(row: dict[str, str], keys: list[str]) -> str:
        for key in keys:
            value = row.get(key, "")
            if value:
                return str(value).strip()
        return ""

    def _build_item_from_browser_row(self, raw_row: dict[str, str]) -> dict[str, str] | None:
        normalized_row = {
            self._normalize_csv_key(key): str(value or "").strip()
            for key, value in raw_row.items()
            if key
        }

        url = self._pick_csv_value(normalized_row, ["url", "website", "site", "origin", "网址", "网站", "站点"])
        username = self._pick_csv_value(normalized_row, ["username", "user", "login", "用户名", "账号", "账户"])
        password = self._pick_csv_value(normalized_row, ["password", "密码"])
        note = self._pick_csv_value(normalized_row, ["note", "notes", "备注", "name", "名称"])

        if not url or not password:
            return None

        return KeyItem(
            {
                "URL": url,
                "UserName": username or "(空用户名)",
                "Password": password,
                "LinkURL": "",
                "Note": note,
            }
        )

    def _on_delete_item_click(self):
        item = self._ensure_item_selected()
        if not item:
            return

        user_password = self._verify_action("删除密码条目")
        if not user_password:
            return

        url = item.get("URL", "")
        confirm = ConfirmDialog(self, f"确定删除条目「{url}」吗？删除后不可恢复。", "删除", "取消")
        if confirm.exec_() != QDialog.Accepted:
            return

        ok = self.password_book.remove_item(str(item.get("Index", "")), user_password=user_password)
        if ok:
            self.status_bar.showMessage("删除成功", 3000)
            self._refresh_items()
            return
        ErrorDialog(self, "删除失败，请重试").exec_()

    def _on_edit_item_click(self):
        item = self._ensure_item_selected()
        if not item:
            return

        user_password = self._verify_action("修改密码条目")
        if not user_password:
            return

        item_id = str(item.get("Index", ""))
        full_data = self.password_book.get_item(item_id, user_password=user_password)
        if not full_data:
            ErrorDialog(self, "无法读取条目详情，修改已取消").exec_()
            return

        dlg = ItemEditDialog(full_data, self)
        if dlg.exec_() != QDialog.Accepted:
            return

        result = self.password_book.update_item(item_id, data=dlg.item_data, user_password=user_password)
        if result:
            self.status_bar.showMessage(f"修改成功：条目 {result}", 3000)
            self._refresh_items()
            return
        ErrorDialog(self, "修改失败，请重试").exec_()

    def _on_show_password_click(self):
        item = self._ensure_item_selected()
        if not item:
            return

        user_password = self._verify_action("查看密码")
        if not user_password:
            return

        item_id = str(item.get("Index", ""))
        full_data = self.password_book.get_item(item_id, user_password=user_password)
        if not full_data or "Password" not in full_data:
            ErrorDialog(self, "无法获取明文密码").exec_()
            return

        self.current_plain_password = str(full_data["Password"])
        self.detail_password.setText(self.current_plain_password)
        self.reveal_timer.start()
        self.status_bar.showMessage("密码已显示（15秒后自动隐藏）", 3000)

    def _hide_password(self):
        self.current_plain_password = None
        if self.detail_password:
            self.detail_password.setText("********")
        self.reveal_timer.stop()

    def _on_copy_username_click(self):
        item = self._ensure_item_selected()
        if not item:
            return
        username = str(item.get("UserName", ""))
        if not username:
            ErrorDialog(self, "当前条目没有用户名").exec_()
            return
        self._copy_to_clipboard_secure(username, "用户名")
        self._show_copy_tip("已复制用户名")

    def _on_copy_password_click(self):
        item = self._ensure_item_selected()
        if not item:
            return

        # 若明文密码已显示且仍在15秒可见窗口内，则允许直接复制，无需再次验证
        if self.current_plain_password and self.reveal_timer.isActive():
            self._copy_to_clipboard_secure(self.current_plain_password, "密码")
            self._show_copy_tip("已复制密码")
            return

        user_password = self._verify_action("复制密码")
        if not user_password:
            return

        item_id = str(item.get("Index", ""))
        full_data = self.password_book.get_item(item_id, user_password=user_password)
        if not full_data or "Password" not in full_data:
            ErrorDialog(self, "无法获取密码，复制失败").exec_()
            return

        self._copy_to_clipboard_secure(str(full_data["Password"]), "密码")
        self._show_copy_tip("已复制密码")

    def _on_open_url_click(self):
        item = self._ensure_item_selected()
        if not item:
            return

        raw_url = str(item.get("URL", "")).strip()
        if not raw_url:
            ErrorDialog(self, "当前条目没有网址").exec_()
            return

        if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
            raw_url = f"https://{raw_url}"

        opened = QDesktopServices.openUrl(QUrl(raw_url))
        if opened:
            self.status_bar.showMessage("已尝试在默认浏览器打开网址", 2000)
            return
        ErrorDialog(self, "打开网址失败，请检查网址格式").exec_()

    def _show_copy_tip(self, text: str):
        if not self.copy_tip_label:
            return
        self.copy_tip_label.setText(text)
        self.copy_tip_label.setVisible(True)
        QTimer.singleShot(1600, lambda: self.copy_tip_label.setVisible(False))

    @staticmethod
    def _format_relative_time(time_text: str) -> str:
        if not time_text:
            return "-"
        try:
            time_value = datetime.strptime(time_text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return time_text

        now = datetime.now()
        seconds = int((now - time_value).total_seconds())
        if seconds < 0:
            return time_text
        if seconds < 60:
            return "刚刚"

        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}分钟前"

        hours = minutes // 60
        if hours < 24:
            return f"{hours}小时前"

        days = hours // 24
        if days < 30:
            return f"{days}天前"

        return time_value.strftime("%Y-%m-%d")

    def _create_detail_copy_button(self, source_label: QLabel, label_name: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName("CopyIconBtn")
        button.setText("⧉")
        button.setCursor(QCursor(Qt.PointingHandCursor))
        button.setToolTip(f"复制{label_name}")
        button.clicked.connect(lambda: self._copy_label_value(source_label, label_name))
        return button

    def _copy_label_value(self, source_label: QLabel, label_name: str):
        text = source_label.text().strip()
        if not text or text == "-":
            ErrorDialog(self, f"当前条目没有{label_name}").exec_()
            return

        self._copy_to_clipboard_secure(text, label_name)
        self._show_copy_tip(f"已复制{label_name}")

    def _copy_to_clipboard_secure(self, text: str, label_name: str):
        QApplication.clipboard().setText(text)
        self._last_copied_sensitive_text = text
        if self.clipboard_clear_timer.isActive():
            self.clipboard_clear_timer.stop()
        self.clipboard_clear_timer.start()
        self.status_bar.showMessage(f"{label_name}已复制到剪贴板", 2500)

    def _clear_clipboard_sensitive_content(self):
        expected_text = self._last_copied_sensitive_text
        if not expected_text:
            return

        clipboard = QApplication.clipboard()
        if self.CLIPBOARD_FORCE_CLEAR:
            clipboard.clear()
            self.status_bar.showMessage("剪贴板中的敏感内容已强制清空", 2500)
        elif clipboard.text() == expected_text:
            clipboard.clear()
            self.status_bar.showMessage("剪贴板中的敏感内容已自动清空", 2500)
        else:
            self.status_bar.showMessage("剪贴板未清空（用户已改写）", 2500)
        self._last_copied_sensitive_text = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_segment_indicator(animate=False)

    def _flush_deferred_sync(self):
        self.password_book.flush_deferred_sync()

    def closeEvent(self, event):
        if self._duplicate_warmup_thread and self._duplicate_warmup_thread.isRunning():
            self._duplicate_warmup_thread.quit()
            self._duplicate_warmup_thread.wait(1000)
        if self.clipboard_clear_timer.isActive():
            self.clipboard_clear_timer.stop()
        self._clear_clipboard_sensitive_content()
        self._flush_deferred_sync()
        super().closeEvent(event)


if __name__ == "__main__":
    pass
