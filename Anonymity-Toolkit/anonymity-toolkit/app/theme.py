"""Colour system, fonts and spacing used across the GUI.

Each colour is a (light, dark) tuple. CustomTkinter picks the right one
automatically when the appearance mode changes, so pages never hard-code colours.
"""

COLORS = {
    "bg": ("#f6f8fa", "#0d1117"),
    "sidebar": ("#e6eaef", "#010409"),
    "card": ("#ffffff", "#161b22"),
    "card_border": ("#d0d7de", "#30363d"),
    "text": ("#1f2328", "#e6edf3"),
    "text_muted": ("#59636e", "#9da7b3"),
    "accent": ("#0969da", "#2f81f7"),
    "accent_hover": ("#0550ae", "#1f6feb"),
    "success": ("#1a7f37", "#3fb950"),
    "warning": ("#9a6700", "#d29922"),
    "error": ("#cf222e", "#f85149"),
    "simulated": ("#8250df", "#a371f7"),   # reserved for SIMULATED content only
    "online": ("#1a7f37", "#3fb950"),
    "offline": ("#59636e", "#9da7b3"),
}
BADGE_TEXT = ("#ffffff", "#0d1117")  # readable on the badge fills above

FONT_FAMILY = "Segoe UI"
FONTS = {
    "title": (FONT_FAMILY, 26, "bold"),
    "heading": (FONT_FAMILY, 18, "bold"),
    "body": (FONT_FAMILY, 14),
    "small": (FONT_FAMILY, 12),
    "mono": ("Consolas", 13),
}

PAD = 16
PAD_SMALL = 8
SIDEBAR_WIDTH = 220
MIN_WINDOW = (900, 600)
