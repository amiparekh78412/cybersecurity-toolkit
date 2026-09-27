# 🔎 OSINT Investigator

> A beginner-friendly Python GUI toolkit for legal, authorized, and publicly sourced Open Source Intelligence (OSINT) research.

## About & Ethics

**OSINT Investigator** is a student cybersecurity project designed to help learners understand how publicly available information can be discovered, organized, and documented during an OSINT investigation.

The tool is intended for **educational purposes, authorized security research, cybersecurity labs, and legitimate investigations using publicly accessible information**.

> ⚠️ **Responsible Use:** This application does not bypass authentication, CAPTCHAs, rate limits, or access controls. It does not perform vulnerability scanning, exploitation, or unauthorized access. Always obtain appropriate authorization before investigating a target and respect applicable laws, privacy requirements, and website terms of service.

---

## ✨ Features

The application provides eight integrated OSINT modules:

* 🔍 **Google Dork Generator** — Generate structured search-engine queries using operators such as `site:`, `filetype:`, `intitle:`, and `inurl:`.
* 👤 **Username OSINT** — Generate and open public profile URLs for usernames across supported platforms.
* 📧 **Email OSINT** — Generate public search queries for an email address without attempting account access.
* 🌐 **Domain OSINT** — Perform basic public domain, DNS, and website information gathering.
* 🔗 **URL Analysis** — Parse URLs into components such as protocol, domain, port, path, query, and fragment.
* 📝 **Investigation Notes** — Record observations and notes during an investigation.
* 📋 **Evidence / Findings** — Organize findings with descriptions, source URLs, queries, timestamps, and notes.
* 📄 **Report Generator** — Export investigation reports as **TXT or HTML** and save/load investigation data using **JSON**.

### 🖥️ Interface

* Dark cybersecurity-dashboard style
* Sidebar navigation
* Integrated investigation workflow
* Beginner-friendly interface
* Single-file Python implementation
* No required third-party dependencies

---

## ⚙️ Requirements

* **Python 3.x**
* Internet connection for modules that access public online resources
* A modern web browser

The project is built primarily with the **Python standard library**, so no external packages are required for the core application.

### Optional: CustomTkinter

If you want the enhanced CustomTkinter styling:

```bash
pip install customtkinter
```

The application can still be used with standard Tkinter where applicable.

---

## 🚀 Installation & Usage

### 1. Clone the repository

```bash
git clone https://github.com/your-username/osint-investigator.git
```

### 2. Enter the project directory

```bash
cd osint-investigator
```

### 3. Run the application

```bash
python osint_investigator.py
```

The graphical interface will open and you can begin an authorized OSINT investigation.

---

## 🧭 Example Usage

A typical investigation workflow looks like this:

### Step 1 — Set a Target

Enter a target appropriate for your authorized investigation.

For example:

```text
example.com
```

For learning and testing, use domains, usernames, or systems that you own or have explicit permission to investigate.

### Step 2 — Generate Google Dorks

Open the **Google Dork Generator** and select the appropriate category.

For example:

```text
site:example.com filetype:pdf
```

The generated query can be copied or opened in a browser.

### Step 3 — Investigate Public Information

Use the appropriate modules to examine publicly available information.

For example:

* Analyze a domain
* Analyze a URL
* Check public username profiles
* Review generated search results

### Step 4 — Add a Finding

When you identify something relevant, record it in **Evidence / Findings**.

A finding can contain:

```text
Category: Public Document

Description:
Publicly indexed document discovered during authorized research.

Source:
https://example.com/document.pdf

Search Query:
site:example.com filetype:pdf
```

### Step 5 — Generate a Report

Use the **Report Generator** to organize the investigation.

Reports can be exported as:

```text
TXT
HTML
```

Investigation data can also be saved and loaded using:

```text
JSON
```

---

## 📁 Project Structure

The project intentionally uses a **single Python file**:

```text
osint-investigator/
│
├── osint_investigator.py
├── README.md
├── LICENSE
└── docs/
    └── screenshot.png
```

Keeping the application in one file makes the project easier for students to:

* Read and understand
* Run without complex setup
* Study during a cybersecurity course
* Demonstrate during an assessment
* Modify and experiment with

The code is organized internally into separate sections and functions for each OSINT module while remaining a single executable Python file.

---

## 🛡️ Limitations & Non-Goals

OSINT Investigator is intentionally designed as a **passive and educational OSINT tool**.

It does **not**:

* ❌ Bypass authentication
* ❌ Bypass CAPTCHAs
* ❌ Circumvent rate limits
* ❌ Access private accounts or information
* ❌ Steal or guess passwords
* ❌ Exploit vulnerabilities
* ❌ Perform vulnerability scanning
* ❌ Perform unauthorized network scanning
* ❌ Attempt privilege escalation
* ❌ Evade security controls
* ❌ Conduct automated aggressive scraping

The application primarily generates search queries and public profile URLs or makes normal public HTTP/DNS requests similar to ordinary browser activity.

### Information Accuracy

Public OSINT data can be incomplete, outdated, misleading, or incorrectly attributed.

Results should therefore be treated as **investigation leads rather than automatically verified facts**. Important findings should be independently validated using reliable sources.

---

## 🔮 Future Improvements

Potential future improvements include:

* Additional OSINT search sources
* More configurable Google Dork categories
* Improved domain information gathering
* Certificate Transparency lookups
* Passive DNS integrations
* Additional report formats
* Investigation case management
* Improved evidence organization
* Search-result bookmarking
* More customizable dashboard themes
* Additional educational OSINT modules

Future functionality will continue to follow the project's focus on **legal, authorized, and responsible security research**.

---

## 📄 License

This project is licensed under the **MIT License**. See the [`LICENSE`](LICENSE) file for details.

### Educational Use

OSINT Investigator was built as part of a cybersecurity learning project.

It is provided for **educational purposes and authorized security research**. Users are responsible for ensuring that their use of the software complies with applicable laws, regulations, privacy requirements, and the terms of the services they access.

**Use responsibly. 🔐**
