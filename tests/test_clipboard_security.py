import unittest
from unittest.mock import patch

import UI


class FakeClipboard:
    def __init__(self):
        self._text = ""

    def setText(self, value: str):
        self._text = value

    def text(self) -> str:
        return self._text

    def clear(self):
        self._text = ""


class FakeStatusBar:
    def __init__(self):
        self.messages = []

    def showMessage(self, message: str, timeout: int = 0):
        self.messages.append((message, timeout))


class FakeTimer:
    def __init__(self):
        self.active = False
        self.start_calls = 0
        self.stop_calls = 0

    def isActive(self) -> bool:
        return self.active

    def start(self):
        self.active = True
        self.start_calls += 1

    def stop(self):
        self.active = False
        self.stop_calls += 1


class DummyWindow:
    def __init__(self, force_clear: bool = False):
        self.status_bar = FakeStatusBar()
        self.clipboard_clear_timer = FakeTimer()
        self.CLIPBOARD_FORCE_CLEAR = force_clear
        self._last_copied_sensitive_text = None

    def copy_secure(self, text: str, label_name: str):
        UI.MainWindow._copy_to_clipboard_secure(self, text, label_name)

    def clear_clipboard_sensitive_content(self):
        UI.MainWindow._clear_clipboard_sensitive_content(self)


class ClipboardSecurityTests(unittest.TestCase):
    def test_should_clear_clipboard_when_content_unchanged(self):
        clipboard = FakeClipboard()
        window = DummyWindow()

        with patch.object(UI.QApplication, "clipboard", return_value=clipboard):
            window.copy_secure("top-secret", "密码")
            self.assertEqual(clipboard.text(), "top-secret")
            self.assertTrue(window.clipboard_clear_timer.isActive())

            window.clear_clipboard_sensitive_content()

        self.assertEqual(clipboard.text(), "")
        self.assertTrue(any("已自动清空" in msg for msg, _ in window.status_bar.messages))

    def test_should_not_clear_when_user_replaced_clipboard_text(self):
        clipboard = FakeClipboard()
        window = DummyWindow()

        with patch.object(UI.QApplication, "clipboard", return_value=clipboard):
            window.copy_secure("top-secret", "密码")
            clipboard.setText("user-new-content")

            window.clear_clipboard_sensitive_content()

        self.assertEqual(clipboard.text(), "user-new-content")
        self.assertTrue(any("未清空（用户已改写）" in msg for msg, _ in window.status_bar.messages))

    def test_should_force_clear_even_when_user_replaced_clipboard_text(self):
        clipboard = FakeClipboard()
        window = DummyWindow(force_clear=True)

        with patch.object(UI.QApplication, "clipboard", return_value=clipboard):
            window.copy_secure("top-secret", "密码")
            clipboard.setText("user-new-content")

            window.clear_clipboard_sensitive_content()

        self.assertEqual(clipboard.text(), "")
        self.assertTrue(any("已强制清空" in msg for msg, _ in window.status_bar.messages))

    def test_should_restart_timer_and_use_latest_copied_text(self):
        clipboard = FakeClipboard()
        window = DummyWindow()

        with patch.object(UI.QApplication, "clipboard", return_value=clipboard):
            window.copy_secure("old-secret", "密码")
            window.copy_secure("new-secret", "密码")

            self.assertEqual(window.clipboard_clear_timer.start_calls, 2)
            self.assertGreaterEqual(window.clipboard_clear_timer.stop_calls, 1)

            window.clear_clipboard_sensitive_content()

        self.assertEqual(clipboard.text(), "")


if __name__ == "__main__":
    unittest.main()
