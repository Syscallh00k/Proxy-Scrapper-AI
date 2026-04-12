import requests
import json
import re
import socket
import sys
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


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
            response = requests.get(url, params=params, headers=headers, timeout=15)
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
        response = requests.get(url, headers=headers, timeout=15)
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
            response = requests.get(url, params=params, headers=headers, timeout=15)
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
            response = requests.get(url, params=params, headers=headers, timeout=15)
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
            response = requests.get(url, params=params, headers=headers, timeout=15)
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
            response = requests.get(f"{base_url}/{proto}.txt", headers=headers, timeout=15)
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

print(f"\nScraping: {', '.join(selected_types)}\n")

sources = [
    ("ProxyScrape", scrape_proxyscrape),
    ("FreeProxyList", scrape_freeproxylist),
    ("GeoNode", scrape_geonode),
    ("HideMN", scrape_hidemn),
    ("FreeProxyWorld", scrape_freeproxyworld),
    ("OpenProxyList", scrape_openproxylist),
]

all_proxies = []
for name, scraper in sources:
    print(f"[{name}]")
    result = scraper(selected_types)
    all_proxies.extend(result)
    print()

seen = set()
unique_proxies = []
for p in all_proxies:
    if p not in seen:
        seen.add(p)
        unique_proxies.append(p)

print(f"Total: {len(all_proxies)} scraped, {len(unique_proxies)} unique\n")

print(f"Verifying {len(unique_proxies)} proxies...\n")

VERIFY_TIMEOUT = 5
VERIFY_THREADS = 300

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
        f.write(proxy + "\n")

print(f"Saved {len(verified)} verified proxies to {filename}")
