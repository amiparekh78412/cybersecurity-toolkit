# Project demonstration script (about 8 minutes)

1. **Intro (30 s).** "This app helps people understand what VPNs and proxies do, using real observations and offline
   simulations. It never claims anonymity."
2. **Architecture (1 min).** Show the README Mermaid diagram: GUI → controller → services/storage; services have no GUI
   imports; network work runs in a worker thread and results return through a queue.
3. **Offline first (1 min).** Start in Offline mode. Open the **Learning Simulator**: show *VPN tunnel* and
   *VPN failure and kill switch*. Point out the SIMULATED badge and "what each party can see".
4. **Online lookup (1 min).** Switch to Online, run an IP lookup, point out validation, timestamp, elapsed time.
   Show the offline/duplicate-click behaviour.
5. **Before/after (1.5 min).** Connect your VPN outside the app, look up again, open **Network Comparison**.
   Read the explanation aloud, stressing the limitations ("changed address ≠ proven anonymity").
6. **Proxy tester (1 min).** Show validation errors, then `http://127.0.0.1:9` failing as a proxy-connection error.
   Mention credentials stay in memory only and the authorisation tick-box.
7. **Privacy checklist (1 min).** Mark two items; show that nothing is scored and statuses are user-reported.
8. **Report (1 min).** Preview, tick *Redact IP addresses*, save HTML, open it. Show the four evidence labels.
9. **Testing and safety (1 min).** Run `python -m unittest discover -s tests -v` (network mocked). Show a corrupted
   `data.json` being quarantined. Close with limitations and the ethical-use statement.
