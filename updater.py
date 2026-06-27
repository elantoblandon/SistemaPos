import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from tkinter import messagebox
import tkinter as tk


APP_NAME = "Sistema POS"
CONFIG_FILE = "updater_config.json"
VERSION_FILE = "version.txt"
DEFAULT_POS_EXE = "SistemaPos.exe"

DATA_EXCLUSIONS = {
    "licorera_pro.db",
    "backups",
    "facturas",
    "cierres_pdf",
    "assets",
    "__pycache__",
}

UPDATER_EXCLUSIONS = {
    "ActualizadorPOS.exe",
    "updater.py",
    CONFIG_FILE,
}


def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def read_text(path, default=""):
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except Exception:
        return default


def write_text(path, value):
    Path(path).write_text(str(value).strip() + "\n", encoding="utf-8")


def load_config(base):
    path = base / CONFIG_FILE
    default = {
        "github_repo": "",
        "pos_exe": DEFAULT_POS_EXE,
        "asset_name_contains": "SistemaPos",
        "allow_prereleases": False,
        "skip_update_check": False,
    }

    if not path.exists():
        bundled_path = Path(getattr(sys, "_MEIPASS", base)) / CONFIG_FILE
        if bundled_path.exists():
            try:
                data = json.loads(bundled_path.read_text(encoding="utf-8"))
                default.update(data if isinstance(data, dict) else {})
            except Exception:
                pass
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        default.update(data if isinstance(data, dict) else {})
    except Exception:
        pass

    return default


def parse_version(value):
    clean = str(value or "0.0.0").strip().lstrip("vV")
    parts = []
    for piece in clean.replace("-", ".").split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer(remote, local):
    return parse_version(remote) > parse_version(local)


def http_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "SistemaPOS-Updater",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def download_file(url, destination, status_callback=None):
    req = urllib.request.Request(url, headers={"User-Agent": "SistemaPOS-Updater"})
    with urllib.request.urlopen(req, timeout=30) as response:
        total = int(response.headers.get("Content-Length") or 0)
        downloaded = 0
        with open(destination, "wb") as file:
            while True:
                chunk = response.read(1024 * 128)
                if not chunk:
                    break
                file.write(chunk)
                downloaded += len(chunk)
                if status_callback and total:
                    percent = int((downloaded / total) * 100)
                    status_callback(f"Descargando actualización... {percent}%")


def get_latest_release(config):
    repo = str(config.get("github_repo", "")).strip()
    if not repo or "/" not in repo or "TU_USUARIO" in repo or "TU_REPOSITORIO" in repo:
        return None

    if config.get("allow_prereleases"):
        releases = http_json(f"https://api.github.com/repos/{repo}/releases")
        if not releases:
            return None
        return releases[0]

    return http_json(f"https://api.github.com/repos/{repo}/releases/latest")


def select_asset(release, config):
    assets = release.get("assets") or []
    name_filter = str(config.get("asset_name_contains", "")).lower().strip()

    zip_assets = [
        asset for asset in assets
        if str(asset.get("name", "")).lower().endswith(".zip")
    ]

    if name_filter:
        for asset in zip_assets:
            if name_filter in str(asset.get("name", "")).lower():
                return asset

    return zip_assets[0] if zip_assets else None


def backup_database(base, status_callback=None):
    db_path = base / "licorera_pro.db"
    if not db_path.exists():
        return None

    backup_dir = base / "backups"
    backup_dir.mkdir(exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = backup_dir / f"backup_pre_update_{stamp}.db"
    shutil.copy2(db_path, backup_path)
    if status_callback:
        status_callback(f"Backup creado: {backup_path.name}")
    return backup_path


def is_excluded(relative_path):
    parts = Path(relative_path).parts
    if not parts:
        return True

    first = parts[0]
    if first in DATA_EXCLUSIONS or first in UPDATER_EXCLUSIONS:
        return True

    name = Path(relative_path).name
    return name in DATA_EXCLUSIONS or name in UPDATER_EXCLUSIONS


def find_update_root(extract_dir):
    entries = [p for p in Path(extract_dir).iterdir() if p.name != "__MACOSX"]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return Path(extract_dir)


def apply_update(zip_path, base, status_callback=None):
    temp_extract = Path(tempfile.mkdtemp(prefix="pos_update_extract_"))
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(temp_extract)

        source_root = find_update_root(temp_extract)
        copied = 0

        for source in source_root.rglob("*"):
            if not source.is_file():
                continue

            relative = source.relative_to(source_root)
            if is_excluded(relative):
                continue

            target = base / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied += 1

        if copied <= 0:
            raise RuntimeError("El paquete no contiene archivos actualizables.")

        if status_callback:
            status_callback(f"Actualización aplicada ({copied} archivos).")
        return copied
    finally:
        shutil.rmtree(temp_extract, ignore_errors=True)


def launch_pos(base, config):
    pos_exe = base / str(config.get("pos_exe") or DEFAULT_POS_EXE)
    if pos_exe.exists():
        subprocess.Popen([str(pos_exe)], cwd=str(base))
        return True

    main_py = base / "main.py"
    if main_py.exists():
        subprocess.Popen([sys.executable, str(main_py)], cwd=str(base))
        return True

    messagebox.showerror(APP_NAME, "No se encontró SistemaPos.exe ni main.py.")
    return False


class UpdaterWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Actualizador POS")
        self.geometry("430x210")
        self.resizable(False, False)
        self.configure(bg="#0f111a")

        self.label_title = tk.Label(
            self,
            text="Sistema POS",
            bg="#0f111a",
            fg="#10b981",
            font=("Segoe UI", 18, "bold"),
        )
        self.label_title.pack(pady=(26, 6))

        self.label_status = tk.Label(
            self,
            text="Preparando...",
            bg="#0f111a",
            fg="#f9fafb",
            font=("Segoe UI", 10),
            wraplength=360,
        )
        self.label_status.pack(pady=(4, 18))

        self.button = tk.Button(
            self,
            text="Abrir POS",
            command=self.open_pos_now,
            bg="#10b981",
            fg="#000000",
            relief="flat",
            padx=18,
            pady=8,
            font=("Segoe UI", 10, "bold"),
        )
        self.button.pack()

        self.base = app_dir()
        self.config = load_config(self.base)
        self.after(350, self.run_update_flow)

    def set_status(self, text):
        self.label_status.configure(text=text)
        self.update_idletasks()

    def open_pos_now(self):
        launch_pos(self.base, self.config)
        self.destroy()

    def run_update_flow(self):
        try:
            if self.config.get("skip_update_check"):
                self.set_status("Revisión desactivada. Abriendo POS...")
                self.after(600, self.open_pos_now)
                return

            repo = str(self.config.get("github_repo", "")).strip()
            if not repo or "TU_USUARIO" in repo or "TU_REPOSITORIO" in repo:
                self.set_status("GitHub no está configurado. Abriendo POS...")
                self.after(800, self.open_pos_now)
                return

            local_version = read_text(self.base / VERSION_FILE, "0.0.0")
            self.set_status("Revisando actualizaciones...")
            release = get_latest_release(self.config)

            if not release:
                self.set_status("No se pudo leer la última versión. Abriendo POS...")
                self.after(900, self.open_pos_now)
                return

            remote_version = str(release.get("tag_name") or release.get("name") or "").lstrip("vV")
            if not is_newer(remote_version, local_version):
                self.set_status(f"Versión {local_version} al día. Abriendo POS...")
                self.after(800, self.open_pos_now)
                return

            asset = select_asset(release, self.config)
            if not asset:
                self.set_status("Hay versión nueva, pero no se encontró ZIP. Abriendo POS...")
                self.after(1200, self.open_pos_now)
                return

            if not messagebox.askyesno(
                "Actualización disponible",
                f"Hay una nueva versión ({remote_version}).\n\n"
                "¿Deseas descargarla e instalarla ahora?"
            ):
                self.open_pos_now()
                return

            backup_database(self.base, self.set_status)
            temp_dir = Path(tempfile.mkdtemp(prefix="pos_update_"))
            zip_path = temp_dir / str(asset.get("name") or "update.zip")

            download_file(asset["browser_download_url"], zip_path, self.set_status)
            self.set_status("Instalando actualización...")
            apply_update(zip_path, self.base, self.set_status)
            write_text(self.base / VERSION_FILE, remote_version)
            shutil.rmtree(temp_dir, ignore_errors=True)

            messagebox.showinfo("Actualización lista", f"Se instaló la versión {remote_version}.")
            self.open_pos_now()

        except urllib.error.URLError:
            self.set_status("Sin conexión o GitHub no respondió. Abriendo POS...")
            self.after(1200, self.open_pos_now)
        except Exception as e:
            messagebox.showwarning(
                "No se pudo actualizar",
                f"No se aplicó ninguna actualización.\n\nDetalle: {e}\n\nSe abrirá el POS normal."
            )
            self.open_pos_now()


if __name__ == "__main__":
    UpdaterWindow().mainloop()
