# 🌐 Advanced Proxy Scraper

A fast, multi-source proxy scraper and verifier written in Python. Aggregates free proxies from **6+ public sources**, deduplicates them, and verifies connectivity at high speed using multithreaded socket checks.

## Features

- **Multi-source scraping** — Pulls proxies from ProxyScrape, FreeProxyList, GeoNode, HideMN, FreeProxyWorld, and OpenProxyList
- **Protocol support** — HTTP, HTTPS, SOCKS4, and SOCKS5
- **High-speed verification** — 300 concurrent threads with configurable timeout
- **Live progress bar** — Real-time terminal feedback during verification
- **Auto-deduplication** — Removes duplicate entries across all sources
- **Dated output** — Saves verified proxies to a timestamped `.txt` file

## Requirements

- Python 3.7+
- `requests`

```
pip install requests
```

## Usage

```
python proxy_scraper.py
```

You'll be prompted to select which proxy types to scrape:

```
Select proxy types to scrape:
  1. HTTP
  2. HTTPS
  3. SOCKS4
  4. SOCKS5
  5. All

Enter choices (comma separated, e.g. 1,3):
```

The scraper will cycle through all sources, collect proxies, remove duplicates, then verify each one. Verified proxies are saved to a file named like `4-21-2026_Proxys.txt`.

## Output

The output file contains one proxy per line in `protocol://ip:port` format:

```
Select proxy types to scrape:
  1. HTTP
  2. HTTPS
  3. SOCKS4
  4. SOCKS5
  5. All

Enter choices (comma separated, e.g. 1,3): 5

Scraping: http, https, socks4, socks5

[ProxyScrape]
  [ProxyScrape] 500/24145 fetched - 500 matched
  [ProxyScrape] 1000/24158 fetched - 1000 matched
  [ProxyScrape] 1500/24158 fetched - 1500 matched
  [ProxyScrape] 2000/24172 fetched - 2000 matched
  [ProxyScrape] 2500/24194 fetched - 2500 matched
  [ProxyScrape] 3000/24205 fetched - 3000 matched
  [ProxyScrape] 3500/24210 fetched - 3500 matched
  [ProxyScrape] 4000/24218 fetched - 4000 matched
  [ProxyScrape] 4500/24225 fetched - 4500 matched
  [ProxyScrape] 5000/24238 fetched - 5000 matched
  [ProxyScrape] 5500/24252 fetched - 5500 matched
  [ProxyScrape] 6000/24273 fetched - 6000 matched
  [ProxyScrape] 6500/24295 fetched - 6500 matched
  [ProxyScrape] 7000/24291 fetched - 7000 matched
  [ProxyScrape] 7500/24313 fetched - 7500 matched
  [ProxyScrape] 8000/24329 fetched - 8000 matched
  [ProxyScrape] 8500/24344 fetched - 8500 matched
  [ProxyScrape] 9000/24361 fetched - 9000 matched
  [ProxyScrape] 9500/24384 fetched - 9500 matched
  [ProxyScrape] 10000/24390 fetched - 10000 matched
  [ProxyScrape] 10500/24413 fetched - 10500 matched
  [ProxyScrape] 11000/24432 fetched - 11000 matched
  [ProxyScrape] 11500/24443 fetched - 11500 matched
  [ProxyScrape] 12000/24470 fetched - 12000 matched

[FreeProxyList]
  [FreeProxyList] 300 scraped - 298 matched

[GeoNode]
  [GeoNode] Page 1 - 500/8057 fetched - 500 matched
  [GeoNode] Page 2 - 1000/8057 fetched - 1000 matched
  [GeoNode] Page 3 - 1500/8057 fetched - 1500 matched
  [GeoNode] Page 4 - 2000/8057 fetched - 2000 matched
  [GeoNode] Page 5 - 2500/8057 fetched - 2500 matched
  [GeoNode] Page 6 - 3000/8057 fetched - 3000 matched
  [GeoNode] Page 7 - 3500/8057 fetched - 3500 matched
  [GeoNode] Page 8 - 4000/8057 fetched - 4000 matched
  [GeoNode] Page 9 - 4500/8057 fetched - 4500 matched
  [GeoNode] Page 10 - 5000/8057 fetched - 5000 matched
  [GeoNode] Page 11 - 5500/8057 fetched - 5500 matched
  [GeoNode] Page 12 - 6000/8057 fetched - 6000 matched
  [GeoNode] Page 13 - 6500/8057 fetched - 6500 matched
  [GeoNode] Page 14 - 7000/8057 fetched - 7000 matched
  [GeoNode] Page 15 - 7500/8057 fetched - 7500 matched
  [GeoNode] Page 16 - 8000/8057 fetched - 8000 matched
  [GeoNode] Page 17 - 8057/8057 fetched - 8057 matched

[HideMN]
  [HideMN] Failed with status 403 (Cloudflare?)

[FreeProxyWorld]
  [FreeProxyWorld] Page 1/40 - 51 matched
  [FreeProxyWorld] Page 2/40 - 101 matched
  [FreeProxyWorld] Page 3/40 - 152 matched
  [FreeProxyWorld] Page 4/40 - 202 matched
  [FreeProxyWorld] Page 5/40 - 253 matched
  [FreeProxyWorld] Page 6/40 - 303 matched
  [FreeProxyWorld] Page 7/40 - 353 matched
  [FreeProxyWorld] Page 8/40 - 404 matched
  [FreeProxyWorld] Page 9/40 - 454 matched
  [FreeProxyWorld] Page 10/40 - 504 matched
  [FreeProxyWorld] Page 11/40 - 554 matched
  [FreeProxyWorld] Page 12/40 - 604 matched
  [FreeProxyWorld] Page 13/40 - 656 matched
  [FreeProxyWorld] Page 14/40 - 708 matched
  [FreeProxyWorld] Page 15/40 - 758 matched
  [FreeProxyWorld] Page 16/40 - 808 matched
  [FreeProxyWorld] Page 17/40 - 860 matched
  [FreeProxyWorld] Page 18/40 - 912 matched
  [FreeProxyWorld] Page 19/40 - 964 matched
  [FreeProxyWorld] Page 20/40 - 1014 matched
  [FreeProxyWorld] Page 21/40 - 1064 matched
  [FreeProxyWorld] Page 22/40 - 1115 matched
  [FreeProxyWorld] Page 23/40 - 1166 matched
  [FreeProxyWorld] Page 24/40 - 1217 matched
  [FreeProxyWorld] Page 25/40 - 1267 matched
  [FreeProxyWorld] Page 26/40 - 1318 matched
  [FreeProxyWorld] Page 27/40 - 1368 matched
  [FreeProxyWorld] Page 28/40 - 1418 matched
  [FreeProxyWorld] Page 29/40 - 1470 matched
  [FreeProxyWorld] Page 30/40 - 1521 matched
  [FreeProxyWorld] Page 31/40 - 1571 matched
  [FreeProxyWorld] Page 32/40 - 1621 matched
  [FreeProxyWorld] Page 33/40 - 1671 matched
  [FreeProxyWorld] Page 34/40 - 1721 matched
  [FreeProxyWorld] Page 35/40 - 1773 matched
  [FreeProxyWorld] Page 36/40 - 1824 matched
  [FreeProxyWorld] Page 37/40 - 1874 matched
  [FreeProxyWorld] Page 38/40 - 1925 matched
  [FreeProxyWorld] Page 39/40 - 1976 matched
  [FreeProxyWorld] Page 40/40 - 2026 matched

[OpenProxyList]
  [OpenProxyList] http.txt - 6976 proxies
  [OpenProxyList] https.txt - 17641 proxies
  [OpenProxyList] socks4.txt - 5335 proxies
  [OpenProxyList] socks5.txt - 29966 proxies

Total: 82299 scraped, 73130 unique

Verifying 73130 proxies...

  [##################################################] 100% | 73130/73130 checked | 21065 alive | 52065 dead

Verification complete: 21065 alive / 52065 dead out of 73130

Saved 21065 verified proxies to 4-21-2026_Proxys.txt
```

## Configuration

These values can be adjusted at the top of the verification section in the script:

| Variable | Default | Description |
|---|---|---|
| `VERIFY_TIMEOUT` | `5` | Socket connection timeout in seconds |
| `VERIFY_THREADS` | `300` | Number of concurrent verification threads |

## Sources

| Source | Method | Notes |
|---|---|---|
| [ProxyScrape](https://proxyscrape.com) | JSON API | Paginated, large dataset |
| [FreeProxyList](https://free-proxy-list.net) | HTML scraping | Single page |
| [GeoNode](https://geonode.com) | JSON API | Paginated, sorted by last checked |
| [HideMN](https://hide.mn) | HTML scraping | May be behind Cloudflare |
| [FreeProxyWorld](https://freeproxy.world) | HTML scraping | Up to 40 pages |
| [OpenProxyList](https://openproxylist.xyz) | Plain text lists | One file per protocol |

## How It Works

1. **Scrape** — Each source is queried sequentially, with pagination handled automatically
2. **Deduplicate** — All collected proxies are filtered to unique entries
3. **Verify** — Each proxy is tested via a raw TCP socket connection to confirm the port is open
4. **Export** — Living proxies are written to a dated text file

> **Note:** Verification checks that the port is open and accepting connections. It does not guarantee the proxy will successfully forward your traffic or that it provides anonymity.

## Disclaimer

This tool is provided for educational and research purposes. Free public proxies are inherently unreliable and should not be used for anything sensitive. The author is not responsible for how scraped proxies are used. Always respect the terms of service of the sources and any applicable laws.

## License

MIT
