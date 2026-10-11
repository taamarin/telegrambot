import yaml
import re
import base64
import json
from html import escape
from telegram import Update
from datetime import datetime
from telegram.ext import Application, CommandHandler, ContextTypes
from urllib.parse import urlparse, parse_qs, unquote

from handlers.user_store import increment_interaction
increment_interaction()

def convert_to_clash(url):
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
            # net_type = params_dict.get("network", "").lower()
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
                    "path": params_dict.get("path", "").replace("%2F", "/").replace("%3D", "=").replace("%3A", ":"),
                    "headers": {"Host": params_dict.get("host", server)}
                }
            elif net_type == "tcp":
                flow = params_dict.get("flow", "")
                if flow:
                    clash_config["flow"] = flow
                if header_type == "http":
                    path = params_dict.get("path", "").replace("%2F", "/").replace("%3D", "=").replace("%3A", ":")
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
                    "path": params_dict.get("path", "").replace("%2F", "/").replace("%3D", "=").replace("%3A", ":"),
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

        elif protocol == "vmess":
            details = details.replace("-", "+").replace("_", "/")
            if len(details) % 4 != 0:
                details += "=" * (4 - len(details) % 4)

            vmess_json = json.loads(base64.b64decode(details).decode("utf-8"))
            net_type = vmess_json.get("net", "tcp")
            header_type = vmess_json.get("type")

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
                }
            elif net_type == "kcp":
                clash_config["kcp-opts"] = {
                    "header": {
                        "type": vmess_json.get("type", "none")
                    }
                }
            elif net_type == "quic":
                clash_config["quic-opts"] = {
                    "security": vmess_json["host"] if vmess_json.get("host") else vmess_json["add"],
                    "key": vmess_json.get("path", ""),
                    "header": {"type": vmess_json.get("type", "none")}
                }

        elif protocol == "trojan":
            # tag = details.split("#", 1)[1] if "#" in details else server
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
                "tls": True,
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
                    path = params_dict.get("path", "").replace("%2F", "/").replace("%3D", "=").replace("%3A", ":")
                    clash_config["http-opts"] = {
                        "method": "GET",
                        "path": [path if path else "/"],
                        "headers": {"Host": [params_dict.get("host", server)]}
                    }
            if net_type == "ws":
                clash_config["ws-opts"] = {
                    "path": params_dict.get("path", "").replace("%2F", "/").replace("%3D", "=").replace("%3A", ":"),
                    "headers": {"Host": params_dict.get("host", server)}
                }
            elif net_type == "http":
                clash_config["http-opts"] = {
                    "method": "GET",
                    "path": ["/"],
                    "headers": {"Host": [params_dict.get("host", server)]}
                }
            elif net_type == "grpc":
                clash_config["grpc-opts"] = {
                    "grpc-service-name": params_dict.get("serviceName", "")
                }
            elif net_type == "h2":
                clash_config["h2-opts"] = {
                    "path": params_dict.get("path", "").replace("%2F", "/").replace("%3D", "=").replace("%3A", ":"),
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
                # "tls": params.get("tls", "false") == "true",
                # "fingerprint": params.get("fp"),
                # "skip-cert-verify": True,
                "udp": True
                # "ip-version": params.get("ip", "ipv4")
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

        elif protocol in ["hy2", "hysteria2"]:
            # Format: hysteria2://password@host:port?param1=value1&param2=value2[#name]
            info_part = details.split("#", 1)
            base = info_part[0]
            name = unquote(info_part[1]) if len(info_part) > 1 else "Hysteria2"

            if "?" in base:
                info, query = base.split("?", 1)
                params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            else:
                info = base
                params = {}

            if "@" not in info or ":" not in info:
                raise ValueError("Format tidak valid untuk hysteria2")

            auth, addr = info.split("@", 1)
            server, port = addr.split(":", 1)
            skip_cert = params.get("insecure", "0") == "1" or params.get("allow_insecure", "0") == "1"
        
            clash_config = {
                "name": name,
                "type": "hysteria2",
                "server": server,
                "port": int(port),
                "up": 100,
                "down": 100,
                "password": auth,
                "sni": params.get("sni", server),
                "skip-cert-verify": skip_cert,
                "obfs": params.get("obfs", ""),
                "obfs-password": params.get("obfs-password", ""),
                # "alpn": params.get("alpn", "").split(",") if "alpn" in params else [],
                "udp": True,
                # "dialer-proxy": "",  # Optional, bisa dikosongkan
            }

        else:
            return f"Protocol {protocol} is not supported."

        # Filter None values from the config dictionary
        clash_config = {k: v for k, v in clash_config.items() if v is not None}

        # Convert dictionary to YAML format
        return yaml.dump([clash_config], sort_keys=False, default_flow_style=False, allow_unicode=True)

    except Exception as e:
        return f"Error while converting URL {url}: {str(e)}"

def extract_valid_urls(text):
    pattern = r"(vless://[^\s]+|vmess://[^\s]+|trojan://[^\s]+|socks5://[^\s]+|ss://[^\s]+|hysteria://[^\s]+|hy2://[^\s]+|hysteria2://[^\s]+|http://[^\s]+)"
    return re.findall(pattern, text)

from telegram import Update, InputFile
from io import BytesIO
async def convert_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    args = context.args

    if args:
        urls = extract_valid_urls(" ".join(args))
    elif message.reply_to_message and message.reply_to_message.text:
        urls = extract_valid_urls(message.reply_to_message.text)
    else:
        urls = []

    if not urls:
        await message.reply_text(
            '<blockquote class="expandable">Format salah!! Gunakan:\n<code>/clash &lt;url&gt;</code> atau reply ke sebuah URL.</blockquote>',
            parse_mode="HTML"
        )
        return

    if urls:
        loading_message = await message.reply_text("loading information...")

        results = []
        for url in urls:
            converted = convert_to_clash(url)
            results.append(converted)

        result_text = "\n\n".join(results)

        if len(result_text) > 2000:
            file_buffer = BytesIO(result_text.encode("utf-8"))
            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            file_buffer.name = f"clash_config-{timestamp}.yaml"
            
            await loading_message.delete()
            await message.reply_document(
                document=InputFile(file_buffer),
                caption=(
                    '<blockquote class="expandable">'
                    'Konversi selesai.\nBerikut hasil file konfigurasi clash(proxies).'
                    '</blockquote>'
                ),
                parse_mode="HTML"
            )
        else:
            await loading_message.edit_text(
                f"<pre>{escape(result_text)}</pre>",
                parse_mode="HTML"
            )
