#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Andy Café Torréfacteur — Générateur d'Étiquettes v2.1
Aperçu | Historique | Batch presets | Résumé | File d'attente | Délai
"""

import sys
import os
import io
import json
import subprocess
import copy
import time
import tempfile
import threading
import platform
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import date, datetime

APP_DIR   = os.path.dirname(os.path.abspath(__file__))
CFG_PATH  = os.path.join(APP_DIR, "config_etiquettes.json")
LOG_PATH  = os.path.join(APP_DIR, "historique_impressions.json")
BATCH_DIR = os.path.join(APP_DIR, "batch_presets")
IS_WINDOWS = platform.system() == "Windows"


# ─────────────────────────────────────────────────────────────────────────────
# Dépendances
# ─────────────────────────────────────────────────────────────────────────────
def ensure_deps():
    import importlib.util
    needed = {
        "reportlab":  "reportlab",
        "pypdf":      "pypdf",
        "PIL":        "pillow",
        "tkcalendar": "tkcalendar",
        "pypdfium2":  "pypdfium2",
    }
    missing = [pkg for mod, pkg in needed.items() if importlib.util.find_spec(mod) is None]
    if not missing:
        return
    root = tk.Tk(); root.withdraw()
    ok = messagebox.askyesno(
        "Installation requise",
        f"Packages nécessaires : {', '.join(missing)}\n\nInstaller maintenant ?",
        parent=root,
    )
    root.destroy()
    if ok:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install"] + missing,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        messagebox.showinfo("✓ Succès", "Packages installés !\nRelancez l'application.")
    sys.exit(0)


ensure_deps()

from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter
from PIL import Image, ImageTk
from tkcalendar import DateEntry


# ─────────────────────────────────────────────────────────────────────────────
# Police Montserrat
# ─────────────────────────────────────────────────────────────────────────────
FONT_NAME = "Helvetica-Bold"


def load_montserrat():
    global FONT_NAME
    search_dirs = [APP_DIR, os.path.expanduser("~"), os.path.dirname(APP_DIR)]
    candidates = [
        ("Montserrat-SemiBold.ttf", "Montserrat-SemiBold"),
        ("Montserrat-Bold.ttf",     "Montserrat-Bold"),
        ("Montserrat-Regular.ttf",  "Montserrat"),
    ]
    for d in search_dirs:
        for fname, key in candidates:
            fp = os.path.join(d, fname)
            if not os.path.exists(fp):
                continue
            try:
                pdfmetrics.registerFont(TTFont(key, fp))
                FONT_NAME = key
                print(f"[Police] {key} chargée depuis {fp}")
                return
            except Exception as e:
                print(f"[Police] échec {fp} : {e}")


load_montserrat()


# ─────────────────────────────────────────────────────────────────────────────
# Données
# ─────────────────────────────────────────────────────────────────────────────
CAFES = [
    "Mélange Andy",
    "Mélange Espresso",
    "Colombie",
    "Éthiopie Guji",
    "Kenya AA",
    "Colombie Décaféiné",
    "Robusta",
    "Pink Bourbon",
    "Pastecoeurant",
    "Red Plum",
    "Lychee Peach",
]
FORMATS = ["200g", "400g", "900g", "5 lbs"]
NIVEAUX = ["Léger", "Médium Léger", "Brun", "Mi-Noir", "Noir"]
NIVEAUX_DEFAUT = {
    "Mélange Andy":       "Brun",
    "Mélange Espresso":   "Noir",
    "Colombie":           "Mi-Noir",
    "Éthiopie Guji":      "Médium Léger",
    "Kenya AA":           "Brun",
    "Colombie Décaféiné": "Brun",
    "Robusta":            "Mi-Noir",
    "Pink Bourbon":       "Léger",
    "Pastecoeurant":      "Léger",
    "Red Plum":           "Léger",
    "Lychee Peach":       "Léger",
}
PRINTER_NAME = "EPSON TM-C3500 Ver2"

FIELDS_STANDARD = {
    "niveau_torrefaction": {"enabled": True, "x": 155, "y": 137, "align": "left",   "font": "Helvetica-Bold", "size": 8, "color": "#000000"},
    "format_poids":        {"enabled": True, "x": 115, "y": 121, "align": "left",   "font": "Helvetica-Bold", "size": 8, "color": "#000000"},
    "date_torrefaction":   {"enabled": True, "x": 136, "y":  90, "align": "center", "font": "Helvetica-Bold", "size": 8, "color": "#000000"},
}

FIELDS_SPECIAL = {
    "niveau_torrefaction": {"enabled": True, "x": 155, "y": 80, "align": "left",   "font": "Helvetica-Bold", "size": 8, "color": "#000000"},
    "format_poids":        {"enabled": True, "x": 103, "y": 66, "align": "left",   "font": "Helvetica-Bold", "size": 8, "color": "#000000"},
    "date_torrefaction":   {"enabled": True, "x": 135, "y": 37, "align": "center", "font": "Helvetica-Bold", "size": 8, "color": "#000000"},
}

CAFES_SPECIAL = {"Pink Bourbon", "Robusta"}


def get_default_fields(cafe):
    if cafe in CAFES_SPECIAL:
        return copy.deepcopy(FIELDS_SPECIAL)
    return copy.deepcopy(FIELDS_STANDARD)


DEFAULT_FIELDS = FIELDS_STANDARD

DEFAULT_CFG = {
    "templates":       {cafe: "" for cafe in CAFES},
    "output_dir":      os.path.join(os.path.expanduser("~"), "Desktop", "Etiquettes_Andy"),
    "queue_dir":       os.path.join(os.path.expanduser("~"), "Dropbox", "Andy_Print_Queue"),
    "fields":          copy.deepcopy(DEFAULT_FIELDS),
    "fields_per_cafe": {cafe: get_default_fields(cafe) for cafe in CAFES_SPECIAL},
    "print_delay":     0,
    "scale_pct":       100,
}

_candidate_dirs = [
    os.path.join(os.path.expanduser("~"), "Documents", "new sticker"),
    os.path.join(os.path.expanduser("~"), "Documents", "andy-sticker"),
    APP_DIR,
]
STICKER_DIR = next((d for d in _candidate_dirs if os.path.isdir(d)), APP_DIR)

for cafe_key, fname in [
    ("Mélange Andy",       "MÉLANGE ANDY.pdf"),
    ("Mélange Espresso",   "MÉLANGE ESPRESSO.pdf"),
    ("Colombie",           "COLOMBIE.pdf"),
    ("Éthiopie Guji",      "Guji.pdf"),
    ("Kenya AA",           "KENYA.pdf"),
    ("Colombie Décaféiné", "Decaf.pdf"),
    ("Robusta",            "ROBUSTA.pdf"),
    ("Pink Bourbon",       "PINK BOURBON.pdf"),
    ("Pastecoeurant",      "pastecoeurant.pdf"),
    ("Red Plum",           "Red plum.pdf"),
    ("Lychee Peach",       "Lychee peach.pdf"),
]:
    DEFAULT_CFG["templates"][cafe_key] = os.path.join(STICKER_DIR, fname)

FIELD_LABELS = {
    "niveau_torrefaction": "Niveau de torréfaction",
    "format_poids":        "Format / Poids",
    "date_torrefaction":   "Date de torréfaction",
}

ALL_CAFES_KEY = "(tous les cafés)"


# ─────────────────────────────────────────────────────────────────────────────
# Persistance config
# ─────────────────────────────────────────────────────────────────────────────
def load_cfg():
    if os.path.exists(CFG_PATH):
        try:
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "template_pdf" in data and "templates" not in data:
                old_path = data.pop("template_pdf")
                data["templates"] = {c: "" for c in CAFES}
                data["templates"]["Mélange Andy"] = old_path
            data.setdefault("templates",       copy.deepcopy(DEFAULT_CFG["templates"]))
            data.setdefault("output_dir",      DEFAULT_CFG["output_dir"])
            data.setdefault("queue_dir",       DEFAULT_CFG["queue_dir"])
            data.setdefault("fields",          copy.deepcopy(DEFAULT_FIELDS))
            data.setdefault("print_delay",     0)
            data.setdefault("scale_pct",       100)
            data.setdefault("fields_per_cafe", {})
            for c in CAFES:
                data["templates"].setdefault(c, "")
            for fk, fv in DEFAULT_FIELDS.items():
                data["fields"].setdefault(fk, copy.deepcopy(fv))
            # Pré-remplir les positions spéciales si absentes
            for cafe in CAFES_SPECIAL:
                data["fields_per_cafe"].setdefault(cafe, get_default_fields(cafe))
            return data
        except Exception as e:
            print(f"[Config] erreur lecture : {e}")
    return copy.deepcopy(DEFAULT_CFG)


def save_cfg(cfg):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# Historique
# ─────────────────────────────────────────────────────────────────────────────
def load_log():
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def append_log(entries):
    log = load_log()
    log.extend(entries)
    log = log[-500:]
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# Batch presets
# ─────────────────────────────────────────────────────────────────────────────
def list_presets():
    os.makedirs(BATCH_DIR, exist_ok=True)
    return sorted(f[:-5] for f in os.listdir(BATCH_DIR) if f.endswith(".json"))


def load_preset(name):
    with open(os.path.join(BATCH_DIR, f"{name}.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def save_preset(name, data):
    os.makedirs(BATCH_DIR, exist_ok=True)
    with open(os.path.join(BATCH_DIR, f"{name}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def delete_preset(name):
    path = os.path.join(BATCH_DIR, f"{name}.json")
    if os.path.exists(path):
        os.remove(path)


# ─────────────────────────────────────────────────────────────────────────────
# Champs effectifs pour un café (per-cafe > global > defaults)
# ─────────────────────────────────────────────────────────────────────────────
def resolve_fields(cfg, cafe):
    cafe_fields = cfg.get("fields_per_cafe", {}).get(cafe, {})
    global_fields = cfg.get("fields", {})
    defaults = get_default_fields(cafe)
    resolved = {}
    for fk in FIELD_LABELS:
        if fk in cafe_fields:
            resolved[fk] = cafe_fields[fk]
        elif fk in global_fields:
            resolved[fk] = global_fields[fk]
        else:
            resolved[fk] = defaults[fk]
    return resolved


# ─────────────────────────────────────────────────────────────────────────────
# Génération PDF
# ─────────────────────────────────────────────────────────────────────────────
def generate_label(cfg, cafe, fmt, niveau, torr_date, copies=1, scale=1.0, out_path=None):
    template_path = cfg.get("templates", {}).get(cafe, "")
    page_w, page_h = 247.50, 186.75

    if not template_path:
        raise FileNotFoundError(f"Aucun template pour « {cafe} »\nVa dans ⚙️ Config.")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template introuvable :\n{template_path}")

    try:
        rdr = PdfReader(template_path)
        box = rdr.pages[0].mediabox
        page_w, page_h = float(box.width), float(box.height)
    except Exception:
        pass

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(page_w, page_h))
    field_data = {
        "niveau_torrefaction": niveau,
        "format_poids":        fmt,
        "date_torrefaction":   torr_date,
    }
    fields = resolve_fields(cfg, cafe)

    for fk, text in field_data.items():
        fd = fields.get(fk, {})
        if not fd.get("enabled", True):
            continue
        try:
            font = fd.get("font") or FONT_NAME
            try:
                c.setFont(font, int(fd.get("size", 8)))
            except Exception:
                c.setFont(FONT_NAME, int(fd.get("size", 8)))
            c.setFillColor(HexColor(fd.get("color", "#000000")))
            x, y = float(fd["x"]), float(fd["y"])
            if fd.get("align") == "center":
                c.drawCentredString(x, y, text)
            else:
                c.drawString(x, y, text)
        except Exception as e:
            print(f"[{fk}] {e}")
    c.save(); buf.seek(0)
    overlay = PdfReader(buf)

    writer = PdfWriter()
    for _ in range(copies):
        tmpl = PdfReader(template_path)
        pg = tmpl.pages[0]
        pg.merge_page(overlay.pages[0])
        if scale and scale != 1.0:
            pg.scale_by(scale)
        writer.add_page(pg)

    if out_path is None:
        out_dir = cfg.get("output_dir") or os.path.expanduser("~")
        os.makedirs(out_dir, exist_ok=True)
        safe = (cafe.replace(" ", "_").replace("/", "-").replace("—", "")
                    .encode("ascii", "ignore").decode().strip("_"))
        out_path = os.path.join(out_dir, f"etiquette_{safe}_{fmt}_{torr_date}.pdf")
    else:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    with open(out_path, "wb") as f:
        writer.write(f)
    return out_path


def generate_preview_image(cfg, cafe, fmt, niveau, torr_date):
    # Écrit dans un fichier temporaire pour ne pas polluer le dossier de sortie
    tmp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_pdf.close()
    try:
        generate_label(cfg, cafe, fmt, niveau, torr_date, copies=1, scale=1.0, out_path=tmp_pdf.name)
        # pypdfium2 = moteur PDF embarqué, aucun binaire externe à installer
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(tmp_pdf.name)
            page = pdf[0]
            # scale=2.2 → ~160 DPI sur une page de label standard
            pil = page.render(scale=2.2).to_pil()
            page.close()
            pdf.close()
            return pil
        except Exception as e:
            from PIL import ImageDraw
            img = Image.new("RGB", (280, 212), color="#f5ece0")
            d = ImageDraw.Draw(img)
            d.text((15, 80),
                   f"Aperçu indisponible\n{type(e).__name__}: {e}",
                   fill="#888")
            return img
    finally:
        try:
            os.unlink(tmp_pdf.name)
        except OSError:
            pass


def send_to_queue(cfg, cafe, fmt, niveau, torr_date, copies=1, scale=1.0):
    """Génère le PDF directement dans le dossier file d'attente (Dropbox/OneDrive)."""
    queue_dir = cfg.get("queue_dir") or ""
    if not queue_dir:
        raise RuntimeError("Dossier file d'attente non configuré — va dans ⚙️ Config.")
    os.makedirs(queue_dir, exist_ok=True)
    # Préfixe horodaté pour ordre chronologique + nom unique
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    safe = (cafe.replace(" ", "_").replace("/", "-").replace("—", "")
                .encode("ascii", "ignore").decode().strip("_"))
    name = f"{ts}__{safe}_{fmt}_x{copies}.pdf"
    out_path = os.path.join(queue_dir, name)
    return generate_label(cfg, cafe, fmt, niveau, torr_date, copies=copies,
                          scale=scale, out_path=out_path)


def open_or_print(path, do_print=False):
    """Ouvre ou imprime un PDF de manière portable."""
    try:
        if IS_WINDOWS:
            if do_print:
                os.startfile(path, "print")
            else:
                os.startfile(path)
        elif platform.system() == "Darwin":
            if do_print:
                subprocess.run(["lpr", path], check=False)
            else:
                subprocess.run(["open", path], check=False)
        else:
            if do_print:
                subprocess.run(["lpr", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
    except Exception as e:
        print(f"[Impression] {e}")
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Palette
# ─────────────────────────────────────────────────────────────────────────────
C_BROWN  = "#3d2008"
C_BROWN2 = "#6b3a1f"
C_CREAM  = "#fdf8f0"
C_LIGHT  = "#f0e6d5"
C_GOLD   = "#c8963e"
C_GRAY   = "#888888"
C_GREEN  = "#2d7a4f"
C_WHITE  = "#ffffff"
C_ORANGE = "#e67e22"
C_RED    = "#c0392b"


# ─────────────────────────────────────────────────────────────────────────────
# Application
# ─────────────────────────────────────────────────────────────────────────────
class EtiquetteApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.cfg = load_cfg()
        self.title("Andy Café — Étiquettes v2.1")
        self.resizable(False, False)
        self.configure(bg=C_CREAM)
        self._preview_img = None
        self._preview_pil = None
        self._zoom_level = 1.0
        self._preview_scale = 1.0
        self._img_offset_x = 0
        self._img_offset_y = 0
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._build_ui()
        self._center()

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _lbl(self, parent, text, bold=False, size=10, color=C_BROWN):
        font = ("Segoe UI", size, "bold") if bold else ("Segoe UI", size)
        return tk.Label(parent, text=text, font=font, bg=C_CREAM, fg=color, anchor="w")

    # ── UI ───────────────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr = tk.Frame(self, bg=C_BROWN)
        hdr.pack(fill="x")
        tk.Label(hdr, text="☕  Andy Café Torréfacteur",
                 font=("Georgia", 16, "bold"), bg=C_BROWN, fg=C_CREAM, pady=14).pack()
        tk.Label(hdr, text="Générateur d'Étiquettes v2.1",
                 font=("Georgia", 9, "italic"), bg=C_BROWN, fg=C_GOLD).pack(pady=(0, 12))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background=C_CREAM, borderwidth=0)
        style.configure("TNotebook.Tab", padding=[14, 7], font=("Segoe UI", 9))
        style.configure("green.Horizontal.TProgressbar",
                        troughcolor=C_LIGHT, background=C_GREEN, thickness=14)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

        self.tab_gen   = tk.Frame(self.nb, bg=C_CREAM)
        self.tab_batch = tk.Frame(self.nb, bg=C_CREAM, padx=16, pady=12)
        self.tab_hist  = tk.Frame(self.nb, bg=C_CREAM)
        self.tab_cfg   = tk.Frame(self.nb, bg=C_CREAM)

        self.nb.add(self.tab_gen,   text="  ✏️  Générer  ")
        self.nb.add(self.tab_batch, text="  📋  Batch  ")
        self.nb.add(self.tab_hist,  text="  📜  Historique  ")
        self.nb.add(self.tab_cfg,   text="  ⚙️  Config  ")

        self._build_gen()
        self._build_batch()
        self._build_hist()
        self._build_cfg()

    # ── Onglet Générer ───────────────────────────────────────────────────────
    def _build_gen(self):
        left  = tk.Frame(self.tab_gen, bg=C_CREAM, padx=24, pady=20)
        right = tk.Frame(self.tab_gen, bg=C_LIGHT, padx=16, pady=20)
        left.pack(side="left", fill="y")
        right.pack(side="left", fill="both", expand=True)

        p = left
        self._lbl(p, "☕  Café / Origine", bold=True).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self.var_cafe = tk.StringVar(value=CAFES[0])
        cb = ttk.Combobox(p, textvariable=self.var_cafe, values=CAFES, state="readonly",
                          width=28, font=("Segoe UI", 11))
        cb.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        cb.bind("<<ComboboxSelected>>", self._on_cafe_change)

        self.tmpl_status_var = tk.StringVar()
        self.tmpl_status_lbl = tk.Label(p, textvariable=self.tmpl_status_var,
                                        font=("Segoe UI", 8, "italic"), bg=C_CREAM, anchor="w")
        self.tmpl_status_lbl.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 12))
        self._update_tmpl_indicator()

        self._lbl(p, "⚖️  Format / Poids", bold=True).grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 6))
        self.var_format = tk.StringVar(value=FORMATS[0])
        self._fmt_frame = tk.Frame(p, bg=C_CREAM)
        self._fmt_frame.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 16))
        self._fmt_btns = {}
        for fmt in FORMATS:
            btn = tk.Radiobutton(
                self._fmt_frame, text=fmt, variable=self.var_format, value=fmt,
                indicatoron=False, bg=C_LIGHT, fg=C_BROWN2, selectcolor=C_BROWN,
                font=("Segoe UI", 10, "bold"), padx=10, pady=6, bd=0, relief="flat",
                cursor="hand2", width=5, command=self._refresh_fmt_btns,
            )
            btn.pack(side="left", padx=3)
            self._fmt_btns[fmt] = btn
        self._refresh_fmt_btns()

        self._lbl(p, "🌡️  Niveau de torréfaction", bold=True).grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self.var_niveau = tk.StringVar(value=NIVEAUX_DEFAUT.get(CAFES[0], NIVEAUX[2]))
        ttk.Combobox(p, textvariable=self.var_niveau, values=NIVEAUX, state="readonly",
                     width=18, font=("Segoe UI", 11)).grid(row=6, column=0, sticky="w", pady=(0, 16))

        self._lbl(p, "📅  Date de torréfaction", bold=True).grid(row=7, column=0, columnspan=2, sticky="w", pady=(0, 4))
        dr = tk.Frame(p, bg=C_CREAM)
        dr.grid(row=8, column=0, columnspan=2, sticky="w", pady=(0, 16))
        self.var_date = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self.date_entry = DateEntry(
            dr, textvariable=self.var_date,
            width=12, font=("Segoe UI", 11),
            date_pattern="yyyy-mm-dd",
            background=C_BROWN, foreground=C_WHITE,
            headersbackground=C_BROWN2, headersforeground=C_WHITE,
            selectbackground=C_GOLD, selectforeground=C_WHITE,
            normalbackground=C_CREAM, normalforeground=C_BROWN,
            weekendbackground=C_LIGHT, weekendforeground=C_BROWN,
            bordercolor=C_GOLD, cursor="hand2",
        )
        self.date_entry.pack(side="left", padx=(0, 8))
        tk.Button(dr, text="Aujourd'hui",
                  command=lambda: self.date_entry.set_date(date.today()),
                  bg=C_LIGHT, fg=C_BROWN2, font=("Segoe UI", 9),
                  relief="flat", padx=8, cursor="hand2").pack(side="left")

        self._lbl(p, "🖨️  Copies", bold=True).grid(row=9, column=0, columnspan=2, sticky="w", pady=(0, 4))
        sr = tk.Frame(p, bg=C_CREAM)
        sr.grid(row=10, column=0, columnspan=2, sticky="w", pady=(0, 18))
        self.var_copies = tk.IntVar(value=1)
        tk.Button(sr, text="−", command=lambda: self._adj(-1), bg=C_LIGHT, fg=C_BROWN2,
                  font=("Segoe UI", 13, "bold"), width=2, relief="flat", cursor="hand2").pack(side="left")
        tk.Label(sr, textvariable=self.var_copies, width=4, font=("Segoe UI", 14, "bold"),
                 bg=C_CREAM, fg=C_BROWN).pack(side="left")
        tk.Button(sr, text="+", command=lambda: self._adj(1), bg=C_LIGHT, fg=C_BROWN2,
                  font=("Segoe UI", 13, "bold"), width=2, relief="flat", cursor="hand2").pack(side="left")

        self._lbl(p, "🔍  Scale impression", bold=True).grid(row=11, column=0, columnspan=2, sticky="w", pady=(0, 4))
        scale_row = tk.Frame(p, bg=C_CREAM)
        scale_row.grid(row=12, column=0, columnspan=2, sticky="w", pady=(0, 14))
        self.var_scale = tk.IntVar(value=self.cfg.get("scale_pct", 100))
        tk.Button(scale_row, text="−", command=lambda: self._adj_scale(-5),
                  bg=C_LIGHT, fg=C_BROWN2, font=("Segoe UI", 11, "bold"),
                  width=2, relief="flat", cursor="hand2").pack(side="left")
        tk.Label(scale_row, textvariable=self.var_scale, width=4,
                 font=("Segoe UI", 13, "bold"), bg=C_CREAM, fg=C_BROWN).pack(side="left")
        tk.Label(scale_row, text="%", font=("Segoe UI", 10),
                 bg=C_CREAM, fg=C_BROWN).pack(side="left", padx=(0, 6))
        tk.Button(scale_row, text="+", command=lambda: self._adj_scale(5),
                  bg=C_LIGHT, fg=C_BROWN2, font=("Segoe UI", 11, "bold"),
                  width=2, relief="flat", cursor="hand2").pack(side="left")
        for preset_pct in (100, 125, 150):
            tk.Button(scale_row, text=f"{preset_pct}%",
                      command=lambda v=preset_pct: self.var_scale.set(v),
                      bg=C_LIGHT, fg=C_GRAY, font=("Segoe UI", 8),
                      relief="flat", padx=6, cursor="hand2").pack(side="left", padx=2)

        ttk.Separator(p, orient="horizontal").grid(row=13, column=0, columnspan=2, sticky="ew", pady=4)

        br = tk.Frame(p, bg=C_CREAM)
        br.grid(row=14, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        tk.Button(br, text="👁  Aperçu", command=self._do_preview,
                  bg=C_LIGHT, fg=C_BROWN2, font=("Segoe UI", 11, "bold"),
                  padx=10, pady=9, relief="flat", cursor="hand2").pack(side="left", padx=(0, 6))
        tk.Button(br, text="📄  Générer", command=self.do_generate,
                  bg=C_BROWN2, fg=C_WHITE, font=("Segoe UI", 11, "bold"),
                  padx=10, pady=9, relief="flat", cursor="hand2",
                  activebackground=C_BROWN).pack(side="left", padx=(0, 6))
        tk.Button(br, text="🖨️  Imprimer", command=self.do_print,
                  bg=C_GREEN, fg=C_WHITE, font=("Segoe UI", 11, "bold"),
                  padx=10, pady=9, relief="flat", cursor="hand2",
                  activebackground="#1a5c38").pack(side="left", padx=(0, 6))
        tk.Button(br, text="📡  Envoyer au café", command=self.do_send_to_queue,
                  bg=C_GOLD, fg=C_WHITE, font=("Segoe UI", 11, "bold"),
                  padx=10, pady=9, relief="flat", cursor="hand2",
                  activebackground="#a07020").pack(side="left")

        self.status_var = tk.StringVar(value="Prêt.")
        tk.Label(p, textvariable=self.status_var, font=("Segoe UI", 9, "italic"),
                 bg=C_CREAM, fg=C_GRAY, anchor="w").grid(row=15, column=0, columnspan=2, sticky="w", pady=(8, 0))
        p.grid_columnconfigure(0, weight=1)

        # ── Panneau aperçu ──
        tk.Label(right, text="👁  Aperçu étiquette", font=("Segoe UI", 10, "bold"),
                 bg=C_LIGHT, fg=C_BROWN).pack(pady=(0, 6))

        zoom_bar = tk.Frame(right, bg=C_LIGHT)
        zoom_bar.pack(pady=(0, 6))
        tk.Button(zoom_bar, text="−", command=self._zoom_out,
                  bg=C_LIGHT, fg=C_BROWN2, font=("Segoe UI", 11, "bold"),
                  width=2, relief="flat", cursor="hand2").pack(side="left", padx=2)
        self.zoom_var = tk.StringVar(value="100%")
        tk.Label(zoom_bar, textvariable=self.zoom_var, width=5,
                 font=("Segoe UI", 9), bg=C_LIGHT, fg=C_BROWN).pack(side="left")
        tk.Button(zoom_bar, text="+", command=self._zoom_in,
                  bg=C_LIGHT, fg=C_BROWN2, font=("Segoe UI", 11, "bold"),
                  width=2, relief="flat", cursor="hand2").pack(side="left", padx=2)
        tk.Button(zoom_bar, text="⊡", command=self._zoom_fit,
                  bg=C_LIGHT, fg=C_BROWN2, font=("Segoe UI", 10),
                  padx=6, relief="flat", cursor="hand2").pack(side="left", padx=(8, 0))

        self.preview_canvas = tk.Canvas(right, width=400, height=300,
                                        bg=C_WHITE, highlightthickness=1,
                                        highlightbackground="#ccc",
                                        cursor="crosshair")
        self.preview_canvas.pack()
        self.preview_canvas.create_text(200, 150,
                                        text="Clique sur 👁 Aperçu\npour voir l'étiquette",
                                        font=("Segoe UI", 9, "italic"),
                                        fill=C_GRAY, justify="center", tags="ph")

        self.preview_canvas.bind("<ButtonPress-1>", self._preview_drag_start)
        self.preview_canvas.bind("<B1-Motion>", self._preview_drag_move)

        self.preview_lbl = tk.Label(right, text="", font=("Segoe UI", 8, "italic"),
                                    bg=C_LIGHT, fg=C_GRAY)
        self.preview_lbl.pack(pady=(6, 0))

    # ── Onglet Batch ─────────────────────────────────────────────────────────
    def _build_batch(self):
        p = self.tab_batch
        ALL_FORMATS = FORMATS + ["Personnalisé"]

        top = tk.Frame(p, bg=C_CREAM)
        top.pack(fill="x", pady=(0, 8))
        tk.Label(top, text="📋  Impression en lot", font=("Segoe UI", 12, "bold"),
                 bg=C_CREAM, fg=C_BROWN).pack(side="left")

        pf = tk.Frame(top, bg=C_CREAM)
        pf.pack(side="right")
        tk.Label(pf, text="Session :", font=("Segoe UI", 9), bg=C_CREAM, fg=C_GRAY).pack(side="left", padx=(0, 4))
        self.preset_var = tk.StringVar()
        self.preset_cb = ttk.Combobox(pf, textvariable=self.preset_var,
                                      values=list_presets(), width=14, font=("Segoe UI", 9))
        self.preset_cb.pack(side="left", padx=(0, 4))
        tk.Button(pf, text="📂 Charger", command=self._load_preset,
                  bg=C_LIGHT, fg=C_BROWN2, font=("Segoe UI", 8),
                  relief="flat", padx=6, cursor="hand2").pack(side="left", padx=2)
        tk.Button(pf, text="💾 Sauver", command=self._save_preset,
                  bg=C_LIGHT, fg=C_BROWN2, font=("Segoe UI", 8),
                  relief="flat", padx=6, cursor="hand2").pack(side="left", padx=2)
        tk.Button(pf, text="🗑", command=self._delete_preset,
                  bg=C_LIGHT, fg=C_RED, font=("Segoe UI", 8),
                  relief="flat", padx=6, cursor="hand2").pack(side="left", padx=2)

        wrapper = tk.Frame(p, bg=C_CREAM)
        wrapper.pack(fill="both", expand=True)
        self.batch_canvas = tk.Canvas(wrapper, bg=C_CREAM, highlightthickness=0, height=280)
        vsb = ttk.Scrollbar(wrapper, orient="vertical", command=self.batch_canvas.yview)
        sf = tk.Frame(self.batch_canvas, bg=C_CREAM)
        sf.bind("<Configure>", lambda e: self.batch_canvas.configure(scrollregion=self.batch_canvas.bbox("all")))
        self.batch_canvas.create_window((0, 0), window=sf, anchor="nw")
        self.batch_canvas.configure(yscrollcommand=vsb.set)
        self.batch_canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._wire_mousewheel(self.batch_canvas)

        r = 0
        tk.Label(sf, text="Café", font=("Segoe UI", 9, "bold"),
                 bg=C_CREAM, fg=C_GRAY, anchor="w", width=24).grid(row=r, column=0, sticky="w", padx=6)
        for fi, fmt in enumerate(ALL_FORMATS):
            tk.Label(sf, text=fmt, font=("Segoe UI", 8, "bold"),
                     bg=C_CREAM, fg=C_GRAY, width=8, anchor="center").grid(row=r, column=1 + fi, padx=2)
        r += 1
        ttk.Separator(sf, orient="horizontal").grid(row=r, column=0, columnspan=8, sticky="ew", padx=4, pady=(0, 4))
        r += 1

        self.batch_rows = []
        for cafe in CAFES:
            fmt_copies = {fmt: tk.IntVar(value=0) for fmt in ALL_FORMATS}
            custom_poids = tk.StringVar(value="")
            tk.Label(sf, text=cafe, font=("Segoe UI", 9), bg=C_CREAM, fg=C_BROWN,
                     anchor="w", width=24).grid(row=r, column=0, sticky="w", padx=6, pady=3)
            for fi, fmt in enumerate(ALL_FORMATS):
                if fmt == "Personnalisé":
                    cell = tk.Frame(sf, bg=C_CREAM)
                    cell.grid(row=r, column=1 + fi, padx=2)
                    tk.Spinbox(cell, from_=0, to=500, textvariable=fmt_copies[fmt],
                               width=3, font=("Segoe UI", 8)).pack(side="left")
                    ttk.Entry(cell, textvariable=custom_poids,
                              width=5, font=("Segoe UI", 8)).pack(side="left", padx=(2, 0))
                else:
                    tk.Spinbox(sf, from_=0, to=500, textvariable=fmt_copies[fmt],
                               width=4, font=("Segoe UI", 9)).grid(row=r, column=1 + fi, padx=2)
            self.batch_rows.append({"cafe": cafe, "fmt_copies": fmt_copies, "custom_poids": custom_poids})
            r += 1

        ttk.Separator(p, orient="horizontal").pack(fill="x", pady=(6, 4))
        sel = tk.Frame(p, bg=C_CREAM)
        sel.pack(fill="x", pady=(0, 4))
        tk.Label(sel, text="Tout mettre à :", font=("Segoe UI", 9),
                 bg=C_CREAM, fg=C_GRAY).pack(side="left", padx=(0, 6))
        for qty in [1, 2, 3, 5]:
            tk.Button(sel, text=f"{qty}×", command=lambda q=qty: self._batch_set_all(q),
                      bg=C_LIGHT, fg=C_BROWN2, font=("Segoe UI", 8, "bold"),
                      relief="flat", padx=8, pady=3, cursor="hand2").pack(side="left", padx=2)
        tk.Button(sel, text="Remettre à 0", command=lambda: self._batch_set_all(0),
                  bg=C_LIGHT, fg=C_GRAY, font=("Segoe UI", 8),
                  relief="flat", padx=8, pady=3, cursor="hand2").pack(side="left", padx=(10, 0))

        bot = tk.Frame(p, bg=C_CREAM)
        bot.pack(fill="x", pady=(4, 6))
        tk.Label(bot, text="📅", font=("Segoe UI", 11), bg=C_CREAM, fg=C_BROWN).pack(side="left", padx=(0, 4))
        self.batch_date = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self.batch_date_entry = DateEntry(
            bot, textvariable=self.batch_date,
            width=12, font=("Segoe UI", 11),
            date_pattern="yyyy-mm-dd",
            background=C_BROWN, foreground=C_WHITE,
            headersbackground=C_BROWN2, headersforeground=C_WHITE,
            selectbackground=C_GOLD, selectforeground=C_WHITE,
            normalbackground=C_CREAM, normalforeground=C_BROWN,
            weekendbackground=C_LIGHT, weekendforeground=C_BROWN,
            bordercolor=C_GOLD, cursor="hand2",
        )
        self.batch_date_entry.pack(side="left", padx=(0, 6))
        tk.Button(bot, text="Aujourd'hui",
                  command=lambda: self.batch_date_entry.set_date(date.today()),
                  bg=C_LIGHT, fg=C_BROWN2, font=("Segoe UI", 9),
                  relief="flat", padx=8, cursor="hand2").pack(side="left", padx=(0, 20))
        tk.Label(bot, text="⏱ Délai :", font=("Segoe UI", 9), bg=C_CREAM, fg=C_GRAY).pack(side="left", padx=(0, 4))
        self.batch_delay = tk.DoubleVar(value=float(self.cfg.get("print_delay", 0)))
        ttk.Combobox(bot, textvariable=self.batch_delay,
                     values=[0, 0.5, 1, 1.5, 2, 3], width=5, font=("Segoe UI", 9)).pack(side="left", padx=(0, 4))
        tk.Label(bot, text="sec", font=("Segoe UI", 9), bg=C_CREAM, fg=C_GRAY).pack(side="left")

        act = tk.Frame(p, bg=C_CREAM)
        act.pack(fill="x", pady=(0, 4))
        tk.Button(act, text="📄  Générer tout", command=lambda: self._do_batch(False),
                  bg=C_BROWN2, fg=C_WHITE, font=("Segoe UI", 11, "bold"),
                  padx=14, pady=9, relief="flat", cursor="hand2",
                  activebackground=C_BROWN).pack(side="left", padx=(0, 8))
        tk.Button(act, text="🖨️  Imprimer tout", command=lambda: self._do_batch(True),
                  bg=C_GREEN, fg=C_WHITE, font=("Segoe UI", 11, "bold"),
                  padx=14, pady=9, relief="flat", cursor="hand2",
                  activebackground="#1a5c38").pack(side="left", padx=(0, 8))
        tk.Button(act, text="📡  Envoyer tout au café", command=self._do_batch_send,
                  bg=C_GOLD, fg=C_WHITE, font=("Segoe UI", 11, "bold"),
                  padx=14, pady=9, relief="flat", cursor="hand2",
                  activebackground="#a07020").pack(side="left")

        self.batch_progress = ttk.Progressbar(p, orient="horizontal", mode="determinate",
                                              length=560, style="green.Horizontal.TProgressbar")
        self.batch_progress.pack(fill="x", pady=(4, 2))
        self.batch_status = tk.StringVar(value="")
        tk.Label(p, textvariable=self.batch_status, font=("Segoe UI", 9, "italic"),
                 bg=C_CREAM, fg=C_GRAY, anchor="w").pack(fill="x")

    # ── Onglet Historique ────────────────────────────────────────────────────
    def _build_hist(self):
        p = self.tab_hist
        top = tk.Frame(p, bg=C_CREAM, padx=16, pady=12)
        top.pack(fill="x")
        tk.Label(top, text="📜  Historique des impressions",
                 font=("Segoe UI", 12, "bold"), bg=C_CREAM, fg=C_BROWN).pack(side="left")
        tk.Button(top, text="🔄  Rafraîchir", command=self._refresh_hist,
                  bg=C_LIGHT, fg=C_BROWN2, font=("Segoe UI", 9),
                  relief="flat", padx=10, cursor="hand2").pack(side="right")
        tk.Button(top, text="🗑  Vider", command=self._clear_hist,
                  bg=C_LIGHT, fg=C_RED, font=("Segoe UI", 9),
                  relief="flat", padx=10, cursor="hand2").pack(side="right", padx=(0, 6))

        cols = ("Date/Heure", "Café", "Format", "Copies", "Niveau")
        self.hist_tree = ttk.Treeview(p, columns=cols, show="headings", height=18)
        for col, w in zip(cols, [140, 200, 70, 60, 110]):
            self.hist_tree.heading(col, text=col)
            self.hist_tree.column(col, width=w, anchor="w")
        vsb = ttk.Scrollbar(p, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=vsb.set)
        self.hist_tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(0, 16))
        vsb.pack(side="right", fill="y", padx=(0, 8), pady=(0, 16))
        self._refresh_hist()

    # ── Onglet Config ────────────────────────────────────────────────────────
    def _build_cfg(self):
        p = self.tab_cfg
        self.cfg_canvas = tk.Canvas(p, bg=C_CREAM, highlightthickness=0, width=540, height=520)
        vsb = ttk.Scrollbar(p, orient="vertical", command=self.cfg_canvas.yview)
        sf = tk.Frame(self.cfg_canvas, bg=C_CREAM, padx=24, pady=18)
        sf.bind("<Configure>", lambda e: self.cfg_canvas.configure(scrollregion=self.cfg_canvas.bbox("all")))
        self.cfg_canvas.create_window((0, 0), window=sf, anchor="nw")
        self.cfg_canvas.configure(yscrollcommand=vsb.set)
        self.cfg_canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._wire_mousewheel(self.cfg_canvas)

        r = 0
        self._lbl(sf, "📁  Templates par café", bold=True, size=11).grid(row=r, column=0, columnspan=4, sticky="w")
        r += 1

        scan_row = tk.Frame(sf, bg=C_CREAM)
        scan_row.grid(row=r, column=0, columnspan=4, sticky="w", pady=(0, 8)); r += 1
        self._lbl(scan_row, "Dossier PDFs :", size=9, color=C_GRAY).pack(side="left", padx=(0, 6))
        self.scan_dir_var = tk.StringVar(value=STICKER_DIR)
        ttk.Entry(scan_row, textvariable=self.scan_dir_var, width=24, font=("Segoe UI", 8)).pack(side="left", padx=(0, 4))
        tk.Button(scan_row, text="📂", command=self._browse_scan_dir,
                  bg=C_LIGHT, fg=C_BROWN2, relief="flat", padx=6, cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(scan_row, text="🔍  Scan automatique", command=self._scan_templates,
                  bg=C_GOLD, fg=C_WHITE, font=("Segoe UI", 9, "bold"),
                  relief="flat", padx=10, pady=4, cursor="hand2",
                  activebackground="#a07020").pack(side="left")

        self.tmpl_vars = {}
        for cafe in CAFES:
            path = self.cfg.get("templates", {}).get(cafe, "")
            var = tk.StringVar(value=path)
            self.tmpl_vars[cafe] = var
            tk.Label(sf, text=cafe, font=("Segoe UI", 9, "bold"),
                     bg=C_CREAM, fg=C_BROWN, anchor="w", width=28).grid(row=r, column=0, sticky="w", pady=3)
            ttk.Entry(sf, textvariable=var, width=20, font=("Segoe UI", 8)).grid(row=r, column=1, padx=(4, 2), sticky="ew")
            ind = tk.Label(sf, font=("Segoe UI", 9), bg=C_CREAM, width=2)
            ind.grid(row=r, column=2, padx=(0, 2))
            self._refresh_tmpl_ind(var, ind)
            var.trace_add("write", lambda *a, v=var, i=ind: self._refresh_tmpl_ind(v, i))
            tk.Button(sf, text="📂",
                      command=lambda c=cafe, v=var, i=ind: self._browse_cafe_tmpl(c, v, i),
                      bg=C_LIGHT, fg=C_BROWN2, font=("Segoe UI", 9),
                      relief="flat", padx=6, cursor="hand2").grid(row=r, column=3)
            r += 1

        ttk.Separator(sf, orient="horizontal").grid(row=r, column=0, columnspan=4, sticky="ew", pady=(8, 8)); r += 1

        self._lbl(sf, "📂  Dossier de sortie", bold=True, size=11).grid(row=r, column=0, columnspan=4, sticky="w", pady=(0, 4)); r += 1
        self.var_outdir = tk.StringVar(value=self.cfg.get("output_dir", ""))
        ttk.Entry(sf, textvariable=self.var_outdir, width=32).grid(row=r, column=0, columnspan=3, sticky="ew", padx=(0, 4))
        tk.Button(sf, text="📂", command=self._browse_outdir,
                  bg=C_LIGHT, fg=C_BROWN2, relief="flat", padx=6, cursor="hand2").grid(row=r, column=3)
        r += 1

        self._lbl(sf, "📡  File d'attente du café (dossier synchronisé Dropbox/OneDrive)",
                  bold=True, size=11).grid(row=r, column=0, columnspan=4, sticky="w", pady=(8, 4)); r += 1
        self.var_queuedir = tk.StringVar(value=self.cfg.get("queue_dir", ""))
        ttk.Entry(sf, textvariable=self.var_queuedir, width=32).grid(row=r, column=0, columnspan=3, sticky="ew", padx=(0, 4))
        tk.Button(sf, text="📂", command=self._browse_queuedir,
                  bg=C_LIGHT, fg=C_BROWN2, relief="flat", padx=6, cursor="hand2").grid(row=r, column=3)
        r += 1

        ttk.Separator(sf, orient="horizontal").grid(row=r, column=0, columnspan=4, sticky="ew", pady=(8, 8)); r += 1

        # ── Sélecteur de café pour les positions ──
        self._lbl(sf, "📍  Positions des champs", bold=True, size=11).grid(row=r, column=0, columnspan=4, sticky="w"); r += 1
        self._lbl(sf, "Coordonnées en points PDF  |  ↑ Y = monte  |  0,0 = bas-gauche",
                  size=8, color=C_GRAY).grid(row=r, column=0, columnspan=4, sticky="w", pady=(0, 8)); r += 1

        cafe_sel_row = tk.Frame(sf, bg=C_CREAM)
        cafe_sel_row.grid(row=r, column=0, columnspan=4, sticky="w", pady=(0, 8)); r += 1
        self._lbl(cafe_sel_row, "Éditer pour :", size=9, color=C_GRAY).pack(side="left", padx=(0, 6))
        self.cfg_cafe_var = tk.StringVar(value=ALL_CAFES_KEY)
        cfg_cafe_cb = ttk.Combobox(
            cafe_sel_row, textvariable=self.cfg_cafe_var,
            values=[ALL_CAFES_KEY] + CAFES, state="readonly",
            width=24, font=("Segoe UI", 9),
        )
        cfg_cafe_cb.pack(side="left")
        cfg_cafe_cb.bind("<<ComboboxSelected>>", self._on_cfg_cafe_change)

        for col, (txt, w) in enumerate([("Champ", 22), ("X", 6), ("Y", 6), ("Taille", 6), ("Police", 14), ("✓", 3)]):
            tk.Label(sf, text=txt, font=("Segoe UI", 9, "bold"),
                     bg=C_CREAM, fg=C_GRAY, width=w, anchor="w").grid(row=r, column=col, padx=3, pady=(0, 4))
        r += 1
        ttk.Separator(sf, orient="horizontal").grid(row=r, column=0, columnspan=6, sticky="ew", pady=(0, 6)); r += 1

        self.fvars = {}
        for fk, flabel in FIELD_LABELS.items():
            fd = self.cfg["fields"].get(fk, DEFAULT_FIELDS.get(fk, {}))
            vx = tk.IntVar(value=fd.get("x", 100))
            vy = tk.IntVar(value=fd.get("y", 50))
            vsz = tk.IntVar(value=fd.get("size", 8))
            vfn = tk.StringVar(value=fd.get("font", "Helvetica-Bold"))
            von = tk.BooleanVar(value=fd.get("enabled", True))
            self.fvars[fk] = {"x": vx, "y": vy, "size": vsz, "font": vfn, "enabled": von}
            tk.Label(sf, text=flabel, font=("Segoe UI", 9), bg=C_CREAM, fg=C_BROWN,
                     anchor="w", width=22).grid(row=r, column=0, pady=4, sticky="w")
            ttk.Spinbox(sf, from_=0, to=2000, textvariable=vx, width=6).grid(row=r, column=1, padx=3)
            ttk.Spinbox(sf, from_=0, to=2000, textvariable=vy, width=6).grid(row=r, column=2, padx=3)
            ttk.Spinbox(sf, from_=5, to=72, textvariable=vsz, width=5).grid(row=r, column=3, padx=3)
            ttk.Combobox(sf, textvariable=vfn,
                         values=["Helvetica", "Helvetica-Bold", "Times-Roman", "Times-Bold"],
                         state="readonly", width=14).grid(row=r, column=4, padx=3)
            tk.Checkbutton(sf, variable=von, bg=C_CREAM).grid(row=r, column=5, padx=6)
            r += 1

        tk.Button(sf, text="💾  Sauvegarder", command=self._save_cfg,
                  bg=C_BROWN, fg=C_WHITE, font=("Segoe UI", 11, "bold"),
                  padx=16, pady=10, relief="flat", cursor="hand2",
                  activebackground=C_BROWN2).grid(row=r, column=0, columnspan=6, sticky="ew", pady=(12, 4))
        r += 1
        tk.Button(sf, text="🔄  Positions par défaut", command=self._reset_cfg,
                  bg=C_LIGHT, fg=C_GRAY, font=("Segoe UI", 9),
                  padx=8, pady=6, relief="flat", cursor="hand2").grid(row=r, column=0, columnspan=6, sticky="ew", pady=(0, 16))

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _wire_mousewheel(self, canvas):
        """Lie la molette de la souris à un canvas uniquement quand il a le focus."""
        def on_wheel(e):
            delta = -1 * (e.delta // 120) if e.delta else (1 if e.num == 5 else -1)
            canvas.yview_scroll(delta, "units")
        canvas.bind("<Enter>", lambda e: (canvas.bind_all("<MouseWheel>", on_wheel),
                                           canvas.bind_all("<Button-4>", on_wheel),
                                           canvas.bind_all("<Button-5>", on_wheel)))
        canvas.bind("<Leave>", lambda e: (canvas.unbind_all("<MouseWheel>"),
                                           canvas.unbind_all("<Button-4>"),
                                           canvas.unbind_all("<Button-5>")))

    def _on_cafe_change(self, *_):
        self._update_tmpl_indicator()
        cafe = self.var_cafe.get()
        if cafe in NIVEAUX_DEFAUT:
            self.var_niveau.set(NIVEAUX_DEFAUT[cafe])

    def _update_tmpl_indicator(self):
        cafe = self.var_cafe.get()
        path = self.cfg.get("templates", {}).get(cafe, "")
        if path and os.path.exists(path):
            self.tmpl_status_var.set(f"✅  {os.path.basename(path)}")
            self.tmpl_status_lbl.configure(fg=C_GREEN)
        elif path:
            self.tmpl_status_var.set("⚠️  Fichier introuvable")
            self.tmpl_status_lbl.configure(fg=C_ORANGE)
        else:
            self.tmpl_status_var.set("⚠️  Aucun template — assigne dans ⚙️ Config")
            self.tmpl_status_lbl.configure(fg=C_ORANGE)

    def _refresh_fmt_btns(self):
        for fmt, btn in self._fmt_btns.items():
            selected = self.var_format.get() == fmt
            btn.configure(bg=C_BROWN if selected else C_LIGHT,
                          fg=C_WHITE if selected else C_BROWN2)

    def _adj(self, delta):
        self.var_copies.set(max(1, min(500, self.var_copies.get() + delta)))

    def _adj_scale(self, delta):
        self.var_scale.set(max(50, min(300, self.var_scale.get() + delta)))

    def _refresh_tmpl_ind(self, var, ind):
        path = var.get()
        if path and os.path.exists(path):
            ind.configure(text="✅", fg=C_GREEN)
        elif path:
            ind.configure(text="⚠️", fg=C_ORANGE)
        else:
            ind.configure(text="—", fg=C_GRAY)

    def _browse_cafe_tmpl(self, cafe, var, ind):
        path = filedialog.askopenfilename(
            title=f"Template PDF — {cafe}",
            filetypes=[("PDF", "*.pdf"), ("Tous", "*.*")],
        )
        if path:
            var.set(path)
            self._refresh_tmpl_ind(var, ind)

    def _browse_outdir(self):
        path = filedialog.askdirectory(title="Dossier de sauvegarde")
        if path:
            self.var_outdir.set(path)

    def _browse_queuedir(self):
        path = filedialog.askdirectory(title="Dossier file d'attente du café (synchronisé)")
        if path:
            self.var_queuedir.set(path)

    def _browse_scan_dir(self):
        path = filedialog.askdirectory(title="Dossier contenant les PDFs")
        if path:
            self.scan_dir_var.set(path)

    def _scan_templates(self):
        scan_dir = self.scan_dir_var.get()
        if not os.path.isdir(scan_dir):
            messagebox.showerror("Introuvable", f"Dossier introuvable :\n{scan_dir}", parent=self)
            return

        pdfs = {f.lower(): os.path.join(scan_dir, f)
                for f in os.listdir(scan_dir) if f.lower().endswith(".pdf")}

        keywords = {
            "Mélange Andy":       ["melange andy", "mélange andy"],
            "Mélange Espresso":   ["melange espresso", "mélange espresso", "espresso"],
            "Colombie":           ["colombie", "colombia"],
            "Éthiopie Guji":      ["guji"],
            "Kenya AA":           ["kenya"],
            "Colombie Décaféiné": ["decaf", "décaf"],
            "Robusta":            ["robusta"],
            "Pink Bourbon":       ["pink bourbon", "pink_bourbon"],
            "Pastecoeurant":      ["pastec", "pastecoeurant"],
            "Red Plum":           ["red plum", "red_plum"],
            "Lychee Peach":       ["lychee", "litchi"],
        }

        # Trier par spécificité (mot-clé le plus long en premier) pour éviter qu'un
        # café générique (« colombie ») mange un café plus spécifique (« colombie décaféiné »).
        ordered = sorted(keywords.items(), key=lambda kv: -max(len(k) for k in kv[1]))
        assigned = set()
        found = 0
        for cafe, keys in ordered:
            for pdf_lower, pdf_path in pdfs.items():
                if pdf_path in assigned:
                    continue
                if any(k in pdf_lower for k in keys):
                    self.tmpl_vars[cafe].set(pdf_path)
                    assigned.add(pdf_path)
                    found += 1
                    break

        messagebox.showinfo(
            "✅ Scan terminé",
            f"{found} template(s) trouvé(s) sur {len(CAFES)} cafés.\n\n"
            "Clique 💾 Sauvegarder pour confirmer.",
            parent=self,
        )

    def _on_cfg_cafe_change(self, *_):
        cafe = self.cfg_cafe_var.get()
        if cafe == ALL_CAFES_KEY:
            fields = self.cfg["fields"]
        else:
            fields = self.cfg.get("fields_per_cafe", {}).get(cafe) or get_default_fields(cafe)
        for fk, fv in self.fvars.items():
            fd = fields.get(fk, DEFAULT_FIELDS.get(fk, {}))
            fv["x"].set(fd.get("x", 100))
            fv["y"].set(fd.get("y", 50))
            fv["size"].set(fd.get("size", 8))
            fv["font"].set(fd.get("font", "Helvetica-Bold"))
            fv["enabled"].set(fd.get("enabled", True))

    def _reset_to_cafe_defaults(self):
        cafe = self.cfg_cafe_var.get()
        defaults = DEFAULT_FIELDS if cafe == ALL_CAFES_KEY else get_default_fields(cafe)
        for fk, fv in self.fvars.items():
            d = defaults.get(fk, {})
            fv["x"].set(d.get("x", 100))
            fv["y"].set(d.get("y", 50))
            fv["size"].set(d.get("size", 8))
            fv["font"].set(d.get("font", "Helvetica-Bold"))
            fv["enabled"].set(d.get("enabled", True))

    def _save_cfg(self):
        self.cfg["output_dir"] = self.var_outdir.get()
        self.cfg["queue_dir"]  = self.var_queuedir.get()
        self.cfg.setdefault("templates", {})
        for cafe, var in self.tmpl_vars.items():
            self.cfg["templates"][cafe] = var.get()

        current_fields = {}
        for fk, fv in self.fvars.items():
            base = DEFAULT_FIELDS.get(fk, {})
            current_fields[fk] = {
                "x":       int(fv["x"].get()),
                "y":       int(fv["y"].get()),
                "size":    int(fv["size"].get()),
                "font":    fv["font"].get(),
                "enabled": bool(fv["enabled"].get()),
                "align":   base.get("align", "left"),
                "color":   base.get("color", "#000000"),
            }

        cafe = self.cfg_cafe_var.get()
        if cafe == ALL_CAFES_KEY:
            self.cfg["fields"] = current_fields
        else:
            self.cfg.setdefault("fields_per_cafe", {})[cafe] = current_fields

        self.cfg["scale_pct"] = self.var_scale.get()
        save_cfg(self.cfg)
        self._update_tmpl_indicator()
        lbl = "globale" if cafe == ALL_CAFES_KEY else f"pour « {cafe} »"
        messagebox.showinfo("✓", f"Configuration {lbl} sauvegardée !", parent=self)

    def _reset_cfg(self):
        if messagebox.askyesno("Réinitialiser", "Remettre les positions par défaut ?", parent=self):
            self._reset_to_cafe_defaults()

    # ── Aperçu ───────────────────────────────────────────────────────────────
    def _do_preview(self):
        self.preview_lbl.configure(text="⏳ Génération…", fg=C_GRAY)
        self.update()

        def run():
            try:
                img = generate_preview_image(
                    self.cfg, self.var_cafe.get(), self.var_format.get(),
                    self.var_niveau.get(), self.var_date.get(),
                )
                self._preview_pil = img
                self._preview_scale = self.var_scale.get() / 100.0
                self._zoom_level = 1.0
                self._img_offset_x = 0
                self._img_offset_y = 0
                self.after(0, self._render_preview)
                self.after(0, lambda: self.preview_lbl.configure(
                    text=f"✅ Aperçu à {self.var_scale.get()}% d'impression", fg=C_GREEN))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: self.preview_lbl.configure(text=f"✗ {err}", fg=C_RED))

        threading.Thread(target=run, daemon=True).start()

    def _render_preview(self):
        if self._preview_pil is None:
            return
        cw, ch = 400, 300
        REF_W, REF_H = 300, 226
        ps = self._preview_scale
        display_w = max(1, int(REF_W * ps * self._zoom_level))
        display_h = max(1, int(REF_H * ps * self._zoom_level))

        img = self._preview_pil.resize((display_w, display_h), Image.LANCZOS)
        self._preview_img = ImageTk.PhotoImage(img)
        self.zoom_var.set(f"{int(self._zoom_level * 100)}%")

        if display_w <= cw and display_h <= ch:
            self._img_offset_x = (cw - display_w) // 2
            self._img_offset_y = (ch - display_h) // 2

        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(self._img_offset_x, self._img_offset_y,
                                         anchor="nw", image=self._preview_img)

    def _zoom_in(self):
        self._zoom_level = min(4.0, round(self._zoom_level + 0.25, 2))
        self._render_preview()

    def _zoom_out(self):
        self._zoom_level = max(0.25, round(self._zoom_level - 0.25, 2))
        self._render_preview()

    def _zoom_fit(self):
        self._zoom_level = 1.0
        self._img_offset_x = 0
        self._img_offset_y = 0
        self._render_preview()

    def _preview_drag_start(self, e):
        self._drag_start_x = e.x
        self._drag_start_y = e.y

    def _preview_drag_move(self, e):
        if self._zoom_level <= 1.0:
            return
        dx = e.x - self._drag_start_x
        dy = e.y - self._drag_start_y
        self._img_offset_x += dx
        self._img_offset_y += dy
        self._drag_start_x = e.x
        self._drag_start_y = e.y
        self._render_preview()

    # ── Actions Générer ──────────────────────────────────────────────────────
    def do_generate(self):
        self.status_var.set("⏳  Génération…")
        self.update()
        try:
            torr_date = self.date_entry.get_date().strftime("%Y-%m-%d")
            scale = self.var_scale.get() / 100.0
            path = generate_label(self.cfg, self.var_cafe.get(), self.var_format.get(),
                                  self.var_niveau.get(), torr_date,
                                  self.var_copies.get(), scale=scale)
            self._log([{
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "cafe":     self.var_cafe.get(),
                "format":   self.var_format.get(),
                "copies":   self.var_copies.get(),
                "niveau":   self.var_niveau.get(),
            }])
            self.status_var.set(f"✓  {os.path.basename(path)}")
            if messagebox.askyesno("✓ PDF généré", f"{path}\n\nOuvrir ?", parent=self):
                open_or_print(path, do_print=False)
        except Exception as e:
            self.status_var.set("✗  Erreur")
            messagebox.showerror("Erreur", str(e), parent=self)

    def do_print(self):
        self.status_var.set("⏳  Impression…")
        self.update()
        try:
            torr_date = self.date_entry.get_date().strftime("%Y-%m-%d")
            scale = self.var_scale.get() / 100.0
            path = generate_label(self.cfg, self.var_cafe.get(), self.var_format.get(),
                                  self.var_niveau.get(), torr_date,
                                  self.var_copies.get(), scale=scale)
            open_or_print(path, do_print=True)
            self._log([{
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "cafe":     self.var_cafe.get(),
                "format":   self.var_format.get(),
                "copies":   self.var_copies.get(),
                "niveau":   self.var_niveau.get(),
            }])
            self.status_var.set(f"✓  Envoyé à {PRINTER_NAME}")
        except Exception as e:
            self.status_var.set("✗  Erreur")
            messagebox.showerror("Erreur", str(e), parent=self)

    def do_send_to_queue(self):
        self.status_var.set("⏳  Envoi au café…")
        self.update()
        try:
            torr_date = self.date_entry.get_date().strftime("%Y-%m-%d")
            scale = self.var_scale.get() / 100.0
            path = send_to_queue(self.cfg, self.var_cafe.get(), self.var_format.get(),
                                 self.var_niveau.get(), torr_date,
                                 self.var_copies.get(), scale=scale)
            self._log([{
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "cafe":     self.var_cafe.get(),
                "format":   self.var_format.get(),
                "copies":   self.var_copies.get(),
                "niveau":   self.var_niveau.get() + "  📡",
            }])
            self.status_var.set(f"📡  Envoyé : {os.path.basename(path)}")
        except Exception as e:
            self.status_var.set("✗  Erreur")
            messagebox.showerror("Erreur", str(e), parent=self)

    # ── Batch ────────────────────────────────────────────────────────────────
    def _batch_set_all(self, qty):
        for row in self.batch_rows:
            for fmt, var in row["fmt_copies"].items():
                if fmt != "Personnalisé":
                    var.set(qty)

    def _do_batch_send(self):
        """Comme _do_batch mais dépose tout dans le dossier file d'attente."""
        jobs = self._collect_batch_jobs()
        if not jobs:
            messagebox.showwarning("Aucune sélection", "Mets au moins 1 copie quelque part !", parent=self)
            return
        lines = "\n".join(f"  • {c}  {f}  ×{n}" for c, f, n in jobs)
        total_etiq = sum(n for _, _, n in jobs)
        if not messagebox.askyesno(
            f"Envoyer au café — {len(jobs)} ligne(s)",
            f"Envoyer ces {total_etiq} étiquette(s) à la file d'attente du café ?\n\n{lines}",
            parent=self,
        ):
            return
        torr_date = self.batch_date_entry.get_date().strftime("%Y-%m-%d")
        errors, log_entries = [], []
        self.batch_progress["maximum"] = len(jobs)
        for i, (cafe, fmt, copies) in enumerate(jobs):
            niveau = NIVEAUX_DEFAUT.get(cafe, NIVEAUX[2])
            self.batch_status.set(f"📡  {i+1}/{len(jobs)} — {cafe} {fmt}…")
            self.batch_progress["value"] = i
            self.update()
            try:
                scale = self.var_scale.get() / 100.0
                send_to_queue(self.cfg, cafe, fmt, niveau, torr_date, copies, scale=scale)
                log_entries.append({
                    "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "cafe": cafe, "format": fmt, "copies": copies,
                    "niveau": niveau + "  📡",
                })
            except Exception as e:
                errors.append(f"{cafe} {fmt} : {e}")
        self.batch_progress["value"] = len(jobs)
        self._log(log_entries)
        if errors:
            self.batch_status.set(f"⚠️  {len(errors)} erreur(s)")
            messagebox.showerror("Erreurs", "\n".join(errors), parent=self)
        else:
            self.batch_status.set(f"📡  {total_etiq} étiquette(s) envoyées au café !")

    def _collect_batch_jobs(self):
        jobs = []
        for row in self.batch_rows:
            cafe = row["cafe"]
            for fmt, var in row["fmt_copies"].items():
                try:
                    copies = int(var.get())
                except (ValueError, tk.TclError):
                    copies = 0
                if copies <= 0:
                    continue
                if fmt == "Personnalisé":
                    poids = row["custom_poids"].get().strip()
                    if not poids:
                        continue
                    real_fmt = poids
                else:
                    real_fmt = fmt
                jobs.append((cafe, real_fmt, copies))
        return jobs

    def _do_batch(self, print_mode=False):
        jobs = self._collect_batch_jobs()
        if not jobs:
            messagebox.showwarning("Aucune sélection", "Mets au moins 1 copie quelque part !", parent=self)
            return

        lines = "\n".join(f"  • {cafe}  {fmt}  ×{copies}" for cafe, fmt, copies in jobs)
        total_etiq = sum(c for _, _, c in jobs)
        action = "imprimer" if print_mode else "générer"
        if not messagebox.askyesno(
            f"Résumé — {len(jobs)} ligne(s)",
            f"Tu es sur le point de {action} :\n\n{lines}\n\n"
            f"Total : {total_etiq} étiquette(s)\n\nContinuer ?",
            parent=self,
        ):
            return

        torr_date = self.batch_date_entry.get_date().strftime("%Y-%m-%d")
        try:
            delay = float(self.batch_delay.get())
        except (ValueError, tk.TclError):
            delay = 0.0
        total = len(jobs)
        errors = []
        log_entries = []

        self.batch_progress["maximum"] = total
        self.batch_progress["value"] = 0

        for i, (cafe, fmt, copies) in enumerate(jobs):
            niveau = NIVEAUX_DEFAUT.get(cafe, NIVEAUX[2])
            self.batch_status.set(f"⏳  {i+1}/{total} — {cafe} {fmt}…")
            self.batch_progress["value"] = i
            self.update()
            try:
                scale = self.var_scale.get() / 100.0
                path = generate_label(self.cfg, cafe, fmt, niveau, torr_date, copies, scale=scale)
                if print_mode:
                    open_or_print(path, do_print=True)
                    if delay > 0:
                        time.sleep(delay)
                log_entries.append({
                    "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "cafe":     cafe,
                    "format":   fmt,
                    "copies":   copies,
                    "niveau":   niveau,
                })
            except Exception as e:
                errors.append(f"{cafe} {fmt} : {e}")

        self.batch_progress["value"] = total
        self._log(log_entries)

        if errors:
            self.batch_status.set(f"⚠️  {len(errors)} erreur(s)")
            messagebox.showerror("Erreurs", "\n".join(errors), parent=self)
        elif print_mode:
            self.batch_status.set(f"✅  {total_etiq} étiquette(s) envoyées à {PRINTER_NAME}")
        else:
            self.batch_status.set(f"✅  {total} PDF générés !")

    # ── Presets ──────────────────────────────────────────────────────────────
    def _save_preset(self):
        name = self.preset_var.get().strip() or f"Session {date.today()}"
        data = []
        for r in self.batch_rows:
            fc = {}
            for fmt, var in r["fmt_copies"].items():
                try:
                    fc[fmt] = int(var.get())
                except (ValueError, tk.TclError):
                    fc[fmt] = 0
            data.append({"cafe": r["cafe"], "fmt_copies": fc, "custom_poids": r["custom_poids"].get()})
        save_preset(name, data)
        self.preset_cb["values"] = list_presets()
        self.preset_var.set(name)
        self.batch_status.set(f"✅  Session « {name} » sauvegardée !")

    def _load_preset(self):
        name = self.preset_var.get().strip()
        if not name:
            messagebox.showwarning("Aucune session", "Sélectionne une session à charger.", parent=self)
            return
        try:
            data = load_preset(name)
            by_cafe = {entry["cafe"]: entry for entry in data}
            for row in self.batch_rows:
                saved = by_cafe.get(row["cafe"])
                if not saved:
                    continue
                for fmt, val in saved.get("fmt_copies", {}).items():
                    if fmt in row["fmt_copies"]:
                        try:
                            row["fmt_copies"][fmt].set(int(val))
                        except (ValueError, tk.TclError):
                            row["fmt_copies"][fmt].set(0)
                row["custom_poids"].set(saved.get("custom_poids", ""))
            self.batch_status.set(f"✅  Session « {name} » chargée !")
        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=self)

    def _delete_preset(self):
        name = self.preset_var.get().strip()
        if not name:
            return
        if messagebox.askyesno("Supprimer", f"Supprimer « {name} » ?", parent=self):
            delete_preset(name)
            self.preset_cb["values"] = list_presets()
            self.preset_var.set("")
            self.batch_status.set("🗑  Session supprimée.")

    # ── Historique ───────────────────────────────────────────────────────────
    def _log(self, entries):
        if not entries:
            return
        append_log(entries)
        self._refresh_hist()

    def _refresh_hist(self):
        self.hist_tree.delete(*self.hist_tree.get_children())
        for e in reversed(load_log()):
            self.hist_tree.insert("", "end", values=(
                e.get("datetime", ""), e.get("cafe", ""),
                e.get("format", ""), e.get("copies", ""), e.get("niveau", ""),
            ))

    def _clear_hist(self):
        if messagebox.askyesno("Vider", "Effacer tout l'historique ?", parent=self):
            with open(LOG_PATH, "w", encoding="utf-8") as f:
                json.dump([], f)
            self._refresh_hist()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = EtiquetteApp()
    app.mainloop()
