from zipfile import ZipFile
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

VARIABLES = ["anterior", "cambio_seccion", "cambio_ciudad"]

def preparar(archivo):
    objetivo = "alquiler_mediano_eur_mes"
    with ZipFile(archivo) as datos:
        with datos.open("Datos_Malaga/alquiler_seccion_malaga.csv") as f:
            panel = pd.read_csv(f, dtype={"zona": str})
        with datos.open("Datos_Malaga/alquiler_municipio_malaga.csv") as f:
            municipal = pd.read_csv(f).set_index("anio")[objetivo]
    alquiler = panel.pivot(index="anio", columns="zona", values=objetivo)
    # La cuadrícula conserva los años sin dato y añade el siguiente año que la aplicación puede estimar.
    alquiler = alquiler.reindex(range(alquiler.index.min(), alquiler.index.max() + 2))
    filas = []
    for anio in alquiler.index[2:]:
        anterior = alquiler.loc[anio - 1]
        bloque = pd.DataFrame({"anterior": anterior, "cambio_seccion": anterior - alquiler.loc[anio - 2],
                               "cambio_ciudad": municipal.get(anio - 1) - municipal.get(anio - 2),
                               "real": alquiler.loc[anio], "anio": anio})
        # Una sección puede tener predicción con dos años previos aunque todavía falte la mediana del año objetivo.
        filas.append(bloque.dropna(subset=["anterior", "cambio_seccion", "cambio_ciudad"]))
    historial = pd.concat(filas).reset_index()
    return historial


def entrenar(archivo):
    datos = preparar(archivo)
    train = datos[datos.anio.le(2022)].dropna(subset=["real"]).reset_index(drop=True)
    validacion = datos[datos.anio.between(2023, 2024)].dropna(subset=["real"])
    # Cada pareja contiene índices de entrenamiento y validación. En el corte de 2020 solo se ajusta con años anteriores a 2020.
    cortes = [(np.flatnonzero(train.anio < anio), np.flatnonzero(train.anio == anio))
              for anio in range(2018, 2023)]
    # Aprender el cambio en euros permite usar el último alquiler como referencia.
    busqueda = GridSearchCV(
        # Huber reduce la influencia de errores extremos. La profundidad y el mínimo de filas por hoja controlan la complejidad.
        GradientBoostingRegressor(random_state=42, loss="huber", n_estimators=40),
        {"max_depth": [1, 2], "min_samples_leaf": [15, 45]},
        scoring="neg_mean_absolute_error", cv=cortes, refit=True)
    # GridSearchCV maximiza el MAE con signo negativo: gana la configuración con menor error medio en los cinco cortes.
    busqueda.fit(train[VARIABLES], train.real - train.anterior)
    consulta = datos.loc[datos.anio.between(2023, 2025)].copy()
    consulta["estimado"] = predecir(busqueda, consulta)
    resultados = []
    for etiqueta, filas in [("Entrenamiento", train), ("Validación", validacion)]:
        pred = predecir(busqueda, filas)
        resultados.append([etiqueta, len(filas), mean_absolute_error(filas.real, pred),
                           np.sqrt(mean_squared_error(filas.real, pred)), r2_score(filas.real, pred)])
    metricas = pd.DataFrame(resultados, columns=["Periodo", "n", "MAE", "RMSE", "R²"]).set_index("Periodo")
    return consulta.set_index(["anio", "zona"]).sort_index(), busqueda, metricas

def predecir(modelo, datos):
    # Los árboles estiman un cambio en euros; sumarlo a la última mediana recupera un alquiler mensual.
    return datos.anterior + modelo.predict(datos[VARIABLES])
