import base64
import json
import random
import re
from urllib.parse import urlparse, parse_qs
from io import BytesIO
from datetime import datetime
from html import escape
from telegram import InputFile

from handlers.user_store import increment_interaction
increment_interaction()

def wrap_with_xray_template(outbounds: list, proxy_tag: str) -> dict:
    return {
        "dns": {
            "queryStrategy": "UseIP",
            "servers": [
                "8.8.8.8"
            ],
            "tag": "dns"
        },
        "inbounds": [
            {
                "port": 9898,
                "protocol": "dokodemo-door",
                "tag": "tproxy-in",
                "settings": {
                    "followRedirect": True,
                    "network": "tcp,udp"
                },
                "sniffing": {
                    "destOverride": ["http", "tls"],
                    "enabled": True,
                    "routeOnly": False
                },
                "streamSettings": {
                    "sockopt": {
                        "tproxy": "tproxy"
                    }
                }
            }
        ],
        "log": {
            "access": "none",
            "loglevel": "none",
            "dnsLog": False
        },
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "domainMatcher": "mph",
            "rules": [
                {
                    "inboundTag": ["tproxy-in"],
                    "outboundTag": "dns-out",
                    "port": 53,
                    "type": "field"
                },
                {
                    "network": "tcp,udp",
                    "outboundTag": proxy_tag,
                    "type": "field"
                }
            ]
        },
        "outbounds": outbounds
    }

def generate_stream_settings(network, security, host, path, sni=None):
    tls_enabled = (security == "tls" or network == "tls")

    stream = {
        "network": network,
        "security": security,
        "tlsSettings": {
            "allowInsecure": tls_enabled,
            # "alpn": ["h3", "h2"],
            "fingerprint": "random",
            "serverName": sni or host,
            "show": False
        }
    }

    if network == "httpupgrade":
        stream["httpupgradeSettings"] = {
            "path": path,
            "host": host
        }
    elif network == "ws":
        stream["wsSettings"] = {
            "path": path,
            "host": host,
            "headers": {"Host": host}
        }
    elif network == "http":
        stream["httpSettings"] = {
            "path": path,
            "host": [host]
        }
    elif network == "grpc":
        stream["grpcSettings"] = {
            "serviceName": path.strip("/"),
            "multiMode": False
        }
    elif network == "tcp":
        stream["tcpSettings"] = {
            "header": {"type": "none"}
        }

    return stream

def convert_vmess_to_xray(vmess_url: str) -> str:
    try:
        decoded_data = base64.urlsafe_b64decode(vmess_url[8:] + '===').decode('utf-8')
        vmess_config = json.loads(decoded_data)

        address = vmess_config.get("add")
        port = vmess_config.get("port")
        id = vmess_config.get("id")
        alter_id = vmess_config.get("aid", 0)
        security = vmess_config.get("scy", "auto")
        network = vmess_config.get("net", "tcp")
        path = vmess_config.get("path", "/")
        host = vmess_config.get("host", "")
        tls = vmess_config.get("tls", "none")

        random_number = random.randint(1, 999)

        outbounds = [
            {
                "protocol": "vmess",
                "tag": f"proxy_{random_number}",
                "settings": {
                    "vnext": [
                        {
                            "address": address,
                            "port": int(port),
                            "users": [
                                {
                                    "id": id,
                                    "alterId": int(alter_id),
                                    "security": security
                                }
                            ]
                        }
                    ]
                },
                "streamSettings": generate_stream_settings(network, tls, host, path),
                "mux": {
                    "enabled": False,
                    "concurrency": -1,
                    "xudpConcurrency": 8,
                    "xudpProxyUDP443": ""
                }
            },
            {
                "protocol": "freedom",
                "settings": {
                    "domainStrategy": "UseIP"
                },
                "tag": "direct"
            },
            {
                "protocol": "blackhole",
                "settings": {
                    "response": {
                        "type": "http"
                    }
                },
                "tag": "block"
            },
            {
                "protocol": "dns",
                "tag": "dns-out"
            }
        ]
        
        config = wrap_with_xray_template(outbounds, f"proxy_{random_number}")
        return json.dumps(config, indent=2)
    except Exception as e:
        return f"Error processing VMess URL: {str(e)}"

def convert_vless_to_xray(vless_url: str) -> str:
    try:
        url_parts = urlparse(vless_url)
        params = parse_qs(url_parts.query)

        id = url_parts.username or (url_parts.netloc.split('@')[0] if '@' in url_parts.netloc else None)
        if not id:
            raise ValueError("UUID tidak ditemukan dalam VLESS URL")
    
        address = url_parts.hostname
        port = url_parts.port
        encryption = params.get("encryption", ["none"])[0]
        flow = params.get("flow", [""])[0]
        host = params.get("host", [address])[0]
        path = params.get("path", ["/"])[0]
        security = params.get("security", ["none"])[0]
        network = params.get("type", ["tcp"])[0]
        sni = params.get("sni", [host])[0]

        random_number = random.randint(1, 999)

        outbounds = [
            {
                "protocol": "vless",
                "tag": f"proxy_{random_number}",
                "settings": {
                    "vnext": [
                        {
                            "address": address,
                            "port": int(port),
                            "users": [
                                {
                                    "id": id,
                                    "encryption": encryption,
                                    "flow": flow,
                                    "level": 8
                                }
                            ]
                        }
                    ]
                },
                "streamSettings": generate_stream_settings(network, security, host, path, sni),
                "mux": {
                    "enabled": False,
                    "concurrency": -1,
                    "xudpConcurrency": 8,
                    "xudpProxyUDP443": ""
                }
            },
            {
                "protocol": "freedom",
                "settings": {
                    "domainStrategy": "UseIP"
                },
                "tag": "direct"
            },
            {
                "protocol": "blackhole",
                "settings": {
                    "response": {
                        "type": "http"
                    }
                },
                "tag": "block"
            },
            {
                "protocol": "dns",
                "tag": "dns-out"
            }
        ]
        
        config = wrap_with_xray_template(outbounds, f"proxy_{random_number}")
        return json.dumps(config, indent=2)
    except Exception as e:
        return f"Error processing VLESS URL: {str(e)}"

def convert_trojan_to_xray(trojan_url: str) -> str:
    try:
        url_parts = urlparse(trojan_url)
        password = url_parts.username
        address = url_parts.hostname
        port = url_parts.port

        params = parse_qs(url_parts.query)
        type_ = params.get("type", ["tcp"])[0]
        host = params.get("host", [address])[0]
        path = params.get("path", ["/"])[0]
        security = params.get("security", ["tls"])[0]
        sni = params.get("sni", [host])[0]

        random_number = random.randint(1, 999)

        outbounds = [
            {
                "protocol": "trojan",
                "tag": f"proxy_{random_number}",
                "settings": {
                    "servers": [
                        {
                            "address": address,
                            "port": int(port),
                            "password": password,
                            "level": 8,
                            "ota": False
                        }
                    ]
                },
                "streamSettings": generate_stream_settings(type_, security, host, path, sni),
                "mux": {
                    "enabled": False,
                    "concurrency": -1,
                    "xudpConcurrency": 8,
                    "xudpProxyUDP443": ""
                }
            },
            {
                "protocol": "freedom",
                "settings": {
                    "domainStrategy": "UseIP"
                },
                "tag": "direct"
            },
            {
                "protocol": "blackhole",
                "settings": {
                    "response": {
                        "type": "http"
                    }
                },
                "tag": "block"
            },
            {
                "protocol": "dns",
                "tag": "dns-out"
            }
        ]
        
        config = wrap_with_xray_template(outbounds, f"proxy_{random_number}")
        return json.dumps(config, indent=2)
    except Exception as e:
        return f"Error processing Trojan URL: {str(e)}"

def convert_shadowsocks_to_xray(ss_url: str) -> str:
    try:
        url = ss_url[5:]
        if '@' in url:
            creds, server_info = url.split('@')
        else:
            decoded = base64.urlsafe_b64decode(url + '===').decode()
            creds, server_info = decoded.split('@')

        method, password = creds.split(':')
        address, port = server_info.split(':')

        random_number = random.randint(1, 999)

        outbounds = [
            {
                "protocol": "shadowsocks",
                "tag": f"proxy_{random_number}",
                "settings": {
                    "servers": [
                        {
                            "address": address,
                            "port": int(port),
                            "method": method,
                            "password": password,
                            "level": 8
                        }
                    ]
                },
                "streamSettings": {
                    "network": "tcp"
                },
                "mux": {
                    "enabled": False,
                    "concurrency": -1,
                    "xudpConcurrency": 8,
                    "xudpProxyUDP443": ""
                }
            },
            {
                "protocol": "freedom",
                "settings": {
                    "domainStrategy": "UseIP"
                },
                "tag": "direct"
            },
            {
                "protocol": "blackhole",
                "settings": {
                    "response": {
                        "type": "http"
                    }
                },
                "tag": "block"
            },
            {
                "protocol": "dns",
                "tag": "dns-out"
            }
        ]
        
        config = wrap_with_xray_template(outbounds, f"proxy_{random_number}")
        return json.dumps(config, indent=2)
    except Exception as e:
        return f"Error processing Shadowsocks URL: {str(e)}"

def convert_socks_to_xray(socks_url: str) -> str:
    try:
        url_parts = urlparse(socks_url)
        username = url_parts.username
        password = url_parts.password
        address = url_parts.hostname
        port = url_parts.port

        random_number = random.randint(1, 999)

        outbounds = [
            {
                "mux": {
                    "concurrency": -1,
                    "enabled": False
                },
                "protocol": "socks",
                "settings": {
                    "servers": [
                        {
                            "address": address,
                            "level": 8,
                            "ota": False,
                            "port": int(port),
                            "users": [
                                {
                                    "level": 8,
                                    "pass": password,
                                    "user": username
                                }
                            ]  if username and password else []
                        }
                    ]
                },
                "streamSettings": {
                    "network": "tcp"
                },
                "tag": f"proxy_{random_number}",
            },

            # {
                # "protocol": "socks",
                # "tag": f"proxy_{random_number}",
                # "settings": {
                    # "servers": [
                        # {
                            # "address": address,
                            # "port": int(port),
                            # "users": [
                                # {
                                    # "user": username,
                                    # "pass": password
                                # }
                            # ] if username and password else []
                        # }
                    # ]
                # },
                # "streamSettings": {
                    # "network": "tcp"
                # }
            # },

            {
                "protocol": "freedom",
                "settings": {
                    "domainStrategy": "UseIP"
                },
                "tag": "direct"
            },
            {
                "protocol": "blackhole",
                "settings": {
                    "response": {
                        "type": "http"
                    }
                },
                "tag": "block"
            },
            {
                "protocol": "dns",
                "tag": "dns-out"
            }
        ]
        
        config = wrap_with_xray_template(outbounds, f"proxy_{random_number}")
        return json.dumps(config, indent=2)
    except Exception as e:
        return f"Error processing SOCKS URL: {str(e)}"

def valid_xray_urls(text):
    pattern = r"(vmess://[^\s]+|vless://[^\s]+|trojan://[^\s]+|socks://[^\s]+)"
    return re.findall(pattern, text)

import ipaddress
def resolve_to_ip(domain):
    try:
        # cek apakah domain sudah IP
        ipaddress.ip_address(domain)
        return domain  # sudah IP langsung return
    except ValueError:
        # bukan IP, lanjut resolve
        try:
            answers = dns.resolver.resolve(domain, 'A')
            ips = [rdata.to_text() for rdata in answers]
            return ips[0] if ips else "Unknown"
        except Exception as e:
            print(f"Failed to resolve {domain}: {e}")
            return "Unknown"

import dns.resolver
import ipaddress

def resolve_to_ip(domain):
    domain = domain.strip()
    if not domain:
        return "Unknown"
    try:
        ipaddress.ip_address(domain)
        return domain
    except ValueError:
        try:
            answers = dns.resolver.resolve(domain, 'A')
            ips = [rdata.to_text() for rdata in answers]
            if ips:
                return ips[0]
            else:
                return "Unknown"
        except Exception as e:
            return "Unknown"

async def handle_xray(update, context):
    message = update.message
    args = context.args

    if args:
        urls = valid_xray_urls(" ".join(args))
    elif message.reply_to_message and message.reply_to_message.text:
        urls = valid_xray_urls(message.reply_to_message.text)
    else:
        urls = []

    if not urls:
        await message.reply_text(
            '<blockquote class="expandable">Format salah!! Gunakan:\n<code>/xray &lt;url&gt;</code> atau reply ke sebuah URL.</blockquote>',
            parse_mode="HTML"
        )
        return

    loading_message = await message.reply_text("loading...")

    converted_list = []
    for url in urls:
        if url.startswith("vmess://"):
            converted = convert_vmess_to_xray(url)
        elif url.startswith("vless://"):
            converted = convert_vless_to_xray(url)
        elif url.startswith("trojan://"):
            converted = convert_trojan_to_xray(url)
        elif url.startswith("socks://"):
            converted = convert_socks_to_xray(url)
        else:
            continue

        if not converted.startswith("Error"):
            converted_list.append(converted)

    if converted_list:
        final_config = json.loads(converted_list[0]) if len(converted_list) == 1 else None

        if final_config:
            json_text = json.dumps(final_config, indent=2, ensure_ascii=False)
            escaped_text = escape(json_text, quote=False)

            if len(json_text) > 2000:
                file_buffer = BytesIO(json_text.encode("utf-8"))
                timestamp = datetime.now().strftime("%Y%m%d%H%M")
                file_buffer.name = f"xray_config-{timestamp}.json"
                
                try:
                    address_raw = final_config["outbounds"][0]["settings"]["vnext"][0]["address"]
                    address_ip = resolve_to_ip(address_raw)
                except (KeyError, IndexError):
                    address_ip = "Unknown"
                
                await loading_message.delete()
                await message.reply_document(
                    document=InputFile(file_buffer),
                    caption=(
                        f'<blockquote class="expandable">'
                        f'Konversi konfigurasi XRAY (BFR) selesai.\n\n'
                        f'❀ IP Server: <code>{address_ip}</code>\n'
                        f'     ↳  <code>add IP server ke "address":</code>\n\n'
                        f'❀ Guide:\n'
                        f'❀ Ubah nama file menjadi:\n'
                        f'     ↳  <code>config.json</code>\n'
                        f'❀ pindahkan ke:\n'
                        f'     ↳  <code>/data/adb/box/xray</code>.'
                        '</blockquote>'
                    ),
                    parse_mode="HTML"
                )
            else:
                await loading_message.delete()
                await message.reply_text(
                    f"XRAY configuration:\n<pre>{escaped_text}</pre>",
                    parse_mode="HTML"
                )
        else:
            await loading_message.delete()
            await message.reply_text(
                "Hanya bisa menampilkan satu konfigurasi XRAY dalam satu waktu.\nSilakan kirim satu URL saja.",
                parse_mode="HTML"
            )
    else:
        await loading_message.edit_text("Tidak ada URL yang berhasil dikonversi.")



