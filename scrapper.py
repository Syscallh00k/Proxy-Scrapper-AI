import requests
import json
import re
import socket
import sys
import threading
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT = (8, 12)
REQUEST_WALL_TIMEOUT = 25
SOURCE_TIMEOUT = 240
MAX_SOURCE_WORKERS = 16


def _safe_get(url, session=None, max_wall=REQUEST_WALL_TIMEOUT, **kwargs):
    """requests.get with a hard wall-clock timeout. Guards against slow-byte-drip servers
    that keep feeding a byte every few seconds so the per-read timeout never trips."""
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    getter = session.get if session is not None else requests.get
    box = {"resp": None, "exc": None}

    def _worker():
        try:
            box["resp"] = getter(url, **kwargs)
        except Exception as e:
            box["exc"] = e

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(max_wall)
    if t.is_alive():
        raise requests.exceptions.Timeout(f"wall-clock timeout after {max_wall}s: {url}")
    if box["exc"] is not None:
        raise box["exc"]
    return box["resp"]


def scrape_proxyscrape(selected_types):
    proxies = []
    url = "https://api.proxyscrape.com/v4/free-proxy-list/get"
    headers = {**HEADERS, "Origin": "https://proxyscrape.com", "Referer": "https://proxyscrape.com/"}
    skip = 0
    limit = 500

    while True:
        params = {
            "request": "get_proxies",
            "skip": skip,
            "proxy_format": "protocolipport",
            "format": "json",
            "limit": limit,
        }
        try:
            response = _safe_get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                break
            data = response.json()
        except Exception:
            break

        batch = data.get("proxies", [])
        for p in batch:
            proto = p.get("protocol", "").lower()
            is_ssl = p.get("ssl", False)
            if proto == "http" and is_ssl and "https" in selected_types:
                proxies.append(f"https://{p['ip']}:{p['port']}")
            elif proto in selected_types:
                proxies.append(p["proxy"])

        total = data.get("total_records", "?")
        print(f"  [ProxyScrape] {skip + len(batch)}/{total} fetched - {len(proxies)} matched")

        if not data.get("nextpage", False):
            break
        skip += limit

    return proxies


def scrape_freeproxylist(selected_types):
    proxies = []
    url = "https://free-proxy-list.net/en/"
    headers = {**HEADERS, "Accept": "text/html", "Referer": "https://free-proxy-list.net/"}

    try:
        response = _safe_get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            print(f"  [FreeProxyList] Failed with status {response.status_code}")
            return proxies
    except Exception as e:
        print(f"  [FreeProxyList] Request failed: {e}")
        return proxies

    rows = re.findall(
        r"<tr><td>(\d+\.\d+\.\d+\.\d+)</td><td>(\d+)</td><td>.*?</td>"
        r"<td.*?>.*?</td><td>.*?</td><td.*?>.*?</td>"
        r"<td.*?>(yes|no)?</td><td.*?>.*?</td></tr>",
        response.text,
    )

    for ip, port, https_flag in rows:
        if ip in ("0.0.0.0", "127.0.0.1", "127.0.0.7"):
            continue
        if https_flag == "yes" and "https" in selected_types:
            proxies.append(f"https://{ip}:{port}")
        elif "http" in selected_types:
            proxies.append(f"http://{ip}:{port}")

    print(f"  [FreeProxyList] {len(rows)} scraped - {len(proxies)} matched")
    return proxies


def scrape_geonode(selected_types):
    proxies = []
    url = "https://proxylist.geonode.com/api/proxy-list"
    headers = {**HEADERS, "Origin": "https://geonode.com", "Referer": "https://geonode.com/"}
    page = 1
    limit = 500
    total = None

    while True:
        params = {
            "limit": limit,
            "page": page,
            "sort_by": "lastChecked",
            "sort_type": "desc",
        }
        try:
            response = _safe_get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                break
            data = response.json()
        except Exception:
            break

        batch = data.get("data", [])
        if not batch:
            break

        if total is None:
            total = data.get("total", "?")

        for p in batch:
            ip = p.get("ip", "")
            port = p.get("port", "")
            protocols = p.get("protocols", [])
            for proto in protocols:
                proto = proto.lower()
                if proto in selected_types:
                    proxies.append(f"{proto}://{ip}:{port}")

        fetched = page * limit if total == "?" else min(page * limit, total)
        print(f"  [GeoNode] Page {page} - {fetched}/{total} fetched - {len(proxies)} matched")

        if len(batch) < limit:
            break
        page += 1

    return proxies


def scrape_hidemn(selected_types):
    proxies = []
    url = "https://hide.mn/en/proxy-list/"
    headers = {
        **HEADERS,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://hide.mn/en/proxy-list/",
    }
    start = 0

    while True:
        params = {"anon": "1234"}
        if start > 0:
            params["start"] = start
        try:
            response = _safe_get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                print(f"  [HideMN] Failed with status {response.status_code} (Cloudflare?)")
                break
        except Exception as e:
            print(f"  [HideMN] Request failed: {e}")
            break

        rows = re.findall(
            r"<tr>\s*<td>(\d+\.\d+\.\d+\.\d+)</td>\s*<td>(\d+)</td>"
            r"\s*<td.*?>.*?</td>\s*<td.*?>.*?</td>\s*<td.*?>(.*?)</td>",
            response.text,
            re.DOTALL,
        )

        for ip, port, type_str in rows:
            if ip in ("0.0.0.0", "127.0.0.1"):
                continue
            types = [t.strip().lower() for t in type_str.split(",")]
            for t in types:
                if t in selected_types:
                    proxies.append(f"{t}://{ip}:{port}")

        page_num = (start // 64) + 1
        print(f"  [HideMN] Page {page_num} - {len(proxies)} matched")

        next_start = start + 64
        if f"start={next_start}" not in response.text:
            break
        start = next_start

    return proxies


def scrape_freeproxyworld(selected_types):
    proxies = []
    url = "https://www.freeproxy.world/"
    headers = {
        **HEADERS,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.freeproxy.world/",
    }
    max_pages = 40
    page = 1

    while page <= max_pages:
        params = {
            "type": "",
            "anonymity": "",
            "country": "",
            "speed": "",
            "port": "",
            "page": page,
        }
        try:
            response = _safe_get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                print(f"  [FreeProxyWorld] Failed with status {response.status_code} (Cloudflare?)")
                break
        except Exception as e:
            print(f"  [FreeProxyWorld] Request failed: {e}")
            break

        rows = re.findall(
            r'<td style="font-weight: 500;">\s*(\d+\.\d+\.\d+\.\d+)\s*</td>'
            r'\s*<td>\s*<a href="/\?port=\d+">(\d+)</a>\s*</td>'
            r'(.*?)</tr>',
            response.text,
            re.DOTALL,
        )

        if not rows:
            break

        for ip, port, rest in rows:
            if ip in ("0.0.0.0", "127.0.0.1"):
                continue
            types = re.findall(r'class="badge[^"]*"[^>]*>\s*([\w]+)\s*</a>', rest)
            for t in types:
                t = t.lower()
                if t in selected_types:
                    proxies.append(f"{t}://{ip}:{port}")

        print(f"  [FreeProxyWorld] Page {page}/{max_pages} - {len(proxies)} matched")
        page += 1

    return proxies


def scrape_openproxylist(selected_types):
    proxies = []
    base_url = "https://api.openproxylist.xyz"
    headers = {**HEADERS, "Referer": "https://api.openproxylist.xyz/"}

    for proto in selected_types:
        try:
            response = _safe_get(f"{base_url}/{proto}.txt", headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                print(f"  [OpenProxyList] {proto}.txt failed with status {response.status_code}")
                continue
        except Exception as e:
            print(f"  [OpenProxyList] {proto}.txt request failed: {e}")
            continue

        lines = response.text.strip().splitlines()
        count = 0
        for line in lines:
            line = line.strip()
            if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", line):
                ip, port = line.rsplit(":", 1)
                if ip not in ("0.0.0.0", "127.0.0.1"):
                    proxies.append(f"{proto}://{ip}:{port}")
                    count += 1
        print(f"  [OpenProxyList] {proto}.txt - {count} proxies")

    return proxies


def _parse_plain_list(text, proto):
    out = []
    for line in text.strip().splitlines():
        line = line.strip()
        if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", line):
            ip, port = line.rsplit(":", 1)
            if ip not in ("0.0.0.0", "127.0.0.1"):
                out.append(f"{proto}://{ip}:{port}")
    return out


def _parse_plain_list_any(text, proto):
    out = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(?:(?:https?|socks[45])://)?(\d+\.\d+\.\d+\.\d+):(\d+)", line)
        if not m:
            continue
        ip, port = m.group(1), m.group(2)
        if ip in ("0.0.0.0", "127.0.0.1"):
            continue
        out.append(f"{proto}://{ip}:{port}")
    return out


def scrape_github_lists(selected_types):
    proxies = []
    repos = [
        ("TheSpeedX", {
            "http": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "socks4": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
            "socks5": "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
        }),
        ("monosans", {
            "http": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
            "socks4": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
            "socks5": "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
        }),
        ("ProxyScraper", {
            "http": "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/http.txt",
            "https": "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/https.txt",
            "socks4": "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/socks4.txt",
            "socks5": "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/socks5.txt",
        }),
        ("sunny9577", {
            "http": "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/http_proxies.txt",
            "socks4": "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/socks4_proxies.txt",
            "socks5": "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/socks5_proxies.txt",
        }),
        ("hookzof", {
            "socks5": "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
        }),
        ("mmpx12", {
            "http": "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
            "https": "https://raw.githubusercontent.com/mmpx12/proxy-list/master/https.txt",
            "socks4": "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks4.txt",
            "socks5": "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
        }),
        ("roosterkid", {
            "https": "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
            "socks4": "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS4_RAW.txt",
            "socks5": "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
        }),
        ("prxchk", {
            "http": "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt",
            "socks4": "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks4.txt",
            "socks5": "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt",
        }),
        ("MuRongPIG", {
            "http": "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/http.txt",
            "socks4": "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks4.txt",
            "socks5": "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks5.txt",
        }),
        ("zloi-user", {
            "http": "https://raw.githubusercontent.com/zloi-user/hideip.me/master/http.txt",
            "https": "https://raw.githubusercontent.com/zloi-user/hideip.me/master/https.txt",
            "socks4": "https://raw.githubusercontent.com/zloi-user/hideip.me/master/socks4.txt",
            "socks5": "https://raw.githubusercontent.com/zloi-user/hideip.me/master/socks5.txt",
        }),
        ("vakhov", {
            "http": "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt",
            "https": "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/https.txt",
            "socks4": "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/socks4.txt",
            "socks5": "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/socks5.txt",
        }),
        ("proxifly", {
            "http": "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
            "socks4": "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks4/data.txt",
            "socks5": "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt",
        }),
    ]
    headers = {**HEADERS, "Accept": "text/plain, */*"}

    for label, urls in repos:
        for proto, url in urls.items():
            if proto not in selected_types:
                continue
            try:
                response = _safe_get(url, headers=headers, timeout=REQUEST_TIMEOUT)
                if response.status_code != 200:
                    print(f"  [{label}] {proto} failed with status {response.status_code}")
                    continue
            except Exception as e:
                print(f"  [{label}] {proto} request failed: {e}")
                continue
            parsed = _parse_plain_list_any(response.text, proto)
            proxies.extend(parsed)
            print(f"  [{label}] {proto} - {len(parsed)} proxies")

    return proxies


def scrape_spys_me(selected_types):
    proxies = []
    headers = {**HEADERS, "Accept": "text/plain, text/html, */*", "Referer": "https://spys.me/"}
    endpoints = []
    if any(t in selected_types for t in ("http", "https")):
        endpoints.append(("https://spys.me/proxy.txt", "http"))
    if any(t in selected_types for t in ("socks4", "socks5")):
        endpoints.append(("https://spys.me/socks.txt", "socks"))

    for url, kind in endpoints:
        try:
            response = _safe_get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                print(f"  [SpysMe] {url} failed with status {response.status_code}")
                continue
        except Exception as e:
            print(f"  [SpysMe] {url} request failed: {e}")
            continue

        count = 0
        for line in response.text.splitlines():
            m = re.match(r"^(\d+\.\d+\.\d+\.\d+):(\d+)\s+([A-Z-]+)\s+([SHN!+-]*)", line.strip())
            if not m:
                continue
            ip, port, _country, flags = m.group(1), m.group(2), m.group(3), m.group(4)
            if ip in ("0.0.0.0", "127.0.0.1"):
                continue
            if kind == "http":
                proto = "https" if "S" in flags and "https" in selected_types else "http"
                if proto not in selected_types:
                    continue
                proxies.append(f"{proto}://{ip}:{port}")
                count += 1
            else:
                for proto in ("socks4", "socks5"):
                    if proto in selected_types:
                        proxies.append(f"{proto}://{ip}:{port}")
                        count += 1
        print(f"  [SpysMe] {url.rsplit('/', 1)[1]} - {count} proxies")

    return proxies


def scrape_proxyspace(selected_types):
    proxies = []
    headers = {**HEADERS, "Accept": "text/plain, */*", "Referer": "https://proxyspace.pro/"}
    urls = {
        "http": "https://proxyspace.pro/http.txt",
        "https": "https://proxyspace.pro/https.txt",
        "socks4": "https://proxyspace.pro/socks4.txt",
        "socks5": "https://proxyspace.pro/socks5.txt",
    }
    for proto in selected_types:
        url = urls.get(proto)
        if not url:
            continue
        try:
            response = _safe_get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                print(f"  [ProxySpace] {proto} failed with status {response.status_code}")
                continue
        except Exception as e:
            print(f"  [ProxySpace] {proto} request failed: {e}")
            continue
        parsed = _parse_plain_list_any(response.text, proto)
        proxies.extend(parsed)
        print(f"  [ProxySpace] {proto} - {len(parsed)} proxies")
    return proxies


def scrape_proxyscan(selected_types):
    proxies = []
    headers = {**HEADERS, "Accept": "application/json", "Referer": "https://www.proxyscan.io/"}
    type_map = {"http": "http", "https": "https", "socks4": "socks4", "socks5": "socks5"}

    for proto in selected_types:
        api_type = type_map.get(proto)
        if not api_type:
            continue
        url = f"https://www.proxyscan.io/api/proxy?type={api_type}&limit=100"
        try:
            response = _safe_get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                print(f"  [ProxyScan] {proto} failed with status {response.status_code}")
                continue
            data = response.json()
        except Exception as e:
            print(f"  [ProxyScan] {proto} request failed: {e}")
            continue

        count = 0
        if isinstance(data, list):
            for entry in data:
                ip = entry.get("Ip")
                port = entry.get("Port")
                if not ip or not port or ip in ("0.0.0.0", "127.0.0.1"):
                    continue
                proxies.append(f"{proto}://{ip}:{port}")
                count += 1
        print(f"  [ProxyScan] {proto} - {count} proxies")
    return proxies


def scrape_proxy_daily(selected_types):
    proxies = []
    headers = {**HEADERS, "Accept": "text/html", "Referer": "https://proxy-daily.com/"}
    try:
        response = _safe_get("https://proxy-daily.com/", headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            print(f"  [ProxyDaily] failed with status {response.status_code}")
            return proxies
    except Exception as e:
        print(f"  [ProxyDaily] request failed: {e}")
        return proxies

    sections = re.findall(
        r'<h3[^>]*>\s*(HTTP|SOCKS4|SOCKS5)[^<]*</h3>\s*<div class="centeredProxyList freeProxyStyle">(.*?)</div>',
        response.text,
        re.DOTALL | re.IGNORECASE,
    )
    counts = {}
    for heading, block in sections:
        h = heading.strip().upper()
        if h == "HTTP":
            proto = "http"
        elif h == "SOCKS4":
            proto = "socks4"
        elif h == "SOCKS5":
            proto = "socks5"
        else:
            continue
        if proto not in selected_types:
            continue
        parsed = _parse_plain_list_any(block, proto)
        proxies.extend(parsed)
        counts[proto] = counts.get(proto, 0) + len(parsed)
    for proto, c in counts.items():
        print(f"  [ProxyDaily] {proto} - {c} proxies")
    if not counts:
        print("  [ProxyDaily] no proxies parsed (layout changed?)")
    return proxies


def scrape_advanced_name(selected_types):
    proxies = []
    headers = {**HEADERS, "Accept": "text/plain, */*", "Referer": "https://advanced.name/freeproxy"}
    urls = {
        "http": "https://advanced.name/freeproxy/txt/?type=http",
        "https": "https://advanced.name/freeproxy/txt/?type=https",
        "socks4": "https://advanced.name/freeproxy/txt/?type=socks4",
        "socks5": "https://advanced.name/freeproxy/txt/?type=socks5",
    }
    for proto in selected_types:
        url = urls.get(proto)
        if not url:
            continue
        try:
            response = _safe_get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                print(f"  [AdvancedName] {proto} failed with status {response.status_code}")
                continue
        except Exception as e:
            print(f"  [AdvancedName] {proto} request failed: {e}")
            continue
        parsed = _parse_plain_list_any(response.text, proto)
        proxies.extend(parsed)
        print(f"  [AdvancedName] {proto} - {len(parsed)} proxies")
    return proxies


def scrape_geonix(selected_types):
    proxies = []
    landing = "https://free.geonix.com/en/"
    headers = {
        **HEADERS,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": landing,
    }

    try:
        session = requests.Session()
        response = _safe_get(landing, session=session, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            print(f"  [Geonix] Landing failed with status {response.status_code}")
            return proxies
    except Exception as e:
        print(f"  [Geonix] Landing request failed: {e}")
        return proxies

    cache_hashes = set(re.findall(r'/ssr/cache/([a-f0-9]{32,})', response.text))
    if not cache_hashes:
        print("  [Geonix] No SSR cache hash found on landing page")
        return proxies

    api_headers = {
        **HEADERS,
        "Accept": "application/json",
        "Referer": landing,
        "X-Requested-With": "XMLHttpRequest",
    }

    proto_map = {
        "HTTP": "http",
        "HTTPS": "https",
        "SOCKS4": "socks4",
        "SOCKS5": "socks5",
    }

    total_found = 0
    missing_port = 0
    for cache_hash in cache_hashes:
        api_url = f"https://free.geonix.com/ssr/cache/{cache_hash}"
        try:
            api_resp = _safe_get(api_url, session=session, headers=api_headers, timeout=REQUEST_TIMEOUT)
            if api_resp.status_code != 200:
                continue
            data = api_resp.json()
        except Exception:
            continue

        proxy_data = None
        if isinstance(data, dict):
            if "proxy" in data and isinstance(data["proxy"], dict):
                proxy_data = data["proxy"].get("data") or data["proxy"].get("content")
            elif "data" in data:
                proxy_data = data["data"]
        if not isinstance(proxy_data, list):
            continue

        for entry in proxy_data:
            if not isinstance(entry, dict):
                continue
            ip = entry.get("ip") or entry.get("address")
            port = entry.get("port")
            port_img = entry.get("portImageUrl") or entry.get("portImage") or ""
            if not port and port_img:
                m = re.search(r"(\d{2,5})", port_img)
                if m:
                    port = m.group(1)
            if not ip or not port:
                missing_port += 1
                continue

            raw_type = (entry.get("proxyType") or entry.get("type") or "HTTP").upper()
            proto = proto_map.get(raw_type, "http")
            if proto not in selected_types:
                continue
            if ip in ("0.0.0.0", "127.0.0.1"):
                continue
            proxies.append(f"{proto}://{ip}:{port}")
            total_found += 1

    note = ""
    if missing_port:
        note = f" ({missing_port} skipped - port obfuscated as image, OCR not implemented)"
    print(f"  [Geonix] {total_found} proxies{note}")
    return proxies


print("Advanced Proxy Scrapper By Legend")
print("Scrapping & Verifying proxys from 25+ sites & Sources... Enjoy\n")

print("Select proxy types to scrape:")
print("  1. HTTP")
print("  2. HTTPS")
print("  3. SOCKS4")
print("  4. SOCKS5")
print("  5. All\n")

selection = input("Enter choices (comma separated, e.g. 1,3): ").strip()

type_map = {"1": "http", "2": "https", "3": "socks4", "4": "socks5"}
if "5" in selection:
    selected_types = ["http", "https", "socks4", "socks5"]
else:
    selected_types = [type_map[s.strip()] for s in selection.split(",") if s.strip() in type_map]

if not selected_types:
    print("No valid types selected. Exiting.")
    exit()


def _prompt_int(prompt, default, minimum=1, maximum=None):
    raw = input(f"{prompt} [default {default}]: ").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        print(f"  Invalid number, using default {default}")
        return default
    if value < minimum:
        print(f"  Value below minimum {minimum}, using {minimum}")
        return minimum
    if maximum is not None and value > maximum:
        print(f"  Value above maximum {maximum}, using {maximum}")
        return maximum
    return value


def _prompt_float(prompt, default, minimum=0.1, maximum=None):
    raw = input(f"{prompt} [default {default}]: ").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        print(f"  Invalid number, using default {default}")
        return default
    if value < minimum:
        print(f"  Value below minimum {minimum}, using {minimum}")
        return minimum
    if maximum is not None and value > maximum:
        print(f"  Value above maximum {maximum}, using {maximum}")
        return maximum
    return value


print("\nVerification settings:")
VERIFY_THREADS = _prompt_int("  Threads for proxy checking", 300, minimum=1, maximum=5000)
VERIFY_TIMEOUT = _prompt_float("  Timeout per proxy (seconds)", 5, minimum=0.5, maximum=60)

print(f"\nScraping: {', '.join(selected_types)}")
print(f"Verification: {VERIFY_THREADS} threads, {VERIFY_TIMEOUT}s timeout\n")

sources = [
    ("ProxyScrape", scrape_proxyscrape),
    ("FreeProxyList", scrape_freeproxylist),
    ("GeoNode", scrape_geonode),
    ("HideMN", scrape_hidemn),
    ("FreeProxyWorld", scrape_freeproxyworld),
    ("OpenProxyList", scrape_openproxylist),
    ("GitHubLists", scrape_github_lists),
    ("SpysMe", scrape_spys_me),
    ("ProxySpace", scrape_proxyspace),
    ("ProxyScan", scrape_proxyscan),
    ("ProxyDaily", scrape_proxy_daily),
    ("AdvancedName", scrape_advanced_name),
    ("Geonix", scrape_geonix),
]


PER_SOURCE_TIMEOUT = 60


def _draw_scrape_bar(done, total, label, count, out):
    pct = int(done / total * 100) if total else 0
    hashes = pct // 2
    bar = "#" * hashes + "-" * (50 - hashes)
    msg = f"  [{bar}] {pct}% | {done}/{total} sources | {count} scraped | {label}"
    out.write("\r" + msg.ljust(120))
    out.flush()


all_proxies = []
total_sources = len(sources)
real_stdout = sys.stdout
silence_buf = StringIO()

print(f"Scraping {total_sources} sources ({PER_SOURCE_TIMEOUT}s timeout per source)...")
sys.stdout = silence_buf
try:
    _draw_scrape_bar(0, total_sources, "starting...", 0, real_stdout)
    for i, (name, scraper) in enumerate(sources):
        box = {"result": [], "done": False}

        def _worker(scr=scraper, b=box):
            try:
                b["result"] = scr(selected_types)
            except Exception:
                pass
            b["done"] = True

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        start = time.time()
        while not box["done"] and time.time() - start < PER_SOURCE_TIMEOUT:
            elapsed = int(time.time() - start)
            _draw_scrape_bar(i, total_sources, f"{name} ({elapsed}s)", len(all_proxies), real_stdout)
            time.sleep(0.3)
        if box["done"]:
            all_proxies.extend(box["result"])
        else:
            real_stdout.write("\r" + f"  [timeout] {name} (>60s) — skipped".ljust(120) + "\n")
        _draw_scrape_bar(i + 1, total_sources, name, len(all_proxies), real_stdout)
finally:
    sys.stdout = real_stdout
real_stdout.write("\n\n")

seen = set()
unique_proxies = []
for p in all_proxies:
    if p not in seen:
        seen.add(p)
        unique_proxies.append(p)

print(f"Total: {len(all_proxies)} scraped, {len(unique_proxies)} unique\n")

print(f"Verifying {len(unique_proxies)} proxies ({VERIFY_THREADS} threads, {VERIFY_TIMEOUT}s timeout)...\n")

lock = threading.Lock()
verified = []
checked = 0
dead = 0


def verify_proxy(proxy_str):
    global checked, dead
    try:
        host = proxy_str.split("://")[1]
        ip, port = host.rsplit(":", 1)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(VERIFY_TIMEOUT)
        sock.connect((ip, int(port)))
        sock.close()
        with lock:
            verified.append(proxy_str)
            checked += 1
        return True
    except Exception:
        with lock:
            checked += 1
            dead += 1
        return False


total_to_check = len(unique_proxies)
with ThreadPoolExecutor(max_workers=VERIFY_THREADS) as executor:
    futures = {executor.submit(verify_proxy, p): p for p in unique_proxies}
    for future in as_completed(futures):
        with lock:
            c, d, v = checked, dead, len(verified)
        pct = int(c / total_to_check * 100)
        done = pct // 2
        bar = "#" * done + "-" * (50 - done)
        sys.stdout.write(f"\r  [{bar}] {pct}% | {c}/{total_to_check} checked | {v} alive | {d} dead")
        sys.stdout.flush()

print(f"\n\nVerification complete: {len(verified)} alive / {dead} dead out of {total_to_check}\n")

date_str = datetime.now().strftime("%#m-%#d-%Y")
filename = f"{date_str}_Proxys.txt"

with open(filename, "w") as f:
    for proxy in verified:
        f.write(proxy.split("://", 1)[-1] + "\n")

print(f"Saved {len(verified)} verified proxies to {filename}")
