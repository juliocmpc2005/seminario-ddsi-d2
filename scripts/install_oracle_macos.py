#!/usr/bin/env python3
"""Instalación local reproducible de Instant Client para macOS ARM64."""
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
VERSION = "23.26.3.0.0"
HASHES = {
    "basic": "9ad4824c5dca702e6bb68d459e2cd738e6ee1e750c668e54a09a43fee9f5d08a",
    "odbc": "e83fd8bc33638cf85f8451241d6ca33299b5930b481b75669d96aa2d7129fc62",
    "sqlplus": "332d6b73e213cd4652888430368f3ba258b03a7f1ec6837c13d0f6c3637fbe68",
}


def replace_file(source, target):
    target = Path(target)
    if target.exists() or target.is_symlink():
        target.unlink()
    return shutil.copy2(source, target)


def main():
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise SystemExit("Este instalador es para macOS ARM64. Consulta README.md para otros sistemas.")
    if not shutil.which("odbcinst"):
        raise SystemExit("Instala unixODBC antes: brew install unixodbc")
    cache = ROOT / ".cache"
    destination = ROOT / ".local" / "instantclient"
    cache.mkdir(exist_ok=True)
    destination.mkdir(parents=True, exist_ok=True)
    for package, expected in HASHES.items():
        dmg = cache / f"instantclient-{package}.dmg"
        if not dmg.exists():
            url = ("https://download.oracle.com/otn_software/mac/instantclient/2326300/"
                   f"instantclient-{package}-macos.arm64-{VERSION}.dmg")
            print("Descargando", package, flush=True)
            urllib.request.urlretrieve(url, dmg)
        actual = hashlib.file_digest(dmg.open("rb"), "sha256").hexdigest()
        if actual != expected:
            raise SystemExit(f"SHA256 incorrecto: {dmg}. Borra ese fichero y vuelve a ejecutar.")
        volume = Path(f"/Volumes/instantclient-{package}-macos.arm64-{VERSION}")
        mounted_here = not volume.exists()
        if mounted_here:
            subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", str(dmg)], check=True)
        try:
            # Misma copia de archivos que install_ic.sh, acotada a estos tres paquetes
            # y a .local/instantclient; conserva enlaces simbólicos y licencias.
            for source in volume.iterdir():
                target = destination / source.name
                if source.is_dir() and not source.is_symlink():
                    shutil.copytree(source, target, dirs_exist_ok=True, symlinks=True,
                                    copy_function=replace_file)
                else:
                    if target.exists() or target.is_symlink():
                        target.unlink()
                    if source.is_symlink():
                        target.symlink_to(os.readlink(source))
                    else:
                        shutil.copy2(source, target)
        finally:
            if mounted_here:
                subprocess.run(["hdiutil", "detach", str(volume)], check=True)
    (ROOT / ".local" / "odbcinst.ini").write_text(
        "[OracleSeminario]\nDescription=Oracle Instant Client ARM64\n"
        f"Driver={destination / 'libsqora.dylib.23.1'}\nThreading=2\n", encoding="utf-8")
    (ROOT / ".local" / "odbc.ini").touch()
    print("Instant Client instalado en", destination)
    print("ODBC configurado solo para este proyecto. Ejecuta ./ejecutar.sh --comprobar")


if __name__ == "__main__":
    main()
