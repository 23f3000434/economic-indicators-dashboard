# Reviewed market fixtures

Original public data bodies captured with verified TLS on 15 October 2026 UTC (16 October IST). The Upstox credential and all request headers are excluded. Fixtures are test-only.

| Body | URL | SHA-256 |
| --- | --- | --- |
| nse_quotes | https://www.nseindia.com/api/allIndices | db3f17422b07bc5ed5ab0c5c537fa1a1177e178e59af2306eaf8db00feac8a57 |
| upstox_sensex | https://api.upstox.com/v3/market-quote/quotes?instrument_key=BSE_INDEX%7CSENSEX | e66de810577aa9f53335a22162e727a0b7200a3074b3b766e908755b32984b04 |
| upstox_status_nse | https://api.upstox.com/v2/market/status/NSE | 692488ac0baa75935a1e9e71d2d642fb490fe0239ef21518aabf43222732789c |
| upstox_status_bse | https://api.upstox.com/v2/market/status/BSE | de70963442bbe9c9bee14e987f33b225af5c93e541544634caa5f7e25f0eadac |

Reviewed: NSE NIFTY BANK 55810.5, previous55316; NIFTY IT30719.8, previous30171. NSE exchange timestamp15-Oct-2026 15:30 IST. SENSEX74315.61; documented net change1533.72 implies previous72781.89; V3 prev_close_price is null and OHLC close is current close. Last-trade milliseconds give15-Oct-2026 15:59:59.981 IST; response timestamp is later and must not replace it. Both exchange status responses are CLOSING_END.

Verified regular-session timetable: https://api.upstox.com/v2/market/timings/2026-10-15 · 599 bytes · SHA-256 `959c7a6440681c617b90dcc00892f2fc22c9f743d09a6aa4da57aacf1e00941b`. Both NSE/BSE regular sessions end at 15:30 IST; CLOSING_END at 16:00 is a distinct phase event.
