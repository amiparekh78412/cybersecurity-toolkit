# Anonymity Toolkit

### A Python-Based Network Privacy & Cybersecurity Learning Application

Anonymity Toolkit is a Python desktop application developed to explore **network privacy, VPN concepts, proxy servers, public IP addresses, and anonymity-related security practices**.

The project provides interactive tools for basic network diagnostics, along with offline learning simulations to help cybersecurity students understand how different network privacy technologies work.

> **Disclaimer:** This application is intended for educational purposes. It does not provide guaranteed anonymity, function as a VPN, or replace professional privacy and security tools.

---

## Features and Functionality

### 1. Public IP Lookup
- Retrieves the current public IP address using an online IP lookup service.
- Helps users understand how their public IP address is visible to external services.
- Requires an internet connection.

### 2. HTTP/HTTPS Proxy Tester
- Tests connectivity through user-configured HTTP or HTTPS proxies.
- Helps users understand how proxy routing affects network requests.
- Displays connection results and relevant errors.
- Supports testing authorized proxy servers.

### 3. Network Observation Comparison
- Allows users to compare network observations collected under different connection conditions.
- Useful for understanding how a VPN or proxy may change the public IP address observed by an external service.
- Does not automatically verify complete anonymity or VPN security.

### 4. Privacy Checklist
- Provides a seven-item privacy checklist.
- Helps users review important privacy and security considerations.
- Saves checklist progress locally.

### 5. Offline Learning Simulator
- Includes seven educational network privacy scenarios.
- Explains VPN, proxy, and anonymity-related concepts.
- Works without an internet connection.
- Designed for learning rather than performing real network attacks.

### 6. Report Generator
- Generates investigation and observation reports.
- Supports TXT and HTML report formats.
- Includes optional IP address redaction to reduce accidental exposure of sensitive information.

### 7. Online and Offline Modes
- Offline mode is available by default for educational activities.
- Online mode enables features requiring network access, such as public IP lookup and proxy testing.

### 8. Desktop Dashboard
- Graphical user interface built with CustomTkinter.
- Sidebar navigation for accessing application modules.
- Light and dark theme support.
- Local storage for application history and settings.

---

## Technologies Used

| Technology | Purpose |
|---|---|
| Python 3.11+ | Main programming language |
| CustomTkinter | Desktop graphical user interface |
| Requests | HTTP requests and network connectivity |
| Tkinter | Underlying GUI framework |
| JSON | Local data storage and simulator scenarios |
| unittest | Automated unit testing |
| HTML / TXT | Report generation |

---

## System Requirements

Before running the application, ensure that your computer meets these requirements.

**Software:**
- Python 3.11 or later
- pip (Python package installer)
- Internet connection for online features
- Windows, or another desktop operating system supported by the dependencies

**Python packages:**
- `customtkinter==5.2.2`
- `requests>=2.31,<3`

All required third-party dependencies are listed in `requirements.txt`.

---

## Installation Guide

### Step 1 — Download the Project

1. Open the GitHub repository.
2. Click the green **Code** button.
3. Select **Download ZIP**.
4. Extract the downloaded ZIP file.
5. Open the `Anonymity-Toolkit` folder inside the extracted repository.

Alternatively, clone the repository using Git:

```bash
git clone https://github.com/amiparekh78412/cybersecurity-toolkit.git
```

Then open the project directory:

```bash
cd cybersecurity-toolkit/Anonymity-Toolkit
```

### Step 2 — Verify Python Installation

Open Command Prompt or PowerShell in the `Anonymity-Toolkit` directory.

```bash
python --version
```

Python 3.11 or later is recommended.

If Python is not installed, download it from:

https://www.python.org/downloads/

### Step 3 — Create a Virtual Environment

On Windows:

```powershell
python -m venv .venv
```

Activate it using Command Prompt:

```cmd
.venv\Scripts\activate
```

Or using PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, use Command Prompt to activate the virtual environment instead.

### Step 4 — Install Dependencies

Run:

```bash
python -m pip install -r requirements.txt
```

This installs the packages required by the application.

### Step 5 — Run the Application

Start Anonymity Toolkit:

```bash
python main.py
```

The desktop application window should open.

---

## How to Use the Application

### Public IP Lookup

1. Launch the application.
2. Enable Online Mode.
3. Navigate to the Public IP module.
4. Start the lookup.
5. Review the returned public IP address.

### Proxy Testing

1. Enable Online Mode.
2. Open the Proxy Tester.
3. Enter an authorized HTTP/HTTPS proxy address.
4. Start the connection test.
5. Review the result and any connection errors.

Example proxy address:

```text
http://127.0.0.1:8899
```

This is an example of a locally hosted proxy. It will only work if a compatible proxy server is running on that port.

### Network Comparison

1. Open the Network Comparison module.
2. Record the initial network observation.
3. Change the network connection or VPN state externally, if desired.
4. Record another observation.
5. Compare the results.

The application does not establish or manage VPN connections itself.

### Privacy Checklist

1. Open the Privacy Checklist.
2. Review the seven privacy items.
3. Mark the items you have reviewed or completed.
4. Revisit the checklist to track your progress.

### Offline Simulator

1. Open the Simulator module.
2. Select one of the seven available scenarios.
3. Read the scenario explanation.
4. Explore the network privacy concepts presented.

The simulator is educational and does not create real VPN tunnels or launch attacks.

### Report Generation

1. Open the Reports module.
2. Review the available findings and observations.
3. Choose TXT or HTML export.
4. Enable IP redaction if you want to avoid exposing IP addresses.
5. Generate and save the report.

---

## Run Automated Tests

The project includes automated tests using Python's built-in `unittest` framework.

From the Anonymity Toolkit project directory, run:

```bash
python -m unittest discover -s tests
```

A successful test run should finish with:

```text
OK
```

Test results depend on the local environment and the version of the project.

---

## Project Structure

```text
Anonymity-Toolkit/
│
├── main.py
├── requirements.txt
├── README.md
│
├── app/
│   └── Application controller and supporting modules
│
├── ui/
│   └── Graphical interface and application pages
│
├── services/
│   └── IP lookup, proxy testing and privacy services
│
├── simulator/
│   └── Offline educational simulation logic
│
├── data/
│   └── Educational scenario data
│
├── storage/
│   └── Local JSON storage
│
├── reports/
│   └── TXT and HTML report generation
│
├── tests/
│   └── Automated unit tests
│
└── docs/
    └── Supporting documentation
```

---

## Important Limitations

Anonymity Toolkit is an educational project and has the following limitations:

- It does not provide or guarantee anonymity.
- It is not a VPN client and cannot establish VPN tunnels.
- Proxy testing focuses on HTTP/HTTPS proxies.
- SOCKS proxy testing is not supported.
- It does not provide comprehensive DNS, WebRTC, IPv6, or VPN kill-switch leak testing.
- Local JSON data is not encrypted.
- Online functionality depends on internet access and external service availability.

**Important:** A changed public IP address alone does not prove that a network connection is anonymous or fully protected.

---

## Ethical Usage

This project was developed for cybersecurity education and authorized testing.

Users should:
- Test only networks and proxy servers they own or have permission to use.
- Avoid exposing real IP addresses or sensitive information in public reports.
- Avoid using the application for unauthorized network activity.
- Understand the limitations of privacy and anonymity tools.

---

## Learning Outcomes

Developing this project helped explore:

- Python desktop application development
- Network privacy and public IP visibility
- VPN and proxy concepts
- HTTP requests and connection testing
- GUI navigation and modular programming
- Error handling and input validation
- Local data storage
- Automated testing
- Privacy-aware report generation

---

## Developer

**Ami Parekh**

Cybersecurity Learner | Python Developer

Cyber Security Program — Adani Skill Development Center

**GitHub:** https://github.com/amiparekh78412

**LinkedIn:** https://www.linkedin.com/in/ami-parekh-281628439/

---

## Feedback and Contributions

Feedback, suggestions, and improvements are welcome.

If you find an issue or have an idea for improving the project, feel free to open a GitHub issue.

---

**Anonymity Toolkit — Learn Network Privacy Through Practical Exploration.**
