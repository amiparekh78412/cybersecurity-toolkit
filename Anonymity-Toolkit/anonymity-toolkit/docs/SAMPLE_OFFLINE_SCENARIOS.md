# Sample offline scenarios (no internet needed)

All of these use the Learning Simulator (`data/scenarios.json`) and are **SIMULATED**.

1. **"Is my coffee-shop Wi-Fi safe?"** Open *Public Wi-Fi with HTTPS*. Question: what can the operator see although
   HTTPS is on? (Metadata such as domains; not content.) Then open *VPN tunnel* and compare what changes.
2. **"My VPN dropped."** Open *VPN failure and kill switch*. Compare the two flows. Question: when would your real
   address reach the website? Then record on the Privacy Checklist whether *you* checked your kill switch.
3. **"Why am I still tracked on a VPN?"** Open *Browser tracking*. Question: which things does a VPN not change?
4. **"Who sees my DNS lookups?"** Open *DNS privacy*. Compare plain and encrypted DNS flows.

Offline report practice: with Offline mode on, open **Reports**, tick *Include learning scenario summaries* and save a
report. The scenario lines are labelled SIMULATED and are kept apart from any observed data.
