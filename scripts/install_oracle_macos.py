#!/usr/bin/env python3
"""Descarga e instala Oracle Instant Client (driver ODBC incluido) en .local.

Solo para macOS con Apple Silicon. Lo llama configurar.sh. No toca nada fuera
de la carpeta del proyecto: los .dmg descargados quedan en .cache y las
bibliotecas en .local/instantclient.
"""
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
VERSION = "23.26.3.0.0"
# Paquetes necesarios y su SHA256 publicado por Oracle, para comprobar que la
# descarga es íntegra: basic = bibliotecas cliente, odbc = driver ODBC,
# sqlplus = cliente de consola (útil como cliente de consulta en la defensa).
HASHES = {
    "basic": "9ad4824c5dca702e6bb68d459e2cd738e6ee1e750c668e54a09a43fee9f5d08a",
    "odbc": "e83fd8bc33638cf85f8451241d6ca33299b5930b481b75669d96aa2d7129fc62",
    "sqlplus": "332d6b73e213cd4652888430368f3ba258b03a7f1ec6837c13d0f6c3637fbe68",
}


def replace_file(source, target):
    """Copia un fichero sustituyendo el que hubiera (para poder reinstalar)."""
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
        # 1. Descargar el .dmg (solo si no está ya en .cache).
        dmg = cache / f"instantclient-{package}.dmg"
        if not dmg.exists():
            url = ("https://download.oracle.com/otn_software/mac/instantclient/2326300/"
                   f"instantclient-{package}-macos.arm64-{VERSION}.dmg")
            print("Descargando", package, flush=True)
            urllib.request.urlretrieve(url, dmg)
        # 2. Comprobar su SHA256.
        actual = hashlib.file_digest(dmg.open("rb"), "sha256").hexdigest()
        if actual != expected:
            raise SystemExit(f"SHA256 incorrecto: {dmg}. Borra ese fichero y vuelve a ejecutar.")
        # 3. Montar el .dmg como un disco (si no lo estaba ya).
        volume = Path(f"/Volumes/instantclient-{package}-macos.arm64-{VERSION}")
        mounted_here = not volume.exists()
        if mounted_here:
            subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", str(dmg)], check=True)
        try:
            # 4. Copiar su contenido a .local/instantclient. Es lo mismo que hace
            # el install_ic.sh de Oracle; se conservan los enlaces simbólicos.
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
            # 5. Desmontar el disco si lo montamos nosotros.
            if mounted_here:
                subprocess.run(["hdiutil", "detach", str(volume)], check=True)
    # El registro del driver en unixODBC (odbcinst.ini) lo escribe ejecutar.sh.
    print("Instant Client instalado en", destination)
    print("Ahora ejecuta ./ejecutar.sh --comprobar")


if __name__ == "__main__":
    main()
