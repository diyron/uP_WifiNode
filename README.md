# uP_WifiNode
Micropython project for ESP32-platform,
simple sensor node pushing data HTTPS POST via wifi connection

### update (2020-02-23)
- add exception handling for TLS
- add NTP time sync for timestamp
- writes last exception with timestamp to file "crash_logs.txt"
