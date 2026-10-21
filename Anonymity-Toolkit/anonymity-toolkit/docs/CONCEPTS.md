# Concepts to understand before presenting

- **Public IP address vs private/local address; NAT.** What a website sees is your network's public address.
- **What a VPN does:** encrypts traffic into a tunnel to the VPN server; websites see the server's address; the VPN
  provider can see where you connect. **Split tunnelling**, **kill switch** and **leaks** (DNS, WebRTC, IPv6).
- **What a proxy does:** relays requests for one application; HTTP `CONNECT` tunnelling for HTTPS; the proxy operator
  sees your real IP and destinations; plain `http://` sites are readable by the proxy.
- **HTTPS/TLS:** protects content from the network path, not metadata such as destination host names.
- **DNS:** name lookups reveal visited sites to the resolver; DoH/DoT; DNS leak.
- **Browser tracking:** cookies, accounts, third-party trackers, fingerprinting; why a VPN does not stop them.
- **Public Wi-Fi risks** and why HTTPS still helps.
- **Evidence kinds:** observed vs user-reported vs unverified vs simulated, and why the report separates them.
- **Defensive design choices:** timeouts, input validation, threads + queue (GUI never freezes), atomic file writes,
  corrupted-file recovery, credential redaction, offline mode as the safe default.
- **Testing:** `unittest`, mocking HTTP so tests are offline and repeatable.
- **Ethics:** only test what you own or are authorised to test; why there is no scanning or proxy discovery.
