#!/usr/bin/env python3
"""
ATLAS AgriSmart IoT Dashboard v2
Interface améliorée : thème ATLAS · Logo · Carte de zones interactive
"""

import customtkinter as ctk
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import filedialog, messagebox
import datetime
import os
import math

# ══════════════════════════════════════════════════════════════════════════════
# THÈME ATLAS  (vert forêt + bleu acier + fond quasi-noir)
# ══════════════════════════════════════════════════════════════════════════════
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

C = {
    "bg":        "#f0faf4",
    "bg2":       "#e6f5ec",
    "sidebar":   "#ffffff",
    "card":      "#ffffff",
    "card2":     "#edf7f1",
    "border":    "#b2dfc5",
    "border2":   "#7dc4a0",
    "green":     "#1a7a4a",
    "green_lt":  "#25a366",
    "green_dk":  "#145e38",
    "green_xdk": "#0d3f25",
    "blue":      "#0077b6",
    "blue_lt":   "#0096c7",
    "blue_dk":   "#005f8a",
    "amber":     "#ff9f43",
    "amber_dk":  "#f4a261",
    "red":       "#ff6b6b",
    "red_dk":    "#e63946",
# PAR :
    "txt":       "#0a0a0a",
    "txt2":      "#1a1a1a",
    "txt3":      "#333333",
    "txt4":      "#555555",
    # état zones carte
    "zone_ok":   "#25a366",
    "zone_warn": "#e07b00",
    "zone_crit": "#cc2936",
    "zone_sel":  "#0077b6",
}

# ══════════════════════════════════════════════════════════════════════════════
# SEUILS & UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════
THRESHOLDS = {
    "sol_hum":    {"ok": (35, 70),  "warn": (20, 80),   "label": "Humidité Sol",      "unit": "%"},
    "sol_temp":   {"ok": (15, 28),  "warn": (10, 32),   "label": "Temp. Sol",         "unit": "°C"},
    "sol_ph":     {"ok": (5.5,7.2), "warn": (5.0, 7.8), "label": "pH Sol",            "unit": ""},
    "sol_ec":     {"ok": (0.6,2.0), "warn": (0.4, 2.5), "label": "EC Sol",            "unit": "dS/m"},
    "air_temp":   {"ok": (15, 30),  "warn": (10, 35),   "label": "Temp. Air",         "unit": "°C"},
    "air_hum":    {"ok": (40, 70),  "warn": (30, 80),   "label": "Humidité Air",      "unit": "%"},
    "air_co2":    {"ok": (350,450), "warn": (300, 500), "label": "CO₂",               "unit": "ppm"},
    "air_vent":   {"ok": (2, 15),   "warn": (0, 20),    "label": "Vent",              "unit": "km/h"},
    "eau_ph":     {"ok": (6.5,7.5), "warn": (6.0, 8.0), "label": "pH Eau",            "unit": ""},
    "eau_turb":   {"ok": (0, 5),    "warn": (0, 10),    "label": "Turbidité",         "unit": "NTU"},
    "eau_niveau": {"ok": (40,100),  "warn": (20, 100),  "label": "Niveau Réservoir",  "unit": "%"},
    "eau_debit":  {"ok": (1, 5),    "warn": (0.5, 7),   "label": "Débit",             "unit": "L/min"},
}


def get_status(field, value):
    if field not in THRESHOLDS:
        return C["txt2"], "OK"
    t = THRESHOLDS[field]
    lo_ok, hi_ok = t["ok"]
    lo_w,  hi_w  = t["warn"]
    if lo_ok <= value <= hi_ok:
        return C["green"], "OK"
    if lo_w  <= value <= hi_w:
        return C["amber"], "ATTEN."
    return C["red"], "CRIT."


def zone_score(row):
    scores = []
    for f in THRESHOLDS:
        v = row.get(f)
        if v is not None:
            try:
                _, st = get_status(f, float(v))
                scores.append(1.0 if st == "OK" else 0.5 if st == "ATTEN." else 0.0)
            except Exception:
                pass
    return round(sum(scores) / len(scores) * 100) if scores else 50


def score_to_map_color(score):
    if score >= 70:
        return C["zone_ok"]
    if score >= 40:
        return C["zone_warn"]
    return C["zone_crit"]


# ══════════════════════════════════════════════════════════════════════════════
# GESTIONNAIRE DE DONNÉES
# ══════════════════════════════════════════════════════════════════════════════
class DataManager:
    def __init__(self):
        self.df = pd.DataFrame()

    def load(self, path):
        try:
            df = pd.read_csv(path)
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            self.df = df
            return True, ""
        except Exception as e:
            return False, str(e)

    def zones(self):
        if "zone" not in self.df.columns:
            return []
        return sorted(self.df["zone"].dropna().unique().tolist())

    def latest(self, zone):
        if self.df.empty or "zone" not in self.df.columns:
            return {}
        sub = self.df[self.df["zone"] == zone]
        if sub.empty:
            return {}
        if "timestamp" in sub.columns:
            sub = sub.sort_values("timestamp")
        return sub.iloc[-1].to_dict()

    def history(self, zone, col, n=24):
        if self.df.empty or col not in self.df.columns:
            return [], []
        sub = self.df[self.df["zone"] == zone].copy()
        if sub.empty:
            return [], []
        if "timestamp" in sub.columns:
            sub = sub.sort_values("timestamp").tail(n)
            labels = sub["timestamp"].dt.strftime("%Hh").tolist()
        else:
            sub = sub.tail(n)
            labels = [str(i) for i in range(len(sub))]
        return labels, sub[col].tolist()


dm = DataManager()


# ══════════════════════════════════════════════════════════════════════════════
# LOGO ATLAS (dessin Canvas)
# ══════════════════════════════════════════════════════════════════════════════
class AtlasLogo(tk.Canvas):
    """Logo ATLAS vectoriel — drone + terrain agricole + cercle."""

    def __init__(self, parent, size=120, **kwargs):
        super().__init__(parent, width=size, height=size + 30,
                         bg=C["sidebar"], highlightthickness=0, **kwargs)
        self.s = size
        self._draw()

    def _draw(self):
        s = self.s
        cx, cy = s // 2, s // 2 - 4
        r = s // 2 - 6

        # Cercle extérieur vert
        self.create_oval(cx - r, cy - r, cx + r, cy + r,
                         outline=C["green"], width=2, fill=C["bg2"])

        # Arc bleu supérieur (drone zone)
        arc_pad = 8
        self.create_arc(cx - r + arc_pad, cy - r + arc_pad,
                        cx + r - arc_pad, cy + r - arc_pad,
                        start=20, extent=140, outline=C["blue_lt"],
                        width=1.5, style="arc")

        # Corps drone
        dw, dh = 18, 6
        dx, dy = cx - dw // 2, cy - 20
        self.create_rectangle(dx, dy, dx + dw, dy + dh,
                               fill=C["blue"], outline="", width=0)
        # Bras drone
        for bx, by in [(-14, -2), (14, -2)]:
            self.create_line(cx, dy + 3, cx + bx, dy + by, fill=C["blue_lt"], width=2)
            # Rotor
            self.create_oval(cx + bx - 5, dy + by - 3, cx + bx + 5, dy + by + 3,
                             outline=C["blue_lt"], width=1, fill="")
        # Caméra drone
        self.create_rectangle(cx - 3, dy + dh, cx + 3, dy + dh + 5,
                               fill=C["txt3"], outline="")

        # Soleil (petit, haut-droite)
        sx, sy = cx + r - 18, cy - r + 16
        self.create_oval(sx - 5, sy - 5, sx + 5, sy + 5,
                         fill=C["amber"], outline="")
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            x1 = sx + 7 * math.cos(rad)
            y1 = sy + 7 * math.sin(rad)
            x2 = sx + 10 * math.cos(rad)
            y2 = sy + 10 * math.sin(rad)
            self.create_line(x1, y1, x2, y2, fill=C["amber"], width=1)

        # Terrain / montagnes (bas du cercle)
        horizon_y = cy + 4
        ground_pts = [
            cx - r + 4, cy + r - 4,
            cx - r + 4, horizon_y + 8,
            cx - 18, horizon_y - 6,
            cx - 6,  horizon_y + 2,
            cx + 4,  horizon_y - 14,
            cx + 16, horizon_y - 4,
            cx + r - 4, horizon_y + 6,
            cx + r - 4, cy + r - 4,
        ]
        self.create_polygon(*ground_pts, fill=C["green_xdk"], outline="")

        # Champs (lignes vertes dans la partie basse)
        for i in range(3):
            y_line = horizon_y + 8 + i * 6
            self.create_line(cx - r + 8, y_line, cx + r - 8, y_line,
                             fill=C["green_dk"], width=1)

        # Feuille (droite bas)
        lx, ly = cx + r - 20, cy + r - 20
        self.create_polygon(
            lx, ly, lx - 8, ly - 12, lx + 4, ly - 18, lx + 10, ly - 8,
            fill=C["green_lt"], outline="")

        # Texte ATLAS
        self.create_text(cx, s - 2, text="ATLAS",
                         font=("Arial", 14, "bold"), fill=C["blue_lt"])
        self.create_text(cx, s + 14, text="ATLAS voit, ATLAS agit",
                         font=("Arial", 7), fill=C["txt3"])


# ══════════════════════════════════════════════════════════════════════════════
# CARTE DES ZONES (canvas interactif)
# ══════════════════════════════════════════════════════════════════════════════
class ZoneMapWidget(tk.Canvas):
    """
    Grille de zones colorées selon leur score de santé.
    Clic sur une zone → callback(zone_id).
    """

    def __init__(self, parent, on_select, **kwargs):
        super().__init__(parent, bg=C["card"], highlightthickness=0, **kwargs)
        self.on_select = on_select
        self.selected  = None
        self.zone_rects = {}       # zone_id → rect_id
        self.bind("<Button-1>", self._click)
        self._empty_msg()

    def _empty_msg(self):
        self.delete("all")
        self.create_text(10, 10, anchor="nw",
                         text="Carte des zones\n(charger un CSV)",
                         font=("Arial", 9), fill=C["txt4"])

    def refresh(self, zones, selected=None):
        self.delete("all")
        self.zone_rects.clear()
        if not zones:
            self._empty_msg()
            return

        self.selected = selected
        n   = len(zones)
        cols = max(1, math.ceil(math.sqrt(n * 1.6)))
        rows = math.ceil(n / cols)

        w = self.winfo_width()  or 320
        h = self.winfo_height() or 200
        pad = 6
        cell_w = (w - pad * 2 - (cols - 1) * 4) // cols
        cell_h = (h - pad * 2 - (rows - 1) * 4) // rows

        for i, z in enumerate(zones):
            col_i = i % cols
            row_i = i // cols
            x1 = pad + col_i * (cell_w + 4)
            y1 = pad + row_i * (cell_h + 4)
            x2, y2 = x1 + cell_w, y1 + cell_h

            row    = dm.latest(z)
            score  = zone_score(row)
            color  = score_to_map_color(score)
            border = C["zone_sel"] if str(z) == str(selected) else "#000000"
            bw     = 3 if str(z) == str(selected) else 1

            rid = self.create_rectangle(x1, y1, x2, y2,
                                         fill=color, outline=border, width=bw)
            self.zone_rects[rid] = z

            # Label zone
            self.create_text((x1 + x2) // 2, (y1 + y2) // 2 - 8,
                              text=f"Z{z}", font=("Arial", 8, "bold"),
                              fill="#ffffff")
            # Score
            self.create_text((x1 + x2) // 2, (y1 + y2) // 2 + 7,
                              text=f"{score}", font=("Arial", 8),
                              fill="#ffffff")

        # Légende
        lx = pad
        ly = h - 14
        for lbl, col in [("OK", C["zone_ok"]), ("Attention", C["zone_warn"]), ("Critique", C["zone_crit"])]:
            self.create_rectangle(lx, ly, lx + 10, ly + 10, fill=col, outline="")
            self.create_text(lx + 14, ly + 5, anchor="w", text=lbl,
                             font=("Arial", 7), fill=C["txt3"])
            lx += 72

    def _click(self, event):
        for rid, z in self.zone_rects.items():
            x1, y1, x2, y2 = self.coords(rid)
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.on_select(z)
                return


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — TABLEAU DE BORD
# ══════════════════════════════════════════════════════════════════════════════
class PageDashboard(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=C["bg"], corner_radius=0)
        self.current_zone = None
        self._build()

    def _build(self):
        # Layout principal : gauche = carte + résumé ; droite = capteurs
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL,
                                    bg=C["bg"], sashwidth=4,
                                    sashrelief="flat", bd=0)
        self.paned.pack(fill="both", expand=True)

        # ── Colonne gauche ────────────────────────────────────────────────
        left = ctk.CTkFrame(self.paned, fg_color=C["bg"], corner_radius=0)
        self.paned.add(left, width=340, minsize=260)

        # Titre carte
        ctk.CTkLabel(left, text="CARTE DES ZONES",
                     font=("Arial", 9, "bold"), text_color=C["txt4"]).pack(
            anchor="w", padx=16, pady=(14, 4))

        map_frame = ctk.CTkFrame(left, fg_color=C["card"],
                                  corner_radius=10, border_width=1,
                                  border_color=C["border"])
        map_frame.pack(fill="x", padx=14, pady=(0, 8))
        map_frame.pack_propagate(False)
        map_frame.configure(height=210)

        self.zone_map = ZoneMapWidget(map_frame, on_select=self._select_zone)
        self.zone_map.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Indicateurs santé (cards compactes)
        ctk.CTkLabel(left, text="SANTÉ DES ZONES",
                     font=("Arial", 9, "bold"), text_color=C["txt4"]).pack(
            anchor="w", padx=16, pady=(4, 4))

        self.health_scroll = ctk.CTkScrollableFrame(
            left, fg_color=C["bg"], height=160,
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["border2"])
        self.health_scroll.pack(fill="x", padx=14, pady=(0, 8))

        # ── Colonne droite ────────────────────────────────────────────────
        right = ctk.CTkFrame(self.paned, fg_color=C["bg"], corner_radius=0)
        self.paned.add(right)

        # Barre onglets zones (droite)
        self.tabs_bar = ctk.CTkFrame(right, fg_color=C["bg2"], height=52)
        self.tabs_bar.pack(fill="x", pady=(0, 1))
        self.tabs_bar.pack_propagate(False)

        self.detail_scroll = ctk.CTkScrollableFrame(
            right, fg_color=C["bg"],
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["border2"])
        self.detail_scroll.pack(fill="both", expand=True, padx=18, pady=(10, 16))

    # ── Sélection zone ────────────────────────────────────────────────────
    def _select_zone(self, zone):
        self.current_zone = zone
        self._render_zone_detail(zone)
        self._render_tabs(zone)
        self.zone_map.refresh(dm.zones(), selected=zone)

    def render(self, zone=None):
        zones = dm.zones()
        selected = zone if zone in zones else (zones[0] if zones else None)
        self.current_zone = selected
        self.zone_map.refresh(zones, selected=selected)
        self._render_health()
        self._render_tabs(selected)

    def _render_health(self):
        for w in self.health_scroll.winfo_children():
            w.destroy()

        zones = dm.zones()
        if not zones:
            ctk.CTkLabel(self.health_scroll, text="Aucune donnée — chargez un CSV.",
                         font=("Arial", 11), text_color=C["txt4"]).pack(pady=20)
            return

        for z in zones:
            row    = dm.latest(z)
            score  = zone_score(row)
            color  = score_to_map_color(score)
            active = (str(z) == str(self.current_zone))

            card = ctk.CTkFrame(
                self.health_scroll, fg_color=C["card2"] if active else C["card"],
                corner_radius=8, border_width=2 if active else 1,
                border_color=C["blue_lt"] if active else color if score < 70 else C["border"],
                cursor="hand2"
            )
            card.pack(fill="x", pady=3)
            card.bind("<Button-1>", lambda e, _z=z: self._select_zone(_z))

            row_f = ctk.CTkFrame(card, fg_color="transparent")
            row_f.pack(fill="x", padx=10, pady=6)
            row_f.bind("<Button-1>", lambda e, _z=z: self._select_zone(_z))

            # Pastille couleur
            dot = tk.Canvas(row_f, width=10, height=10, bg=C["card2"] if active else C["card"],
                            highlightthickness=0)
            dot.create_oval(1, 1, 9, 9, fill=color, outline="")
            dot.pack(side="left", padx=(0, 8))

            ctk.CTkLabel(row_f, text=f"Zone {z}",
                         font=("Arial", 10, "bold" if active else "normal"),
                         text_color=C["blue_lt"] if active else C["txt2"]).pack(side="left")

            ctk.CTkProgressBar(row_f, height=6, width=80, corner_radius=3,
                                progress_color=color, fg_color=C["border"]).pack(
                side="left", padx=(8, 8))
            score_bar = ctk.CTkProgressBar(row_f, height=6, width=80,
                                            corner_radius=3, progress_color=color,
                                            fg_color=C["border"])
            score_bar.set(score / 100)
            score_bar.pack(side="left", padx=(0, 8))

            ctk.CTkLabel(row_f, text=f"{score}/100",
                         font=("Courier New", 9, "bold"), text_color=color).pack(side="left")

    def _render_tabs(self, zone=None):
        for w in self.tabs_bar.winfo_children():
            w.destroy()

        zones = dm.zones()
        if not zones:
            return

        if zone is None or zone not in zones:
            zone = zones[0]
        self.current_zone = zone

        ctk.CTkLabel(self.tabs_bar, text="ZONE :",
                     font=("Arial", 9, "bold"), text_color=C["txt3"]).pack(
            side="left", padx=(14, 8), pady=12)

        for z in zones:
            active = (str(z) == str(zone))
            ctk.CTkButton(
                self.tabs_bar, text=f"  Zone {z}  ", height=32, width=90,
                font=("Arial", 10, "bold" if active else "normal"),
                fg_color=C["green"] if active else C["card2"],
                hover_color=C["green_dk"] if active else C["border2"],
                text_color="#ffffff" if active else C["txt2"],
                border_width=2 if active else 1,
                border_color=C["green_lt"] if active else C["border"],
                corner_radius=7,
                command=lambda _z=z: self._select_zone(_z)
            ).pack(side="left", padx=3)

        self._render_zone_detail(zone)

    def _render_zone_detail(self, zone):
        for w in self.detail_scroll.winfo_children():
            w.destroy()

        row = dm.latest(zone)
        if not row:
            ctk.CTkLabel(self.detail_scroll, text=f"Aucune donnée pour la zone {zone}.",
                         text_color=C["txt4"]).pack(pady=40)
            return

        groups = [
            ("Sol",  ["sol_hum", "sol_temp", "sol_ph", "sol_ec"]),
            ("Air",  ["air_temp", "air_hum", "air_co2", "air_vent"]),
            ("Eau",  ["eau_ph", "eau_turb", "eau_niveau", "eau_debit"]),
        ]

        for g_name, fields in groups:
            # En-tête de groupe
            sec = ctk.CTkFrame(self.detail_scroll, fg_color="transparent", height=28)
            sec.pack(fill="x", pady=(14, 6))
            sec.pack_propagate(False)
            ctk.CTkLabel(sec, text=f"■  Capteurs {g_name}",
                         font=("Arial", 10, "bold"),
                         text_color=C["blue_lt"]).pack(side="left")
            ctk.CTkFrame(sec, fg_color=C["border"], height=1).pack(
                side="left", fill="x", expand=True, padx=(10, 0))

            grid_f = ctk.CTkFrame(self.detail_scroll, fg_color="transparent")
            grid_f.pack(fill="x")
            grid_f.grid_columnconfigure((0, 1, 2, 3), weight=1)

            for col_i, field in enumerate(fields):
                t     = THRESHOLDS.get(field, {})
                label = t.get("label", field)
                unit  = t.get("unit", "")
                val   = row.get(field)

                card = ctk.CTkFrame(grid_f, fg_color=C["card"], corner_radius=10,
                                    border_width=1, border_color=C["border"])
                card.grid(row=0, column=col_i, padx=5, pady=4, sticky="nsew")

                if val is not None:
                    try:
                        fval = float(val)
                        color, status = get_status(field, fval)
                        val_str = f"{fval:.1f}" if fval != int(fval) else str(int(fval))
                    except Exception:
                        val_str, color, status = str(val), C["txt3"], "---"
                else:
                    val_str, color, status = "---", C["txt4"], "N/A"

                # Barre colorée latérale
                ctk.CTkFrame(card, fg_color=color, width=4, corner_radius=2).pack(
                    side="left", fill="y")
                inner = ctk.CTkFrame(card, fg_color="transparent")
                inner.pack(fill="both", expand=True, padx=(8, 12), pady=10)

                ctk.CTkLabel(inner, text=label.upper(), font=("Arial", 7, "bold"),
                             text_color=C["txt4"]).pack(anchor="w")
                vf = ctk.CTkFrame(inner, fg_color="transparent")
                vf.pack(anchor="w", pady=(3, 0))
                ctk.CTkLabel(vf, text=val_str, font=("Courier New", 22, "bold"),
                             text_color=C["txt"]).pack(side="left")
                if unit:
                    ctk.CTkLabel(vf, text=f" {unit}", font=("Arial", 9),
                                 text_color=C["txt3"]).pack(side="left", pady=(10, 0))

                # Badge statut
                badge_bg = {
                    C["green"]: "#e0f5ea",
                    C["red"]:   "#ffe0e0",
                    C["red"]:   "#2e0808",
                }.get(color, C["card2"])
                badge_f = ctk.CTkFrame(inner, fg_color=badge_bg, corner_radius=4)
                badge_f.pack(anchor="w", pady=(4, 0))
                ctk.CTkLabel(badge_f, text=f"  {status}  ",
                             font=("Arial", 8, "bold"), text_color=color).pack(padx=2, pady=2)

        # ── Barres de progression "état du champ" ────────────────────────
        sec2 = ctk.CTkFrame(self.detail_scroll, fg_color="transparent", height=28)
        sec2.pack(fill="x", pady=(18, 8))
        sec2.pack_propagate(False)
        ctk.CTkLabel(sec2, text="■  ÉTAT DU CHAMP",
                     font=("Arial", 10, "bold"), text_color=C["blue_lt"]).pack(side="left")
        ctk.CTkFrame(sec2, fg_color=C["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(10, 0))

        for field, label in [
            ("sol_hum",    "Humidité Sol"),
            ("eau_niveau", "Niveau Eau"),
            ("air_hum",    "Humidité Air"),
            ("sol_ec",     "EC Sol"),
        ]:
            v = row.get(field)
            if v is None:
                continue
            try:
                fval  = float(v)
                color, _ = get_status(field, fval)
                hi    = THRESHOLDS[field]["ok"][1]
                pct   = min(1.0, max(0.0, fval / max(1, hi)))
                unit  = THRESHOLDS[field].get("unit", "")
                bf    = ctk.CTkFrame(self.detail_scroll, fg_color="transparent")
                bf.pack(fill="x", pady=5)
                ctk.CTkLabel(bf, text=label, font=("Arial", 11),
                             text_color=C["txt2"], width=150, anchor="w").pack(side="left")
                prog = ctk.CTkProgressBar(bf, height=8, corner_radius=4,
                                          progress_color=color, fg_color=C["card2"])
                prog.set(pct)
                prog.pack(side="left", fill="x", expand=True, padx=(8, 10))
                ctk.CTkLabel(bf, text=f"{fval:.1f}{unit}",
                             font=("Courier New", 10, "bold"),
                             text_color=color, width=70).pack(side="left")
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — GRAPHIQUES
# ══════════════════════════════════════════════════════════════════════════════
class PageGraphiques(ctk.CTkFrame):

    VARIABLES = {
        "sol_hum":    "Humidité Sol (%)",
        "sol_temp":   "Température Sol (°C)",
        "sol_ph":     "pH Sol",
        "sol_ec":     "EC Sol (dS/m)",
        "air_temp":   "Température Air (°C)",
        "air_hum":    "Humidité Air (%)",
        "air_co2":    "CO₂ (ppm)",
        "eau_niveau": "Niveau Réservoir (%)",
        "eau_debit":  "Débit Eau (L/min)",
    }

    def __init__(self, parent):
        super().__init__(parent, fg_color=C["bg"], corner_radius=0)
        self._canvas = None
        self._fig    = None
        self._build()

    def _build(self):
        ctrl = ctk.CTkFrame(self, fg_color=C["bg2"], height=56)
        ctrl.pack(fill="x", pady=(0, 1))
        ctrl.pack_propagate(False)

        ctk.CTkLabel(ctrl, text="Variable :", font=("Arial", 10),
                     text_color=C["txt2"]).pack(side="left", padx=(20, 4), pady=14)
        self.var_menu = ctk.CTkOptionMenu(
            ctrl, width=220, height=34, values=list(self.VARIABLES.values()),
            command=self._draw_chart, fg_color=C["card"],
            button_color=C["green"], button_hover_color=C["green_dk"],
            text_color="#0a0a0a", dropdown_fg_color="#ffffff",
            dropdown_text_color="#0a0a0a", dropdown_hover_color="#e0f5ea"
        )
        self.var_menu.set(list(self.VARIABLES.values())[0])
        self.var_menu.pack(side="left", padx=4)

        ctk.CTkLabel(ctrl, text="Zone :", font=("Arial", 10),
                     text_color=C["txt2"]).pack(side="left", padx=(20, 4))
        self.zone_menu = ctk.CTkOptionMenu(
            ctrl, width=120, height=34, values=["---"],
            command=self._draw_chart, fg_color=C["card"],
            button_color=C["green"], button_hover_color=C["green_dk"],
            text_color="#0a0a0a", dropdown_fg_color="#ffffff",
            dropdown_text_color="#0a0a0a", dropdown_hover_color="#e0f5ea"
        )
        self.zone_menu.pack(side="left", padx=4)

        ctk.CTkButton(ctrl, text="  Actualiser", width=130, height=34,
                      font=("Arial", 11), fg_color=C["card2"],
                      hover_color=C["border2"], border_width=1,
                      border_color=C["border"], corner_radius=7,
                      command=self._draw_chart).pack(side="right", padx=20)

        self.chart_area = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        self.chart_area.pack(fill="both", expand=True, padx=20, pady=16)

    def render(self, zone=None):
        zones = dm.zones()
        if zones:
            self.zone_menu.configure(values=zones)
            if zone and zone in zones:
                self.zone_menu.set(zone)
            elif self.zone_menu.get() not in zones:
                self.zone_menu.set(zones[0])
        self._draw_chart()

    def _get_field(self):
        lbl = self.var_menu.get()
        for k, v in self.VARIABLES.items():
            if v == lbl:
                return k
        return list(self.VARIABLES.keys())[0]

    def _draw_chart(self, _=None):
        if dm.df.empty:
            return
        zone  = self.zone_menu.get()
        field = self._get_field()
        t     = THRESHOLDS.get(field, {})
        unit  = t.get("unit", "")
        labels, values = dm.history(zone, field, n=24)
        if not values:
            return

        if self._canvas:
            self._canvas.get_tk_widget().destroy()
        if self._fig:
            plt.close(self._fig)
        for w in self.chart_area.winfo_children():
            w.destroy()

        fig = Figure(figsize=(11, 5.5), facecolor=C["bg2"])
        fig.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.13, hspace=0.5)

        ax1 = fig.add_subplot(2, 2, (1, 2))
        ax2 = fig.add_subplot(2, 2, 3)
        ax3 = fig.add_subplot(2, 2, 4)

        x      = list(range(len(values)))
        lo, hi = t.get("ok", (min(values), max(values)))

        # Courbe temporelle
        ax1.set_facecolor(C["card"])
        ax1.plot(x, values, color=C["green_lt"], linewidth=2,
                 marker="o", markersize=3.5, zorder=3)
        ax1.fill_between(x, values, alpha=0.15, color=C["green_lt"])
        ax1.axhspan(lo, hi, alpha=0.07, color=C["green"])
        ax1.axhline(lo, color=C["green"], lw=0.8, ls="--", alpha=0.5)
        ax1.axhline(hi, color=C["green"], lw=0.8, ls="--", alpha=0.5)
        title_txt = f"Zone {zone}  ·  {t.get('label', field)}"
        if unit:
            title_txt += f"  ({unit})"
        ax1.set_title(title_txt, color=C["txt"], fontsize=11, loc="left", pad=8)
        tick_step = max(1, len(labels) // 8)
        ax1.set_xticks(range(0, len(labels), tick_step))
        ax1.set_xticklabels([labels[i] for i in range(0, len(labels), tick_step)],
                             color=C["txt3"], fontsize=8)
        ax1.tick_params(colors=C["txt3"], labelsize=8)
        ax1.set_xlim(-0.5, len(values) - 0.5)
        for sp in ax1.spines.values():
            sp.set_color(C["border"])
        ax1.grid(axis="y", color=C["border"], lw=0.5)

        # Barres dernières mesures
        mv = values[-8:]
        ml = labels[-8:]
        bc = [get_status(field, v)[0] for v in mv]
        ax2.set_facecolor(C["card"])
        ax2.bar(range(len(mv)), mv, color=bc, width=0.6, alpha=0.88)
        ax2.set_xticks(range(len(ml)))
        ax2.set_xticklabels(ml, color=C["txt3"], fontsize=7.5)
        ax2.tick_params(colors=C["txt3"], labelsize=8)
        for sp in ax2.spines.values():
            sp.set_color(C["border"])
        ax2.grid(axis="y", color=C["border"], lw=0.5)
        ax2.set_title("Dernières mesures", color=C["txt2"], fontsize=9, loc="left", pad=6)

        # Comparaison zones
        zv, zn, zc = [], [], []
        for z in dm.zones():
            r = dm.latest(z)
            v = r.get(field)
            if v is not None:
                try:
                    fv = float(v)
                    zv.append(fv)
                    zn.append(f"Zone {z}")
                    zc.append(get_status(field, fv)[0])
                except Exception:
                    pass
        ax3.set_facecolor(C["card"])
        if zv:
            ax3.barh(range(len(zv)), zv, color=zc, alpha=0.88, height=0.55)
            ax3.set_yticks(range(len(zn)))
            ax3.set_yticklabels(zn, color=C["txt3"], fontsize=8)
            ax3.axvline(lo, color=C["green"], lw=0.8, ls="--", alpha=0.5)
            ax3.axvline(hi, color=C["green"], lw=0.8, ls="--", alpha=0.5)
        ax3.tick_params(colors=C["txt3"], labelsize=8)
        for sp in ax3.spines.values():
            sp.set_color(C["border"])
        ax3.grid(axis="x", color=C["border"], lw=0.5)
        ax3.set_title("Comparaison zones", color=C["txt2"], fontsize=9, loc="left", pad=6)

        self._fig    = fig
        self._canvas = FigureCanvasTkAgg(fig, master=self.chart_area)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill="both", expand=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — ALERTES
# ══════════════════════════════════════════════════════════════════════════════
class PageAlertes(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=C["bg"], corner_radius=0)
        self._build()

    def _build(self):
        self.counter_bar = ctk.CTkFrame(self, fg_color=C["bg2"], height=54)
        self.counter_bar.pack(fill="x", pady=(0, 1))
        self.counter_bar.pack_propagate(False)

        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color=C["bg"],
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["border2"])
        self.scroll.pack(fill="both", expand=True, padx=20, pady=12)

    def render(self, zone=None):
        for w in self.counter_bar.winfo_children():
            w.destroy()
        for w in self.scroll.winfo_children():
            w.destroy()

        zones = dm.zones()
        if not zones:
            ctk.CTkLabel(self.scroll, text="Chargez un fichier CSV pour voir les alertes.",
                         font=("Arial", 12), text_color=C["txt3"]).pack(pady=60)
            return

        all_alerts = []
        for z in zones:
            row    = dm.latest(z)
            alerts = self._compute_alerts(z, row)
            all_alerts.extend(alerts)

        crits = sum(1 for a in all_alerts if a["severity"] == "crit")
        warns = sum(1 for a in all_alerts if a["severity"] == "warn")
        oks   = sum(1 for a in all_alerts if a["severity"] == "ok")

        ctk.CTkLabel(self.counter_bar, text="RÉSUMÉ :",
                     font=("Arial", 9, "bold"), text_color=C["txt4"]).pack(
            side="left", padx=(20, 12), pady=14)

        for count, label, color, bg in [
            (crits, "Critique(s)", C["red"],   "#ffe0e0"),
            (warns, "Attention",   C["amber"],  "#fff0e0"),
            (oks,   "Normal",      C["green"],  "#e0f5ea"),
        ]:
            f = ctk.CTkFrame(self.counter_bar, fg_color=bg, corner_radius=6,
                             border_width=1, border_color=color)
            f.pack(side="left", padx=4, pady=10)
            ctk.CTkLabel(f, text=f"  {count}  {label}  ",
                         font=("Arial", 10, "bold"), text_color=color).pack(padx=4, pady=4)

        priority = {"crit": 0, "warn": 1, "ok": 2}
        all_alerts.sort(key=lambda a: (priority.get(a["severity"], 9), a["zone"]))

        for z in zones:
            zone_alerts = [a for a in all_alerts if a["zone"] == z]
            self._render_zone(z, zone_alerts)

    def _render_zone(self, zone, alerts):
        score = zone_score(dm.latest(zone))
        s_col = score_to_map_color(score)

        zh = ctk.CTkFrame(self.scroll, fg_color=C["card2"], corner_radius=8,
                          border_width=2, border_color=C["border"])
        zh.pack(fill="x", pady=(14, 4))
        ctk.CTkLabel(zh, text=f"  ▶  Zone {zone}",
                     font=("Arial", 12, "bold"), text_color=C["txt"]).pack(
            side="left", padx=14, pady=10)
        ctk.CTkLabel(zh, text=f"Score : {score}/100",
                     font=("Courier New", 10, "bold"), text_color=s_col).pack(
            side="right", padx=14)

        nok = [a for a in alerts if a["severity"] != "ok"]
        if not nok:
            card = ctk.CTkFrame(self.scroll, fg_color="#e0f5ea", corner_radius=8,
                                border_width=1, border_color=C["green"])
            card.pack(fill="x", padx=4, pady=3)
            ctk.CTkLabel(card, text="  ✓  Tous les capteurs dans la plage optimale.",
                         font=("Arial", 11), text_color=C["green_lt"]).pack(
                anchor="w", padx=16, pady=10)
        else:
            for a in nok:
                self._alert_card(a)

    def _alert_card(self, a):
        cfg = {
            "crit": {"bg": "#fff0f0", "border": C["red_dk"],  "icon": "⚠ CRITIQUE", "color": C["red"]},
            "warn": {"bg": "#fff8f0", "border": C["amber_dk"],"icon": "! ATTENTION", "color": C["amber"]},
        }
        s = cfg.get(a["severity"], cfg["warn"])

        card = ctk.CTkFrame(self.scroll, fg_color=s["bg"], corner_radius=8,
                            border_width=1, border_color=s["border"])
        card.pack(fill="x", padx=4, pady=3)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(top, text=f"{s['icon']}  {a['title']}",
                     font=("Arial", 11, "bold"), text_color=s["color"]).pack(side="left")
        ctk.CTkLabel(top, text=a.get("badge", ""),
                     font=("Courier New", 9), text_color=C["txt3"]).pack(side="right")

        ctk.CTkLabel(card, text=a["message"], font=("Arial", 10),
                     text_color=C["txt2"], wraplength=800, justify="left").pack(
            anchor="w", padx=16, pady=(0, 4))

        if a.get("action"):
            af = ctk.CTkFrame(card, fg_color=C["card"], corner_radius=4)
            af.pack(fill="x", padx=14, pady=(0, 10))
            ctk.CTkLabel(af, text=f"→  {a['action']}",
                         font=("Arial", 9), text_color=C["blue_lt"],
                         wraplength=800, justify="left").pack(anchor="w", padx=10, pady=5)

    def _compute_alerts(self, zone, row):
        alerts = []
        RULES = [
            ("sol_hum",    "Humidité Sol",
             "{:.0f}% — Stress hydrique sévère, risque de perte de rendement.",
             "{:.0f}% — Humidité insuffisante, irrigation recommandée.",
             "Activer l'irrigation. Durée estimée : 30–45 min."),
            ("sol_ph",     "pH Sol",
             "{:.1f} — Acidité excessive, absorption nutriments compromise.",
             "{:.1f} — pH hors plage (5.5–7.2), surveillance requise.",
             "Appliquer amendement calcaire. Recalibrer capteur sous 48h."),
            ("sol_ec",     "Conductivité Électrique",
             "{:.2f} dS/m — Carence en nutriments sévère.",
             "{:.2f} dS/m — Fertilisation recommandée.",
             "Ajouter engrais NPK dilué à l'eau d'irrigation."),
            ("air_temp",   "Température Air",
             "{:.1f}°C — Chaleur excessive, risque de brûlure foliaire.",
             "{:.1f}°C — Température élevée, surveiller les cultures.",
             "Activer la brumisation. Envisager un ombrage temporaire."),
            ("air_co2",    "Concentration CO₂",
             "{:.0f} ppm — Ventilation critique.",
             "{:.0f} ppm — CO₂ élevé, vérifier la ventilation.",
             "Ouvrir les ventilations. Inspecter la zone."),
            ("eau_niveau", "Niveau Réservoir",
             "{:.0f}% — Réservoir quasi-vide, rupture imminente.",
             "{:.0f}% — Niveau bas, planifier remplissage sous 24h.",
             "Déclencher la pompe d'appoint."),
            ("eau_turb",   "Turbidité Eau",
             "{:.1f} NTU — Eau très trouble, risque colmatage.",
             "{:.1f} NTU — Turbidité élevée, filtration recommandée.",
             "Nettoyer les filtres. Vérifier la source d'eau."),
        ]
        for field, title, msg_c, msg_w, action in RULES:
            v = row.get(field)
            if v is None:
                continue
            try:
                fval = float(v)
            except Exception:
                continue
            t    = THRESHOLDS.get(field, {})
            unit = t.get("unit", "")
            col, st = get_status(field, fval)
            sev  = {"OK": "ok", "ATTEN.": "warn", "CRIT.": "crit"}.get(st, "ok")
            msg  = (msg_c if sev == "crit" else msg_w if sev == "warn" else "")
            alerts.append({
                "zone": zone, "severity": sev, "title": title,
                "message": msg.format(fval) if msg else "",
                "action":  action if sev != "ok" else "",
                "badge":   f"{fval:.1f}{unit}",
            })
        return alerts


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════
class AtlasApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ATLAS AgriSmart — IoT Dashboard")
        self.geometry("1340x820")
        self.minsize(960, 640)
        self.configure(fg_color=C["bg"])
        self._active_page = None
        self._nav_btns    = {}
        self._build_layout()

        # Chargement automatique si agri_data.csv présent
        script_dir  = os.path.dirname(os.path.abspath(__file__))
        default_csv = os.path.join(script_dir, "agri_data.csv")
        if os.path.exists(default_csv):
            self.after(400, lambda: self._do_load(default_csv))

    # ── Mise en page ─────────────────────────────────────────────────────────
    def _build_layout(self):
        main = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        main.pack(fill="both", expand=True)
        self._build_sidebar(main)
        self._build_content_area(main)

    def _build_sidebar(self, parent):
        sb = ctk.CTkFrame(parent, fg_color=C["sidebar"], width=220, corner_radius=0)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        # ── Logo ATLAS ───────────────────────────────────────────────────
        logo_frame = ctk.CTkFrame(sb, fg_color=C["sidebar"], height=168)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)
        logo = AtlasLogo(logo_frame, size=120)
        logo.pack(expand=True, pady=(10, 4))

        # Séparateur
        ctk.CTkFrame(sb, fg_color=C["border"], height=1).pack(fill="x", padx=14, pady=6)

        # Horloge
        self.clock_lbl = ctk.CTkLabel(sb, text="", font=("Courier New", 10),
                                       text_color=C["txt4"])
        self.clock_lbl.pack(pady=(0, 8))
        self._tick()

        ctk.CTkFrame(sb, fg_color=C["border"], height=1).pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkLabel(sb, text="NAVIGATION", font=("Arial", 8, "bold"),
                     text_color=C["txt4"]).pack(anchor="w", padx=18, pady=(0, 6))

        nav_items = [
            ("dashboard",  "  ◉  Tableau de Bord"),
            ("graphiques", "  ◈  Graphiques"),
            ("alertes",    "  ◆  Alertes"),
        ]
        for page_id, label in nav_items:
            btn = ctk.CTkButton(
                sb, text=label, anchor="w", height=46,
                font=("Arial", 12),
                fg_color="transparent",
                hover_color=C["border2"],
                text_color=C["txt2"],
                corner_radius=8,
                command=lambda pid=page_id: self._show_page(pid)
            )
            btn.pack(fill="x", padx=10, pady=2)
            self._nav_btns[page_id] = btn

        # Espace flexible
        ctk.CTkFrame(sb, fg_color="transparent").pack(fill="both", expand=True)
        ctk.CTkFrame(sb, fg_color=C["border"], height=1).pack(fill="x", padx=14, pady=8)

        # Bouton CSV
        ctk.CTkButton(
            sb, text="  Charger CSV", height=42,
            font=("Arial", 11, "bold"), fg_color=C["green"],
            hover_color=C["green_dk"], corner_radius=8,
            command=self._load_csv
        ).pack(fill="x", padx=14, pady=(0, 6))

        self.file_lbl = ctk.CTkLabel(sb, text="Aucun fichier chargé",
                                      font=("Arial", 8), text_color=C["txt4"],
                                      wraplength=190)
        self.file_lbl.pack(padx=12, pady=(0, 18))

    def _build_content_area(self, parent):
        right = ctk.CTkFrame(parent, fg_color=C["bg"], corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        # Bandeau titre
        self.hdr_bar = ctk.CTkFrame(right, fg_color=C["card"], height=54, corner_radius=0)
        self.hdr_bar.pack(fill="x")
        self.hdr_bar.pack_propagate(False)

        # Trait bleu en haut du bandeau
        ctk.CTkFrame(self.hdr_bar, fg_color=C["blue"], height=2).pack(
            fill="x", side="top")

        hdr_inner = ctk.CTkFrame(self.hdr_bar, fg_color="transparent")
        hdr_inner.pack(fill="both", expand=True, padx=24)

        # Petit badge ATLAS
        ctk.CTkLabel(hdr_inner, text="ATLAS",
                     font=("Arial", 8, "bold"),
                     text_color=C["blue_lt"]).pack(side="left", padx=(0, 10), pady=14)
        ctk.CTkFrame(hdr_inner, fg_color=C["border"], width=1).pack(
            side="left", fill="y", pady=10)

        self.hdr_title = ctk.CTkLabel(hdr_inner, text="",
                                       font=("Arial", 14, "bold"), text_color=C["txt"])
        self.hdr_title.pack(side="left", padx=(14, 0))

        # Horloge dans le bandeau (droite)
        self.hdr_time = ctk.CTkLabel(hdr_inner, text="",
                                      font=("Courier New", 10), text_color=C["txt4"])
        self.hdr_time.pack(side="right")
        self._tick_hdr()

        # Conteneur pages
        self.page_container = ctk.CTkFrame(right, fg_color=C["bg"], corner_radius=0)
        self.page_container.pack(fill="both", expand=True)

        self.pages = {
            "dashboard":  PageDashboard(self.page_container),
            "graphiques": PageGraphiques(self.page_container),
            "alertes":    PageAlertes(self.page_container),
        }

        self._show_page("dashboard")

    # ── Navigation ───────────────────────────────────────────────────────────
    def _show_page(self, page_id):
        titles = {
            "dashboard":  "Tableau de Bord — Capteurs IoT",
            "graphiques": "Graphiques & Tendances",
            "alertes":    "Alertes & Recommandations",
        }

        for pid, btn in self._nav_btns.items():
            if pid == page_id:
                btn.configure(fg_color=C["border2"], text_color=C["blue_lt"],
                              font=("Arial", 12, "bold"))
            else:
                btn.configure(fg_color="transparent", text_color=C["txt2"],
                              font=("Arial", 12))

        for p in self.pages.values():
            p.pack_forget()

        self.hdr_title.configure(text=titles.get(page_id, ""))
        page = self.pages[page_id]
        page.pack(fill="both", expand=True)
        self._active_page = page_id

        if not dm.df.empty:
            zones = dm.zones()
            zone  = zones[0] if zones else None
            page.render(zone)

    # ── Horloges ─────────────────────────────────────────────────────────────
    def _tick(self):
        now = datetime.datetime.now().strftime("%d/%m/%Y\n%H:%M:%S")
        self.clock_lbl.configure(text=now)
        self.after(1000, self._tick)

    def _tick_hdr(self):
        now = datetime.datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
        self.hdr_time.configure(text=now)
        self.after(1000, self._tick_hdr)

    # ── CSV ──────────────────────────────────────────────────────────────────
    def _load_csv(self):
        path = filedialog.askopenfilename(
            title="Sélectionner le fichier de données IoT",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
        )
        if path:
            self._do_load(path)

    def _do_load(self, path):
        ok, err = dm.load(path)
        if not ok:
            messagebox.showerror("Erreur", f"Impossible de lire :\n{err}")
            return
        self.file_lbl.configure(text=os.path.basename(path))
        if self._active_page:
            self._show_page(self._active_page)


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = AtlasApp()
    app.mainloop()
