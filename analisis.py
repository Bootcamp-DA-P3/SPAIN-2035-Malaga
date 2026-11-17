"""Cálculos reproducibles de SPAIN 2035. Datos, modelos y escenarios separados.

El simulador aprobado se conserva en otro módulo sin modificar su contenido.
Este módulo reutiliza su preparación temporal y calcula las nuevas vistas.
"""
from pathlib import Path
from zipfile import ZipFile
import base64
import io
import json
import math
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import simulador_original as original

RAIZ = Path(__file__).resolve().parent
ARCHIVO = RAIZ / "datos" / "Atlas_Malaga_datos.zip"
OBJETIVO = "alquiler_mediano_eur_mes"
VIDA = "Life evaluation (3-year average)"
PAISES = {"ESP": "Spain", "DEU": "Germany", "NLD": "Netherlands", "DNK": "Denmark",
          "CHE": "Switzerland", "NOR": "Norway", "SWE": "Sweden"}
NOMBRES = {"Spain": "España", "Germany": "Alemania", "Netherlands": "Países Bajos",
           "Denmark": "Dinamarca", "Switzerland": "Suiza", "Norway": "Noruega", "Sweden": "Suecia"}


@st.cache_data
def leer(nombre):
    """Lee los CSV conservando los identificadores territoriales como texto."""
    with ZipFile(ARCHIVO) as z:
        return pd.read_csv(z.open("Datos_Malaga/" + nombre + ".csv"), dtype={"zona": str})


@st.cache_data
def geografia():
    """Reutiliza exactamente el cruce postal y la cartografía del simulador."""
    with ZipFile(io.BytesIO(base64.b64decode(original.RECURSOS))) as z:
        return json.loads(z.read("postales.json")), json.loads(z.read("Datos_Malaga/mapa_secciones_malaga_2021.geojson"))


@st.cache_data(show_spinner="Evaluando los modelos con cortes temporales…")
def modelos():
    """Ajusta hasta 2022 y compara sobre las mismas filas de 2023–2024.

    El Gradient Boosting mantiene la búsqueda de cinco cortes del simulador.
    Las regresiones lineales reproducen las tres variantes del notebook.
    La selección lineal usa únicamente cortes 2018–2022. La evaluación posterior
    es retrospectiva: esos años ya se inspeccionaron durante el desarrollo.
    """
    archivo = io.BytesIO(base64.b64decode(original.RECURSOS))
    consulta, gb, _ = original.entrenar(archivo)
    historial = original.preparar(archivo)
    train = historial[historial.anio.le(2022)].dropna(subset=["real"])
    val = historial[historial.anio.between(2023, 2024)].dropna(subset=["real"])
    variables = {"Lineal · alquiler previo": ["anterior"],
                 "Lineal · tendencia local": ["anterior", "cambio_seccion"],
                 "Lineal · local y municipal": original.VARIABLES}
    cortes = []
    for anio in range(2018, 2023):
        t = train[train.anio.lt(anio)]
        v = train[train.anio.eq(anio)]
        for nombre, cols in variables.items():
            m = LinearRegression().fit(t[cols], t.real)
            cortes.append({"Año": anio, "Modelo": nombre, "n": len(v),
                           "MAE": mean_absolute_error(v.real, m.predict(v[cols]))})
    cv = pd.DataFrame(cortes)
    ranking = (cv.MAE * cv.n).groupby(cv.Modelo).sum() / cv.groupby("Modelo").n.sum()
    elegido = ranking.idxmin()
    met = []
    predicciones = val[["zona", "anio", "real", "anterior"]].copy()
    for nombre in ["Repetir último alquiler", *variables, "Gradient Boosting"]:
        if nombre in variables:
            cols = variables[nombre]
            m = LinearRegression().fit(train[cols], train.real)
        for periodo, muestra in [("Entrenamiento", train), ("Validación 2023–2024", val)]:
            if nombre == "Repetir último alquiler":
                p = muestra.anterior.to_numpy()
            elif nombre == "Gradient Boosting":
                p = original.predecir(gb, muestra)
            else:
                p = m.predict(muestra[cols])
            met.append({"Modelo": nombre, "Periodo": periodo, "n": len(muestra),
                        "MAE": mean_absolute_error(muestra.real, p),
                        "RMSE": float(np.sqrt(mean_squared_error(muestra.real, p))),
                        "R²": r2_score(muestra.real, p)})
            if periodo.startswith("Validación"):
                predicciones[nombre] = p
    return {"consulta": consulta.reset_index(), "metricas": pd.DataFrame(met),
            "predicciones": predicciones, "cv": cv, "lineal_elegida": elegido,
            "parametros": gb.best_params_, "mae_cv_gb": -gb.best_score_}


def seleccion(anio, cp):
    """Devuelve valores por sección asociada al CP, sin inventar un precio postal.

    2023–2024: medianas declaradas; 2025: modelo a un año; 2026–2035:
    escenario compuesto del 2 % desde 2024. Una sección puede solaparse con
    varios CP. No se pondera por hogares, viviendas ni superficie de cruce.
    """
    postales, _ = geografia()
    zonas = postales["codigos"][cp]
    if anio <= 2024:
        d = leer("alquiler_seccion_malaga")
        s = d[d.anio.eq(anio)].set_index("zona")[OBJETIVO]
        tipo = "Dato observado · SERPAVI"
    elif anio == 2025:
        d = modelos()["consulta"]
        s = d[d.anio.eq(anio)].set_index("zona").estimado
        tipo = "Modelo a un año · Gradient Boosting"
    else:
        d = leer("alquiler_seccion_malaga")
        s = d[d.anio.eq(2024)].set_index("zona")[OBJETIVO] * 1.02 ** (anio - 2024)
        tipo = "Escenario · +2 % anual desde 2024"
    return s.reindex(zonas).dropna(), tipo


def neto_mensual(bruto):
    """Interpola el neto Eurostat 2024 para una persona sola sin hijos.

    No es una liquidación individual de IRPF. Se rechaza extrapolar fuera de
    los sueldos disponibles y se reparte el neto anual en doce mensualidades.
    """
    f = leer("fiscalidad_siete_paises")
    f = f[(f.pais == "ES") & (f.anio == 2024) & (f.moneda == "EUR") & f.perfil.str.startswith("P1_NCH_AW")]
    escala = f.pivot(index="perfil", columns="concepto", values="euros_anuales").sort_values("GRS")
    if not escala.GRS.min() <= bruto <= escala.GRS.max():
        raise ValueError("El sueldo queda fuera de la escala fiscal disponible.")
    return float(np.interp(bruto, escala.GRS, escala.NET) / 12)


def gastos_base():
    """Evita contar dos veces vivienda: excluye agregado general y grupo 04."""
    d = leer("gastos_andalucia").query("Periodo == 2024").copy()
    d["codigo"] = d["Grupos de gasto (2 dígitos)"].str.extract(r"^(\d{2})")[0]
    d = d[d.codigo.notna() & d.codigo.ne("04")]
    return float(d.euros_persona_anio.sum() / 12)


def perfiles():
    """Bandas salariales originales; el punto central es un supuesto de perfil."""
    d = leer("salario_data_analyst").copy()
    d["Perfil"] = d.experiencia_anios.map({"0-2": "Júnior", "2-5": "Intermedio", "5-10": "Sénior"})
    d["Bruto central"] = (d.banda_inferior_eur_anuales + d.banda_superior_eur_anuales) / 2
    d["Neto mensual"] = d["Bruto central"].map(neto_mensual)
    return d


def cuota(capital, tipo, anios):
    """Cuota constante: capital·r / (1−(1+r)^−n). Caso tipo cero separado."""
    if capital < 0 or tipo < 0 or anios <= 0:
        raise ValueError("Capital y tipo deben ser no negativos y el plazo positivo.")
    n, r = int(anios * 12), tipo / 1200
    return capital / n if r == 0 else capital * r / (1 - (1 + r) ** -n)


def plazo_ahorro(objetivo, inicial, mensual):
    """Meses para reunir entrada y provisión de gastos, sin rendimientos."""
    pendiente = max(0, objetivo - inicial)
    if pendiente == 0:
        return 0
    return None if mensual <= 0 else math.ceil(pendiente / mensual)


def contexto():
    """Cruza país y año, sin interpolar huecos ni inferir causalidad."""
    p = leer("economia_siete_paises").query("codigo == 'NY.GDP.PCAP.PP.KD'").copy()
    p["Country name"] = p.iso3.map(PAISES)
    w = leer("bienestar_whr_siete_paises")
    return p.merge(w, left_on=["Country name", "anio"], right_on=["Country name", "Year"]).dropna(subset=["valor", VIDA])
