# 🌐 Advanced Proxy Scraper

A fast, multi-source proxy scraper and verifier written in Python. Aggregates free proxies from **30+ public sources**, deduplicates them, and verifies connectivity at high speed using configurable multithreaded socket checks.

## Features

- **Multi-source scraping** — 13 top-level scrapers, with 11 of them being GitHub community lists bundled under one source (30+ distinct endpoints in total)
- **Protocol support** — HTTP, HTTPS, SOCKS4, and SOCKS5
- **Configurable verification** — Prompted at runtime for thread count and per-proxy timeout
- **Live progress bars** — One bar for the scraping phase, one for verification, no verbose per-source output
- **Per-source 60s timeout** — A slow or hung source is skipped automatically so it can't stall the pipeline
- **Hard wall-clock HTTP timeout** — Each request is wrapped in a 25-second wall-clock guard, defending against slow-byte-drip servers that sneak past normal read timeouts
- **Auto-deduplication** — Removes duplicate entries across all sources
- **Dated output** — Saves verified proxies to a timestamped `.txt` file in plain `ip:port` format

## Requirements

- Python 3.7+
- `requests`

```
pip install requests
```

## Usage

```
python scrapper.py
```

You'll be prompted for:

```
Select proxy types to scrape:
  1. HTTP
  2. HTTPS
  3. SOCKS4
  4. SOCKS5
  5. All

Enter choices (comma separated, e.g. 1,3): 5

Verification settings:
  Threads for proxy checking [default 300]: 300
  Timeout per proxy (seconds) [default 5]: 5
```

The scraper cycles through all sources (with a 60-second cap on each), dedupes the results, then verifies each proxy over a raw TCP socket. Verified proxies are saved to a file named like `4-23-2026_Proxys.txt`.

## Example Run

```
Advanced Proxy Scrapper By Legend
Scrapping & Verifying proxys from 25+ sites & Sources... Enjoy

Select proxy types to scrape:
  1. HTTP
  2. HTTPS
  3. SOCKS4
  4. SOCKS5
  5. All

Enter choices (comma separated, e.g. 1,3): 5

Verification settings:
  Threads for proxy checking [default 300]: 900
  Timeout per proxy (seconds) [default 5]: 4

Scraping: http, https, socks4, socks5
Verification: 900 threads, 4.0s timeout

Scraping 13 sources (60s timeout per source)...
  [##################################################] 100% | 13/13 sources | 412580 scraped | Geonix

Total: 412580 scraped, 298411 unique

Verifying 298411 proxies (900 threads, 4.0s timeout)...

  [##################################################] 100% | 298411/298411 checked | 43218 alive | 255193 dead

Verification complete: 43218 alive / 255193 dead out of 298411

Saved 43218 verified proxies to 4-23-2026_Proxys.txt
```

## Output format

One proxy per line, plain `ip:port` (protocol prefix stripped):

```
45.12.34.56:8080
102.213.7.19:3128
185.199.229.156:1080
...
```

## Configuration

Most knobs are set at runtime via prompts. A few constants near the top of `scrapper.py` control low-level behavior:

| Variable | Default | Description |
|---|---|---|
| `REQUEST_TIMEOUT` | `(8, 12)` | `(connect, read)` timeout tuple for each HTTP call |
| `REQUEST_WALL_TIMEOUT` | `25` | Hard wall-clock timeout per HTTP request — guards against slow-drip servers |
| `PER_SOURCE_TIMEOUT` | `60` | Maximum wall-clock seconds any single source is allowed before being skipped |

## Sources

| Source | Method | Notes |
|---|---|---|
| [ProxyScrape](https://proxyscrape.com) | JSON API | Paginated, large dataset |
| [FreeProxyList](https://free-proxy-list.net) | HTML scraping | Single page |
| [GeoNode](https://geonode.com) | JSON API | Paginated, sorted by last checked |
| [HideMN](https://hide.mn) | HTML scraping | Often 403s behind Cloudflare |
| [FreeProxyWorld](https://freeproxy.world) | HTML scraping | Up to 40 pages |
| [OpenProxyList](https://openproxylist.xyz) | Plain text lists | One file per protocol |
| GitHubLists | Plain text / JSON | Aggregates 11 community-maintained repos (see below) |
| [spys.me](https://spys.me) | Plain text | HTTP/S flags parsed from list |
| [ProxySpace](https://proxyspace.pro) | Plain text lists | One file per protocol |
| [ProxyScan](https://www.proxyscan.io) | JSON API | Per-protocol endpoint |
| [ProxyDaily](https://proxy-daily.com) | HTML scraping | Daily refresh |
| [advanced.name](https://advanced.name/freeproxy) | Plain text | Per-protocol `?type=` endpoint |
| [Geonix](https://free.geonix.com) | SSR cache JSON | Port is served as an image — entries without extractable port are skipped (OCR not implemented) |

### GitHub community lists bundled under `GitHubLists`

- [TheSpeedX/PROXY-List](https://github.com/TheSpeedX/PROXY-List)
- [monosans/proxy-list](https://github.com/monosans/proxy-list)
- [ProxyScraper/ProxyScraper](https://github.com/ProxyScraper/ProxyScraper)
- [sunny9577/proxy-scraper](https://github.com/sunny9577/proxy-scraper)
- [hookzof/socks5_list](https://github.com/hookzof/socks5_list)
- [mmpx12/proxy-list](https://github.com/mmpx12/proxy-list)
- [roosterkid/openproxylist](https://github.com/roosterkid/openproxylist)
- [prxchk/proxy-list](https://github.com/prxchk/proxy-list)
- [MuRongPIG/Proxy-Master](https://github.com/MuRongPIG/Proxy-Master)
- [zloi-user/hideip.me](https://github.com/zloi-user/hideip.me)
- [vakhov/fresh-proxy-list](https://github.com/vakhov/fresh-proxy-list)
- [proxifly/free-proxy-list](https://github.com/proxifly/free-proxy-list)

## How It Works

1. **Scrape** — Each source is queried sequentially with a hard 60-second per-source ceiling. Inside each source, every HTTP request has a `(8, 12)` connect/read timeout and a 25-second wall-clock guard to prevent slow-drip hangs.
2. **Deduplicate** — All collected proxies are filtered to unique `protocol://ip:port` entries.
3. **Verify** — Each proxy is tested via a raw TCP socket connection (`socket.connect`) to confirm the port is open. Thread count and timeout are user-configurable.
4. **Export** — Alive proxies are written to a dated text file as plain `ip:port`, one per line.

> **Note:** Verification only checks that the port is open and accepting connections. It does not guarantee the proxy will successfully forward your traffic or that it provides anonymity.

## Disclaimer

This tool is provided for educational and research purposes. Free public proxies are inherently unreliable and should not be used for anything sensitive. The author is not responsible for how scraped proxies are used. Always respect the terms of service of the sources and any applicable laws.

## Author

**Websites Scrapped & Scrapper Setup - legend | General code - Claude <3**

## License

MIT
