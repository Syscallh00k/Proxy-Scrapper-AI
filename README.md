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
http://203.0.113.50:8080
https://198.51.100.22:3128
socks5://192.0.2.10:1080
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
