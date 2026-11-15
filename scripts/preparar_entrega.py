#!/usr/bin/env python3
"""Genera lo que se sube a Prado: la memoria en PDF y el ZIP con el código.

    .venv/bin/python -m pip install -r requirements-docs.txt   (solo la primera vez)
    .venv/bin/python scripts/preparar_entrega.py

Pasos: 1) ejecuta las pruebas y se detiene si alguna falla; 2) conserva la
memoria PDF existente del grupo; 3) crea entrega/Seminario1_DDSI_<subgrupo>.zip.
Solo --regenerar-memoria sustituye el PDF por la plantilla de este fichero.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED

# ReportLab es la biblioteca que crea el PDF. Solo se usa aquí, no en la aplicación.
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Texto de la memoria: (título del apartado, contenido). El enunciado pide,
# muy brevemente: lenguaje, instalación, fuentes y reparto de trabajo.
# ---------------------------------------------------------------------------
SECTIONS = [
    ("Lenguaje y herramientas",
     "Lenguaje: <b>Python 3.14</b>. Conexión mediante <b>ODBC</b>: biblioteca pyodbc 5.3.0, "
     "Driver Manager unixODBC 2.3.14 y driver ODBC de Oracle Instant Client 23.26 (paquetes "
     "Basic, ODBC y SQL*Plus). SGBD: <b>Oracle</b> de la ETSIIT (oracle0.ugr.es, puerto 1521, "
     "servicio practbd). Equipo de desarrollo: macOS con Apple Silicon."),
    ("Instalación realizada",
     "1) unixODBC con Homebrew (brew install unixodbc). 2) Entorno virtual de Python (.venv) "
     "con pyodbc instalado mediante pip. 3) Descarga de los tres paquetes de Instant Client "
     "desde la web de Oracle, comprobando su SHA256, y copia a la carpeta .local del proyecto. "
     "4) Registro del driver de Oracle en unixODBC con el nombre OracleSeminario (fichero "
     "odbcinst.ini local al proyecto). Todo ello está automatizado en configurar.sh. La "
     "contraseña no se guarda: se pide al arrancar, con la entrada oculta."),
    ("Implementación",
     "Aplicación de consola con el menú del enunciado: 1) borrar y crear las tres tablas e "
     "insertar las 10 tuplas de Stock predefinidas en el código, 2) dar de alta un pedido, "
     "3) mostrar las tablas y 4) salir cerrando la conexión. El alta pide los datos del pedido, "
     "los inserta en Pedido y ofrece: añadir detalle (solo si hay stock, que se descuenta), "
     "eliminar todos los detalles, cancelar y finalizar. Tras las tres primeras se muestra el "
     "contenido de la BD. Código: seminario/db.py (conexión y consultas), seminario/orders.py "
     "(tablas y transacciones) y seminario/__main__.py (menús)."),
    ("Control de transacciones",
     "La conexión se abre con el autocommit desactivado. El INSERT de la cabecera inicia la "
     "transacción y a continuación se fija el <b>SAVEPOINT</b> pedido_sin_detalles. Eliminar "
     "todos los detalles hace <b>ROLLBACK TO</b> ese punto: desaparecen los detalles, se "
     "recupera el stock y se conserva la cabecera, con la transacción aún activa. Cada línea "
     "usa además el savepoint antes_detalle para que descontar el stock e insertar el detalle "
     "ocurran los dos o ninguno. Cancelar hace <b>ROLLBACK</b> y finalizar hace <b>COMMIT</b>. "
     "Al salir se deshace lo pendiente y se cierra la conexión. La creación de tablas queda "
     "fuera del alta porque en Oracle el DDL hace COMMIT implícito."),
    ("Comprobación",
     "El proyecto incluye pruebas automáticas de la lógica (tests/test_orders.py) y una "
     "validación contra Oracle con dos sesiones simultáneas (./ejecutar.sh --probar-oracle), "
     "que comprueba qué ve cada sesión antes y después de COMMIT y ROLLBACK. En la defensa "
     "se usa un cliente de consulta independiente (SQL Developer, SQL*Plus o "
     "./ejecutar.sh --consulta); los pasos están en docs/DEFENSA.md."),
    ("Fuentes",
     "No se ha reutilizado código de entregas de otros cursos. El código se ha escrito para "
     "este enunciado con asistencia de herramientas de IA (Codex y Claude Code). "
     "Documentación consultada: enunciado del seminario y sus anexos; "
     "wiki de pyodbc (Connection: autocommit, commit, rollback), "
     "github.com/mkleehammer/pyodbc/wiki; documentación de Oracle sobre SAVEPOINT, ROLLBACK, "
     "transacciones y el driver ODBC, docs.oracle.com; e instrucciones de instalación de "
     "Oracle Instant Client para macOS ARM64, oracle.com/database/technologies/instant-client."),
]


def run_tests():
    """Ejecuta las pruebas; si alguna falla no se genera la entrega."""
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit("No se prepara la entrega: hay pruebas fallidas.")


def build_pdf(team, pdf):
    """Escribe la memoria: cabecera, apartados de SECTIONS y tabla de reparto."""
    styles = getSampleStyleSheet()  # Estilos de texto predefinidos de ReportLab.
    body = styles["BodyText"]
    story = [  # Lista de elementos que se colocan uno debajo de otro.
        Paragraph("Seminario 1 · Acceso a bases de datos", styles["Title"]),
        Paragraph("Diseño y Desarrollo de Sistemas de Información · Curso 2026/2027<br/>"
                  f"Subgrupo <b>{team['subgrupo']}</b> · {team['fecha']}<br/><b>Integrantes:</b> "
                  + ", ".join(person["nombre"] for person in team["integrantes"]), body),
    ]
    for title, text in SECTIONS:
        story.append(Paragraph(title, styles["Heading2"]))
        story.append(Paragraph(text, body))

    # Reparto de trabajo: una fila por integrante, leída de docs/equipo.json.
    rows = [[Paragraph("<b>Integrante</b>", body), Paragraph("<b>Tareas realizadas</b>", body)]]
    for person in team["integrantes"]:
        rows.append([Paragraph(person["nombre"], body), Paragraph(person["tareas"], body)])
    table = Table(rows, colWidths=[3.2 * cm, 13.2 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F7")),      # cabecera sombreada
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD8E3")),  # línea bajo cada fila
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    # KeepTogether evita que el título y la tabla queden partidos entre dos páginas.
    story.append(KeepTogether([Paragraph("Reparto de trabajo", styles["Heading2"]), table]))

    SimpleDocTemplate(str(pdf), pagesize=A4, leftMargin=2.3 * cm, rightMargin=2.3 * cm,
                      topMargin=1.7 * cm, bottomMargin=1.7 * cm,
                      title=f"Memoria Seminario 1 DDSI - {team['subgrupo']}").build(story)


def build_zip(pdf, archive_path):
    """Crea el ZIP con la memoria y el código fuente.

    Solo entran ficheros elegidos aquí: nunca config.ini (datos personales),
    ni .venv, .local o .cache (dependencias descargadas).
    """
    files = [ROOT / name for name in ("README.md", "config.example.ini", "requirements.txt",
                                      "requirements-docs.txt", "configurar.sh", "ejecutar.sh")]
    files += ROOT.glob("*.command")
    for directory in ("seminario", "scripts", "tests", "sql", "docs"):
        files += (path for path in (ROOT / directory).rglob("*")
                  if path.is_file() and "__pycache__" not in path.parts)
    base = archive_path.stem  # Carpeta raíz dentro del ZIP.
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        # La memoria también va en la raíz del ZIP para que se vea nada más abrirlo.
        archive.write(pdf, f"{base}/{pdf.name}")
        for path in sorted(files):
            archive.write(path, f"{base}/{path.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser(description="Prepara el ZIP conservando la memoria PDF del grupo.")
    parser.add_argument("--regenerar-memoria", action="store_true",
                        help="Sustituye el PDF existente por la plantilla automática; usar solo si se desea reemplazarlo.")
    args = parser.parse_args()
    run_tests()
    team = json.loads((ROOT / "docs" / "equipo.json").read_text(encoding="utf-8"))
    pdf = ROOT / "docs" / f"Memoria_{team['subgrupo']}.pdf"
    if args.regenerar_memoria:
        build_pdf(team, pdf)
    elif not pdf.is_file():
        raise SystemExit(f"Falta la memoria {pdf}. Copia el PDF del grupo o usa --regenerar-memoria para crear una plantilla.")
    (ROOT / "entrega").mkdir(exist_ok=True)
    archive_path = ROOT / "entrega" / f"Seminario1_DDSI_{team['subgrupo']}.zip"
    build_zip(pdf, archive_path)
    print("PDF:", pdf)
    print("ZIP:", archive_path)
    if any("pendiente" in person["tareas"].lower() for person in team["integrantes"]):
        print("\nAVISO: falta el reparto real de trabajo. Rellena docs/equipo.json y "
              "vuelve a ejecutar este script antes de entregar.")


if __name__ == "__main__":
    main()
