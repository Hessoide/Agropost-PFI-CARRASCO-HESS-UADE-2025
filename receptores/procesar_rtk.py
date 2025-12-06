import subprocess
import os
import sys

# --- CONFIGURACIÓN ---
BASE_GPS_FILE = "base_gps_1743.ubx"
ROVER_GPS_FILE = "rover_gps_1743.ubx"

# Ejecutables (Sin "./")
CONVBIN_EXE = "convbin.exe"
RNX2RTKP_EXE = "rnx2rtkp.exe"
RTKPLOT_EXE = "rtkplot.exe"
POS2KML_EXE = "pos2kml.exe"
RTK_CONF_FILE = "rtk_conf.conf"

SOLUTION_FILE = "solucion_final.pos"

def clean_previous_files():
    print("Limpiando archivos anteriores...")
    # Agregamos .sbs a la lista de limpieza
    extensions = [".obs", ".nav", ".gnav", ".lnav", ".qnav", ".hnav", ".sbs"]
    prefixes = ["base", "rover"]
    
    files_to_delete = [SOLUTION_FILE, f"{SOLUTION_FILE}.kml"]
    
    for pre in prefixes:
        for ext in extensions:
            files_to_delete.append(pre + ext)
            
    for f in files_to_delete:
        if os.path.exists(f):
            try:
                os.remove(f)
            except: pass

def run_command(command, description):
    print(f"\n--- {description} ---")
    try:
        subprocess.run(command, check=True, shell=False) 
        print("OK.")
        return True
    except subprocess.CalledProcessError:
        print(f"ERROR CRÍTICO en: {description}")
        return False
    except FileNotFoundError:
        print(f"ERROR: No se encontró el programa '{command[0]}'.")
        return False

def main():
    print("=== PROCESAMIENTO AGROPOST RTK (FULL GNSS + SBAS) ===")
    
    clean_previous_files()

    # 1. CONVERSIÓN A RINEX
    # AHORA INCLUIMOS TODOS LOS SISTEMAS PARA EVITAR ERRORES DE NOMBRE
    print("\n1. Convirtiendo archivos .ubx a RINEX...")
    
    # Comando BASE
    cmd_conv_base = [
        CONVBIN_EXE, "-r", "ubx", 
        "-o", "base.obs",   # GPS Observaciones
        "-n", "base.nav",   # GPS Nav
        "-g", "base.gnav",  # GLONASS Nav
        "-l", "base.lnav",  # Galileo Nav
        "-s", "base.sbs",   # SBAS Messages (Corrección del error î╩GwLΘ↓)
        BASE_GPS_FILE
    ]
    if not run_command(cmd_conv_base, "Convirtiendo BASE"):
        sys.exit(1)
    
    # Comando ROVER
    cmd_conv_rover = [
        CONVBIN_EXE, "-r", "ubx",
        "-o", "rover.obs",
        "-n", "rover.nav",
        "-g", "rover.gnav",
        "-l", "rover.lnav",
        "-s", "rover.sbs",  # SBAS Messages
        ROVER_GPS_FILE
    ]
    if not run_command(cmd_conv_rover, "Convirtiendo ROVER"):
        sys.exit(1)

    # 2. PROCESAMIENTO PPK
    print("\n2. Calculando solución cinemática (PPK)...")
    
    cmd_ppk = [
        RNX2RTKP_EXE,
        "-k", RTK_CONF_FILE,
        "-o", SOLUTION_FILE,
        "rover.obs",
        "base.obs",
        "base.nav"
    ]
    
    # Agregamos todos los archivos extra de navegación disponibles
    # para que el motor matemático tenga la mayor cantidad de datos posible
    extra_navs = ["base.gnav", "base.lnav", "base.sbs", 
                  "rover.nav", "rover.gnav", "rover.lnav", "rover.sbs"]
    
    for nav in extra_navs:
        if os.path.exists(nav):
            cmd_ppk.append(nav)

    if not run_command(cmd_ppk, "Procesamiento Matemático RTK"):
        sys.exit(1)

    # 3. GENERAR KML
    print("\n3. Generando mapa para Google Earth...")
    if run_command([POS2KML_EXE, "-c", "2", SOLUTION_FILE], "Creando KML"):
        kml_file = SOLUTION_FILE + ".kml"
        if os.path.exists(kml_file):
            print(f"Abriendo Google Earth...")
            try:
                os.startfile(kml_file)
            except: pass

    # 4. ABRIR GRÁFICO
    if os.path.exists(SOLUTION_FILE):
        print("\n4. Abriendo gráfico de análisis...")
        try:
            subprocess.Popen([RTKPLOT_EXE, SOLUTION_FILE])
        except: pass
    
    print("\n=== PROCESO TERMINADO ===")

if __name__ == "__main__":
    main()