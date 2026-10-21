"""Entry point: run with `python main.py`."""
import sys


def main() -> int:
    from app.logging_setup import configure_logging

    configure_logging()
    try:
        from app.main_window import MainWindow
    except ModuleNotFoundError as exc:  # most likely: customtkinter not installed
        print(f"Missing dependency: {exc.name}. Run: pip install -r requirements.txt")
        return 1

    window = MainWindow()
    window.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
