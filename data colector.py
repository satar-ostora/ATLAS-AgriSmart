#!/usr/bin/env python3
"""
ATLAS AgriSmart — Collecteur Série → CSV
════════════════════════════════════════════════════════════════════════════════
Lit les données de l'Arduino (AgroDrone_CSV.ino) sur le port série et les
enregistre dans agri_data.csv, directement compatible avec le dashboard ATLAS.

Installation des dépendances :
    pip install pyserial

Utilisation :
    python serial_to_csv.py                        # détection auto du port
    python serial_to_csv.py --port COM3            # Windows
    python serial_to_csv.py --port /dev/ttyUSB0   # Linux
    python serial_to_csv.py --port /dev/cu.usbmodem14101  # macOS

Options :
    --port    PORT       Port série (défaut : auto-détection)
    --baud    BAUD       Vitesse (défaut : 9600)
    --output  FICHIER    Fichier CSV de sortie (défaut : agri_data.csv)
    --zone    ZONE_ID    Forcer un identifiant de zone (ex : 1, 2, A…)
    --append             Ajouter aux données existantes (défaut : écraser)
    --verbose            Afficher chaque ligne reçue
════════════════════════════════════════════════════════════════════════════════
"""

import argparse
import csv
import datetime
import os
import sys
import time

# ── Colonnes attendues par le dashboard ATLAS ─────────────────────────────
COLUMNS = [
    "timestamp", "zone",
    "sol_hum", "sol_temp", "sol_ph", "sol_ec",
    "air_temp", "air_hum", "air_co2", "air_vent",
    "eau_ph", "eau_turb", "eau_niveau", "eau_debit",
]

# ── Couleurs ANSI pour le terminal ────────────────────────────────────────
class Clr:
    RESET  = "\033[0m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"

def banner():
    print(f"""
{Clr.GREEN}{Clr.BOLD}
  ╔═══════════════════════════════════════════╗
  ║   ATLAS AgriSmart — Collecteur Série→CSV  ║
  ║   AgroDrone IoT · Prototype v1            ║
  ╚═══════════════════════════════════════════╝
{Clr.RESET}""")

def info(msg):    print(f"{Clr.CYAN}[INFO]{Clr.RESET}  {msg}")
def ok(msg):      print(f"{Clr.GREEN}[ OK ]{Clr.RESET}  {msg}")
def warn(msg):    print(f"{Clr.YELLOW}[WARN]{Clr.RESET}  {msg}")
def error(msg):   print(f"{Clr.RED}[ERR ]{Clr.RESET}  {msg}")


# ── Détection automatique du port Arduino ────────────────────────────────
def auto_detect_port():
    """Retourne le premier port qui ressemble à un Arduino."""
    try:
        import serial.tools.list_ports
        candidates = []
        for p in serial.tools.list_ports.comports():
            desc = (p.description or "").lower()
            hwid = (p.hwid or "").lower()
            if any(k in desc or k in hwid for k in
                   ("arduino", "ch340", "ch341", "cp210", "ftdi", "usb serial", "usbmodem")):
                candidates.append(p.device)
        if candidates:
            return candidates[0]
        # Dernier recours : premier port disponible
        all_ports = list(serial.tools.list_ports.comports())
        if all_ports:
            return all_ports[0].device
    except Exception:
        pass
    return None


# ── Initialisation / vérification du fichier CSV ─────────────────────────
def init_csv(path: str, append: bool) -> bool:
    """
    Crée le fichier CSV avec l'en-tête si nécessaire.
    Retourne True si le fichier existait déjà (mode append).
    """
    exists = os.path.isfile(path)
    if not append or not exists:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(COLUMNS)
        return False
    # Vérifier que l'en-tête est compatible
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            header = []
    if header != COLUMNS:
        warn("En-tête CSV différent — recréation du fichier.")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(COLUMNS)
        return False
    return True


# ── Parsing d'une ligne Arduino → dict CSV ───────────────────────────────
def parse_line(raw_line: str, forced_zone: str | None) -> dict | None:
    """
    Accepte deux formats émis par l'Arduino :

    Format 1 (CSV natif, AgroDrone_CSV.ino) :
        2000-01-01T00:00:05,1,,,,, 24.5,61.0,412,,,,78.3,

    Format 2 (texte lisible, code original) :
        ----- Nouvelles Données -----
        Température      : 24.5 °C
        Humidité         : 61.0 %
        Qualité de l'air : 312 / 1023
        Niveau d'eau     : 450 (Mouillé / Immergé)

    Retourne un dict avec les clés de COLUMNS, ou None si non parsable.
    """
    line = raw_line.strip()

    # Ignorer commentaires, en-têtes et lignes vides
    if not line or line.startswith("#") or line.startswith("=") or line.startswith("-"):
        return None
    if line == ",".join(COLUMNS):   # ligne header Arduino
        return None

    row = {c: "" for c in COLUMNS}
    row["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Format CSV (virgules) ────────────────────────────────────────────
    parts = line.split(",")
    if len(parts) >= 8:
        # Vérifier que la 2e colonne ressemble à une zone
        try:
            zone_val = parts[1].strip()
            # La 6e colonne devrait être air_temp (float)
            float(parts[6]) if parts[6].strip() else None
        except (ValueError, IndexError):
            pass  # pas le bon format, on essaie le format texte
        else:
            if forced_zone:
                row["zone"] = forced_zone
            else:
                row["zone"] = zone_val if zone_val else "1"

            col_map = {i: COLUMNS[i] for i in range(1, len(COLUMNS))}
            for idx, col in col_map.items():
                if idx < len(parts):
                    val = parts[idx].strip()
                    if val:
                        row[col] = val
            return row

    # ── Format texte lisible (code Arduino original) ─────────────────────
    text_values = {}
    line_lower = line.lower()

    if "température" in line_lower or "temperature" in line_lower:
        try:
            text_values["air_temp"] = float(line.split(":")[1].split("°")[0].strip())
        except Exception:
            pass
    elif "humidité" in line_lower or "humidity" in line_lower:
        try:
            text_values["air_hum"] = float(line.split(":")[1].split("%")[0].strip())
        except Exception:
            pass
    elif "qualité" in line_lower or "air" in line_lower:
        try:
            raw = float(line.split(":")[1].split("/")[0].strip())
            # Mapper 0–1023 → ppm CO₂ (approx. linéaire)
            co2 = max(350, min(5000, int(350 + (raw / 1023) * 4650)))
            text_values["air_co2"] = co2
        except Exception:
            pass
    elif "eau" in line_lower or "water" in line_lower or "niveau" in line_lower:
        try:
            raw = float(line.split(":")[1].split("(")[0].strip())
            pct = round((raw / 1023) * 100, 1)
            text_values["eau_niveau"] = pct
        except Exception:
            pass

    if text_values:
        row["zone"] = forced_zone or "1"
        row.update({k: str(v) for k, v in text_values.items()})
        # Format texte : on accumule les champs dans la même ligne ?
        # Non — chaque ligne texte donne une ligne CSV partielle.
        # Pour regrouper, utiliser AgroDrone_CSV.ino (format CSV natif).
        return row

    return None


# ── Accumulation des lignes texte en un enregistrement complet ───────────
class TextAccumulator:
    """
    Regroupe les 4 lignes du format texte Arduino en un seul enregistrement.
    (Seulement utile avec le code Arduino original non modifié.)
    """
    FIELDS = ("air_temp", "air_hum", "air_co2", "eau_niveau")

    def __init__(self, zone: str):
        self.zone   = zone
        self._data  = {}
        self._ready = False

    def feed(self, raw_line: str) -> dict | None:
        line = raw_line.strip().lower()
        val  = None

        if "température" in line or "temperature" in line:
            try:
                val = float(raw_line.split(":")[1].split("°")[0].strip())
                self._data["air_temp"] = val
            except Exception: pass

        elif "humidité" in line and "%" in raw_line:
            try:
                val = float(raw_line.split(":")[1].split("%")[0].strip())
                self._data["air_hum"] = val
            except Exception: pass

        elif "qualité" in line or ("air" in line and "/" in raw_line):
            try:
                raw = float(raw_line.split(":")[1].split("/")[0].strip())
                self._data["air_co2"] = int(350 + (raw / 1023) * 4650)
            except Exception: pass

        elif "eau" in line or "niveau" in line:
            try:
                raw = float(raw_line.split(":")[1].split("(")[0].strip())
                self._data["eau_niveau"] = round((raw / 1023) * 100, 1)
            except Exception: pass

        # Enregistrement complet quand on a les 4 champs
        if len(self._data) >= 4:
            row = {c: "" for c in COLUMNS}
            row["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row["zone"]      = self.zone
            row.update({k: str(v) for k, v in self._data.items()})
            self._data  = {}
            return row

        return None


# ── Boucle principale ─────────────────────────────────────────────────────
def run(port: str, baud: int, output: str, zone: str | None,
        append: bool, verbose: bool):
    try:
        import serial
    except ImportError:
        error("Module 'pyserial' manquant. Lancez : pip install pyserial")
        sys.exit(1)

    banner()

    # Initialisation CSV
    existed = init_csv(output, append)
    if existed:
        ok(f"Fichier existant — ajout des données : {output}")
    else:
        ok(f"Nouveau fichier CSV créé : {output}")

    # Ouverture du port série
    try:
        ser = serial.Serial(port, baud, timeout=2)
        ok(f"Port série ouvert : {port}  @ {baud} baud")
    except serial.SerialException as e:
        error(f"Impossible d'ouvrir {port} : {e}")
        sys.exit(1)

    info("En attente de données Arduino… (Ctrl+C pour arrêter)")
    print()

    accum     = TextAccumulator(zone or "1")
    count     = 0
    csv_mode  = None    # None=inconnu, True=CSV, False=texte

    with open(output, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")

        try:
            while True:
                raw = ser.readline()
                if not raw:
                    continue

                try:
                    line = raw.decode("utf-8", errors="replace").strip()
                except Exception:
                    continue

                if not line:
                    continue

                # Détecter le mode (CSV ou texte)
                if csv_mode is None:
                    parts = line.split(",")
                    csv_mode = len(parts) >= 8 and not line.startswith("#")

                if verbose:
                    print(f"{Clr.DIM}  ← {line}{Clr.RESET}")

                # Ignorer commentaires
                if line.startswith("#") or line.startswith("="):
                    if verbose:
                        info(line[1:].strip())
                    continue

                row = None

                if csv_mode:
                    row = parse_line(line, zone)
                else:
                    row = accum.feed(line)

                if row:
                    writer.writerow(row)
                    f.flush()
                    count += 1
                    ts   = row["timestamp"]
                    z    = row.get("zone", "?")
                    temp = row.get("air_temp", "—")
                    hum  = row.get("air_hum",  "—")
                    co2  = row.get("air_co2",  "—")
                    eau  = row.get("eau_niveau","—")
                    print(
                        f"  {Clr.GREEN}#{count:04d}{Clr.RESET}  "
                        f"{ts}  Zone {z}  "
                        f"T={Clr.YELLOW}{temp}°C{Clr.RESET}  "
                        f"H={Clr.CYAN}{hum}%{Clr.RESET}  "
                        f"CO₂={co2}ppm  "
                        f"Eau={eau}%"
                    )

        except KeyboardInterrupt:
            print()
            ok(f"Arrêt demandé. {count} enregistrement(s) sauvegardé(s) dans {output}")
        except serial.SerialException as e:
            error(f"Port série déconnecté : {e}")
        finally:
            ser.close()


# ── Point d'entrée ────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="ATLAS AgriSmart — Collecteur Série → CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--port",    default=None,
                        help="Port série (ex: COM3, /dev/ttyUSB0). Défaut : auto-détection")
    parser.add_argument("--baud",    type=int, default=9600,
                        help="Vitesse du port série (défaut : 9600)")
    parser.add_argument("--output",  default=r"C:\hackaton\csv\agri_data.csv",
                        help="Fichier CSV de sortie (défaut : agri_data.csv)")
    parser.add_argument("--zone",    default=None,
                        help="Forcer l'identifiant de zone (ex : 1, 2, A)")
    parser.add_argument("--append",  action="store_true",
                        help="Ajouter aux données existantes (défaut : écraser)")
    parser.add_argument("--verbose", action="store_true",
                        help="Afficher chaque ligne brute reçue")
    args = parser.parse_args()

    port = args.port
    if port is None:
        port = auto_detect_port()
        if port is None:
            error("Aucun port Arduino détecté automatiquement.")
            error("Spécifiez-le avec --port  (ex: --port COM3)")
            sys.exit(1)
        info(f"Port détecté automatiquement : {port}")

    run(
        port    = port,
        baud    = args.baud,
        output  = args.output,
        zone    = args.zone,
        append  = args.append,
        verbose = args.verbose,
    )


if __name__ == "__main__":
    main()
