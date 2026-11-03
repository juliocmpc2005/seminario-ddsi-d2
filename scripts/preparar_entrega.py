#!/usr/bin/env python3
"""Genera memoria breve y ZIP sin configuración personal ni dependencias binarias."""
import json
from pathlib import Path
import subprocess
import sys
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT = Path(__file__).resolve().parent.parent


def main():
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                            cwd=ROOT, capture_output=True, text=True)
    print(result.stdout + result.stderr)
    if result.returncode:
        raise SystemExit("No se prepara la entrega: hay pruebas fallidas.")
    (ROOT / "docs/PRUEBAS.txt").write_text(
        "Pruebas locales de lógica con SQLite (no acreditan Oracle/ODBC).\n\n" + result.stdout + result.stderr,
        encoding="utf-8")
    team = json.loads((ROOT / "docs/equipo.json").read_text(encoding="utf-8"))
    group = team["subgrupo"]
    if not group.isalnum():
        raise SystemExit("El identificador de subgrupo debe ser alfanumérico.")
    pdf = ROOT / "docs" / f"Memoria_{group}.pdf"
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodySmall", fontName="Helvetica", fontSize=10,
                              leading=14, spaceAfter=8, textColor=colors.HexColor("#243247")))
    styles.add(ParagraphStyle(name="CaptionSmall", parent=styles["BodySmall"], fontSize=8,
                              leading=11, spaceAfter=4))
    styles["Title"].textColor = colors.HexColor("#17395C")
    styles["Heading2"].textColor = colors.HexColor("#17395C")
    story = []

    def p(text, style="BodySmall"):
        story.append(Paragraph(text, styles[style]))

    def section(title, text):
        p(title, "Heading2")
        p(text)

    p("Seminario 1 · Acceso a bases de datos", "Title")
    p(f"Diseño y Desarrollo de Sistemas de Información · Curso 2026/2027<br/>"
      f"Subgrupo <b>{escape(group)}</b> · {escape(team['fecha'])}")
    p("<b>Integrantes:</b> " + ", ".join(escape(person["nombre"]) for person in team["integrantes"]))
    section("Lenguaje y herramientas", "Python 3.14.7, pyodbc 5.3.0, unixODBC 2.3.14 y Oracle "
            "Instant Client 23.26.3.0.0 (Basic, ODBC y SQL*Plus). Plataforma configurada: macOS ARM64. "
            "SGBD de la aplicación: Oracle de la ETSIIT, servicio practbd.")
    section("Instalación realizada", "Se ha creado un entorno Python aislado en .venv e instalado pyodbc. "
            "Se ha instalado unixODBC mediante Homebrew y descargado los tres paquetes oficiales "
            "de Instant Client, verificando sus SHA256. Las bibliotecas y el registro del driver "
            "ODBC se alojan en .local. Los lanzadores configuran las rutas solo para el proyecto. "
            "La contraseña se solicita en la consola con entrada oculta y no se guarda.")
    section("Implementación", "El menú principal permite reiniciar las tres tablas con diez productos, "
            "dar de alta pedidos, consultar tablas y salir. Las claves son numéricas y la fecha es DATE. "
            "El submenú permite añadir productos, eliminar todos los detalles, cancelar o finalizar. "
            "Se muestra la base de datos después de añadir, eliminar detalles y cancelar. "
            "Los productos repetidos acumulan cantidad y las consultas DML usan parámetros ODBC.")
    section("Control de transacciones", "La conexión usa autocommit=False. Tras insertar la cabecera se "
            "establece pedido_sin_detalles. Eliminar detalles vuelve a ese punto y restaura el stock, "
            "manteniendo la cabecera. Cada línea tiene otro savepoint para deshacer un fallo sin perder "
            "las anteriores. Cancelar hace ROLLBACK y finalizar COMMIT. Al salir se deshace lo pendiente "
            "y se cierra la conexión. El reinicio de tablas queda fuera del alta porque el DDL de "
            "Oracle realiza commits implícitos.")
    p("Ejecución: <font face='Courier'>./ejecutar.sh</font>. Consulta independiente: "
      "<font face='Courier'>./ejecutar.sh --consulta</font>. "
      "La guía de defensa incluida detalla una demostración con dos sesiones.")
    story.append(PageBreak())
    p("Reparto, fuentes y validación", "Title")
    p("Reparto de trabajo", "Heading2")
    rows = [[Paragraph("<b>Integrante</b>", styles["BodySmall"]),
             Paragraph("<b>Tareas efectivamente realizadas</b>", styles["BodySmall"])]]
    for person in team["integrantes"]:
        rows.append([Paragraph(escape(person["nombre"]), styles["BodySmall"]),
                     Paragraph(escape(person["tareas"]), styles["BodySmall"])])
    table = Table(rows, colWidths=[3.2 * cm, 13.1 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F7")),
        ("LINEBELOW", (0, 0), (-1, -1), .4, colors.HexColor("#CFD8E3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 8))
    if any("pendiente" in person["tareas"].lower() for person in team["integrantes"]):
        p("<b>Pendiente antes de entregar:</b> el grupo debe completar el reparto real. "
          "No se han atribuido tareas sin confirmación. Todos los integrantes deben revisar "
          "y poder explicar el código completo.")
    section("Fuentes y asistencia", "La implementación se ha preparado de nuevo para este enunciado "
            "con asistencia de Codex. No se ha reutilizado código de entregas de años anteriores. "
            "Las siguientes fuentes se han consultado como documentación de las herramientas "
            "y de la semántica de las transacciones:")
    sources = [
        ("Enunciado del seminario, implementación y anexos", None),
        ("Oracle Instant Client ARM64: descarga, instalación y hashes", "https://www.oracle.com/database/technologies/instant-client/macos-arm64-downloads.html"),
        ("pyodbc: Connection, autocommit, commit y rollback", "https://github.com/mkleehammer/pyodbc/wiki/Connection"),
        ("Oracle: SAVEPOINT", "https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/SAVEPOINT.html"),
        ("Oracle: ROLLBACK", "https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/ROLLBACK.html"),
        ("Oracle: transacciones y commits del DDL", "https://docs.oracle.com/en/database/oracle/oracle-database/21/cncpt/transactions.html"),
    ]
    for label, url in sources:
        p((f'<link href="{escape(url)}" color="#175A9B">{escape(label)}</link>' if url else escape(label)), "CaptionSmall")
    oracle_file = ROOT / ".local/oracle-validation.json"
    oracle_ok = oracle_file.exists() and json.loads(oracle_file.read_text()).get("ok")
    login_file = ROOT / ".local/conexion.json"
    login_ok = login_file.exists() and json.loads(login_file.read_text()).get("ok")
    status = ("Validación real con Oracle/ODBC completada; las tablas de prueba se han eliminado."
              if oracle_ok else "La validación real de transacciones con Oracle/ODBC está pendiente.")
    preparation_file = ROOT / ".local/preparacion.json"
    if preparation_file.exists() and json.loads(preparation_file.read_text()).get("menu_oracle"):
        status += (" Se han creado las tres tablas de la aplicación con diez productos y se ha "
                   "comprobado el menú completo en Oracle, dejando los pedidos de prueba cancelados.")
    login_status = ("Login Oracle comprobado correctamente. " if login_ok else "Login Oracle pendiente de comprobar. ")
    section("Validación", "Las 12 pruebas locales han pasado: commit y visibilidad entre sesiones, "
            "rollback total, savepoints repetidos, recuperación de stock, errores de inserción, "
            "códigos duplicados, validación de entradas y menús. Usan SQLite como soporte de pruebas "
            "de lógica y no acreditan por sí solas Oracle. " + login_status + status)
    p("Validación real: <font face='Courier'>./ejecutar.sh --probar-oracle</font>. "
      "Reproducción y demostración detalladas en README.md y docs/DEFENSA.md.", "CaptionSmall")

    def footer(canvas, document):
        canvas.setStrokeColor(colors.HexColor("#CFD8E3"))
        canvas.line(1.8 * cm, 1.5 * cm, 19.2 * cm, 1.5 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#65758B"))
        canvas.drawString(1.8 * cm, 1.1 * cm, f"DDSI 2026/2027 · Subgrupo {group}")
        canvas.drawRightString(19.2 * cm, 1.1 * cm, str(document.page))

    SimpleDocTemplate(str(pdf), pagesize=(21 * cm, 29.7 * cm),
                      leftMargin=2.3 * cm, rightMargin=2.3 * cm,
                      topMargin=1.7 * cm, bottomMargin=2 * cm,
                      title=f"Memoria Seminario 1 DDSI - {group}",
                      author=", ".join(p["nombre"] for p in team["integrantes"])).build(
                          story, onFirstPage=footer, onLaterPages=footer)
    destination = ROOT / "entrega"
    destination.mkdir(exist_ok=True)
    archive_path = destination / f"Seminario1_DDSI_{group}.zip"
    base = f"Seminario1_DDSI_{group}"
    names = ["README.md", "config.example.ini", "requirements.txt", "requirements-docs.txt",
             "configurar.sh", "ejecutar.sh", ".gitignore", ".vscode/settings.json"]
    files = [ROOT / name for name in names] + list(ROOT.glob("*.command"))
    for directory in ("seminario", "scripts", "tests", "sql", "docs"):
        files.extend(path for path in (ROOT / directory).rglob("*")
                     if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc")
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path, f"{base}/{path.relative_to(ROOT)}")
        archive.writestr(f"{base}/config.ini", (ROOT / "config.example.ini").read_bytes())
        if oracle_ok:
            validation = json.loads(oracle_file.read_text())
            archive.writestr(f"{base}/docs/VALIDACION_ORACLE.json",
                             json.dumps(validation, ensure_ascii=False, indent=2))
    print("PDF:", pdf)
    print("ZIP:", archive_path)


if __name__ == "__main__":
    main()
