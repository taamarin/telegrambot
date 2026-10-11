import yaml
import re
import base64
import json
from html import escape
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from io import StringIO
from datetime import datetime
from urllib.parse import urlparse, unquote
from handlers.user_store import increment_interaction

increment_interaction()

def convert_clash(url):
    try:
        protocol, details = url.split("://", 1)

        if protocol == "vless":
            parsed = urlparse(url)
            uuid, serverport = parsed.username, f"{parsed.hostname}:{parsed.port}"
            tag = unquote(parsed.fragment or parsed.hostname)
            details = details.split("#", 1)[0]
            params = re.split(r"[?&]", details)
            server, port = params[0].split("@")[1].split(":")
            port = int(port.rstrip("/"))
            uuid = params[0].split("@")[0]
            params_dict = dict(p.split("=") for p in params[1:])
            net_type = params_dict.get("type", "tcp")
            header_type = params_dict.get("headerType", "").lower()

            clash_config = {
                "name": tag,
                "type": "vless",
                "server": server,
                "port": port,
                "uuid": uuid,
                "cipher": "auto",
                "tls": params_dict.get("security") == "tls",
                "skip-cert-verify": True,
                "servername": params_dict.get("sni", server),
                "network": net_type,
                "udp": True,
                "xudp": True,
            }

            if net_type == "ws":
                clash_config["ws-opts"] = {
                    "path": params_dict.get("path", "").replace("%2F", "/").replace("%3D", "="),
                    "headers": {
                        "Host": params_dict.get("host", server)
                    }
                }
            elif net_type == "tcp":
                flow = params_dict.get("flow", "")
                if flow:
                    clash_config["flow"] = flow
                if header_type == "http":
                    path = params_dict.get("path", "").replace("%2F", "/").replace("%3D", "=")
                    clash_config["http-opts"] = {
                        "method": "GET",
                        "path": [path if path else "/"],
                        "headers": {"Host": [params_dict.get("host", server)]}
                    }
            elif net_type == "grpc":
                clash_config["grpc-opts"] = {
                    "grpc-service-name": params_dict.get("serviceName", "")
                }
            elif net_type == "h2":
                clash_config["h2-opts"] = {
                    "path": params_dict.get("path", "").replace("%2F", "/").replace("%3D", "="),
                    "host": [params_dict.get("host", "")]
                }
            elif net_type == "kcp":
                clash_config["kcp-opts"] = {
                    "header": {
                        "type": params_dict.get("type", "none")
                    }
                }
            elif net_type == "quic":
                clash_config["quic-opts"] = {
                    "security": params_dict.get("host", ""),
                    "key": params_dict.get("path", ""),
                    "header": {
                        "type": params_dict.get("type", "none")
                    }
                }
            elif net_type == "httpupgrade":
                clash_config["network"] = "ws"
                clash_config["ws-opts"] = {
                    "path": params_dict.get("path", "/").replace("%2F", "/").replace("%3D", "="),
                    "headers": {
                        "Host": params_dict.get("host", server)
                    },
                    "v2ray-http-upgrade": True,
                    "v2ray-http-upgrade-fast-open": True
                }

        elif protocol == "vmess":
            details = details.replace("-", "+").replace("_", "/")
            if len(details) % 4 != 0:
                details += "=" * (4 - len(details) % 4)

            vmess_json = json.loads(base64.b64decode(details).decode("utf-8"))
            net_type = vmess_json.get("net", "tcp")

            clash_config = {
                "name": vmess_json.get("ps", "Unnamed"),
                "type": "vmess",
                "server": vmess_json["add"],
                "port": int(vmess_json["port"]),
                "uuid": vmess_json["id"],
                "alterId": int(vmess_json.get("aid", 0)),
                "cipher": vmess_json.get("cipher", "auto"),
                "tls": vmess_json.get("tls", "") == "tls",
                "skip-cert-verify": True,
                "servername": vmess_json["host"] if vmess_json.get("host") else vmess_json["add"],
                "network": net_type,
                "udp": True,
            }

            if net_type == "tcp":
                if header_type == "http":
                    path = vmess_json.get("path", "").replace("%2F", "/").replace("%3D", "=")
                    clash_config["http-opts"] = {
                        "method": "GET",
                        "path": [path if path else "/"],
                        "headers": {
                            "Host": [vmess_json["host"] if vmess_json.get("host") else vmess_json["add"]]
                        }
                    }
            elif net_type == "ws":
                clash_config["ws-opts"] = {
                    "path": vmess_json.get("path", "").replace("%2F", "/").replace("%3D", "="),
                    "headers": {
                        "Host": vmess_json["host"] if vmess_json.get("host") else vmess_json["add"]
                    }
                }
            elif net_type == "httpupgrade":
                clash_config["network"] = "ws"
                clash_config["ws-opts"] = {
                    "path": vmess_json.get("path", "").replace("%2F", "/").replace("%3D", "="),
                    "headers": {
                        "Host": vmess_json["host"] if vmess_json.get("host") else vmess_json["add"]
                    },
                    # "max-early-data": 2048,
                    # "early-data-header-name": "Sec-WebSocket-Protocol",
                    "v2ray-http-upgrade": True,
                    "v2ray-http-upgrade-fast-open": True
                }
            elif net_type == "grpc":
                clash_config["grpc-opts"] = {
                    "grpc-service-name": vmess_json.get("serviceName") or vmess_json.get("path", "").lstrip("/")
                }
            elif net_type == "h2":
                clash_config["h2-opts"] = {
                    "path": vmess_json.get("path", "").replace("%2F", "/").replace("%3D", "="),
                    "host": [vmess_json["host"] if vmess_json.get("host") else vmess_json["add"]]
                    # "host": [vmess_json.get("host", "")]
                }
            elif net_type == "kcp":
                clash_config["kcp-opts"] = {
                    "header": {
                        "type": vmess_json.get("type", "none")
                    }
                }
            elif net_type == "quic":
                clash_config["quic-opts"] = {
                    "security": vmess_json.get("host", ""),
                    "key": vmess_json.get("path", ""),
                    "header": {"type": vmess_json.get("type", "none")}
                }

        elif protocol == "trojan":
            parsed = urlparse(url)
            uuid, serverport = parsed.username, f"{parsed.hostname}:{parsed.port}"
            tag = unquote(parsed.fragment or parsed.hostname)
            details = details.split("#", 1)[0]
            params = re.split(r"[?&]", details)
            server, port = params[0].split("@")[1].split(":")
            port = int(port.rstrip("/"))
            password = params[0].split("@")[0]
            params_dict = dict(p.split("=") for p in params[1:])
            net_type = params_dict.get("type", "ws")
            header_type = params_dict.get("headerType", "").lower()

            clash_config = {
                "name": tag,
                "type": "trojan",
                "server": server,
                "port": port,
                "password": password,
                "skip-cert-verify": True,
                "sni": params_dict.get("sni", ""),
                "network": net_type,
                "udp": True,
            }

            flow = params_dict.get("flow", "")
            if flow:
                clash_config["flow"] = flow

            if net_type == "tcp":
                if header_type == "http":
                    path = params_dict.get("path", "").replace("%2F", "/").replace("%3D", "=")
                    clash_config["http-opts"] = {
                        "method": "GET",
                        "path": [path if path else "/"],
                        "headers": {"Host": [params_dict.get("host", server)]}
                    }
            elif net_type == "ws":
                clash_config["ws-opts"] = {
                    "path": params_dict.get("path", "").replace("%2F", "/").replace("%3D", "="),
                    "headers": {"Host": params_dict.get("host", server)}
                }
            elif net_type == "grpc":
                clash_config["grpc-opts"] = {
                    "grpc-service-name": params_dict.get("serviceName", server)
                }
            elif net_type == "h2":
                clash_config["h2-opts"] = {
                    "path": params_dict.get("path", "").replace("%2F", "/").replace("%3D", "="),
                    "host": [params_dict.get("host", server)]
                }
            elif net_type == "kcp":
                clash_config["kcp-opts"] = {
                    "header": {
                        "type": params_dict.get("type", "none")
                    }
                }
            elif net_type == "quic":
                clash_config["quic-opts"] = {
                    "security": params_dict.get("host", server),
                    "key": params_dict.get("path", ""),
                    "header": {"type": params_dict.get("type", "none")}
                }
            elif net_type == "httpupgrade":
                clash_config["network"] = "ws"
                clash_config["ws-opts"] = {
                    "path": params_dict.get("path", "/").replace("%2F", "/").replace("%3D", "="),
                    "headers": {"Host": params_dict.get("host", server)},
                    "v2ray-http-upgrade": True,
                    "v2ray-http-upgrade-fast-open": True
                }

        elif protocol == "socks5":
            # socks5://username:password@host:port?tls=true&fp=xxx&ip=ipv6
            creds, addr = details.split("@")
            server, port = addr.split(":")
            username, password = creds.split(":")
            port = int(port.split("?")[0])

            query = details.split("?", 1)[-1] if "?" in details else ""
            params = dict(p.split("=") for p in query.split("&") if "=" in p)

            clash_config = {
                "name": server,
                "type": "socks5",
                "server": server,
                "port": port,
                "username": username,
                "password": password,
                "tls": params.get("tls", "false") == "true",
                "fingerprint": params.get("fp"),
                "skip-cert-verify": True,
                "udp": True,
                "ip-version": params.get("ip", "ipv4")
            }

        elif protocol == "ss":
            # ss://base64(method:password@server:port)#name
            ss_pattern = re.match(r"(ss://)([^#]+)#?(.*)", url)
            encoded = ss_pattern.group(2)
            name = ss_pattern.group(3) or "Shadowsocks"

            # Base64 decode
            padding = '=' * (4 - len(encoded) % 4) if len(encoded) % 4 else ''
            decoded = base64.urlsafe_b64decode(encoded + padding).decode()
            method_pass, server_port = decoded.rsplit("@", 1)
            method, password = method_pass.split(":", 1)
            server, port = server_port.split(":")

            clash_config = {
                "name": name,
                "type": "ss",
                "server": server,
                "port": int(port),
                "cipher": method,
                "password": password,
                "udp": True
            }

        elif protocol == "hysteria":
            details = details.rstrip("/")
            info, query = details.split("?", 1)
            server, port = info.split(":")
            params = dict(p.split("=") for p in query.split("&"))

            clash_config = {
                "name": params.get("sni", "Hysteria"),
                "type": "hysteria",
                "server": server,
                "port": int(port),
                "auth": params.get("auth", ""),
                "alpn": params.get("alpn", "").split(",") if "alpn" in params else None,
                "protocol": params.get("protocol", "udp"),
                "obfs": params.get("obfs", ""),
                "sni": params.get("sni", ""),
                "insecure": params.get("insecure", "0") == "1",
                "udp": True
            }

        elif protocol == "http":
            # http://username:password@host:port?sni=domain.com&tls=true&fp=xxx&ip=dual
            creds, addr = details.split("@")
            server, port = addr.split(":")
            username, password = creds.split(":")
            port = int(port.split("?")[0])

            query = details.split("?", 1)[-1] if "?" in details else ""
            params = dict(p.split("=") for p in query.split("&") if "=" in p)

            clash_config = {
                "name": server,
                "type": "http",
                "server": server,
                "port": port,
                "username": username,
                "password": password,
                "tls": params.get("tls", "false") == "true",
                "skip-cert-verify": True,
                "sni": params.get("sni"),
                "fingerprint": params.get("fp"),
                "ip-version": params.get("ip", "ipv4")
            }

        elif protocol == "hy2":
            # Example: hy2://password@host:port?sni=example.com
            info, query = details.split("?", 1)
            auth, addr = info.split("@")
            server, port = addr.split(":")
            params = dict(p.split("=") for p in query.split("&"))

            clash_config = {
                "name": params.get("sni", "Hysteria2"),
                "type": "hysteria2",
                "server": server,
                "port": int(port),
                "password": auth,
                "sni": params.get("sni", ""),
                "insecure": params.get("insecure", "0") == "1",
                "alpn": params.get("alpn", "").split(",") if "alpn" in params else None,
                "udp": True
            }

        else:
            return f"Protocol {protocol} is not supported."

        # Filter None values from the config dictionary
        clash_config = {k: v for k, v in clash_config.items() if v is not None}

        # Convert dictionary to YAML format
        return yaml.dump([clash_config], sort_keys=False, default_flow_style=False, allow_unicode=True)

    except Exception as e:
        return f"Error: while converting URL {url}: {str(e)}"

TEMPLATE_YAML = """
mode: rule
allow-lan: true
bind-address: '*'
log-level: silent
unified-delay: true
ipv6: false
global-client-fingerprint: chrome
find-process-mode: strict
keep-alive-interval: 15
tcp-concurrent: false

tun:
  enable: true
  mtu: 9000
  device: clash
  stack: mixed
  dns-hijack:
    - any:53
    - tcp://any:53
  auto-route: true
  strict-route: false
  auto-redirect: true
  auto-detect-interface: true

profile:
  store-selected: true
  store-fake-ip: false

sniffer:
  enable: true
  force-dns-mapping: false
  parse-pure-ip: false
  override-destination: false
  sniff:
    QUIC:
      ports: [443]
    TLS:
      ports: [443, 8443]
    HTTP:
      ports: [80, 8080-8880]
      override-destination: true
  sniffing: [tls, http]
  port-whitelist: [80, 443]

dns:
  cache-algorithm: arc
  enable: true
  prefer-h3: false
  ipv6: false
  ipv6-timeout: 300
  default-nameserver:
    - 8.8.8.8
    - 8.8.4.4
  listen: 0.0.0.0:1053
  use-hosts: true
  enhanced-mode: redir-host
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter:
    - '*.lan'
    - '*.ntp.*'
  nameserver:
    - 8.8.8.8
    - 1.1.1.1
  proxy-server-nameserver:
    - ISI DNS PROVIDER
  respect-rules: true

proxies: []

proxy-groups:
- name: CMFA
  type: select
  proxies: []

rules:
  - MATCH,CMFA
"""

def make_unique_names(proxies):
    seen = {}
    unique_proxies = []

    for proxy in proxies:
        base_name = proxy.get("name", "Unnamed")
        name = base_name
        count = seen.get(base_name, 0)

        while name in seen:
            count += 1
            name = f"{base_name}[{count}]"

        seen[base_name] = count
        seen[name] = 0
        proxy["name"] = name
        unique_proxies.append(proxy)

    return unique_proxies

def generate_final_config(converted_yaml_list):
    config = yaml.safe_load(TEMPLATE_YAML)

    proxies = []
    for yaml_str in converted_yaml_list:
        try:
            nodes = yaml.safe_load(yaml_str)
            if isinstance(nodes, list):
                proxies.extend(nodes)
        except yaml.YAMLError:
            continue

    # Pastikan nama unik
    proxies = make_unique_names(proxies)

    # Masukkan ke bagian 'proxies' template
    config['proxies'] = proxies

    # Tambahkan nama-nama ke grup
    proxy_names = [p['name'] for p in proxies]
    for group in config.get("proxy-groups", []):
        if group.get("name") == "CMFA":
            group['proxies'].extend(proxy_names)

    final_yaml = yaml.dump(config, sort_keys=False, allow_unicode=True)
    return final_yaml

# Fungsi untuk mencari semua URL dengan protokol tertentu dalam teks
def valid_urls(text):
    pattern = r"(vless://[^\s]+|vmess://[^\s]+|trojan://[^\s]+|socks5://[^\s]+|ss://[^\s]+|hysteria://[^\s]+|hy2://[^\s]+|http://[^\s]+)"
    return re.findall(pattern, text)

async def template_cmfa_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    args = context.args

    if args:
        urls = valid_urls(" ".join(args))
    elif message.reply_to_message and message.reply_to_message.text:
        urls = valid_urls(message.reply_to_message.text)
    else:
        urls = []

    if not urls:
        await message.reply_text(
            '<blockquote class="expandable">Format salah!! Gunakan:\n<code>/cmfa &lt;url&gt;</code> atau reply ke sebuah URL.</blockquote>',
            parse_mode="HTML"
        )
        return

    if urls:
        loading_message = await message.reply_text("loading information...")

        converted_list = []
        for url in urls:
            converted = convert_clash(url)
            if not converted.startswith("Error"):
                converted_list.append(converted)

        if converted_list:
            final_yaml = generate_final_config(converted_list)

            await loading_message.delete()

            file_obj = StringIO(final_yaml)
            file_obj.seek(0)

            # Tambahkan timestamp ke nama file
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"cmfa_{timestamp}.yaml"

            await message.reply_document(
                document=file_obj,
                filename=filename,
                caption=(
                    '<blockquote class="expandable">'
                    'Konversi konfigurasi clash(CMFA) selesai.'
                    '</blockquote>'
                ),
                parse_mode="HTML"
            )
        else:
            await loading_message.edit_text("Tidak ada URL yang berhasil dikonversi.")