import os
import yaml
import base64
import json
import re
from urllib.parse import quote_plus
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from handlers.user_store import increment_interaction
from datetime import datetime
from io import BytesIO

increment_interaction()

def encode_vmess(node):
    net = node.get("network", "tcp")
    tls = node.get("tls", False)
    host = ""
    path = ""
    header_type = node.get("type", "none")
    service_name = ""

    # Deteksi httpupgrade (khusus websocket)
    ws_opts = node.get("ws-opts", {})
    if net == "ws" and ws_opts.get("v2ray-http-upgrade") and ws_opts.get("v2ray-http-upgrade-fast-open"):
        net = "httpupgrade"

    # Ekstraksi opsi berdasarkan network
    if net in ["ws", "httpupgrade"]:
        path = ws_opts.get("path", "")
        host = ws_opts.get("headers", {}).get("Host", "")
    elif net == "tcp":
        http_opts = node.get("http-opts", {})
        if http_opts:
            header_type = "http"
            path_list = http_opts.get("path", [])
            path = path_list[0] if path_list else ""
            host_list = http_opts.get("headers", {}).get("Host", [])
            host = host_list[0] if isinstance(host_list, list) and host_list else ""
    elif net == "grpc":
        grpc_opts = node.get("grpc-opts", {})
        service_name = grpc_opts.get("grpc-service-name", "")
    elif net == "h2":
        h2_opts = node.get("h2-opts", {})
        path = h2_opts.get("path", "")
        host_list = h2_opts.get("host", [])
        host = host_list[0] if isinstance(host_list, list) and host_list else ""
    elif net == "kcp":
        kcp_opts = node.get("kcp-opts", {})
        header_type = kcp_opts.get("header", {}).get("type", "none")
    elif net == "quic":
        quic_opts = node.get("quic-opts", {})
        path = quic_opts.get("key", "")
        host = quic_opts.get("security", "")
        header_type = quic_opts.get("header", {}).get("type", "none")

    # Susun format JSON V2Ray vmess
    config = {
        "v": "2",
        "ps": node.get("name", ""),
        "add": node.get("server", ""),
        "port": str(node.get("port", 0)),
        "id": node.get("uuid", ""),
        "aid": str(node.get("alterId", 0)),
        "net": net,
        "type": header_type,
        "host": host,
        "path": path,
        "tls": "tls" if tls else "",
    }

    if service_name:
        config["serviceName"] = service_name

    json_str = json.dumps(config, separators=(",", ":"))
    encoded = base64.urlsafe_b64encode(json_str.encode()).decode().rstrip("=")
    return "vmess://" + encoded

def encode_vless(node):
    net = node.get("network", "tcp")
    ws_opts = node.get("ws-opts", {})
    is_httpupgrade = (
        net == "ws"
        and ws_opts.get("v2ray-http-upgrade") is True
        and ws_opts.get("v2ray-http-upgrade-fast-open") is True
    )

    query = {
        "type": "httpupgrade" if is_httpupgrade else net,
        "security": "tls" if node.get("tls") else "",
        "sni": node.get("sni") or node.get("servername", "")
    }

    if node.get("flow"):
        query["flow"] = node["flow"]

    if net == "ws":
        query["path"] = ws_opts.get("path", "")
        query["host"] = ws_opts.get("headers", {}).get("Host", "")
    elif net == "grpc":
        grpc = node.get("grpc-opts", {})
        query["serviceName"] = grpc.get("grpc-service-name", "")
    elif net == "h2":
        h2 = node.get("h2-opts", {})
        query["path"] = h2.get("path", "")
        query["host"] = ",".join(h2.get("host", []))
    elif net == "quic":
        quic = node.get("quic-opts", {})
        query["security"] = quic.get("security", "")
        query["key"] = quic.get("key", "")
        query["type"] = quic.get("header", {}).get("type", "")
    elif net == "kcp":
        kcp = node.get("kcp-opts", {})
        query["type"] = kcp.get("header", {}).get("type", "")
    elif net == "tcp":
        http_opts = node.get("http-opts", {})
        if http_opts:
            query["headerType"] = "http"
            query["path"] = http_opts.get("path", ["/"])[0]
            query["host"] = ",".join(http_opts.get("headers", {}).get("Host", []))

    query_str = '&'.join(f"{k}={quote_plus(str(v))}" for k, v in query.items() if v)
    return f"vless://{node['uuid']}@{node['server']}:{node['port']}?{query_str}#{quote_plus(node.get('name', ''))}"

def encode_trojan(node):
    ws_opts = node.get("ws-opts", {})
    is_httpupgrade = (
        node.get("network") == "ws"
        and ws_opts.get("v2ray-http-upgrade") is True
        and ws_opts.get("v2ray-http-upgrade-fast-open") is True
    )
    net = "httpupgrade" if is_httpupgrade else node.get("network", "tcp")

    query = {
        "type": net,
        "sni": node.get("sni") or node.get("servername", "")
    }

    if node.get("flow"):
        query["flow"] = node["flow"]

    if net in ["ws", "httpupgrade"]:
        query["path"] = ws_opts.get("path", "")
        query["host"] = ws_opts.get("headers", {}).get("Host", "")
    elif net == "http":
        http_opts = node.get("http-opts", {})
        query["headerType"] = "http"
        query["path"] = http_opts.get("path", ["/"])[0]
        query["host"] = ",".join(http_opts.get("headers", {}).get("Host", []))
    elif net == "grpc":
        grpc = node.get("grpc-opts", {})
        query["serviceName"] = grpc.get("grpc-service-name", "")
    elif net == "h2":
        h2 = node.get("h2-opts", {})
        query["path"] = h2.get("path", "")
        query["host"] = ",".join(h2.get("host", []))
    elif net == "kcp":
        kcp = node.get("kcp-opts", {})
        query["type"] = kcp.get("header", {}).get("type", "")
    elif net == "quic":
        quic = node.get("quic-opts", {})
        query["security"] = quic.get("security", "")
        query["key"] = quic.get("key", "")
        query["type"] = quic.get("header", {}).get("type", "")

    # Encode query string
    query_str = '&'.join(f"{k}={quote_plus(str(v))}" for k, v in query.items() if v)

    return f"trojan://{node['password']}@{node['server']}:{node['port']}?{query_str}#{quote_plus(node.get('name', ''))}"

def encode_ss(node):
    userinfo = f"{node['cipher']}:{node['password']}"
    hostinfo = f"{node['server']}:{node['port']}"
    base64_str = base64.urlsafe_b64encode(f"{userinfo}@{hostinfo}".encode()).decode().rstrip("=")
    return f"ss://{base64_str}#{quote_plus(node.get('name', 'Shadowsocks'))}"

def encode_socks5(node):
    query = {
        "tls": "true" if node.get("tls") else "",
        "fp": node.get("fingerprint", ""),
        "ip": node.get("ip-version", "ipv4")
    }
    query_str = '&'.join(f"{k}={quote_plus(str(v))}" for k, v in query.items() if v)
    creds = f"{node['username']}:{node['password']}"
    return f"socks5://{creds}@{node['server']}:{node['port']}?{query_str}"

def encode_http(node):
    query = {
        "tls": "true" if node.get("tls") else "",
        "fp": node.get("fingerprint", ""),
        "sni": node.get("sni", ""),
        "ip": node.get("ip-version", "ipv4")
    }
    query_str = '&'.join(f"{k}={quote_plus(str(v))}" for k, v in query.items() if v)
    creds = f"{node['username']}:{node['password']}"
    return f"http://{creds}@{node['server']}:{node['port']}?{query_str}"

def encode_hysteria(node):
    query = {
        "auth": node.get("auth", ""),
        "alpn": ",".join(node.get("alpn", [])) if node.get("alpn") else "",
        "protocol": node.get("protocol", "udp"),
        "obfs": node.get("obfs", ""),
        "sni": node.get("sni", ""),
        "insecure": "1" if node.get("insecure") else "0"
    }
    query_str = '&'.join(f"{k}={quote_plus(str(v))}" for k, v in query.items() if v)
    return f"hysteria://{node['server']}:{node['port']}?{query_str}"

def encode_hy2(node):
    query = {
        "sni": node.get("sni", ""),
        "alpn": ",".join(node.get("alpn", [])) if node.get("alpn") else "",
        "insecure": "1" if node.get("insecure") else "0"
    }
    query_str = '&'.join(f"{k}={quote_plus(str(v))}" for k, v in query.items() if v)
    return f"hy2://{node['password']}@{node['server']}:{node['port']}?{query_str}"

def parse_clash_yaml(yaml_text):
    try:
        documents = list(yaml.safe_load_all(yaml_text))
        proxies = []
        for doc in documents:
            if isinstance(doc, dict):
                proxies.extend(doc.get("proxies", []))
            elif isinstance(doc, list):
                proxies.extend(doc)
    except Exception as e:
        return None, f"YAML tidak valid: {e}"

    if not proxies:
        return None, "Tidak ditemukan entri proxy yang valid."

    urls = []
    valid_type_found = False
    for node in proxies:
        proto = node.get('type')
        if not proto:
            urls.append(f"# [Error] Node '{node.get('name', '')}' tidak memiliki field 'type'. Tambahkan type: vmess/vless/dll")
            continue

        proto = proto.lower()
        if proto == 'vmess':
            urls.append(encode_vmess(node)); valid_type_found = True
        elif proto == 'vless':
            urls.append(encode_vless(node)); valid_type_found = True
        elif proto == 'trojan':
            urls.append(encode_trojan(node)); valid_type_found = True
        elif proto == 'ss':
            urls.append(encode_ss(node)); valid_type_found = True
        elif proto == 'socks5':
            urls.append(encode_socks5(node)); valid_type_found = True
        elif proto == 'http':
            urls.append(encode_http(node)); valid_type_found = True
        elif proto in ['hysteria', 'hysteria2', 'hy2']:
            urls.append(encode_hy2(node)); valid_type_found = True
        else:
            urls.append(f"# [Tidak didukung] {node.get('name', '')} dengan type: {proto}")

    if not valid_type_found:
        return None, "Tidak ditemukan entri dengan `type` yang valid."

    return urls, None

# --- Handler utama .revclash ---l
async def revclash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    yaml_text = None
    # Jika argumen diberikan langsung
    # if args:
        # loading_message = await update.message.reply_text("Sedang memproses...")
        # input_text = " ".join(args)
        # yaml_text = "\n".join(
            # line for line in input_text.strip().splitlines()
            # if not line.strip().lower().startswith("clash configuration:")
        # )
        # yaml_text = re.sub(r"Host:\s*''[`´]+", "Host: ''", yaml_text)

    # Jika reply ke dokumen
    if update.message.reply_to_message and update.message.reply_to_message.document:
        loading_message = await update.message.reply_text("Sedang memproses...")
        file = await update.message.reply_to_message.document.get_file()
        path = await file.download_to_drive()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                yaml_text = f.read()
        except Exception as e:
            await update.message.reply_text(f"Gagal membaca file: {str(e)}")
            return
        os.remove(path)

    else:
        # await loading_message.delete()
        await update.message.reply_text("/revclash Reply ke file YAML.")
        return

    # Parsing YAML
    urls, err = parse_clash_yaml(yaml_text)
    if err:
        await update.message.reply_text(f"Gagal parsing:\n{err}")
        return

    # Output hasil parsing
    output = "\n\n".join(urls)

    # Jika output lebih dari 2000 karakter, kirimkan sebagai file
    if len(output) > 2000:
        file_buffer = BytesIO(output.encode("utf-8"))
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        file_buffer.name = f"v2ray_urls-{timestamp}.txt"
        
        # Menghapus pesan loading dan mengirim file
        await loading_message.delete()
        await update.message.reply_document(
            document=InputFile(file_buffer),
            caption=(
                '<blockquote class="expandable">'
                'Konversi selesai.\nBerikut hasil file konfigurasi parser v2ray urls.'
                '</blockquote>'
            ),
            parse_mode="HTML"
        )
    else:
        await loading_message.delete()
        await update.message.reply_text(f"Berikut hasil konversi:\n\n{output}")