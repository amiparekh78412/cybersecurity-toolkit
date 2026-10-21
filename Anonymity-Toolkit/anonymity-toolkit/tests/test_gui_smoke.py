"""Opens every page once. Skipped automatically when customtkinter or a display is unavailable.

This is the only automated check that touches the real GUI. It uses a temporary data
folder, so it never reads or changes your saved data.
"""
import os
import tempfile
import unittest
from unittest import mock

try:
    import customtkinter  # noqa: F401
    import tkinter

    HAVE_GUI = True
except ImportError:
    HAVE_GUI = False


@unittest.skipUnless(HAVE_GUI, "customtkinter/tkinter not installed")
class GuiSmokeTests(unittest.TestCase):
    def test_every_page_opens_and_window_closes(self):
        from app.main_window import MainWindow
        from app.navigation import PAGES

        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"ANONYMITY_TOOLKIT_HOME": tmp}):
            try:
                window = MainWindow()
            except tkinter.TclError:
                self.skipTest("no display available")
            try:
                for spec in PAGES:
                    window.show_page(spec.key)
                    window.update()
                self.assertEqual(len(window._pages), len(PAGES))
                window.show_page("ip")  # revisit a page after switching away
                window.update()
            finally:
                window._on_close()


if __name__ == "__main__":
    unittest.main()
