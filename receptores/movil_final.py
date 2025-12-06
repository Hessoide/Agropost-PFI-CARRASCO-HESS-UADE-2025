#!/usr/bin/env python3
# PROYECTO AGROPOST - SCRIPT ESTACION MOVIL (FINAL)
# Autores: Carrasco, Hess
# Descripcion: Recibe correcciones via LoRa, las envia al GNSS para RTK
# y postea posicion al backend (misma interfaz que sender.py).

import os
import time
import serial
import requests
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from LoRaRF import SX127x

# --- CONFIGURACION ---
SERIAL_PORT = os.getenv("ROVER_GPS_PORT", "/dev/ttyACM0")
BAUD_RATE = int(os.getenv("ROVER_GPS_BAUD", "9600"))

API_HOST = os.getenv("AGROPOST_HOST", "127.0.0.1")
API_PORT = int(os.getenv("AGROPOST_PORT", "8000"))
POST_MIN_INTERVAL = float(os.getenv("AGROPOST_POST_INTERVAL", "1.0"))  # seg entre envios al backend
MIN_FIX_QUALITY = int(os.getenv("AGROPOST_MIN_FIX", "4"))  # 4=RTK Fixed, 5=Float

# RTKLIB (usar ejecutables locales)
RTKLIB_DIR = Path(os.getenv("RTKLIB_DIR", "../RTKLIB")).resolve()
CONVBIN_EXE = RTKLIB_DIR / ("convbin.exe" if os.name == "nt" else "convbin")
RNX2RTKP_EXE = RTKLIB_DIR / ("rnx2rtkp.exe" if os.name == "nt" else "rnx2rtkp")
RTK_TMP_DIR = Path(os.getenv("RTK_TMP_DIR", "./rtk_tmp")).resolve()
RTK_SOLVE_INTERVAL = float(os.getenv("RTK_SOLVE_INTERVAL", "5.0"))  # seg entre soluciones RTK
BASE_DIR = Path(__file__).resolve().parent
RTK_CONF_FILE = Path(os.getenv("RTK_CONF_FILE", BASE_DIR / "rtk_conf.conf")).resolve()

TIMESTAMP_START = datetime.now().strftime('%H%M')
GPS_FILE = f"rover_gps_{TIMESTAMP_START}.ubx"
CORR_FILE = f"rover_corr_{TIMESTAMP_START}.bin"
LORA_FILE = f"rover_lora_{TIMESTAMP_START}.csv"

# Parametros LoRa (deben coincidir con la base)
LORA_FREQ = 433000000
LORA_SF = 7
LORA_BW = 250000
LORA_CR = 5
LORA_SYNCWORD = 0x3444

# Protocolo de correcciones
CORR_HEADER = b"\xAA\xC1"


def nmea_to_deg(raw: str, hemi: str, is_lat: bool = True):
    """Convierte coordenadas NMEA ddmm.mmmm a grados decimales."""
    if not raw:
        return None
    try:
        val = float(raw)
    except ValueError:
        return None
    deg_len = 2 if is_lat else 3
    deg = int(val // (10 ** deg_len))
    minutes = val - deg * (10 ** deg_len)
    res = deg + minutes / 60.0
    if hemi in ("S", "W"):
        res *= -1
    return res


def parse_gga(line: str):
    """Extrae lat/lon/fix/sats/hdop desde un mensaje GGA."""
    if "GGA" not in line:
        return None
    parts = line.split(",")
    if len(parts) < 9:
        return None
    lat = nmea_to_deg(parts[2], parts[3], is_lat=True)
    lon = nmea_to_deg(parts[4], parts[5], is_lat=False)
    if lat is None or lon is None:
        return None
    try:
        fix = int(parts[6] or 0)
    except ValueError:
        fix = 0
    try:
        sats = int(parts[7] or 0)
    except ValueError:
        sats = 0
    try:
        hdop = float(parts[8] or 0.0)
    except ValueError:
        hdop = None
    return {"lat": lat, "lon": lon, "fix": fix, "sats": sats, "hdop": hdop}


def parse_gsa(line: str):
    """Obtiene PDOP aproximado desde GSA (campo 15)."""
    if "GSA" not in line:
        return None
    parts = line.split(",")
    if len(parts) < 15:
        return None
    try:
        return float(parts[14]) if parts[14] else None
    except ValueError:
        return None


def post_pos(host: str, port: int, lat: float, lon: float, fix: int | None = 4, pdop: float | None = None, sats: int | None = None):
    url = f"http://{host}:{port}/api/pos"
    payload = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "lat": float(lat),
        "lon": float(lon),
        "fix_quality": fix,
        "pdop": pdop,
        "sats": sats,
    }
    r = requests.post(url, json=payload, timeout=5)
    r.raise_for_status()
    return r.json()


def run_convbin(input_path: Path, fmt: str, out_dir: Path, prefix: str):
    """Ejecuta convbin para generar RINEX desde archivo raw."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(CONVBIN_EXE),
        "-r",
        fmt,
        "-o",
        str(out_dir / f"{prefix}.obs"),
        "-n",
        str(out_dir / f"{prefix}.nav"),
        "-g",
        str(out_dir / f"{prefix}.gnav"),
        "-l",
        str(out_dir / f"{prefix}.lnav"),
        "-s",
        str(out_dir / f"{prefix}.sbs"),
        str(input_path),
    ]
    subprocess.run(cmd, check=True, cwd=str(RTKLIB_DIR))


def run_rnx2rtkp(rover_obs: Path, base_obs: Path, rover_nav: Path | None, base_nav: Path | None, out_pos: Path, conf_path: Path, nav_extras: list[Path] | None = None):
    """Ejecuta rnx2rtkp en modo cinemático (2) para obtener solución RTK."""
    cmd = [str(RNX2RTKP_EXE), "-p", "2", "-k", str(conf_path), "-o", str(out_pos)]
    # Orden: obs rover, obs base, luego nav (si hay)
    cmd.append(str(rover_obs))
    cmd.append(str(base_obs))
    if rover_nav and rover_nav.exists():
        cmd.append(str(rover_nav))
    if base_nav and base_nav.exists():
        cmd.append(str(base_nav))
    if nav_extras:
        for nav in nav_extras:
            if nav and nav.exists():
                cmd.append(str(nav))
    subprocess.run(cmd, check=True, cwd=str(RTKLIB_DIR))


def parse_rtk_solution(pos_file: Path):
    """Lee el ultimo fix del archivo .pos de RTKLIB."""
    if not pos_file.exists():
        return None
    lines = pos_file.read_text().splitlines()
    for line in reversed(lines):
        if not line.strip() or line.startswith("%"):
            continue
        cols = line.split()
        if len(cols) < 7:
            continue
        try:
            lat = float(cols[2])
            lon = float(cols[3])
            fix_q = int(cols[5])
            sats = int(cols[6])
        except Exception:
            continue
        # Mapear calidad RTKLIB -> fix_quality del backend
        # RTKLIB Q: 1=Fix, 2=Float, 3=SBAS, 4=DGPS, 5=Single, 6=PPP
        fix_quality = 4 if fix_q == 1 else 5 if fix_q == 2 else 1
        return {"lat": lat, "lon": lon, "fix": fix_quality, "rtk_q": fix_q, "sats": sats}
    return None


class RTKWorker:
    """Procesa RTK en segundo plano usando RTKLIB y publica al backend."""

    def __init__(self, raw_path: Path, corr_path: Path):
        self.raw_path = raw_path.resolve()
        self.corr_path = corr_path.resolve()
        self.tmp_dir = RTK_TMP_DIR
        self.stop_event = threading.Event()
        self.last_post = 0.0

    def loop(self):
        if not CONVBIN_EXE.exists() or not RNX2RTKP_EXE.exists():
            print(f"RTKLIB no encontrado en {RTKLIB_DIR}. convbin/rnx2rtkp requeridos.")
            return
        if not RTK_CONF_FILE.exists():
            print(f"Archivo de configuracion RTK no encontrado: {RTK_CONF_FILE}")
            return
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        while not self.stop_event.is_set():
            try:
                self.run_once()
            except Exception as e:
                print(f"[RTK] ERROR: {e}")
            self.stop_event.wait(RTK_SOLVE_INTERVAL)

    def run_once(self):
        # Evitar correr si los archivos estan vacios
        if not self.raw_path.exists() or self.raw_path.stat().st_size < 2048:
            return
        if not self.corr_path.exists() or self.corr_path.stat().st_size < 512:
            return

        # Limpiar salidas anteriores
        rover_obs = self.tmp_dir / "rover.obs"
        base_obs = self.tmp_dir / "base.obs"
        rover_nav = self.tmp_dir / "rover.nav"
        base_nav = self.tmp_dir / "base.nav"
        pos_out = self.tmp_dir / "solution.pos"
        for f in [rover_obs, base_obs, rover_nav, base_nav, pos_out]:
            try:
                f.unlink()
            except FileNotFoundError:
                pass

        # 1) RINEX de rover (UBX crudo)
        run_convbin(self.raw_path, "ubx", self.tmp_dir, "rover")
        # 2) RINEX de base (RTCM recibido)
        run_convbin(self.corr_path, "rtcm3", self.tmp_dir, "base")
        # 3) Solucion RTK
        nav_extras = [
            self.tmp_dir / "base.gnav",
            self.tmp_dir / "base.lnav",
            self.tmp_dir / "base.sbs",
            self.tmp_dir / "rover.gnav",
            self.tmp_dir / "rover.lnav",
            self.tmp_dir / "rover.sbs",
        ]
        run_rnx2rtkp(rover_obs, base_obs, rover_nav, base_nav, pos_out, RTK_CONF_FILE, nav_extras=nav_extras)

        sol = parse_rtk_solution(pos_out)
        if not sol:
            return
        now = time.time()
        if sol["fix"] >= MIN_FIX_QUALITY and (now - self.last_post) >= POST_MIN_INTERVAL:
            resp = post_pos(API_HOST, API_PORT, sol["lat"], sol["lon"], fix=sol["fix"], pdop=None, sats=sol["sats"])
            print(f"[RTK] -> lat={sol['lat']:.7f} lon={sol['lon']:.7f} fixQ={sol['fix']} (rtklib={sol['rtk_q']}) sats={sol['sats']} delivered={resp.get('delivered')}")
            self.last_post = now


def main():
    # --- 1. CONFIGURACION LORA ---
    lora = SX127x()
    lora.setPins(22, -1, -1, -1)
    lora.setSpi(0, 0, 7800000)

    if not lora.begin():
        print("ERROR: No se detecta el modulo LoRa.")
        return

    lora.setFrequency(LORA_FREQ)
    lora.setLoRaModulation(LORA_SF, LORA_BW, LORA_CR, False)  # BW 250k
    lora.setLoRaPacket(lora.HEADER_EXPLICIT, 8, 0, True, False)
    lora.setSyncWord(LORA_SYNCWORD)

    # --- 2. CONFIGURACION GPS Y LOGS ---
    try:
        gps_serial = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.05)
    except Exception as e:
        print(f"Error abriendo GPS: {e}")
        return

    f_gps = open(GPS_FILE, "wb")
    f_corr = open(CORR_FILE, "wb")
    f_lora = open(LORA_FILE, "w")
    f_lora.write("TIMESTAMP,EVENTO,SEQ,LEN,RSSI,SNR,DETALLE\n")

    # Lanzar hilo de RTK (procesa archivos y publica al backend)
    rtk_worker = RTKWorker(Path(GPS_FILE), Path(CORR_FILE))
    rtk_thread = threading.Thread(target=rtk_worker.loop, daemon=True)
    rtk_thread.start()

    print(f"=== AGROPOST ROVER INICIADO ===")
    print(f"GPS Log   > {GPS_FILE}")
    print(f"Corr Log  > {CORR_FILE}")
    print(f"LoRa Log  > {LORA_FILE}")
    print(f"Publicando posiciones hacia http://{API_HOST}:{API_PORT}/api/pos cada {POST_MIN_INTERVAL}s")
    print("Esperando correcciones y RTK fix...")

    nmea_buffer = ""
    last_pdop = None
    last_gga = None

    try:
        while True:
            # 1) Leer y guardar datos del GNSS local (incluye NMEA/UBX)
            if gps_serial.in_waiting:
                data = gps_serial.read(gps_serial.in_waiting)
                if data:
                    f_gps.write(data)
                    text = data.decode(errors="ignore")
                    nmea_buffer += text

                    # Procesar NMEA por lineas para obtener fix RTK
                    while "\n" in nmea_buffer:
                        line, nmea_buffer = nmea_buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        if "GGA" in line:
                            gga = parse_gga(line)
                            if gga:
                                last_gga = gga
                        elif "GSA" in line:
                            pdop = parse_gsa(line)
                            if pdop is not None:
                                last_pdop = pdop

            # 2) Escuchar LoRa (correcciones desde base)
            lora.request()
            lora.wait()  # Espera interrupcion DIO0

            if lora.available():
                buf = []
                while lora.available():
                    buf.append(lora.read())

                packet = bytes(buf)
                ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                rssi = lora.packetRssi()
                snr = lora.packetSnr()

                evento = "RX_OTHER"
                seq = ""
                detalle = ""
                length = len(packet)

                if packet.startswith(CORR_HEADER) and length >= 4:
                    seq = packet[2]
                    expected_len = packet[3]
                    payload = packet[4:4 + expected_len]
                    if len(payload) != expected_len:
                        evento = "CORR_BADLEN"
                        detalle = packet.hex()
                    else:
                        # Enviar correccion al receptor GNSS local
                        gps_serial.write(payload)
                        f_corr.write(payload)
                        f_corr.flush()
                        evento = "CORR_OK"
                        detalle = payload.hex()
                    print(f"[{ts}] Rx CORR seq={seq} len={len(payload)} RSSI={rssi}dBm SNR={snr}")
                else:
                    # Beacon u otro mensaje
                    evento = "RX_OTHER"
                    try:
                        detalle = packet.decode(errors="replace")
                    except Exception:
                        detalle = packet.hex()
                    print(f"[{ts}] Rx {detalle} RSSI={rssi}dBm SNR={snr}")

                f_lora.write(f"{ts},{evento},{seq},{length},{rssi},{snr},{detalle}\n")
                f_lora.flush()

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\nDeteniendo...")
    finally:
        rtk_worker.stop_event.set()
        rtk_thread.join(timeout=2.0)
        f_gps.close()
        f_corr.close()
        f_lora.close()
        gps_serial.close()
        print("Archivos cerrados correctamente.")


if __name__ == "__main__":
    main()
