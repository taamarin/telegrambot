import base64
import json
import re
import base64
import json
import tempfile
from io import BytesIO
from io import StringIO
from telegram import InputFile
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote
from handlers.user_store import increment_interaction
from collections import defaultdict
from html import escape

increment_interaction()

def make_unique_tag(tag: str, tag_counts: defaultdict) -> str:
    tag_counts[tag] += 1
    return f"{tag}-{tag_counts[tag]}" if tag_counts[tag] > 1 else tag

def convert_url_to_singbox(url: str, tag_counts: defaultdict) -> str:
    try:
        if url.startswith("vmess://"):
            # Decode and parse VMess config
            decoded_data = base64.urlsafe_b64decode(url[8:] + '===').decode('utf-8')
            vmess_config = json.loads(decoded_data)

            name = vmess_config.get("ps")
            server = vmess_config.get("add")
            port = int(vmess_config.get("port", 443))
            uuid = vmess_config.get("id")
            security = vmess_config.get("scy", "auto")
            network = vmess_config.get("net", "tcp")
            type_ = vmess_config.get("type")
            path = vmess_config.get("path", "/")
            host = vmess_config.get("host", server)
            sni = vmess_config.get("sni", host)
            alpn = vmess_config.get("alpn", "").split(",") if "alpn" in vmess_config else []
            tls_enabled = vmess_config.get("tls", "none") == "tls"
            tag = make_unique_tag(name, tag_counts)

            # Build transport based on network type
            transport = {}
    
            if network == "ws":
                transport = {
                    "type": "ws",
                    "path": path,
                    "headers": {
                        "Host": host
                    }
                }
            elif network == "grpc":
                transport = {
                    "type": "grpc",
                    "service_name": path.lstrip("/"),
                    "idle_timeout": "15s",
                    "ping_timeout": "15s",
                    "permit_without_stream": False
                }
            elif network == "tcp":
                if type_ == "http":
                    transport = {
                        "type": "http",
                        "host": [host],
                        "path": path,
                        "headers": {},
                        "idle_timeout": "15s",
                        "ping_timeout": "15s"
                    }
            elif network == "h2":  # sometimes used as alias for http2
                transport = {
                    "type": "http",
                    "host": [host],
                    "path": path
                }
            elif network == "quic":
                transport = {
                    "type": "quic"
                }
            elif network == "httpupgrade":
                transport = {
                    "type": "httpupgrade",
                    "host": host,
                    "path": path,
                    "headers": {}
                }
            else:  # TCP or unknown
                transport = {}
    
            # Compose final config
            config = {
                "outbounds": [
                    {
                        "tag": tag,
                        "type": "vmess",
                        "server": server,
                        "server_port": port,
                        "uuid": uuid,
                        "alter_id": int(vmess_config.get("aid", 0)),
                        "security": security,
                        "tls": {
                            "enabled": tls_enabled,
                            "server_name": sni,
                            "insecure": True
                            # "alpn": alpn
                        },
                        "transport": transport,
                        "multiplex": {
                            "enabled": False
                        }
                    }
                ]
            }
    
            return json.dumps(config, indent=2)

        elif url.startswith("vless://"):
            # Hilangkan skema `vless://`
            url_body = url[8:]
            
            # Pisahkan bagian utama dari query dan fragment
            base, _, query_fragment = url_body.partition('?')
            userhost, _, _ = base.partition('#')
            uuid, _, serverport = userhost.partition('@')
            server, _, port_str = serverport.partition(':')
            # Ambil port, abaikan apa pun setelah tanda /
            port_str_clean = port_str.split('/')[0]
            port = int(port_str_clean or 443)
            # port = int(port_str or 443)

            # Parsing ulang menggunakan urlparse agar query dan fragment dapat diekstrak
            parsed = urlparse("vless://" + serverport + '?' + query_fragment)
            # Ambil parameter query
            query = parse_qs(parsed.query)

            # Ambil nilai-nilai dari query string
            path = query.get("path", ["/"])[0]
            host = query.get("host", [server])[0]
            sni = query.get("sni", [host])[0]
            serviceName = query.get("serviceName", ["/"])[0]
            insecure = query.get("allowInsecure", ["0"])[0] == "1"
            security = query.get("security", ["none"])[0]
            network = query.get("type", ["tcp"])[0]
            flow = query.get("flow", [""])[0]
            alpn = query.get("alpn", [""])[0].split(",") if "alpn" in query else []
            tag = unquote(parsed.fragment or server)
            type_ = query.get("headerType", [""])[0].lower()

            # Build transport
            transport = {}
    
            if network == "ws":
                transport = {
                    "type": "ws",
                    "path": path,
                    "headers": {
                        "Host": host
                    }
                }
            elif network == "grpc":
                transport = {
                    "type": "grpc",
                    "service_name": serviceName.lstrip("/"),
                    "idle_timeout": "15s",
                    "ping_timeout": "15s",
                    "permit_without_stream": False
                }
            elif network == "tcp":
                if type_ == "http":
                    transport = {
                        "type": "http",
                        "host": [host],
                        "path": path,
                        "headers": {},
                        "idle_timeout": "15s",
                        "ping_timeout": "15s"
                    }
            elif network == "quic":
                transport = {
                    "type": "quic"
                }
            elif network == "httpupgrade":
                transport = {
                    "type": "httpupgrade",
                    "host": host,
                    "path": path,
                    "headers": {}
                }
            else:  # tcp or default
                transport = {}
    
            config = {
                "outbounds": [
                    {
                        "tag": tag,
                        "type": "vless",
                        "server": server,
                        "server_port": port,
                        "uuid": uuid,
                        "flow": flow if flow else None,
                        "packet_encoding": "xudp",
                        "tls": {
                            "enabled": security == "tls" or bool(sni),
                            "insecure": security == "tls" or bool(sni),
                            "server_name": sni,
                            # "alpn": alpn
                        },
                        "transport": transport,
                        "multiplex": {
                            "enabled": False
                        }
                    }
                ]
            }
    
            # Remove nulls
            def clean(d):
                if isinstance(d, dict):
                    return {k: clean(v) for k, v in d.items() if v is not None}
                return d
    
            return json.dumps(clean(config), indent=2)

        elif url.startswith("trojan://"):
            parsed = urlparse(url)
            password = parsed.username
            server = parsed.hostname
            port = parsed.port or 443
            query = parse_qs(parsed.query)

            path = query.get("path", ["/"])[0]
            serviceName = query.get("serviceName", ["/"])[0]
            host = query.get("host", [server])[0]
            sni = query.get("sni", [host])[0]
            insecure = query.get("allowInsecure", ["0"])[0] == "1"
            security = query.get("security", ["none"])[0]
            network = query.get("type", ["tcp"])[0]
            alpn = query.get("alpn", [""])[0].split(",") if "alpn" in query else []
            tag = unquote(parsed.fragment or server)
            type_ = query.get("headerType", [""])[0].lower()

            # Build transport config
            transport = {}
            if network == "ws":
                transport = {
                    "type": "ws",
                    "path": path,
                    "headers": {
                        "Host": host
                    }
                }
            elif network == "grpc":
                transport = {
                    "type": "grpc",
                    "service_name": serviceName.lstrip("/"),
                    "idle_timeout": "15s",
                    "ping_timeout": "15s",
                    "permit_without_stream": False
                }
            elif network == "tcp":
                if type_ == "http":
                    transport = {
                        "type": "http",
                        "host": [host],
                        "path": path,
                        "headers": {},
                        "idle_timeout": "15s",
                        "ping_timeout": "15s"
                    }
            elif network == "httpupgrade":
                transport = {
                    "type": "httpupgrade",
                    "host": host,
                    "path": path,
                    "headers": {}
                }
            elif network == "quic":
                transport = {
                    "type": "quic"
                }
    
            config = {
                "outbounds": [
                    {
                        "tag": tag,
                        "type": "trojan",
                        "server": server,
                        "server_port": port,
                        "password": password,
                        "tls": {
                            "enabled": security == "tls" or bool(sni),
                            "insecure": security == "tls" or bool(sni),
                            "server_name": sni,
                            # "alpn": alpn
                        },
                        "transport": transport,
                        "multiplex": {
                            "enabled": False
                        }
                    }
                ]
            }

            # Remove None fields
            def clean(d):
                if isinstance(d, dict):
                    return {k: clean(v) for k, v in d.items() if v is not None}
                return d

            return json.dumps(clean(config), indent=2, ensure_ascii=False)

        elif url.startswith("hysteria2://"):
            parsed = urlparse(url)
            password = parsed.username
            server = parsed.hostname
            port = parsed.port or 443
            query = parse_qs(parsed.query)
            tag = unquote(parsed.fragment or server)

            obfs = query.get("obfs", [""])[0]
            obfs_password = query.get("obfs-password", [""])[0]
            sni = query.get("sni", [server])[0]
            insecure = (
                query.get("insecure", ["0"])[0] == "1"
                or query.get("allow_insecure", ["0"])[0] == "1"
            )

            config = {
                "outbounds": [
                    {
                        "type": "hysteria2",
                        "tag": tag,
                        "server": server,
                        "server_port": port,
                        "up_mbps": 100,
                        "down_mbps": 100,
                        "password": password,
                        "obfs": {
                            "type": obfs,
                            "password": obfs_password
                        },
                        # "network": "tcp",
                        "tls": {
                            "enabled": True,
                            "server_name": sni,
                            "insecure": insecure
                        }
                    }
                ]
            }

            # Remove None fields
            def clean(d):
                if isinstance(d, dict):
                    return {k: clean(v) for k, v in d.items() if v is not None}
                return d

            return json.dumps(clean(config), indent=2, ensure_ascii=False)

        elif url.startswith(("socks4://", "socks4a://", "socks5://")):
            parsed = urlparse(url)
            username = parsed.username
            password = parsed.password
            server = parsed.hostname
            port = parsed.port or 1080
            raw_tag = unquote(parsed.fragment or server)
            tag = make_unique_tag(raw_tag, tag_counts)

            version = "5"
            if url.startswith("socks4://"):
                version = "4"
            elif url.startswith("socks4a://"):
                version = "4a"

            config = {
                "outbounds": [
                    {
                        "type": "socks",
                        "tag": tag,
                        "server": server,
                        "server_port": port,
                        "version": version,
                        "network": "udp"
                    }
                ]
            }

            # Tambahkan username/password jika ada
            if username:
                config["outbounds"][0]["username"] = username
            if password:
                config["outbounds"][0]["password"] = password

            # Remove None fields
            def clean(d):
                if isinstance(d, dict):
                    return {k: clean(v) for k, v in d.items() if v is not None}
                return d

            return json.dumps(clean(config), indent=2, ensure_ascii=False)

        else:
            return "Unsupported protocol."

    except Exception as e:
        return f"Error processing URL for sing-box: {str(e)}"

def valid_urls(text):
    pattern = r"(vless://[^\s]+|vmess://[^\s]+|trojan://[^\s]+|hysteria2://[^\s]+|socks4://[^\s]+|socks5://[^\s]+)"
    return re.findall(pattern, text)

async def handle_sing(update, context):
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
            '<blockquote class="expandable">Format salah!! Gunakan:\n<code>/sing &lt;url&gt;</code> atau reply ke sebuah URL.</blockquote>',
            parse_mode="HTML"
        )
        return

    loading_message = await message.reply_text("Memuat informasi...")

    converted_list = []
    tag_counts = defaultdict(int)
    tag_names = []

    for url in urls:
        converted = convert_url_to_singbox(url, tag_counts)
        if not converted.startswith("Error"):
            parsed = json.loads(converted)
            converted_list.append(parsed)
            tag_names.append(parsed["outbounds"][0]["tag"])

    if not converted_list:
        await loading_message.edit_text("Tidak ada konfigurasi valid yang berhasil dikonversi.")
        return

    all_outbounds = sum([conf["outbounds"] for conf in converted_list], [])

    # Tambahkan selector outbound
    all_outbounds.append({
        "type": "selector",
        "tag": "sing",
        "outbounds": tag_names,
        "interrupt_exist_connections": True
    })

    final_config = {
        "outbounds": all_outbounds
    }

    json_text = json.dumps(final_config, indent=2, ensure_ascii=False)
    escaped_text = escape(json_text, quote=False)

    if len(json_text) > 2000:
        file_buffer = BytesIO(json_text.encode("utf-8"))
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        file_buffer.name = f"singbox_config-{timestamp}.json"
        await loading_message.delete()
        await message.reply_document(
            document=InputFile(file_buffer),
            caption=(
                '<blockquote class="expandable">'
                'Konversi selesai.\nBerikut hasil file konfigurasi sing-box (outbounds) Anda.'
                '</blockquote>'
            ),
            parse_mode="HTML"
        )
    else:
        await loading_message.delete()
        await message.reply_text(
            f"sing-box configuration:\n<pre>{json_text}</pre>",
            parse_mode="HTML"
        )