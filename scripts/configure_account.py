#!/usr/bin/env python3
"""Guarda el usuario de Oracle en config.ini. La contraseña nunca se guarda."""
import configparser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Se parte del config.ini existente o, si aún no lo hay, de la plantilla.
config = configparser.ConfigParser()
config.read(ROOT / "config.ini", encoding="utf-8")
if not config.has_section("oracle"):
    config.read(ROOT / "config.example.ini", encoding="utf-8")

print("Según el anexo I: DNI sin letra final, cambiando el primer dígito por x minúscula.")
print("Ejemplo ficticio: 12345678Z -> x2345678. La contraseña inicial es el mismo usuario.")
user = input("Usuario ORACLE (no el usuario de correo UGR): ").strip()
if not user or ";" in user:
    raise SystemExit("Usuario vacío o inválido; no se cambió la configuración.")

config["oracle"]["usuario"] = user
with (ROOT / "config.ini").open("w", encoding="utf-8") as output:
    config.write(output)
print("Usuario guardado. Ahora se comprobará la conexión con contraseña oculta.")
