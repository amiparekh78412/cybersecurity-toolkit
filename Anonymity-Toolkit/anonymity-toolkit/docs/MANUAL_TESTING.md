# Manual testing checklist

Tick each box as you test. Use a temporary data folder if you do not want to touch your saved data:
`ANONYMITY_TOOLKIT_HOME=/tmp/at-test python main.py` (Linux/macOS) or `set ANONYMITY_TOOLKIT_HOME=C:\temp\at-test` first (Windows).

## Startup and navigation
- [ ] `python main.py` opens the window without errors.
- [ ] All 8 sidebar pages open; switching away and back redraws each page fully.
- [ ] Resizing the window keeps content usable; the sidebar stays fixed width.
- [ ] Mode starts as **Offline**; selector switches the badge to ONLINE and back.
- [ ] Light/Dark switch changes the whole app and is remembered after restart.
- [ ] Closing the window exits the process cleanly.

## IP Information
- [ ] Offline: button disabled with an explanatory message.
- [ ] Online: lookup shows IP, version, timestamp, source, elapsed time.
- [ ] Double-clicking does not start two lookups; button shows "Looking up…".
- [ ] Disconnect internet: readable error, no traceback; button re-enabled.
- [ ] Result is recorded automatically ("Saved as observation #n").

## Proxy Tester
- [ ] Test button stays disabled until the authorisation box is ticked (and Online).
- [ ] Bad inputs give clear messages: `proxy.com:80`, `ftp://x:1`, `http://host`, `http://host:99999`, `http://u:p@host:80`.
- [ ] `http://127.0.0.1:9` reports a proxy connection failure.
- [ ] A proxy you own succeeds and shows status, elapsed time and egress IP.
- [ ] Password box clears after each test; no password in the saved data file or the console.

## Network Comparison
- [ ] With fewer than two observations a helpful message appears and Compare is disabled.
- [ ] Two different IPs → "OBSERVED ADDRESS CHANGED" with the "does not prove" wording.
- [ ] Two identical IPs → "IDENTICAL" with the "does not establish" wording.
- [ ] Limitations and follow-up checks are always shown. Works in Offline mode.

## Privacy Checklist
- [ ] All items start as "Not verified". Statuses change badge colour and the summary counts.
- [ ] "Show details" reveals evidence, limitations and guided steps.
- [ ] Answers persist after restart; "Reset checklist" clears them.

## Learning Simulator
- [ ] All 7 scenarios open offline; every card heading says SIMULATED.
- [ ] Diagram text readable in light and dark mode; wraps when the window is narrow.

## Reports
- [ ] Preview shows sections labelled OBSERVED, USER-REPORTED / UNVERIFIED, and SIMULATED only if ticked.
- [ ] Save as .txt and .html; open both; HTML renders and has no external requests.
- [ ] "Redact IP addresses" replaces addresses with [IP-1], [IP-2]; same address = same token.
- [ ] Saving inside the app data folder is refused; saving to a read-only folder gives a friendly error.
- [ ] No passwords or credentials in any report.

## Storage
- [ ] Dashboard shows the data file location; "Clear saved history" asks first and then empties counts.
- [ ] Add junk text to `data.json`, restart: warning shown, `data.corrupt-…json` created, app works.

## Acceptance criteria (from the project brief)
- [ ] GUI launches · [ ] pages open · [ ] IP lookup handles success/failure · [ ] proxy test validates and handles failures
- [ ] comparison wording is qualified · [ ] checklist shows evidence and limits · [ ] simulator works offline
- [ ] Offline mode makes no requests · [ ] reports generate from local data · [ ] storage handles missing/corrupt files
- [ ] tests pass offline · [ ] README matches the app · [ ] no credentials stored or logged · [ ] nothing claims guaranteed anonymity
