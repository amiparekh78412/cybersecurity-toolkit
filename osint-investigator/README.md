# 🔎 OSINT Investigator

A beginner-friendly **Open Source Intelligence (OSINT) Investigation Dashboard** built with Python.

This project was created as an educational cybersecurity tool to help students understand how publicly available information can be collected, organized, and documented during an OSINT investigation.

> **⚠️ Educational & Ethical Use Only**
>
> This tool is intended for authorized security research, cybersecurity education, CTF/lab environments, and investigations involving information that is publicly accessible.
>
> Do not use this tool to harass, stalk, impersonate, threaten, target, or harm individuals or organizations. Do not use it to bypass authentication, access private information, evade security controls, or perform unauthorized security testing.
>
> The responsibility for using this software legally and ethically belongs to the user.

---

## 📌 Features

The application provides several OSINT-related modules through a single graphical interface.

### 🔍 1. Google Dork Generator

Generates search queries using Google search operators for authorized OSINT research.

Examples include:

* `site:`
* `filetype:`
* `intitle:`
* `inurl:`
* Exact phrase searches

The generated queries can be copied or opened directly in a web browser.

---

### 👤 2. Username OSINT

Helps investigate the public presence of a username across selected online platforms.

The tool generates public profile URLs and allows the investigator to open them in a browser.

Example platforms may include:

* GitHub
* GitLab
* Reddit
* X
* Instagram
* YouTube
* Medium
* Dev.to

The module is intended for checking **publicly accessible profiles only**.

---

### 🌐 3. Domain OSINT

Provides basic information and OSINT utilities for a domain.

Depending on network availability and the target website, the module may provide information such as:

* Domain
* Website URL
* Public DNS information
* Website availability
* Basic website information
* Generated search queries

The tool does not perform vulnerability exploitation.

---

### 🔗 4. URL Analysis

Analyzes the structure of a URL without attempting to exploit the target.

It can identify components such as:

* Protocol
* Domain
* Port
* Path
* Query parameters
* Fragment

Example:

```text
https://example.com:443/products?id=10#details
```

The application can break this URL into its individual components for easier analysis.

---

### 📝 5. Investigation Notes

Allows investigators to maintain notes during an investigation.

Example:

```text
Target appears to have several publicly indexed documents.
```

Notes can help organize observations and investigation progress.

---

### 📋 6. Evidence / Findings

The tool allows findings to be recorded during an investigation.

A finding can contain:

* Finding ID
* Category
* Description
* Source URL
* Search query
* Date/time
* Additional notes

This helps convert scattered OSINT observations into organized evidence.

---

### 📄 7. Report Generation

Investigation information can be organized into a report containing:

* Investigation target
* Generated queries
* Findings
* Investigation notes
* Date/time
* Ethical-use disclaimer

This can be useful for cybersecurity assignments, lab exercises, and authorized investigations.

---

# 🖥️ Application Workflow

The general workflow is:

```text
                 ┌──────────────────┐
                 │   Enter Target   │
                 └────────┬─────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ Select OSINT Module│
                └─────────┬──────────┘
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
     Google Dork      Username         Domain / URL
          │               │                │
          └───────────────┼────────────────┘
                          ▼
                 ┌──────────────────┐
                 │ Record Findings  │
                 │ & Investigation  │
                 │      Notes       │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Generate Report  │
                 └──────────────────┘
```

---

# ⚙️ Requirements

* Python 3.x
* Internet connection for online OSINT functionality
* A modern web browser

Depending on the version of the application, additional Python packages may be required.

Install the required dependencies using:

```bash
pip install customtkinter
```
---

# 🚀 Installation

Clone or download this repository.

Then open a terminal in the project directory.

Example:

```bash
git clone <repository-url>
cd osint-investigator
```

Run the application:

```bash
python osint_investigator.py
```

---

# 📖 How to Use

## 1. Start the application

Run:

```bash
python osint_investigator.py
```

The OSINT Investigator dashboard will open.

---

## 2. Enter an Investigation Target

Enter a domain, username, or URL depending on the module you want to use.

For testing, use domains and accounts that you own or are explicitly authorized to investigate.

Example:

```text
example.com
```

---

## 3. Select an OSINT Module

Choose one of the available modules:

* Google Dork Generator
* Username OSINT
* Domain OSINT
* URL Analysis
* Investigation Notes
* Evidence / Findings

---

## 4. Review the Results

Review the information generated by the application.

Do not assume that every search result is accurate.

OSINT information should be verified using reliable sources before being treated as evidence.

---

## 5. Record Findings

If you identify something relevant, add it to the Findings section.

Record enough context to explain:

* What was discovered
* Where it was discovered
* How it was discovered
* When it was discovered

---

## 6. Generate a Report

After completing the investigation, use the report functionality to organize the collected information.

The report can be used for:

* Academic assignments
* Cybersecurity labs
* Authorized security assessments
* Personal learning

---

# 🧪 Recommended Testing

For safe testing, use:

* Your own website
* A domain you control
* Your own username
* Intentionally provided test environments
* Public educational/CTF targets where testing is explicitly permitted

Do not test the application against random individuals or organizations without authorization.

---

# 🛡️ Responsible Use

OSINT information may appear to be publicly available, but **publicly accessible does not automatically mean ethically appropriate to collect, store, or distribute**.

Users should:

* Respect privacy.
* Follow applicable laws and regulations.
* Follow the terms of websites and services.
* Investigate only authorized targets.
* Avoid collecting unnecessary personal information.
* Avoid harassment or surveillance of individuals.
* Avoid publishing sensitive findings.
* Secure any investigation data that is collected.

---

# ❌ What This Tool Should NOT Be Used For

Do not use this application to:

* Stalk individuals.
* Harass or threaten people.
* Dox individuals.
* Obtain private information.
* Bypass authentication.
* Guess or steal passwords.
* Circumvent CAPTCHAs or security controls.
* Perform unauthorized vulnerability testing.
* Exploit websites or systems.
* Evade rate limits or access restrictions.
* Conduct phishing or impersonation.
* Facilitate fraud or other illegal activity.

This project does not provide authorization to investigate any person, organization, website, or system.

---

# ⚠️ Limitations

OSINT results can change over time.

The application may also encounter:

* Websites blocking automated requests
* Network connectivity problems
* DNS resolution failures
* Rate limiting
* Changed website structures
* Search-engine restrictions
* Incorrect or outdated public information

Therefore, results should be treated as **investigation leads rather than automatically verified facts**.

---

# 🎓 Educational Purpose

This project was developed as part of cybersecurity learning to understand concepts including:

* Open Source Intelligence
* Google Dorking
* Public information discovery
* Username enumeration through public profiles
* Domain information gathering
* URL analysis
* Evidence organization
* Investigation reporting
* Ethical cybersecurity practices

The project demonstrates how multiple OSINT activities can be organized into a single Python-based graphical application.

---

# 🔮 Future Improvements

Possible future versions could include:

* Additional OSINT modules
* More configurable search operators
* Better result organization
* Investigation case management
* Database-backed investigations
* Improved report templates
* Additional public-source integrations
* Passive DNS integrations
* Certificate transparency information
* More detailed domain analysis
* Export to additional report formats

Any future functionality should continue to follow applicable laws, service terms, authorization requirements, and responsible-security principles.

---

# 👨‍💻 Project Information

**Project:** OSINT Investigator

**Type:** Cybersecurity / OSINT Educational Tool

**Language:** Python

**Interface:** Python GUI

**Purpose:** Cybersecurity education and authorized OSINT research

---

# ⚖️ Disclaimer

This software is provided for **educational and authorized security research purposes**.

The developer does not encourage or support illegal activities, harassment, unauthorized surveillance, privacy violations, unauthorized access, exploitation, or any activity intended to harm another person or organization.

The user is solely responsible for how the software is used.

Before conducting an investigation, ensure that you have appropriate authorization and that your activities comply with applicable laws, regulations, and the terms of the services being accessed.

---

## ⭐ Project Status

**Current Version:** 1.0

**Status:** Educational Project

Built as part of cybersecurity learning and practical OSINT experimentation.
