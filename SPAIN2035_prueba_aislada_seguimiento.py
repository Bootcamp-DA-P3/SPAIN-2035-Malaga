# -*- coding: utf-8 -*-
"""SPAIN 2035: prueba aislada de registro, seguimiento y CSV.

Este script NO modifica el proyecto real: copia los archivos necesarios en
una carpeta temporal, inicia allí una instancia independiente y realiza una
única observación ficticia *solo* en la base de datos temporal.
Al finalizar, cierra esa instancia y elimina su copia temporal.
"""
from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


RAIZ = Path.cwd()
NECESARIOS = ("app_malaga.py", "modelo.py", "Atlas_Malaga_datos.zip")


def consultar(url: str, *, datos: dict | None = None):
    """Consultar una API y devolver (estado HTTP, contenido, tipo MIME)."""
    cuerpo = None if datos is None else json.dumps(datos).encode("utf-8")
    cabeceras = {} if datos is None else {"Content-Type": "application/json"}
    peticion = urllib.request.Request(url, data=cuerpo, headers=cabeceras)
    try:
        with urllib.request.urlopen(peticion, timeout=5) as respuesta:
            return respuesta.status, respuesta.read().decode("utf-8-sig"), respuesta.headers.get_content_type()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8-sig", errors="replace"), "error"


def ejecutar_prueba():
    # 1. Verificamos que se ejecuta desde Nivel_2, sin alterar archivo alguno.
    faltan = [n for n in NECESARIOS if not (RAIZ / n).is_file()]
    if not (RAIZ / "web").is_dir():
        faltan.append("web/")
    if faltan:
        raise RuntimeError("Ejecuta desde Nivel_2. Faltan: " + ", ".join(faltan))

    # 2. Preparamos una COPIA TEMPORAL. El fichero SQLite original no se copia:
    #    la instancia de prueba creará su propia base nueva.
    with tempfile.TemporaryDirectory(prefix="spain2035_prueba_") as carpeta:
        temporal = Path(carpeta)
        for nombre in NECESARIOS:
            shutil.copy2(RAIZ / nombre, temporal / nombre)
        shutil.copytree(RAIZ / "web", temporal / "web")

        # 3. Lanzamos la aplicación copiada en un proceso independiente.
        #    Desactivamos únicamente la apertura automática del navegador.
        lanzador = (
            "import runpy,webbrowser; "
            "webbrowser.open=lambda *a,**k: True; "
            "webbrowser.open_new_tab=lambda *a,**k: True; "
            "runpy.run_path('app_malaga.py',run_name='__main__')"
        )
        proceso = subprocess.Popen(
            [sys.executable, "-u", "-c", lanzador],
            cwd=temporal,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        mensajes: queue.Queue[str] = queue.Queue()

        def recoger_salida():
            assert proceso.stdout is not None
            for linea in proceso.stdout:
                mensajes.put(linea.rstrip())

        lector = threading.Thread(target=recoger_salida, daemon=True)
        lector.start()
        salida = []
        url_base = None
        try:
            # 4. Esperamos al servidor copiado, no al servidor real del proyecto.
            limite = time.monotonic() + 35
            while time.monotonic() < limite:
                try:
                    linea = mensajes.get(timeout=0.3)
                    salida.append(linea)
                    puerto = re.search(r"http://127\.0\.0\.1:(\d+)", linea)
                    if puerto:
                        url_base = f"http://127.0.0.1:{puerto.group(1)}"
                        break
                except queue.Empty:
                    if proceso.poll() is not None:
                        break
            if url_base is None:
                ultimas = "\n".join(salida[-12:])
                raise RuntimeError("La copia del servidor no inició.\n" + ultimas)

            estado, contenido, _ = consultar(url_base + "/api/seguimiento")
            if estado != 200:
                raise RuntimeError(f"Seguimiento responde HTTP {estado}: {contenido[:400]}")
            antes = json.loads(contenido)
            numero_antes = int(antes.get("n", -1))
            if numero_antes != 0:
                raise RuntimeError("La copia de prueba no comenzó vacía. Se detiene por precaución.")
            print("1/4 API de seguimiento: CORRECTA (0 registros iniciales)")

            # 5. Buscamos una zona para la que ya exista predicción oficial
            #    del modelo, a fin de usar un identificador válido en la prueba.
            estado, contenido, _ = consultar(url_base + "/api/secciones")
            if estado != 200:
                raise RuntimeError(f"Catálogo de zonas: HTTP {estado}")
            catalogo = json.loads(contenido)
            candidatos = list(catalogo.get("base2024", {}).keys())
            if not candidatos:
                candidatos = list(catalogo.get("secciones", {}).get("2025", []))
            candidato = None
            for zona in candidatos[:100]:
                ruta = "/api/prediccion?" + urllib.parse.urlencode({"anio": 2025, "zona": zona})
                estado, contenido, _ = consultar(url_base + ruta)
                if estado != 200:
                    continue
                prediccion = json.loads(contenido)
                estimado = prediccion.get("estimado")
                if isinstance(estimado, (int, float)) and estimado > 0:
                    candidato = (zona, float(estimado))
                    break
            if candidato is None:
                raise RuntimeError("No se encontró ninguna zona válida para la prueba de registro.")
            zona, valor_ficticio = candidato
            print("2/4 API de predicción: CORRECTA (zona válida localizada)")

            # 6. Insertamos un registro FICTICIO solo en la copia temporal.
            #    No es un dato publicado y no será utilizado para entrenar.
            observacion = {
                "anio": 2025,
                "zona": str(zona),
                "real": round(valor_ficticio, 2),
                "fuente": "PRUEBA TECNICA FICTICIA - NO OFICIAL",
            }
            estado, contenido, _ = consultar(url_base + "/api/observaciones", datos=observacion)
            if not 200 <= estado < 300:
                raise RuntimeError(f"Registro de observaciones: HTTP {estado}: {contenido[:400]}")
            print("3/4 Registro de observación en copia temporal: CORRECTO")

            # 7. Verificamos que el seguimiento y la exportación ven el registro.
            estado, contenido, _ = consultar(url_base + "/api/seguimiento")
            if estado != 200:
                raise RuntimeError(f"Seguimiento posterior: HTTP {estado}")
            despues = json.loads(contenido)
            if int(despues.get("n", -1)) != 1:
                raise RuntimeError(f"El seguimiento no cuenta una observación: {despues}")
            estado, csv, _ = consultar(url_base + "/api/datos.csv")
            if estado != 200 or str(zona) not in csv:
                raise RuntimeError("El CSV no refleja la observación de prueba.")
            print("4/4 Seguimiento y CSV: CORRECTOS (1 registro solo en la copia)")
            print("\nRESULTADO: PRUEBA COMPLETADA, SIN CAMBIOS EN TU PROYECTO REAL.")
            print("Puedes documentar que la API acepta, registra, monitoriza y exporta observaciones.")
            print("El reentrenamiento con nuevos datos sigue pendiente de implementar.")
        finally:
            # 8. Cerramos el servidor de pruebas y eliminamos sus datos.
            proceso.terminate()
            try:
                proceso.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proceso.kill()
                proceso.wait(timeout=5)


if __name__ == "__main__":
    try:
        ejecutar_prueba()
    except Exception as error:
        print("\nLA PRUEBA NO SE COMPLETÓ:", error)
        print("No se han añadido observaciones a la base de datos real.")
        sys.exit(1)
