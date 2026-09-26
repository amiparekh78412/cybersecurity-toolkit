#!/usr/bin/env python3
"""
OSINT Investigator - Open Source Intelligence Investigation Dashboard
=======================================================================

A beginner-friendly, single-file Python GUI application for a cybersecurity
student project. It helps organize LEGAL, AUTHORIZED, PUBLIC-SOURCE OSINT
research: Google Dork generation, username/domain lookups, URL
analysis, note-taking, evidence/findings tracking, and report generation.

WHAT THIS TOOL DOES NOT DO (by design):
    - It does NOT bypass logins, CAPTCHAs, rate limits, or access controls.
    - It does NOT attempt password checking, credential stuffing, or
      account takeover.
    - It does NOT perform vulnerability scanning or exploitation.
    - It only builds search queries / public URLs and, where practical,
      reads plain public web pages (like a normal browser request would).

Run with:
    python osint_investigator.py

Optional dependency (nicer dark theme):
    pip install customtkinter
If customtkinter is not installed, the app automatically falls back to
plain Tkinter (which ships with Python) so it always runs.
"""

# ==============================================================
# IMPORTS
# ==============================================================

import json
import re
import socket
import webbrowser
from datetime import datetime
from urllib.parse import urlparse, parse_qsl, quote_plus

# Plain Tkinter is part of the Python standard library and is always used
# for the base widgets (frames, dialogs, message boxes). CustomTkinter is
# an optional "skin" that makes things look nicer - we try to use it, but
# the app works fine without it.
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False

# urllib is used instead of the third-party "requests" library so that the
# app has NO required external dependencies at all.
import urllib.request
import urllib.error


# ==============================================================
# CONFIGURATION
# ==============================================================

APP_TITLE = "OSINT Investigator - Open Source Intelligence Dashboard"
APP_MIN_WIDTH = 1150
APP_MIN_HEIGHT = 700

# A small "dark cybersecurity dashboard" color palette used everywhere in
# the app, whether or not CustomTkinter is available.
COLOR_BG = "#0d1117"            # main window background
COLOR_SIDEBAR = "#111820"       # sidebar background
COLOR_PANEL = "#161b22"         # cards / panels
COLOR_PANEL_ALT = "#1c232c"     # slightly lighter panel (rows, inputs)
COLOR_ACCENT = "#00d1b2"        # teal accent (buttons, highlights)
COLOR_ACCENT_DARK = "#00a894"
COLOR_TEXT = "#e6edf3"          # main text
COLOR_TEXT_DIM = "#8b949e"      # secondary / muted text
COLOR_WARN = "#f0b429"
COLOR_DANGER = "#f85149"
COLOR_OK = "#3fb950"
COLOR_BORDER = "#30363d"

FONT_NAME = "Segoe UI"          # falls back gracefully on non-Windows systems
FONT_TITLE = (FONT_NAME, 18, "bold")
FONT_HEADING = (FONT_NAME, 13, "bold")
FONT_NORMAL = (FONT_NAME, 10)
FONT_MONO = ("Consolas", 10)

# Network requests should never hang forever - a short timeout keeps the
# GUI from freezing when a site is slow or unreachable.
REQUEST_TIMEOUT_SECONDS = 4


# ==============================================================
# GLOBAL DATA
# ==============================================================
# For this version of the project, all investigation data is kept in
# simple Python lists/dictionaries in memory while the app runs. It can
# optionally be saved to / loaded from a JSON file.

class Investigation:
    """
    Holds all the data for the CURRENT investigation session.
    Using a single object (instead of scattered global variables) keeps
    the data organized, but the object itself is still just plain lists
    and dictionaries underneath - nothing fancy.
    """

    def __init__(self):
        self.target = ""                 # the main target (domain/username/etc.)
        self.status = "Not Started"       # Not Started / In Progress / Completed
        self.generated_queries = []       # list of dork/query strings generated
        self.findings = []                # list of finding dictionaries
        self.notes = []                   # list of note dictionaries
        self.next_finding_id = 1

    def add_queries(self, queries):
        """Add a list of newly generated search queries to the running total."""
        self.generated_queries.extend(queries)

    def add_note(self, text):
        note = {
            "id": len(self.notes) + 1,
            "text": text,
            "timestamp": now_string(),
        }
        self.notes.append(note)
        return note

    def add_finding(self, category, description, source_url, search_query, extra_notes=""):
        finding = {
            "id": self.next_finding_id,
            "category": category,
            "description": description,
            "source_url": source_url,
            "search_query": search_query,
            "notes": extra_notes,
            "timestamp": now_string(),
        }
        self.findings.append(finding)
        self.next_finding_id += 1
        return finding

    def to_dict(self):
        """Convert the investigation into a plain dictionary for JSON export."""
        return {
            "target": self.target,
            "status": self.status,
            "generated_queries": self.generated_queries,
            "findings": self.findings,
            "notes": self.notes,
            "next_finding_id": self.next_finding_id,
        }

    def load_from_dict(self, data):
        """Restore an investigation from a dictionary (loaded from JSON)."""
        self.target = data.get("target", "")
        self.status = data.get("status", "Not Started")
        self.generated_queries = data.get("generated_queries", [])
        self.findings = data.get("findings", [])
        self.notes = data.get("notes", [])
        self.next_finding_id = data.get("next_finding_id", len(self.findings) + 1)


# A single, shared Investigation object used by every module in the app.
investigation = Investigation()


# ==============================================================
# UTILITY FUNCTIONS
# ==============================================================

def now_string():
    """Return the current date/time as a readable string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_valid_domain(domain):
    """
    Very simple domain format check (not a full RFC validator).
    Accepts things like 'example.com' or 'sub.example.co.uk'.
    """
    domain = domain.strip().lower()
    pattern = r"^(?!-)[a-z0-9-]{1,63}(?<!-)(\.[a-z0-9-]{1,63})+$"
    return bool(re.match(pattern, domain))


def is_valid_url(url):
    """Check that a string parses into a URL with at least a scheme and host."""
    try:
        parsed = urlparse(url.strip())
        return bool(parsed.scheme) and bool(parsed.netloc)
    except ValueError:
        return False


def clean_domain_input(domain):
    """
    Turn something like 'https://example.com/page' into just 'example.com',
    so the user can paste a full URL and still get a clean domain.
    """
    domain = domain.strip()
    if "://" in domain:
        domain = urlparse(domain).netloc
    domain = domain.split("/")[0]
    return domain.lower().strip()


def google_search_url(query):
    """Build a normal Google search URL for a given query string."""
    return "https://www.google.com/search?q=" + quote_plus(query)


def safe_http_get_title(url):
    """
    Try to fetch a public web page and extract its <title> text.
    This is a NORMAL, non-invasive HTTP GET - the same kind of request any
    web browser makes when visiting a page. It never attempts to log in,
    bypass any protection, or send credentials of any kind.

    Returns (success: bool, result: str) where result is either the title
    or a human-readable error message.
    """
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (OSINT-Investigator-Student-Project)"},
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            html_bytes = response.read(200_000)  # read only the first part of the page
            html_text = html_bytes.decode("utf-8", errors="ignore")
            match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
            if match:
                title = re.sub(r"\s+", " ", match.group(1)).strip()
                return True, title if title else "(no title found)"
            return True, "(no title found)"
    except urllib.error.HTTPError as error:
        return False, "Site responded with HTTP error {}".format(error.code)
    except urllib.error.URLError:
        return False, "Information unavailable (could not connect)"
    except socket.timeout:
        return False, "Information unavailable (request timed out)"
    except Exception:
        return False, "Information unavailable"


def safe_dns_lookup(domain):
    """
    Try to resolve a domain name to an IP address using the standard
    socket library. This is normal, public DNS resolution - the same
    lookup that happens whenever you visit a website.
    """
    try:
        ip_address = socket.gethostbyname(domain)
        return True, ip_address
    except socket.gaierror:
        return False, "Information unavailable (DNS lookup failed)"
    except Exception:
        return False, "Information unavailable"


# ==============================================================
# GOOGLE DORK MODULE
# ==============================================================
# NOTE: These queries only use standard public search-engine operators
# (site:, filetype:, intitle:, inurl:) against PUBLICLY INDEXED pages.
# They never target passwords, API keys, tokens, or other secrets.

DORK_CATEGORIES = {
    "Documents": [
        'site:{domain} filetype:pdf',
        'site:{domain} filetype:doc',
        'site:{domain} filetype:docx',
        'site:{domain} filetype:xls',
        'site:{domain} filetype:xlsx',
        'site:{domain} filetype:ppt',
        'site:{domain} filetype:pptx',
    ],
    "Directory / Index Discovery": [
        'site:{domain} intitle:"index of"',
    ],
    "Login / Administrative Pages (public listing only)": [
        'site:{domain} inurl:login',
        'site:{domain} inurl:signin',
        'site:{domain} inurl:admin',
    ],
    "Information Discovery": [
        'site:{domain} "contact"',
        'site:{domain} "about"',
        'site:{domain} "documentation"',
        'site:{domain} "policy"',
    ],
    "Technology / Development": [
        'site:{domain} "github"',
        'site:{domain} "api"',
        'site:{domain} "documentation"',
    ],
}


def generate_dorks(domain, selected_categories=None):
    """
    Build a dictionary of {category_name: [list of query strings]} for the
    given domain. If selected_categories is given, only build those
    categories; otherwise build all of them.
    """
    domain = clean_domain_input(domain)
    categories = selected_categories or list(DORK_CATEGORIES.keys())
    results = {}
    for category in categories:
        templates = DORK_CATEGORIES.get(category, [])
        results[category] = [template.format(domain=domain) for template in templates]
    return results


# ==============================================================
# USERNAME OSINT MODULE
# ==============================================================
# We only ever CONSTRUCT normal public profile URLs. Optional availability
# checking uses a plain HTTP GET, the same as a browser visiting the page.

USERNAME_PLATFORMS = {
    "GitHub": "https://github.com/{u}",
    "GitLab": "https://gitlab.com/{u}",
    "Reddit": "https://www.reddit.com/user/{u}",
    "X (Twitter)": "https://x.com/{u}",
    "Instagram": "https://www.instagram.com/{u}/",
    "YouTube": "https://www.youtube.com/@{u}",
    "Medium": "https://medium.com/@{u}",
    "Dev.to": "https://dev.to/{u}",
}


def build_username_profiles(username):
    """Return a list of (platform_name, url) tuples for a given username."""
    username = username.strip()
    profiles = []
    for platform, template in USERNAME_PLATFORMS.items():
        url = template.format(u=quote_plus(username))
        profiles.append((platform, url))
    return profiles


def check_profile_status(url):
    """
    Conservative, best-effort check of whether a public profile page
    appears to exist. This performs one normal GET request per platform -
    it does NOT bypass CAPTCHAs, logins, or rate limits, and many
    platforms may block automated checks entirely (which is expected and
    handled gracefully below).
    """
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (OSINT-Investigator-Student-Project)"},
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if response.status == 200:
                return "Open"
            return "Unknown ({})".format(response.status)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return "Not Found"
        return "Unknown (HTTP {})".format(error.code)
    except Exception:
        return "Unknown (blocked/unavailable)"


# ==============================================================
# DOMAIN OSINT MODULE
# ==============================================================

def gather_domain_info(domain):
    """
    Collect basic, publicly available information about a domain:
    normalized domain, website URL, DNS (IP address), and page title
    (if reachable). Every step degrades gracefully to "Information
    unavailable" instead of crashing if something cannot be retrieved.
    """
    domain = clean_domain_input(domain)
    info = {"Domain": domain}

    website_url = "https://{}".format(domain)
    info["Website URL"] = website_url

    dns_ok, dns_result = safe_dns_lookup(domain)
    info["DNS (IP Address)"] = dns_result if dns_ok else dns_result

    if dns_ok:
        title_ok, title_result = safe_http_get_title(website_url)
        info["HTTPS Availability"] = "Reachable" if title_ok else title_result
        info["Website Title"] = title_result if title_ok else "Information unavailable"
    else:
        info["HTTPS Availability"] = "Information unavailable"
        info["Website Title"] = "Information unavailable"

    return info


# ==============================================================
# URL ANALYSIS MODULE
# ==============================================================

def analyze_url(url):
    """
    Break a URL down into its parts using Python's standard urllib.parse
    library. Purely informational - no requests are made to the URL here.
    """
    url = url.strip()
    parsed = urlparse(url)
    query_pairs = parse_qsl(parsed.query)

    return {
        "Full URL": url,
        "Protocol": parsed.scheme or "(none)",
        "Domain": parsed.hostname or "(none)",
        "Port": str(parsed.port) if parsed.port else "(default)",
        "Path": parsed.path or "(none)",
        "Query Parameters": ", ".join(
            "{}={}".format(k, v) for k, v in query_pairs
        ) if query_pairs else "(none)",
        "Fragment": parsed.fragment or "(none)",
    }


# ==============================================================
# REPORT GENERATOR
# ==============================================================

REPORT_DISCLAIMER = (
    "This report contains information collected from publicly available "
    "sources for authorized educational/investigative use only. No "
    "authentication bypass, unauthorized access, or exploitation was "
    "performed in the collection of this information."
)


def build_report_text():
    """Build the full investigation report as a plain-text string."""
    lines = []
    lines.append("OSINT INVESTIGATION REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Investigation Target: {}".format(investigation.target or "(not set)"))
    lines.append("Status: {}".format(investigation.status))
    lines.append("Report Generated: {}".format(now_string()))
    lines.append("")

    lines.append("-" * 60)
    lines.append("GENERATED QUERIES ({})".format(len(investigation.generated_queries)))
    lines.append("-" * 60)
    if investigation.generated_queries:
        for query in investigation.generated_queries:
            lines.append("  - {}".format(query))
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("-" * 60)
    lines.append("FINDINGS ({})".format(len(investigation.findings)))
    lines.append("-" * 60)
    if investigation.findings:
        for finding in investigation.findings:
            lines.append("Finding #{}".format(finding["id"]))
            lines.append("  Category:      {}".format(finding["category"]))
            lines.append("  Description:   {}".format(finding["description"]))
            lines.append("  Source URL:    {}".format(finding["source_url"]))
            lines.append("  Search Query:  {}".format(finding["search_query"]))
            if finding.get("notes"):
                lines.append("  Notes:         {}".format(finding["notes"]))
            lines.append("  Recorded:      {}".format(finding["timestamp"]))
            lines.append("")
    else:
        lines.append("  (none)")
        lines.append("")

    lines.append("-" * 60)
    lines.append("INVESTIGATION NOTES ({})".format(len(investigation.notes)))
    lines.append("-" * 60)
    if investigation.notes:
        for note in investigation.notes:
            lines.append("  [{}] {}".format(note["timestamp"], note["text"]))
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("-" * 60)
    lines.append("DISCLAIMER")
    lines.append("-" * 60)
    lines.append(REPORT_DISCLAIMER)

    return "\n".join(lines)


def build_report_html():
    """Build the full investigation report as a simple, readable HTML page."""
    def escape(text):
        text = str(text)
        return (text.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace('"', "&quot;"))

    findings_html = ""
    if investigation.findings:
        for finding in investigation.findings:
            findings_html += """
            <div class="card">
                <h3>Finding #{id}: {category}</h3>
                <p><b>Description:</b> {description}</p>
                <p><b>Source URL:</b> {source_url}</p>
                <p><b>Search Query:</b> <code>{search_query}</code></p>
                <p><b>Notes:</b> {notes}</p>
                <p class="timestamp">Recorded: {timestamp}</p>
            </div>
            """.format(
                id=finding["id"],
                category=escape(finding["category"]),
                description=escape(finding["description"]),
                source_url=escape(finding["source_url"]),
                search_query=escape(finding["search_query"]),
                notes=escape(finding.get("notes", "")),
                timestamp=escape(finding["timestamp"]),
            )
    else:
        findings_html = "<p>(none)</p>"

    notes_html = ""
    if investigation.notes:
        for note in investigation.notes:
            notes_html += "<li><span class='timestamp'>[{}]</span> {}</li>".format(
                escape(note["timestamp"]), escape(note["text"])
            )
    else:
        notes_html = "<li>(none)</li>"

    queries_html = ""
    if investigation.generated_queries:
        for query in investigation.generated_queries:
            queries_html += "<li><code>{}</code></li>".format(escape(query))
    else:
        queries_html = "<li>(none)</li>"

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>OSINT Investigation Report - {target}</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#0d1117;
                    color:#e6edf3; padding: 30px; }}
            h1 {{ color:#00d1b2; }}
            h2 {{ color:#00d1b2; border-bottom: 1px solid #30363d; padding-bottom:6px; }}
            .meta {{ color:#8b949e; margin-bottom: 20px;}}
            .card {{ background:#161b22; border:1px solid #30363d; border-radius:8px;
                      padding:14px; margin-bottom:12px; }}
            .timestamp {{ color:#8b949e; font-size: 0.85em; }}
            code {{ background:#1c232c; padding:2px 6px; border-radius:4px; }}
            .disclaimer {{ background:#1c232c; border-left:4px solid #f0b429;
                            padding:12px; margin-top:20px; }}
        </style>
    </head>
    <body>
        <h1>OSINT Investigation Report</h1>
        <p class="meta">
            <b>Target:</b> {target} &nbsp;|&nbsp;
            <b>Status:</b> {status} &nbsp;|&nbsp;
            <b>Generated:</b> {generated}
        </p>

        <h2>Generated Queries ({query_count})</h2>
        <ul>{queries_html}</ul>

        <h2>Findings ({finding_count})</h2>
        {findings_html}

        <h2>Investigation Notes ({note_count})</h2>
        <ul>{notes_html}</ul>

        <div class="disclaimer"><b>Disclaimer:</b> {disclaimer}</div>
    </body>
    </html>
    """.format(
        target=escape(investigation.target or "(not set)"),
        status=escape(investigation.status),
        generated=escape(now_string()),
        query_count=len(investigation.generated_queries),
        queries_html=queries_html,
        finding_count=len(investigation.findings),
        findings_html=findings_html,
        note_count=len(investigation.notes),
        notes_html=notes_html,
        disclaimer=REPORT_DISCLAIMER,
    )
    return html


# ==============================================================
# MAIN GUI
# ==============================================================
# Everything below builds the actual window. Plain Tkinter (ttk) widgets
# are used throughout and manually colored to create a dark dashboard
# look, so the app runs on any standard Python install. If CustomTkinter
# is installed, a couple of small visual touches (like the appearance
# mode) are enabled automatically, but the widget logic stays identical.

if CTK_AVAILABLE:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")


def make_scrollable_frame(parent, bg=COLOR_PANEL):
    """
    Helper that creates a vertically scrollable area. Returns the
    scrollable inner frame that content should be placed into.
    This is used for result areas that can grow long (dorks, findings...).
    """
    container = tk.Frame(parent, bg=bg)
    canvas = tk.Canvas(container, bg=bg, highlightthickness=0)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    inner_frame = tk.Frame(canvas, bg=bg)

    inner_frame.bind(
        "<Configure>",
        lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.create_window((0, 0), window=inner_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    container.pack(fill="both", expand=True)

    return inner_frame


class StyledButton(tk.Button):
    """A small helper so every button in the app looks consistent."""

    def __init__(self, parent, text, command, kind="primary", **kwargs):
        colors = {
            "primary": (COLOR_ACCENT, "#00221d"),
            "secondary": (COLOR_PANEL_ALT, COLOR_TEXT),
            "danger": (COLOR_DANGER, "#2a0a08"),
        }
        bg, fg = colors.get(kind, colors["primary"])
        super().__init__(
            parent, text=text, command=command,
            bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
            font=FONT_NORMAL, relief="flat", padx=10, pady=6,
            cursor="hand2", bd=0, **kwargs
        )


class OsintInvestigatorApp:
    """The main application window and controller for all modules."""

    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("{}x{}".format(APP_MIN_WIDTH, APP_MIN_HEIGHT))
        self.root.minsize(APP_MIN_WIDTH, APP_MIN_HEIGHT)
        self.root.configure(bg=COLOR_BG)

        self._setup_styles()

        # Top bar with the shared "current target" field
        self._build_topbar()

        # Main layout: sidebar (left) + content area (right)
        body = tk.Frame(self.root, bg=COLOR_BG)
        body.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(body, bg=COLOR_SIDEBAR, width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = tk.Frame(body, bg=COLOR_BG)
        self.content.pack(side="left", fill="both", expand=True)

        # Each "page" is a frame stacked in the same spot; only one is
        # shown at a time (a common, simple Tkinter navigation pattern).
        self.pages = {}
        self._build_sidebar_nav()
        self._build_all_pages()

        self.show_page("Dashboard")

    # ---------------------------------------------------------
    # Styling / layout scaffolding
    # ---------------------------------------------------------

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Treeview",
                         background=COLOR_PANEL_ALT,
                         fieldbackground=COLOR_PANEL_ALT,
                         foreground=COLOR_TEXT,
                         rowheight=26,
                         borderwidth=0)
        style.configure("Treeview.Heading",
                         background=COLOR_PANEL,
                         foreground=COLOR_ACCENT,
                         font=FONT_HEADING,
                         borderwidth=0)
        style.map("Treeview", background=[("selected", COLOR_ACCENT_DARK)])

        style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=COLOR_PANEL,
                         foreground=COLOR_TEXT, padding=(14, 8))
        style.map("TNotebook.Tab", background=[("selected", COLOR_ACCENT)],
                  foreground=[("selected", "#00221d")])

    def _build_topbar(self):
        topbar = tk.Frame(self.root, bg=COLOR_PANEL, height=56)
        topbar.pack(side="top", fill="x")

        tk.Label(topbar, text="OSINT INVESTIGATOR", bg=COLOR_PANEL, fg=COLOR_ACCENT,
                  font=FONT_TITLE).pack(side="left", padx=16)

        target_frame = tk.Frame(topbar, bg=COLOR_PANEL)
        target_frame.pack(side="right", padx=16, pady=8)

        tk.Label(target_frame, text="Current Target:", bg=COLOR_PANEL,
                  fg=COLOR_TEXT_DIM, font=FONT_NORMAL).pack(side="left", padx=(0, 6))

        self.target_var = tk.StringVar(value=investigation.target)
        target_entry = tk.Entry(target_frame, textvariable=self.target_var, width=28,
                                 bg=COLOR_PANEL_ALT, fg=COLOR_TEXT, insertbackground=COLOR_TEXT,
                                 relief="flat", font=FONT_NORMAL)
        target_entry.pack(side="left", ipady=4, padx=4)

        StyledButton(target_frame, "Set Target", self.on_set_target, kind="primary").pack(side="left", padx=4)

    def _build_sidebar_nav(self):
        tk.Label(self.sidebar, text="MODULES", bg=COLOR_SIDEBAR, fg=COLOR_TEXT_DIM,
                  font=FONT_HEADING).pack(anchor="w", padx=16, pady=(18, 6))

        nav_items = [
            "Dashboard",
            "Google Dork Generator",
            "Username OSINT",
            "Domain OSINT",
            "URL Analysis",
            "Investigation Notes",
            "Evidence / Findings",
            "Report Generator",
            "About / Ethics",
        ]
        self.nav_buttons = {}
        for name in nav_items:
            btn = tk.Button(
                self.sidebar, text=name, anchor="w",
                bg=COLOR_SIDEBAR, fg=COLOR_TEXT, activebackground=COLOR_PANEL_ALT,
                activeforeground=COLOR_ACCENT, relief="flat", bd=0, padx=16, pady=10,
                font=FONT_NORMAL, cursor="hand2",
                command=lambda n=name: self.show_page(n),
            )
            btn.pack(fill="x")
            self.nav_buttons[name] = btn

    def _build_all_pages(self):
        self.pages["Dashboard"] = self._build_dashboard_page()
        self.pages["Google Dork Generator"] = self._build_dork_page()
        self.pages["Username OSINT"] = self._build_username_page()
        self.pages["Domain OSINT"] = self._build_domain_page()
        self.pages["URL Analysis"] = self._build_url_page()
        self.pages["Investigation Notes"] = self._build_notes_page()
        self.pages["Evidence / Findings"] = self._build_findings_page()
        self.pages["Report Generator"] = self._build_report_page()
        self.pages["About / Ethics"] = self._build_about_page()

    def show_page(self, name):
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)

        for nav_name, btn in self.nav_buttons.items():
            if nav_name == name:
                btn.configure(bg=COLOR_PANEL_ALT, fg=COLOR_ACCENT)
            else:
                btn.configure(bg=COLOR_SIDEBAR, fg=COLOR_TEXT)

        if name == "Dashboard":
            self.refresh_dashboard()

    def page_header(self, parent, title, subtitle=""):
        header = tk.Frame(parent, bg=COLOR_BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text=title, bg=COLOR_BG, fg=COLOR_TEXT, font=FONT_TITLE).pack(anchor="w")
        if subtitle:
            tk.Label(header, text=subtitle, bg=COLOR_BG, fg=COLOR_TEXT_DIM,
                      font=FONT_NORMAL).pack(anchor="w", pady=(2, 0))
        return header

    def labeled_entry(self, parent, label_text, width=40):
        """Small helper: builds a 'Label above Entry' pair and returns the Entry widget."""
        frame = tk.Frame(parent, bg=COLOR_PANEL)
        frame.pack(fill="x", pady=6)
        tk.Label(frame, text=label_text, bg=COLOR_PANEL, fg=COLOR_TEXT_DIM,
                  font=FONT_NORMAL).pack(anchor="w")
        entry = tk.Entry(frame, width=width, bg=COLOR_PANEL_ALT, fg=COLOR_TEXT,
                          insertbackground=COLOR_TEXT, relief="flat", font=FONT_NORMAL)
        entry.pack(fill="x", ipady=6, pady=(4, 0))
        return entry

    # ---------------------------------------------------------
    # Shared actions
    # ---------------------------------------------------------

    def on_set_target(self):
        target = self.target_var.get().strip()
        if not target:
            messagebox.showwarning("No Target", "Please enter a target before setting it.")
            return
        investigation.target = target
        if investigation.status == "Not Started":
            investigation.status = "In Progress"
        messagebox.showinfo("Target Set", "Current investigation target set to:\n{}".format(target))
        self.refresh_dashboard()

    def copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()  # keeps clipboard contents after the app loses focus

    # ---------------------------------------------------------
    # DASHBOARD PAGE
    # ---------------------------------------------------------

    def _build_dashboard_page(self):
        page = tk.Frame(self.content, bg=COLOR_BG)
        self.page_header(page, "Dashboard", "Overview of the current investigation")

        stats_row = tk.Frame(page, bg=COLOR_BG)
        stats_row.pack(fill="x", padx=24, pady=10)

        self.stat_labels = {}
        stat_defs = [
            ("target", "Current Target"),
            ("status", "Investigation Status"),
            ("queries", "Generated Queries"),
            ("findings", "Findings Recorded"),
            ("notes", "Notes Taken"),
        ]
        for key, label in stat_defs:
            card = tk.Frame(stats_row, bg=COLOR_PANEL, padx=16, pady=14)
            card.pack(side="left", fill="both", expand=True, padx=6)
            tk.Label(card, text=label, bg=COLOR_PANEL, fg=COLOR_TEXT_DIM,
                      font=FONT_NORMAL).pack(anchor="w")
            value_label = tk.Label(card, text="-", bg=COLOR_PANEL, fg=COLOR_ACCENT,
                                     font=FONT_HEADING)
            value_label.pack(anchor="w", pady=(6, 0))
            self.stat_labels[key] = value_label

        workflow_panel = tk.Frame(page, bg=COLOR_PANEL, padx=20, pady=16)
        workflow_panel.pack(fill="both", expand=True, padx=24, pady=10)
        tk.Label(workflow_panel, text="Suggested Workflow", bg=COLOR_PANEL, fg=COLOR_TEXT,
                  font=FONT_HEADING).pack(anchor="w")
        workflow_text = (
            "1. Set your investigation target at the top of the window.\n"
            "2. Use the OSINT modules on the left to generate queries and gather public information.\n"
            "3. Record anything relevant as a Finding.\n"
            "4. Write down observations in Investigation Notes.\n"
            "5. Open the Report Generator to produce a final report."
        )
        tk.Label(workflow_panel, text=workflow_text, bg=COLOR_PANEL, fg=COLOR_TEXT_DIM,
                  font=FONT_NORMAL, justify="left").pack(anchor="w", pady=(10, 0))

        return page

    def refresh_dashboard(self):
        self.stat_labels["target"].configure(text=investigation.target or "(not set)")
        self.stat_labels["status"].configure(text=investigation.status)
        self.stat_labels["queries"].configure(text=str(len(investigation.generated_queries)))
        self.stat_labels["findings"].configure(text=str(len(investigation.findings)))
        self.stat_labels["notes"].configure(text=str(len(investigation.notes)))

    # ---------------------------------------------------------
    # MODULE 1: GOOGLE DORK GENERATOR PAGE
    # ---------------------------------------------------------

    def _build_dork_page(self):
        page = tk.Frame(self.content, bg=COLOR_BG)
        self.page_header(page, "Google Dork Generator",
                          "Generate safe, public search-engine queries for a domain")

        controls = tk.Frame(page, bg=COLOR_PANEL, padx=16, pady=14)
        controls.pack(fill="x", padx=24)

        self.dork_domain_entry = self.labeled_entry(controls, "Domain (e.g. example.com)")

        button_row = tk.Frame(controls, bg=COLOR_PANEL)
        button_row.pack(fill="x", pady=(10, 0))
        StyledButton(button_row, "Generate Dorks", self.on_generate_dorks).pack(side="left", padx=(0, 6))
        StyledButton(button_row, "Copy Selected", self.on_copy_selected_dork, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Copy All", self.on_copy_all_dorks, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Open Selected", self.on_open_selected_dork, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Open All", self.on_open_all_dorks, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Clear", self.on_clear_dorks, kind="danger").pack(side="left", padx=6)

        results_frame = tk.Frame(page, bg=COLOR_BG)
        results_frame.pack(fill="both", expand=True, padx=24, pady=14)

        self.dork_tree = ttk.Treeview(results_frame, columns=("category", "query"),
                                        show="headings", selectmode="extended")
        self.dork_tree.heading("category", text="Category")
        self.dork_tree.heading("query", text="Generated Query")
        self.dork_tree.column("category", width=260)
        self.dork_tree.column("query", width=560)
        self.dork_tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.dork_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.dork_tree.configure(yscrollcommand=scrollbar.set)

        return page

    def on_generate_dorks(self):
        domain = self.dork_domain_entry.get().strip()
        if not is_valid_domain(clean_domain_input(domain)):
            messagebox.showerror("Invalid Domain", "Please enter a valid domain, e.g. example.com")
            return

        self.dork_tree.delete(*self.dork_tree.get_children())
        categories = generate_dorks(domain)
        all_queries = []
        for category, queries in categories.items():
            for query in queries:
                self.dork_tree.insert("", "end", values=(category, query))
                all_queries.append(query)

        investigation.add_queries(all_queries)
        messagebox.showinfo("Dorks Generated", "{} queries generated for {}".format(
            len(all_queries), clean_domain_input(domain)))

    def _get_selected_dork_queries(self):
        selected = self.dork_tree.selection()
        return [self.dork_tree.item(item, "values")[1] for item in selected]

    def on_copy_selected_dork(self):
        queries = self._get_selected_dork_queries()
        if not queries:
            messagebox.showwarning("Nothing Selected", "Select one or more rows first.")
            return
        self.copy_to_clipboard("\n".join(queries))
        messagebox.showinfo("Copied", "{} quer{} copied to clipboard.".format(
            len(queries), "y" if len(queries) == 1 else "ies"))

    def on_copy_all_dorks(self):
        all_queries = [self.dork_tree.item(i, "values")[1] for i in self.dork_tree.get_children()]
        if not all_queries:
            messagebox.showwarning("No Data", "Generate some dorks first.")
            return
        self.copy_to_clipboard("\n".join(all_queries))
        messagebox.showinfo("Copied", "All {} queries copied to clipboard.".format(len(all_queries)))

    def on_open_selected_dork(self):
        queries = self._get_selected_dork_queries()
        if not queries:
            messagebox.showwarning("Nothing Selected", "Select one or more rows first.")
            return
        for query in queries:
            webbrowser.open(google_search_url(query))

    def on_open_all_dorks(self):
        all_queries = [self.dork_tree.item(i, "values")[1] for i in self.dork_tree.get_children()]
        if not all_queries:
            messagebox.showwarning("No Data", "Generate some dorks first.")
            return
        if len(all_queries) > 8:
            confirmed = messagebox.askyesno(
                "Open Many Tabs?",
                "This will open {} browser tabs. Continue?".format(len(all_queries)))
            if not confirmed:
                return
        for query in all_queries:
            webbrowser.open(google_search_url(query))

    def on_clear_dorks(self):
        self.dork_tree.delete(*self.dork_tree.get_children())

    # ---------------------------------------------------------
    # MODULE 2: USERNAME OSINT PAGE
    # ---------------------------------------------------------

    def _build_username_page(self):
        page = tk.Frame(self.content, bg=COLOR_BG)
        self.page_header(page, "Username OSINT", "Look up a username across common public platforms")

        controls = tk.Frame(page, bg=COLOR_PANEL, padx=16, pady=14)
        controls.pack(fill="x", padx=24)
        self.username_entry = self.labeled_entry(controls, "Username (e.g. john123)")

        button_row = tk.Frame(controls, bg=COLOR_PANEL)
        button_row.pack(fill="x", pady=(10, 0))
        StyledButton(button_row, "Build Profile List", self.on_build_username_list).pack(side="left", padx=(0, 6))
        StyledButton(button_row, "Check Status (slower)", self.on_check_username_status, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Open Selected", self.on_open_selected_username, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Copy Selected URL", self.on_copy_selected_username, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Open All", self.on_open_all_usernames, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Clear", self.on_clear_usernames, kind="danger").pack(side="left", padx=6)

        results_frame = tk.Frame(page, bg=COLOR_BG)
        results_frame.pack(fill="both", expand=True, padx=24, pady=14)

        self.username_tree = ttk.Treeview(results_frame, columns=("platform", "url", "status"),
                                            show="headings", selectmode="extended")
        self.username_tree.heading("platform", text="Platform")
        self.username_tree.heading("url", text="Profile URL")
        self.username_tree.heading("status", text="Status")
        self.username_tree.column("platform", width=140)
        self.username_tree.column("url", width=480)
        self.username_tree.column("status", width=160)
        self.username_tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.username_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.username_tree.configure(yscrollcommand=scrollbar.set)

        return page

    def on_build_username_list(self):
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Invalid Username", "Please enter a username.")
            return
        self.username_tree.delete(*self.username_tree.get_children())
        for platform, url in build_username_profiles(username):
            self.username_tree.insert("", "end", values=(platform, url, "Not Checked"))
        investigation.add_queries(["username lookup: {}".format(username)])

    def on_check_username_status(self):
        items = self.username_tree.get_children()
        if not items:
            messagebox.showwarning("No Data", "Build a profile list first.")
            return
        confirmed = messagebox.askyesno(
            "Check Availability",
            "This sends one normal request per platform to check if the page "
            "loads. Some platforms may block automated checks - that's expected. Continue?")
        if not confirmed:
            return
        for item in items:
            platform, url, _ = self.username_tree.item(item, "values")
            status = check_profile_status(url)
            self.username_tree.item(item, values=(platform, url, status))
            self.root.update_idletasks()  # let the GUI repaint between requests

    def _get_selected_username_urls(self):
        selected = self.username_tree.selection()
        return [self.username_tree.item(i, "values")[1] for i in selected]

    def on_open_selected_username(self):
        urls = self._get_selected_username_urls()
        if not urls:
            messagebox.showwarning("Nothing Selected", "Select one or more rows first.")
            return
        for url in urls:
            webbrowser.open(url)

    def on_copy_selected_username(self):
        urls = self._get_selected_username_urls()
        if not urls:
            messagebox.showwarning("Nothing Selected", "Select one or more rows first.")
            return
        self.copy_to_clipboard("\n".join(urls))
        messagebox.showinfo("Copied", "URL(s) copied to clipboard.")

    def on_open_all_usernames(self):
        all_urls = [self.username_tree.item(i, "values")[1] for i in self.username_tree.get_children()]
        if not all_urls:
            messagebox.showwarning("No Data", "Build a profile list first.")
            return
        for url in all_urls:
            webbrowser.open(url)

    def on_clear_usernames(self):
        self.username_tree.delete(*self.username_tree.get_children())

    # ---------------------------------------------------------
    # MODULE 3: DOMAIN OSINT PAGE
    # ---------------------------------------------------------

    def _build_domain_page(self):
        page = tk.Frame(self.content, bg=COLOR_BG)
        self.page_header(page, "Domain OSINT", "Collect basic public information about a domain")

        controls = tk.Frame(page, bg=COLOR_PANEL, padx=16, pady=14)
        controls.pack(fill="x", padx=24)
        self.domain_entry = self.labeled_entry(controls, "Domain (e.g. example.com)")

        button_row = tk.Frame(controls, bg=COLOR_PANEL)
        button_row.pack(fill="x", pady=(10, 0))
        StyledButton(button_row, "Gather Domain Info", self.on_gather_domain_info).pack(side="left", padx=(0, 6))
        StyledButton(button_row, "Generate Dorks for this Domain", self.on_domain_generate_dorks, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Add as Finding", self.on_add_domain_finding, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Clear", self.on_clear_domain_info, kind="danger").pack(side="left", padx=6)

        results_frame = tk.Frame(page, bg=COLOR_PANEL, padx=16, pady=14)
        results_frame.pack(fill="both", expand=True, padx=24, pady=14)

        self.domain_result_labels = {}
        self.domain_info_fields = [
            "Domain", "Website URL", "DNS (IP Address)", "HTTPS Availability", "Website Title",
        ]
        for field in self.domain_info_fields:
            row = tk.Frame(results_frame, bg=COLOR_PANEL)
            row.pack(fill="x", pady=6)
            tk.Label(row, text=field + ":", bg=COLOR_PANEL, fg=COLOR_TEXT_DIM,
                      font=FONT_NORMAL, width=20, anchor="w").pack(side="left")
            value_label = tk.Label(row, text="-", bg=COLOR_PANEL, fg=COLOR_TEXT,
                                     font=FONT_NORMAL, anchor="w", wraplength=640, justify="left")
            value_label.pack(side="left", fill="x", expand=True)
            self.domain_result_labels[field] = value_label

        return page

    def on_gather_domain_info(self):
        domain_raw = self.domain_entry.get().strip()
        cleaned = clean_domain_input(domain_raw)
        if not is_valid_domain(cleaned):
            messagebox.showerror("Invalid Domain", "Please enter a valid domain, e.g. example.com")
            return

        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:
            info = gather_domain_info(cleaned)
        finally:
            self.root.config(cursor="")

        for field in self.domain_info_fields:
            self.domain_result_labels[field].configure(text=info.get(field, "Information unavailable"))

        self._last_domain_info = info

    def on_domain_generate_dorks(self):
        domain_raw = self.domain_entry.get().strip()
        if not is_valid_domain(clean_domain_input(domain_raw)):
            messagebox.showerror("Invalid Domain", "Please enter a valid domain first.")
            return
        self.show_page("Google Dork Generator")
        self.dork_domain_entry.delete(0, "end")
        self.dork_domain_entry.insert(0, clean_domain_input(domain_raw))
        self.on_generate_dorks()

    def on_add_domain_finding(self):
        info = getattr(self, "_last_domain_info", None)
        if not info:
            messagebox.showwarning("No Data", "Gather domain info first.")
            return
        finding = investigation.add_finding(
            category="Domain OSINT",
            description="Domain: {} | IP: {} | Title: {}".format(
                info.get("Domain"), info.get("DNS (IP Address)"), info.get("Website Title")),
            source_url=info.get("Website URL", ""),
            search_query="",
        )
        messagebox.showinfo("Finding Added", "Finding #{} added.".format(finding["id"]))

    def on_clear_domain_info(self):
        for field in self.domain_info_fields:
            self.domain_result_labels[field].configure(text="-")
        self._last_domain_info = None

    # ---------------------------------------------------------
    # MODULE 4: URL ANALYSIS PAGE
    # ---------------------------------------------------------

    def _build_url_page(self):
        page = tk.Frame(self.content, bg=COLOR_BG)
        self.page_header(page, "URL Analysis", "Break a URL down into its component parts")

        controls = tk.Frame(page, bg=COLOR_PANEL, padx=16, pady=14)
        controls.pack(fill="x", padx=24)
        self.url_entry = self.labeled_entry(controls, "URL (e.g. https://example.com/page?id=1)", width=60)

        button_row = tk.Frame(controls, bg=COLOR_PANEL)
        button_row.pack(fill="x", pady=(10, 0))
        StyledButton(button_row, "Analyze URL", self.on_analyze_url).pack(side="left", padx=(0, 6))
        StyledButton(button_row, "Add as Finding", self.on_add_url_finding, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Clear", self.on_clear_url_analysis, kind="danger").pack(side="left", padx=6)

        results_frame = tk.Frame(page, bg=COLOR_PANEL, padx=16, pady=14)
        results_frame.pack(fill="both", expand=True, padx=24, pady=14)

        self.url_result_labels = {}
        self.url_info_fields = ["Full URL", "Protocol", "Domain", "Port", "Path", "Query Parameters", "Fragment"]
        for field in self.url_info_fields:
            row = tk.Frame(results_frame, bg=COLOR_PANEL)
            row.pack(fill="x", pady=6)
            tk.Label(row, text=field + ":", bg=COLOR_PANEL, fg=COLOR_TEXT_DIM,
                      font=FONT_NORMAL, width=20, anchor="w").pack(side="left")
            value_label = tk.Label(row, text="-", bg=COLOR_PANEL, fg=COLOR_TEXT,
                                     font=FONT_NORMAL, anchor="w", wraplength=640, justify="left")
            value_label.pack(side="left", fill="x", expand=True)
            self.url_result_labels[field] = value_label

        return page

    def on_analyze_url(self):
        url = self.url_entry.get().strip()
        if not is_valid_url(url):
            messagebox.showerror("Invalid URL", "Please enter a full URL, including http:// or https://")
            return
        info = analyze_url(url)
        for field in self.url_info_fields:
            self.url_result_labels[field].configure(text=info.get(field, "(none)"))
        self._last_url_info = info

    def on_add_url_finding(self):
        info = getattr(self, "_last_url_info", None)
        if not info:
            messagebox.showwarning("No Data", "Analyze a URL first.")
            return
        finding = investigation.add_finding(
            category="URL Analysis",
            description="Analyzed URL structure (domain: {}, path: {})".format(
                info.get("Domain"), info.get("Path")),
            source_url=info.get("Full URL", ""),
            search_query="",
        )
        messagebox.showinfo("Finding Added", "Finding #{} added.".format(finding["id"]))

    def on_clear_url_analysis(self):
        for field in self.url_info_fields:
            self.url_result_labels[field].configure(text="-")
        self._last_url_info = None

    # ---------------------------------------------------------
    # MODULE 5: INVESTIGATION NOTES PAGE
    # ---------------------------------------------------------

    def _build_notes_page(self):
        page = tk.Frame(self.content, bg=COLOR_BG)
        self.page_header(page, "Investigation Notes", "Freeform notes for the current investigation")

        input_frame = tk.Frame(page, bg=COLOR_PANEL, padx=16, pady=14)
        input_frame.pack(fill="x", padx=24)
        tk.Label(input_frame, text="New Note:", bg=COLOR_PANEL, fg=COLOR_TEXT_DIM,
                  font=FONT_NORMAL).pack(anchor="w")
        self.note_text_box = tk.Text(input_frame, height=4, bg=COLOR_PANEL_ALT, fg=COLOR_TEXT,
                                       insertbackground=COLOR_TEXT, relief="flat", font=FONT_NORMAL)
        self.note_text_box.pack(fill="x", pady=(4, 8))

        button_row = tk.Frame(input_frame, bg=COLOR_PANEL)
        button_row.pack(fill="x")
        StyledButton(button_row, "Add Note", self.on_add_note).pack(side="left", padx=(0, 6))
        StyledButton(button_row, "Edit Selected", self.on_edit_note, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Delete Selected", self.on_delete_note, kind="danger").pack(side="left", padx=6)
        StyledButton(button_row, "Clear All Notes", self.on_clear_notes, kind="danger").pack(side="left", padx=6)

        list_frame = tk.Frame(page, bg=COLOR_BG)
        list_frame.pack(fill="both", expand=True, padx=24, pady=14)

        self.notes_tree = ttk.Treeview(list_frame, columns=("timestamp", "text"),
                                         show="headings", selectmode="browse")
        self.notes_tree.heading("timestamp", text="Timestamp")
        self.notes_tree.heading("text", text="Note")
        self.notes_tree.column("timestamp", width=160)
        self.notes_tree.column("text", width=600)
        self.notes_tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.notes_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.notes_tree.configure(yscrollcommand=scrollbar.set)

        return page

    def refresh_notes_tree(self):
        self.notes_tree.delete(*self.notes_tree.get_children())
        for note in investigation.notes:
            self.notes_tree.insert("", "end", iid=str(note["id"]),
                                     values=(note["timestamp"], note["text"]))

    def on_add_note(self):
        text = self.note_text_box.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Empty Note", "Please write something before adding a note.")
            return
        investigation.add_note(text)
        self.note_text_box.delete("1.0", "end")
        self.refresh_notes_tree()

    def _get_selected_note_id(self):
        selected = self.notes_tree.selection()
        if not selected:
            return None
        return int(selected[0])

    def on_edit_note(self):
        note_id = self._get_selected_note_id()
        if note_id is None:
            messagebox.showwarning("Nothing Selected", "Select a note first.")
            return
        note = next((n for n in investigation.notes if n["id"] == note_id), None)
        if not note:
            return
        new_text = simpledialog.askstring("Edit Note", "Update note text:", initialvalue=note["text"])
        if new_text is not None and new_text.strip():
            note["text"] = new_text.strip()
            note["timestamp"] = now_string() + " (edited)"
            self.refresh_notes_tree()

    def on_delete_note(self):
        note_id = self._get_selected_note_id()
        if note_id is None:
            messagebox.showwarning("Nothing Selected", "Select a note first.")
            return
        investigation.notes = [n for n in investigation.notes if n["id"] != note_id]
        self.refresh_notes_tree()

    def on_clear_notes(self):
        if not investigation.notes:
            return
        if messagebox.askyesno("Clear Notes", "Delete ALL notes? This cannot be undone."):
            investigation.notes = []
            self.refresh_notes_tree()

    # ---------------------------------------------------------
    # MODULE 6: EVIDENCE / FINDINGS PAGE
    # ---------------------------------------------------------

    def _build_findings_page(self):
        page = tk.Frame(self.content, bg=COLOR_BG)
        self.page_header(page, "Evidence / Findings", "Record concrete findings discovered during the investigation")

        input_frame = tk.Frame(page, bg=COLOR_PANEL, padx=16, pady=14)
        input_frame.pack(fill="x", padx=24)

        row1 = tk.Frame(input_frame, bg=COLOR_PANEL)
        row1.pack(fill="x")
        self.finding_category_entry = self._inline_labeled_entry(row1, "Category", side="left")
        self.finding_source_entry = self._inline_labeled_entry(row1, "Source URL", side="left", width=40)

        row2 = tk.Frame(input_frame, bg=COLOR_PANEL, pady=8)
        row2.pack(fill="x")
        self.finding_query_entry = self._inline_labeled_entry(row2, "Search Query (optional)", side="left", width=40)

        tk.Label(input_frame, text="Description:", bg=COLOR_PANEL, fg=COLOR_TEXT_DIM,
                  font=FONT_NORMAL).pack(anchor="w", pady=(6, 0))
        self.finding_description_box = tk.Text(input_frame, height=3, bg=COLOR_PANEL_ALT, fg=COLOR_TEXT,
                                                 insertbackground=COLOR_TEXT, relief="flat", font=FONT_NORMAL)
        self.finding_description_box.pack(fill="x", pady=(4, 8))

        button_row = tk.Frame(input_frame, bg=COLOR_PANEL)
        button_row.pack(fill="x")
        StyledButton(button_row, "Add Finding", self.on_add_finding_manual).pack(side="left", padx=(0, 6))
        StyledButton(button_row, "View Selected", self.on_view_finding, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Delete Selected", self.on_delete_finding, kind="danger").pack(side="left", padx=6)
        StyledButton(button_row, "Clear All Findings", self.on_clear_findings, kind="danger").pack(side="left", padx=6)

        list_frame = tk.Frame(page, bg=COLOR_BG)
        list_frame.pack(fill="both", expand=True, padx=24, pady=14)

        self.findings_tree = ttk.Treeview(
            list_frame, columns=("id", "category", "description", "timestamp"),
            show="headings", selectmode="browse")
        self.findings_tree.heading("id", text="#")
        self.findings_tree.heading("category", text="Category")
        self.findings_tree.heading("description", text="Description")
        self.findings_tree.heading("timestamp", text="Recorded")
        self.findings_tree.column("id", width=40)
        self.findings_tree.column("category", width=160)
        self.findings_tree.column("description", width=420)
        self.findings_tree.column("timestamp", width=150)
        self.findings_tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.findings_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.findings_tree.configure(yscrollcommand=scrollbar.set)

        return page

    def _inline_labeled_entry(self, parent, label_text, side="left", width=24):
        frame = tk.Frame(parent, bg=COLOR_PANEL)
        frame.pack(side=side, padx=(0, 16))
        tk.Label(frame, text=label_text, bg=COLOR_PANEL, fg=COLOR_TEXT_DIM,
                  font=FONT_NORMAL).pack(anchor="w")
        entry = tk.Entry(frame, width=width, bg=COLOR_PANEL_ALT, fg=COLOR_TEXT,
                          insertbackground=COLOR_TEXT, relief="flat", font=FONT_NORMAL)
        entry.pack(ipady=5, pady=(4, 0))
        return entry

    def refresh_findings_tree(self):
        self.findings_tree.delete(*self.findings_tree.get_children())
        for finding in investigation.findings:
            self.findings_tree.insert("", "end", iid=str(finding["id"]), values=(
                finding["id"], finding["category"], finding["description"], finding["timestamp"]))

    def on_add_finding_manual(self):
        category = self.finding_category_entry.get().strip() or "Uncategorized"
        source = self.finding_source_entry.get().strip()
        query = self.finding_query_entry.get().strip()
        description = self.finding_description_box.get("1.0", "end").strip()

        if not description:
            messagebox.showwarning("Missing Description", "Please describe the finding.")
            return

        finding = investigation.add_finding(category, description, source, query)

        self.finding_category_entry.delete(0, "end")
        self.finding_source_entry.delete(0, "end")
        self.finding_query_entry.delete(0, "end")
        self.finding_description_box.delete("1.0", "end")

        self.refresh_findings_tree()
        messagebox.showinfo("Finding Added", "Finding #{} added.".format(finding["id"]))

    def _get_selected_finding(self):
        selected = self.findings_tree.selection()
        if not selected:
            return None
        finding_id = int(selected[0])
        return next((f for f in investigation.findings if f["id"] == finding_id), None)

    def on_view_finding(self):
        finding = self._get_selected_finding()
        if not finding:
            messagebox.showwarning("Nothing Selected", "Select a finding first.")
            return
        details = (
            "Finding #{id}\n\n"
            "Category: {category}\n"
            "Description: {description}\n"
            "Source URL: {source_url}\n"
            "Search Query: {search_query}\n"
            "Recorded: {timestamp}"
        ).format(**finding)
        messagebox.showinfo("Finding Details", details)

    def on_delete_finding(self):
        finding = self._get_selected_finding()
        if not finding:
            messagebox.showwarning("Nothing Selected", "Select a finding first.")
            return
        investigation.findings = [f for f in investigation.findings if f["id"] != finding["id"]]
        self.refresh_findings_tree()

    def on_clear_findings(self):
        if not investigation.findings:
            return
        if messagebox.askyesno("Clear Findings", "Delete ALL findings? This cannot be undone."):
            investigation.findings = []
            self.refresh_findings_tree()

    # ---------------------------------------------------------
    # MODULE 7: REPORT GENERATOR PAGE
    # ---------------------------------------------------------

    def _build_report_page(self):
        page = tk.Frame(self.content, bg=COLOR_BG)
        self.page_header(page, "Report Generator", "Preview and export the full investigation report")

        button_row = tk.Frame(page, bg=COLOR_BG)
        button_row.pack(fill="x", padx=24)
        StyledButton(button_row, "Preview Report", self.on_preview_report).pack(side="left", padx=(0, 6))
        StyledButton(button_row, "Export as TXT", self.on_export_report_txt, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Export as HTML", self.on_export_report_html, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Save Investigation (JSON)", self.on_save_json, kind="secondary").pack(side="left", padx=6)
        StyledButton(button_row, "Load Investigation (JSON)", self.on_load_json, kind="secondary").pack(side="left", padx=6)

        preview_frame = tk.Frame(page, bg=COLOR_PANEL)
        preview_frame.pack(fill="both", expand=True, padx=24, pady=14)

        self.report_preview_box = tk.Text(preview_frame, bg=COLOR_PANEL_ALT, fg=COLOR_TEXT,
                                            insertbackground=COLOR_TEXT, relief="flat",
                                            font=FONT_MONO, wrap="word")
        self.report_preview_box.pack(fill="both", expand=True, padx=10, pady=10)

        return page

    def on_preview_report(self):
        self.report_preview_box.delete("1.0", "end")
        self.report_preview_box.insert("1.0", build_report_text())

    def on_export_report_txt(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt")],
            initialfile="osint_report.txt",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as report_file:
                report_file.write(build_report_text())
            messagebox.showinfo("Exported", "Report saved to:\n{}".format(file_path))
        except OSError as error:
            messagebox.showerror("Export Failed", "Could not save file: {}".format(error))

    def on_export_report_html(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML File", "*.html")],
            initialfile="osint_report.html",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as report_file:
                report_file.write(build_report_html())
            messagebox.showinfo("Exported", "Report saved to:\n{}".format(file_path))
        except OSError as error:
            messagebox.showerror("Export Failed", "Could not save file: {}".format(error))

    def on_save_json(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON File", "*.json")],
            initialfile="osint_investigation.json",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(investigation.to_dict(), json_file, indent=2)
            messagebox.showinfo("Saved", "Investigation data saved to:\n{}".format(file_path))
        except OSError as error:
            messagebox.showerror("Save Failed", "Could not save file: {}".format(error))

    def on_load_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON File", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as json_file:
                data = json.load(json_file)
            investigation.load_from_dict(data)
            self.target_var.set(investigation.target)
            self.refresh_notes_tree()
            self.refresh_findings_tree()
            self.refresh_dashboard()
            messagebox.showinfo("Loaded", "Investigation data loaded from:\n{}".format(file_path))
        except (OSError, json.JSONDecodeError) as error:
            messagebox.showerror("Load Failed", "Could not load file: {}".format(error))

    # ---------------------------------------------------------
    # ABOUT / ETHICS PAGE
    # ---------------------------------------------------------

    def _build_about_page(self):
        page = tk.Frame(self.content, bg=COLOR_BG)
        self.page_header(page, "About / Ethics")

        panel = tk.Frame(page, bg=COLOR_PANEL, padx=20, pady=18)
        panel.pack(fill="both", expand=True, padx=24, pady=10)

        about_text = (
            "OSINT Investigator is a student project for learning Open Source "
            "Intelligence (OSINT) concepts, Google Dorking, and basic Python GUI "
            "programming.\n\n"
            "Ethical Use Guidelines:\n\n"
            "  - OSINT relies only on PUBLICLY AVAILABLE information - things "
            "already indexed by search engines or visible on public web pages.\n"
            "  - This tool must only be used for AUTHORIZED investigations, "
            "education, and defensive security research.\n"
            "  - Always respect the privacy of individuals and comply with "
            "applicable laws (e.g. computer misuse laws, data protection laws) "
            "and the target's terms of service.\n"
            "  - This tool does NOT bypass authentication, CAPTCHAs, rate "
            "limits, or any other access control, and does NOT perform "
            "vulnerability scanning or exploitation.\n"
            "  - Findings recorded here should be handled responsibly and "
            "reported through proper legal/organizational channels when needed.\n\n"
            "This project is for educational purposes as part of a cybersecurity "
            "course assessment."
        )
        tk.Label(panel, text=about_text, bg=COLOR_PANEL, fg=COLOR_TEXT, font=FONT_NORMAL,
                  justify="left", wraplength=780).pack(anchor="w")

        return page


# ==============================================================
# ENTRY POINT
# ==============================================================

def main():
    root = tk.Tk()
    app = OsintInvestigatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
