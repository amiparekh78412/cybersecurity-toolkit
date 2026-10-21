# Anonymity Toolkit: Run, Test and Proxy Commands

All commands are for **Windows Command Prompt** unless marked otherwise.
Requires **Python 3.11 or newer**.

---

## 1. One-time setup

```
cd C:\path\to\anonymity-toolkit
python --version
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

- Change `C:\path\to\anonymity-toolkit` to the folder where you unzipped the project.
- `python --version` must show 3.11 or higher.
- If `py -3.11` is not found, use `python -m venv .venv` instead.
- After activating, you should see `(.venv)` at the start of the line.
- **PowerShell:** if activation is blocked, run
  `Set-ExecutionPolicy -Scope Process Bypass` and then `.venv\Scripts\Activate.ps1`.

---

## 2. Every time you test

Open Command Prompt and run:

```
cd C:\path\to\anonymity-toolkit
.venv\Scripts\activate
python -m unittest discover -s tests
python main.py
```

- The unittest line should end with **OK** (about 100 tests).
- `python main.py` opens the app. Close the window to stop it.

---

## 3. Optional: use a throwaway data folder

This keeps test data away from your real data. Run it **before** `python main.py`.

Command Prompt:
```
set ANONYMITY_TOOLKIT_HOME=C:\temp\at-test
python main.py
```

PowerShell:
```
$env:ANONYMITY_TOOLKIT_HOME = "C:\temp\at-test"
python main.py
```

To start fresh next time, delete only the test folder:
```
rmdir /s /q C:\temp\at-test
```

> With this folder set, About and Dashboard show `C:\temp\at-test\data.json`.
> To check that your user name is hidden, run the app **without** this setting.
> It should then show `%USERPROFILE%\.anonymity_toolkit\data.json`.

---

## 4. Start a local test proxy

Open a **second** Command Prompt window (separate from the app) and leave it open.

```
pip install proxy.py
proxy --hostname 127.0.0.1 --port 8899
```

Stop it with **Ctrl+C**.

---

## 5. How to change the proxy

The Proxy Tester tests **one proxy at a time** and has no saved list.
To test a different proxy, change the address in the form:

1. Switch to **Online** mode (bottom of the sidebar).
2. Open **Proxy Tester**.
3. Click the **Proxy URL** box and replace the old address with the new one.
4. Fill in **Username** and **Password** only if that proxy needs a login.
   Otherwise leave them empty. The password box is cleared after every test, so type it again each time.
5. Tick the authorisation box (it stays ticked after the first time).
6. Click **Test proxy**.

Rules for the address: it must start with `http://` or `https://`, include a port, and must **not**
contain a username or password inside it.

Every result is saved automatically (never with passwords). Reports include all of them
if "Include proxy test results" is ticked.

### Add a second local proxy

Open a **third** Command Prompt window:
```
proxy --hostname 127.0.0.1 --port 8900
```
Then test `http://127.0.0.1:8899` and `http://127.0.0.1:8900` one after the other.

### A local proxy that needs a login

```
proxy --hostname 127.0.0.1 --port 8901 --basic-auth demo:demo123
```
Enter `http://127.0.0.1:8901` as the address, `demo` as Username and `demo123` as Password.
Use made-up credentials like these, never a real password.

### Example addresses and expected results

| Address | Needs | Expected result |
|---|---|---|
| `http://127.0.0.1:8899` | proxy on port 8899 | SUCCESS |
| `http://127.0.0.1:8900` | proxy on port 8900 | SUCCESS |
| `http://localhost:8899` | proxy on port 8899 | SUCCESS |
| `http://127.0.0.1:8901` + demo / demo123 | login proxy | SUCCESS |
| `http://127.0.0.1:8901` + wrong password | login proxy | FAILED: proxy authentication |
| `http://127.0.0.1:9` | nothing running | FAILED: proxy connection |
| `proxy.com:80` | nothing | rejected: address must start with http:// or https:// |
| `http://host` | nothing | rejected: port is missing |
| `http://host:99999` | nothing | rejected: invalid port |

When a test succeeds with a proxy on your own PC, the Egress IP is your normal public IP.
That is expected: the proxy runs on your PC and forwards through your normal internet.

Only test proxies you own or are authorised to use. Avoid free public proxy lists.

---

## 6. Suggested test order

1. Run the unit tests (section 2). Expect **OK**.
2. Start the app and click all 8 pages. Switch Light/Dark and restart to check the theme is remembered.
3. Switch to **Online**. Run an IP lookup on IP Information.
4. Connect your VPN (outside this app), run a second lookup, then open **Network Comparison** and compare.
5. Start the local proxy (section 4) and test it in Proxy Tester. Then stop it and test again to see a failure.
6. Privacy Checklist: set a few statuses, click Show details, restart and check they were remembered.
7. Learning Simulator: open all 7 scenarios (each says SIMULATED).
8. Reports: preview, tick "Redact IP addresses", save a .txt and a .html file and open them.
9. Close the app, run it **without** the throwaway folder, and confirm About and Dashboard show
   `%USERPROFILE%\.anonymity_toolkit\data.json` and not your real user name.

---

## 7. Common problems

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Reinstall Python from python.org and tick "Add Python to PATH" |
| `'pip' is not recognized` | Use `python -m pip install -r requirements.txt` |
| `No module named customtkinter` | Activate the venv (`.venv\Scripts\activate`), then run `pip install -r requirements.txt` again |
| Port 8899 already in use | Use another port, for example `--port 8902`, and test that address instead |
| Check what is using a port | `netstat -ano \| findstr :8899` |
| Proxy test says connection failed | Make sure the proxy window is still open and the address and port match exactly |
