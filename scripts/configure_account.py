#!/usr/bin/env python3
"""Guarda solo el usuario Oracle. No pide ni guarda el DNI completo."""
import configparser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
config = configparser.ConfigParser(interpolation=None)
config.read(ROOT / "config.ini", encoding="utf-8")
if not config.has_section("oracle"):
    config.read(ROOT / "config.example.ini", encoding="utf-8")
print("Según el anexo I: DNI sin letra final, cambiando el primer dígito por x minúscula.")
print("Ejemplo ficticio: 12345678Z -> x2345678. La contraseña inicial es el mismo usuario.")
user = input("Usuario ORACLE (no el usuario de correo UGR): ").strip()
if not user or any(character in user for character in "\r\n;"):
    raise SystemExit("Usuario vacío o inválido; no se cambió la configuración.")
config["oracle"]["usuario"] = user
with (ROOT / "config.ini").open("w", encoding="utf-8") as output:
    config.write(output)
for name in ("conexion.json", "oracle-validation.json"):
    (ROOT / ".local" / name).unlink(missing_ok=True)
print("Usuario guardado. Ahora se comprobará la conexión con contraseña oculta.")
