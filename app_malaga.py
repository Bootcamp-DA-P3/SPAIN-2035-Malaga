"""SPAIN 2035. Ejecutar con Python junto a Atlas_Malaga_datos.zip."""
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from modelo import entrenar
import csv
import io
import math
import sqlite3
from zipfile import ZipFile

import pandas as pd



WEB = Path(__file__).resolve().parent / "web"
RECURSOS = {"/": ("index.html", "text/html; charset=utf-8"),
            "/atlas.js": ("atlas.js", "text/javascript"), "/estilo.css": ("estilo.css", "text/css"),
            "/leaflet.js": ("leaflet.js", "text/javascript"), "/leaflet.css": ("leaflet.css", "text/css"),
            "/postales.json": ("postales.json", "application/json")}

def crear_servidor(tabla, mae, ruta_db):
    with sqlite3.connect(ruta_db) as db:
        # La clave formada por año y sección identifica cada observación y permite corregirla sin duplicarla.
        db.execute("""CREATE TABLE IF NOT EXISTS observaciones (
            anio INTEGER, zona TEXT, real REAL, fuente TEXT, estimado REAL,
            anterior REAL, cambio_seccion REAL, cambio_ciudad REAL, fecha TEXT,
            PRIMARY KEY(anio,zona))""")
    catalogo = {int(a): list(grupo.index.get_level_values("zona")) for a, grupo in tabla.groupby(level="anio")}

    # Las proyecciones usan la mediana publicada de 2024 incluso donde falte historial para Gradient Boosting.
    with ZipFile(WEB.parent / "Atlas_Malaga_datos.zip") as atlas:
        secciones = atlas.read("Datos_Malaga/mapa_secciones_malaga_2021.geojson")
        with atlas.open("Datos_Malaga/alquiler_seccion_malaga.csv") as f:
            panel = pd.read_csv(f, dtype={"zona": str})
    base = panel.loc[panel.anio.eq(2024)].dropna(subset=["alquiler_mediano_eur_mes"])
    bases = base.set_index("zona").alquiler_mediano_eur_mes.to_dict()

    class Consultas(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/api/observaciones":
                self.send_error(404)
                return
            try:
                longitud = int(self.headers.get("Content-Length", "0"))
                if not 0 < longitud <= 4096 or self.headers.get_content_type() != "application/json":
                    raise ValueError
                dato = json.loads(self.rfile.read(longitud))
                anio, zona = dato["anio"], dato["zona"]
                real, fuente = float(dato["real"]), dato["fuente"]
                if type(anio) is not int or not isinstance(zona, str) or not isinstance(fuente, str):
                    raise ValueError
                fila = tabla.loc[(anio, zona)]
                # Solo se aceptan medianas positivas con fuente para secciones cuyo importe aún falta en los datos de origen.
                if pd.notna(fila.real) or not math.isfinite(real) or real <= 0 or not 1 <= len(fuente.strip()) <= 300:
                    raise ValueError
                with sqlite3.connect(ruta_db) as db:
                    # Guardamos la estimación y las entradas junto con la mediana comunicada para reconstruir el error de esa consulta.
                    db.execute("""INSERT OR REPLACE INTO observaciones VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                        (anio,zona,real,fuente.strip(),fila.estimado,fila.anterior,fila.cambio_seccion,fila.cambio_ciudad))
            except (ValueError, TypeError, KeyError, UnicodeError):
                self.send_error(400, "Observacion no valida")
                return
            self.send_response(204)
            self.end_headers()

        def do_GET(self):
            ruta = urlsplit(self.path)
            if ruta.path in RECURSOS:
                nombre, tipo = RECURSOS[ruta.path]
                contenido = (WEB / nombre).read_bytes()
            elif ruta.path == "/secciones.json":
                contenido, tipo = secciones, "application/json"
            elif ruta.path == "/api/seguimiento":
                with sqlite3.connect(ruta_db) as db:
                    # Este MAE usa las nuevas medianas registradas. El MAE histórico se calculó por separado con 2023 y 2024.
                    n, error = db.execute("SELECT COUNT(*), AVG(ABS(real-estimado)) FROM observaciones").fetchone()
                contenido, tipo = json.dumps({"n":n,"mae":error}).encode(), "application/json"
            elif ruta.path == "/api/datos.csv":
                with sqlite3.connect(ruta_db) as db:
                    # El CSV permite revisar las fuentes y seleccionar observaciones antes de un futuro reentrenamiento.
                    filas = db.execute("SELECT * FROM observaciones ORDER BY anio,zona")
                    salida = io.StringIO()
                    escritor = csv.writer(salida)
                    escritor.writerow([campo[0] for campo in filas.description])
                    escritor.writerows(filas)
                contenido, tipo = salida.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8"
            elif ruta.path == "/api/secciones":
                contenido = json.dumps({"secciones": catalogo, "mae": mae, "base2024": bases}).encode()
                tipo = "application/json"
            elif ruta.path == "/api/prediccion":
                q = parse_qs(ruta.query)
                try:
                    fila = tabla.loc[(int(q["anio"][0]), q["zona"][0])]
                except (KeyError, ValueError):
                    self.send_error(404, "Consulta desconocida")
                    return
                respuesta = {k: None if pd.isna(fila[k]) else float(fila[k]) for k in ["estimado", "anterior", "real"]}
                contenido, tipo = json.dumps(respuesta, allow_nan=False).encode(), "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(contenido)))
            self.end_headers()
            self.wfile.write(contenido)

    return ThreadingHTTPServer(("127.0.0.1", 0), Consultas)


if __name__ == "__main__":
    archivo = Path(__file__).resolve().with_name("Atlas_Malaga_datos.zip")
    if not archivo.is_file():
        raise SystemExit("Coloca Atlas_Malaga_datos.zip en la misma carpeta que app_malaga.py.")
    # Al iniciar se entrena una vez. Cada consulta recupera el resultado correspondiente a su sección y año.
    tabla, ajuste, metricas = entrenar(archivo)
    with crear_servidor(tabla, metricas.loc["Validación","MAE"], archivo.with_name("observaciones.sqlite3")) as servidor:
        url = f"http://127.0.0.1:{servidor.server_port}"
        print(f"Abre {url} en tu navegador. Para cerrar, pulsa Ctrl+C en la terminal.", flush=True)
        webbrowser.open(url)
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            pass
