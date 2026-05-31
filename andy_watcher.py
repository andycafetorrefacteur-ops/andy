#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Andy Café — Watcher d'impression à distance
À installer sur le PC du café. Surveille un dossier synchronisé
(Dropbox / OneDrive / Google Drive) et imprime automatiquement
chaque PDF qui y arrive.
"""

import os
import sys
import json
import time
import shutil
import platform
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(APP_DIR, "config_watcher.json")
IS_WINDOWS = platform.system() == "Windows"

DEFAULT_CFG = {
    "watch_dir":      os.path.join(os.path.expanduser("~"), "Dropbox", "Andy_Print_Queue"),
    "archive_dir":    os.path.join(os.path.expanduser("~"), "Dropbox", "Andy_Print_Queue", "Imprimes"),
    "check_interval": 3,         # secondes entre 2 scans
    "stable_seconds": 2,         # délai d'attente que la sync Dropbox finisse
    "auto_start":     False,
}

C_BROWN = "#3d2008"
C_CREAM = "#fdf8f0"
C_GREEN = "#2d7a4f"
C_RED   = "#c0392b"
C_GOLD  = "#c8963e"
C_GRAY  = "#888888"
C_LIGHT = "#f0e6d5"
C_WHITE = "#ffffff"


def load_cfg():
    if os.path.exists(CFG_PATH):
        try:
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in DEFAULT_CFG.items():
                data.setdefault(k, v)
            return data
        except Exception:
            pass
    return dict(DEFAULT_CFG)


def save_cfg(cfg):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def print_pdf(path):
    if IS_WINDOWS:
        os.startfile(path, "print")
    elif platform.system() == "Darwin":
        subprocess.run(["lpr", path], check=False)
    else:
        subprocess.run(["lpr", path], check=False)


class WatcherApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.cfg = load_cfg()
        self.title("Andy Café — Watcher d'impression")
        self.geometry("680x480")
        self.configure(bg=C_CREAM)
        self.running = False
        self.thread = None
        self.processed = set()
        self._build_ui()
        if self.cfg.get("auto_start"):
            self.after(500, self.start)

    def _build_ui(self):
        hdr = tk.Frame(self, bg=C_BROWN)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📡  Andy Café — Watcher d'impression",
                 font=("Georgia", 14, "bold"), bg=C_BROWN, fg=C_CREAM, pady=10).pack()

        # Config
        cfg_frame = tk.LabelFrame(self, text="  Configuration  ",
                                  font=("Segoe UI", 9, "bold"),
                                  bg=C_CREAM, fg=C_BROWN, padx=12, pady=8)
        cfg_frame.pack(fill="x", padx=12, pady=8)

        # Dossier surveillé
        tk.Label(cfg_frame, text="Dossier surveillé :", bg=C_CREAM, font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=3)
        self.var_watch = tk.StringVar(value=self.cfg["watch_dir"])
        ttk.Entry(cfg_frame, textvariable=self.var_watch, width=55, font=("Segoe UI", 9)).grid(row=0, column=1, padx=4, sticky="ew")
        tk.Button(cfg_frame, text="📂", command=self._browse_watch,
                  bg=C_LIGHT, relief="flat", cursor="hand2").grid(row=0, column=2)

        # Dossier archive
        tk.Label(cfg_frame, text="Dossier archive :", bg=C_CREAM, font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=3)
        self.var_archive = tk.StringVar(value=self.cfg["archive_dir"])
        ttk.Entry(cfg_frame, textvariable=self.var_archive, width=55, font=("Segoe UI", 9)).grid(row=1, column=1, padx=4, sticky="ew")
        tk.Button(cfg_frame, text="📂", command=self._browse_archive,
                  bg=C_LIGHT, relief="flat", cursor="hand2").grid(row=1, column=2)

        # Intervalle
        tk.Label(cfg_frame, text="Intervalle (sec) :", bg=C_CREAM, font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", pady=3)
        self.var_interval = tk.IntVar(value=self.cfg["check_interval"])
        ttk.Spinbox(cfg_frame, from_=1, to=60, textvariable=self.var_interval, width=6).grid(row=2, column=1, sticky="w", padx=4)

        cfg_frame.grid_columnconfigure(1, weight=1)

        # Boutons
        btn_frame = tk.Frame(self, bg=C_CREAM)
        btn_frame.pack(fill="x", padx=12, pady=(0, 8))
        self.btn_start = tk.Button(btn_frame, text="▶  Démarrer la surveillance",
                                   command=self.start,
                                   bg=C_GREEN, fg=C_WHITE,
                                   font=("Segoe UI", 11, "bold"),
                                   padx=14, pady=8, relief="flat", cursor="hand2")
        self.btn_start.pack(side="left", padx=(0, 6))
        self.btn_stop = tk.Button(btn_frame, text="■  Arrêter",
                                  command=self.stop,
                                  bg=C_RED, fg=C_WHITE,
                                  font=("Segoe UI", 11, "bold"),
                                  padx=14, pady=8, relief="flat", cursor="hand2",
                                  state="disabled")
        self.btn_stop.pack(side="left", padx=(0, 6))
        tk.Button(btn_frame, text="💾  Sauver config",
                  command=self._save,
                  bg=C_LIGHT, fg=C_BROWN,
                  font=("Segoe UI", 9),
                  padx=10, pady=8, relief="flat", cursor="hand2").pack(side="left")

        # Statut
        self.status_var = tk.StringVar(value="⏸  Arrêté")
        tk.Label(self, textvariable=self.status_var,
                 font=("Segoe UI", 10, "bold"), bg=C_CREAM, fg=C_GRAY).pack(pady=(4, 0))

        # Journal
        log_frame = tk.LabelFrame(self, text="  Journal  ",
                                  font=("Segoe UI", 9, "bold"),
                                  bg=C_CREAM, fg=C_BROWN, padx=8, pady=6)
        log_frame.pack(fill="both", expand=True, padx=12, pady=8)
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=12, font=("Consolas", 9),
            bg="#1e1e1e", fg="#d4d4d4", state="disabled", wrap="word",
        )
        self.log_text.pack(fill="both", expand=True)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _browse_watch(self):
        path = filedialog.askdirectory(title="Dossier surveillé")
        if path:
            self.var_watch.set(path)

    def _browse_archive(self):
        path = filedialog.askdirectory(title="Dossier archive")
        if path:
            self.var_archive.set(path)

    def _save(self):
        self.cfg["watch_dir"]      = self.var_watch.get()
        self.cfg["archive_dir"]    = self.var_archive.get()
        self.cfg["check_interval"] = int(self.var_interval.get())
        save_cfg(self.cfg)
        self.log("Configuration sauvegardée.", color="#88c")

    def log(self, msg, color="#d4d4d4"):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def start(self):
        if self.running:
            return
        self._save()
        watch = self.cfg["watch_dir"]
        if not os.path.isdir(watch):
            try:
                os.makedirs(watch, exist_ok=True)
                self.log(f"📁 Dossier créé : {watch}", color="#8c8")
            except Exception as e:
                self.log(f"✗ Impossible de créer {watch} : {e}", color="#f88")
                return
        self.running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status_var.set(f"👁  En surveillance : {watch}")
        self.log(f"▶ Surveillance démarrée → {watch}", color="#8f8")
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.status_var.set("⏸  Arrêté")
        self.log("■ Surveillance arrêtée.", color="#fc8")

    def _is_stable(self, path, wait=2):
        """Vérifie que le fichier n'est plus en train d'être copié/synchronisé."""
        try:
            size1 = os.path.getsize(path)
        except OSError:
            return False
        time.sleep(wait)
        try:
            size2 = os.path.getsize(path)
        except OSError:
            return False
        return size1 == size2 and size1 > 0

    def _archive(self, path, archive_dir):
        try:
            os.makedirs(archive_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = os.path.basename(path)
            dest = os.path.join(archive_dir, f"{ts}__{base}")
            shutil.move(path, dest)
            return dest
        except Exception as e:
            self.log(f"⚠ Archivage impossible : {e}", color="#fc8")
            return None

    def _loop(self):
        interval = max(1, int(self.cfg["check_interval"]))
        stable_wait = int(self.cfg["stable_seconds"])
        while self.running:
            watch = self.cfg["watch_dir"]
            archive = self.cfg["archive_dir"]
            try:
                if os.path.isdir(watch):
                    for fname in sorted(os.listdir(watch)):
                        if not self.running:
                            break
                        if not fname.lower().endswith(".pdf"):
                            continue
                        path = os.path.join(watch, fname)
                        if not os.path.isfile(path):
                            continue
                        # Ignore les fichiers .tmp de Dropbox
                        if fname.startswith(".") or fname.endswith(".tmp"):
                            continue
                        # Évite de reprendre un fichier déjà en cours
                        if path in self.processed:
                            continue
                        self.processed.add(path)
                        self.log(f"📥 Nouveau PDF : {fname}", color="#8cf")
                        if not self._is_stable(path, wait=stable_wait):
                            self.log(f"⏳ {fname} encore en sync, on attend…", color="#fc8")
                            self.processed.discard(path)
                            continue
                        try:
                            print_pdf(path)
                            self.log(f"🖨 Imprimé : {fname}", color="#8f8")
                            time.sleep(2)  # laisse à Windows le temps de prendre le job
                            archived = self._archive(path, archive)
                            if archived:
                                self.log(f"📦 Archivé → {os.path.basename(archived)}", color="#aaa")
                            self.processed.discard(path)
                        except Exception as e:
                            self.log(f"✗ Erreur impression {fname} : {e}", color="#f88")
            except Exception as e:
                self.log(f"⚠ Erreur scan : {e}", color="#fc8")
            time.sleep(interval)

    def _on_close(self):
        self.running = False
        self.cfg["auto_start"] = False
        try:
            save_cfg(self.cfg)
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    WatcherApp().mainloop()
