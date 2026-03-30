#!/usr/bin/env python3
"""
ZE HQ — Monitor Server
Backend que coleta dados SNMP do roteador e da rede em tempo real
Serve JSON na porta 9000
"""
import subprocess, json, time, threading, re
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

ROUTER_IP = "10.50.0.1"
COMMUNITY = "HISOL"
NETWORK   = "10.50.0.0/24"
MY_IP     = "10.50.0.121"

# ── Estado global ──────────────────────────────
state = {
    "router": {},
    "devices": [],
    "history": {
        "wan_in":  [],
        "wan_out": [],
        "lan_in":  [],
        "lan_out": [],
        "cpu":     [],
        "timestamps": []
    },
    "alerts": [],
    "last_update": "",
    "scan_running": False,
    "prev_octets": {}
}

LOCK = threading.Lock()

# ── SNMP helpers ───────────────────────────────
def snmpget(oids):
    try:
        cmd = ["snmpget", "-v2c", "-c", COMMUNITY, "-t", "3", ROUTER_IP] + oids
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
        return r.stdout
    except:
        return ""

def snmpwalk(oid):
    try:
        cmd = ["snmpwalk", "-v2c", "-c", COMMUNITY, "-t", "5", ROUTER_IP, oid]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.stdout
    except:
        return ""

def parse_int(text, key):
    m = re.search(rf"{re.escape(key)}.*?=.*?(\d+)", text)
    return int(m.group(1)) if m else 0

def parse_str(text, key):
    m = re.search(rf"{re.escape(key)}.*?=.*?STRING:\s*(.+)", text)
    return m.group(1).strip() if m else "—"

def parse_timeticks(text):
    m = re.search(r"sysUpTimeInstance.*?\((\d+)\)", text)
    if not m:
        return "—", 0
    ticks = int(m.group(1)) // 100  # seconds
    days  = ticks // 86400
    hrs   = (ticks % 86400) // 3600
    mins  = (ticks % 3600) // 60
    secs  = ticks % 60
    return f"{days}d {hrs:02d}h {mins:02d}m {secs:02d}s", ticks

def bytes_to_mbps(delta_bytes, interval_sec=30):
    return round((delta_bytes * 8) / (interval_sec * 1_000_000), 2)

def human_bytes(b):
    for unit in ['B','KB','MB','GB','TB']:
        if b < 1024: return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"

# ── SNMP collector ─────────────────────────────
def collect_router():
    # System
    sys_data = snmpwalk("system")
    uptime_str, uptime_secs = parse_timeticks(sys_data)

    # CPU
    cpu_data = snmpwalk(".1.3.6.1.2.1.25.3.3.1.2")
    cpu_loads = list(map(int, re.findall(r"INTEGER:\s*(\d+)", cpu_data)))
    cpu_avg = round(sum(cpu_loads) / len(cpu_loads), 1) if cpu_loads else 0

    # Memory
    mem_data = snmpwalk(".1.3.6.1.2.1.25.2.3.1")
    mem_total = parse_int(mem_data, "hrStorageSize.65536")
    mem_used  = parse_int(mem_data, "hrStorageUsed.65536")
    mem_pct   = round(mem_used / mem_total * 100, 1) if mem_total else 0

    disk_total = parse_int(mem_data, "hrStorageSize.131072")
    disk_used  = parse_int(mem_data, "hrStorageUsed.131072")
    disk_pct   = round(disk_used / disk_total * 100, 1) if disk_total else 0

    # Interfaces traffic
    iface_data = snmpget([
        "ifOperStatus.3", "ifOperStatus.45",  # WAN2, WAN1
        "ifInOctets.3",   "ifOutOctets.3",    # WAN2 traffic
        "ifInOctets.11",  "ifOutOctets.11",   # LAN traffic
        "ifInErrors.3",   "ifOutErrors.3",
        "ifSpeed.3",      "ifSpeed.45",
    ])

    m2 = re.findall(r"ifOperStatus\.3.*?(\w+\(\d\))", iface_data)
    wan2_status = "UP" if m2 and "up(1)" in m2[0] else "DOWN"
    wan1_status = "UP" if re.findall(r"ifOperStatus\.45.*?up", iface_data) else "DOWN"

    wan_in_raw   = parse_int(iface_data, "ifInOctets.3")
    wan_out_raw  = parse_int(iface_data, "ifOutOctets.3")
    lan_in_raw   = parse_int(iface_data, "ifInOctets.11")
    lan_out_raw  = parse_int(iface_data, "ifOutOctets.11")
    wan_errors_in  = parse_int(iface_data, "ifInErrors.3")
    wan_errors_out = parse_int(iface_data, "ifOutErrors.3")

    # Calculate Mbps from delta
    now = time.time()
    prev = state["prev_octets"]
    interval = now - prev.get("time", now - 30)

    wan_in_mbps  = bytes_to_mbps(max(0, wan_in_raw  - prev.get("wan_in",  wan_in_raw)),  max(interval, 1))
    wan_out_mbps = bytes_to_mbps(max(0, wan_out_raw - prev.get("wan_out", wan_out_raw)), max(interval, 1))
    lan_in_mbps  = bytes_to_mbps(max(0, lan_in_raw  - prev.get("lan_in",  lan_in_raw)),  max(interval, 1))
    lan_out_mbps = bytes_to_mbps(max(0, lan_out_raw - prev.get("lan_out", lan_out_raw)), max(interval, 1))

    state["prev_octets"] = {
        "time": now,
        "wan_in": wan_in_raw, "wan_out": wan_out_raw,
        "lan_in": lan_in_raw, "lan_out": lan_out_raw
    }

    # Interfaces list
    iface_names   = dict(re.findall(r"ifDescr\.(\d+) = STRING: (.+)", snmpwalk("ifDescr")))
    iface_status  = dict(re.findall(r"ifOperStatus\.(\d+) = INTEGER: (\w+\(\d\))", snmpwalk("ifOperStatus")))
    interfaces = []
    key_ifaces = ["3","4","5","6","11","45","46","47","51","52","53","54","56"]
    for idx in key_ifaces:
        name = iface_names.get(idx, f"if{idx}")
        status = "up" if "up(1)" in iface_status.get(idx, "") else "down"
        interfaces.append({"id": idx, "name": name, "status": status})

    # Alerts
    alerts = []
    if wan1_status == "DOWN":
        alerts.append({"level": "warn", "msg": "WAN1 (ether1) está DOWN — sem redundância de link"})
    if cpu_avg > 80:
        alerts.append({"level": "critical", "msg": f"CPU alta: {cpu_avg}%"})
    if mem_pct > 85:
        alerts.append({"level": "warn", "msg": f"Memória alta: {mem_pct}%"})
    if wan_errors_in > 0 or wan_errors_out > 0:
        alerts.append({"level": "warn", "msg": f"Erros na WAN: IN={wan_errors_in} OUT={wan_errors_out}"})

    return {
        "system": {
            "name": parse_str(sys_data, "sysName.0"),
            "descr": parse_str(sys_data, "sysDescr.0"),
            "location": parse_str(sys_data, "sysLocation.0"),
            "uptime": uptime_str,
            "uptime_secs": uptime_secs,
        },
        "cpu": {
            "cores": cpu_loads,
            "avg": cpu_avg,
        },
        "memory": {
            "total_kb": mem_total,
            "used_kb": mem_used,
            "pct": mem_pct,
            "total_human": human_bytes(mem_total * 1024),
            "used_human": human_bytes(mem_used * 1024),
        },
        "disk": {
            "total_kb": disk_total,
            "used_kb": disk_used,
            "pct": disk_pct,
        },
        "wan": {
            "wan1_status": wan1_status,
            "wan2_status": wan2_status,
            "in_mbps": wan_in_mbps,
            "out_mbps": wan_out_mbps,
            "in_total": human_bytes(wan_in_raw),
            "out_total": human_bytes(wan_out_raw),
            "errors_in": wan_errors_in,
            "errors_out": wan_errors_out,
        },
        "lan": {
            "in_mbps": lan_in_mbps,
            "out_mbps": lan_out_mbps,
        },
        "interfaces": interfaces,
        "alerts": alerts,
    }

# ── Network scanner ────────────────────────────
def scan_network():
    if state["scan_running"]:
        return
    state["scan_running"] = True
    try:
        cmd = ["nmap", "-sn", NETWORK, "--open"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        ips = re.findall(r"Nmap scan report for ([\d.]+)", r.stdout)
        latencies = re.findall(r"Host is up \(([\d.]+)s latency\)", r.stdout)
        devices = []
        for i, ip in enumerate(ips):
            lat = float(latencies[i]) * 1000 if i < len(latencies) else None
            label = "Mac Mini (ZE HQ)" if ip == MY_IP else ("Gateway/Roteador" if ip == ROUTER_IP else "Dispositivo")
            devices.append({
                "ip": ip,
                "label": label,
                "latency_ms": round(lat, 1) if lat is not None else None,
                "is_self": ip == MY_IP,
                "is_router": ip == ROUTER_IP,
            })
        with LOCK:
            state["devices"] = devices
    except Exception as e:
        print(f"Scan error: {e}")
    finally:
        state["scan_running"] = False

# ── History (last 30 points) ───────────────────
MAX_HISTORY = 30

def push_history(router):
    h = state["history"]
    ts = datetime.now().strftime("%H:%M:%S")
    h["timestamps"].append(ts)
    h["wan_in"].append(router["wan"]["in_mbps"])
    h["wan_out"].append(router["wan"]["out_mbps"])
    h["lan_in"].append(router["lan"]["in_mbps"])
    h["lan_out"].append(router["lan"]["out_mbps"])
    h["cpu"].append(router["cpu"]["avg"])
    for k in h:
        if isinstance(h[k], list) and len(h[k]) > MAX_HISTORY:
            h[k] = h[k][-MAX_HISTORY:]

# ── Background workers ─────────────────────────
def router_worker():
    while True:
        try:
            data = collect_router()
            with LOCK:
                state["router"] = data
                push_history(data)
                state["alerts"] = data["alerts"]
                state["last_update"] = datetime.now().strftime("%H:%M:%S")
        except Exception as e:
            print(f"Router worker error: {e}")
        time.sleep(15)

def scan_worker():
    while True:
        scan_network()
        time.sleep(60)

# ── HTTP Server ────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/data":
            with LOCK:
                payload = json.dumps({
                    "router": state["router"],
                    "devices": state["devices"],
                    "history": state["history"],
                    "alerts": state["alerts"],
                    "last_update": state["last_update"],
                    "scan_running": state["scan_running"],
                })
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass  # Silence logs

if __name__ == "__main__":
    print("ZE HQ Monitor Server iniciando na porta 9000...")
    threading.Thread(target=router_worker, daemon=True).start()
    threading.Thread(target=scan_worker, daemon=True).start()
    time.sleep(2)  # Give workers a head start
    HTTPServer(("0.0.0.0", 9000), Handler).serve_forever()
