#!/usr/bin/env python3
# PROYECTO AGROPOST - SCRIPT ESTACION BASE (FINAL)
# Autores: Carrasco, Hess
# Descripcion: Envia correcciones GNSS via LoRa y graba datos RAW GNSS para Post-Proceso.

import time
import serial
from datetime import datetime
from LoRaRF import SX127x

# --- CONFIGURACION ---
SERIAL_PORT = "/dev/ttyACM0"  # Puerto del u-blox M8T
BAUD_RATE = 9600

# Generacion de nombres de archivo unicos por hora
TIMESTAMP_START = datetime.now().strftime('%H%M')
GPS_FILE = f"base_gps_{TIMESTAMP_START}.ubx"
LORA_FILE = f"base_lora_{TIMESTAMP_START}.csv"

# Parametros LoRa (deben coincidir con la estacion movil)
LORA_FREQ = 433000000
LORA_TX_POWER = 17
LORA_SF = 7
LORA_BW = 250000
LORA_CR = 5
LORA_SYNCWORD = 0x3444

# Protocolo simple de correcciones: [0xAA,0xC1,seq,len,payload...]
CORR_HEADER = b"\xAA\xC1"
MAX_PAYLOAD = 200           # bytes por paquete (sin header)
FLUSH_INTERVAL = 0.25       # seg. maximos a esperar antes de vaciar el buffer
BEACON_INTERVAL = 5.0       # seg. entre beacons para monitorear enlace


def extract_rtcm_frames(buf: bytearray):
    """Extrae frames RTCM3 (0xD3, len[10 bits], payload, CRC3) del buffer."""
    frames = []
    while True:
        if len(buf) < 3:
            break
        try:
            start = buf.index(0xD3)
        except ValueError:
            buf.clear()
            break
        if start:
            del buf[:start]
        if len(buf) < 3:
            break
        length = ((buf[1] & 0x03) << 8) | buf[2]
        total = 3 + length + 3  # header + payload + CRC24
        if len(buf) < total:
            break
        frame = bytes(buf[:total])
        del buf[:total]
        frames.append(frame)
    return frames


def send_lora(lora: SX127x, payload: bytes):
    """Envia bytes crudos via LoRa."""
    lora.beginPacket()
    lora.write(list(payload))
    lora.endPacket()


def main():
    # --- 1. CONFIGURACION LORA ---
    lora = SX127x()
    # Ajuste de pines (CS=22 para cableado manual en RPi 5)
    lora.setPins(22, -1, -1, -1)
    lora.setSpi(0, 0, 7800000)

    if not lora.begin():
        print("ERROR: No se detecta el modulo LoRa.")
        return

    # Frecuencia y Potencia
    lora.setFrequency(LORA_FREQ)
    lora.setTxPower(LORA_TX_POWER, lora.TX_POWER_PA_BOOST)  # Potencia MAXIMA (17dBm) para campo

    # Modulacion (SF7, BW 250kHz, CR 4/5)
    # BW 250k aumenta la tolerancia a desviaciones del cristal
    lora.setLoRaModulation(LORA_SF, LORA_BW, LORA_CR, False)
    lora.setLoRaPacket(lora.HEADER_EXPLICIT, 8, 0, True, False)
    lora.setSyncWord(LORA_SYNCWORD)

    # --- 2. CONFIGURACION GPS Y LOGS ---
    try:
        gps_serial = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.05)
    except Exception as e:
        print(f"Error abriendo GPS: {e}")
        return

    f_gps = open(GPS_FILE, "wb")
    f_lora = open(LORA_FILE, "w")
    f_lora.write("TIMESTAMP,EVENTO,SEQ,LEN,DETALLE\n")

    print(f"=== AGROPOST BASE INICIADA ===")
    print(f"GPS Log  > {GPS_FILE}")
    print(f"LoRa Log > {LORA_FILE}")
    print("Transmitiendo correcciones + beacon...")

    seq = 0
    last_beacon = 0.0
    last_flush = 0.0
    tx_buffer = bytearray()
    rtcm_buffer = bytearray()

    try:
        while True:
            # A. LEER Y GUARDAR DATOS RAW DEL GPS (Prioridad RTK)
            if gps_serial.in_waiting:
                data = gps_serial.read(gps_serial.in_waiting)
                if data:
                    f_gps.write(data)  # log completo para postproceso
                    rtcm_buffer.extend(data)
                    # Extraer unicamente los frames RTCM que sirven para RTK
                    for frame in extract_rtcm_frames(rtcm_buffer):
                        tx_buffer.extend(frame)

            now = time.time()

            # B. FRAGMENTAR Y ENVIAR CORRECCIONES (RTCM/UBX) VIA LORA
            while tx_buffer and (len(tx_buffer) >= MAX_PAYLOAD or (now - last_flush) > FLUSH_INTERVAL):
                chunk_len = min(MAX_PAYLOAD, len(tx_buffer))
                chunk = bytes(tx_buffer[:chunk_len])
                del tx_buffer[:chunk_len]

                pkt = CORR_HEADER + bytes([seq & 0xFF, chunk_len]) + chunk
                send_lora(lora, pkt)

                ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                f_lora.write(f"{ts},TX_CORR,{seq},{chunk_len},{chunk.hex()}\n")
                f_lora.flush()

                print(f"[{ts}] Tx CORR seq={seq} bytes={chunk_len}")
                seq = (seq + 1) % 256
                last_flush = now
                now = time.time()

            # C. BALIZA PERIODICA PARA MONITOREAR ENLACE
            if now - last_beacon > BEACON_INTERVAL:
                beacon = b"BASE_OK"
                send_lora(lora, beacon)
                ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                f_lora.write(f"{ts},TX_BEACON,{seq},0,{beacon.decode()}\n")
                f_lora.flush()
                print(f"[{ts}] Tx Beacon")
                last_beacon = now

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nDeteniendo...")
    finally:
        f_gps.close()
        f_lora.close()
        gps_serial.close()
        print("Archivos cerrados correctamente.")


if __name__ == "__main__":
    main()
