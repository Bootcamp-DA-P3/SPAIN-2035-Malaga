# SPAIN 2035 · ¿Podré quedarme en Málaga?

**Proyecto 7 de Regresión · Factoría F5 · Aplicación multipágina**  
**Diseño:** Mediterráneo de Cristal  
**Autoría:** Mohamed

## Acceso a la entrega

- **[Abrir la aplicación completa](https://spain-2035-malaga.streamlit.app/)**
- [Consultar el simulador original](https://spain-2035-malaga.streamlit.app/simulador)
- [Leer la exposición del proyecto dentro de la app](https://spain-2035-malaga.streamlit.app/proyecto)
- **[Memoria técnica de la ampliación](DOCUMENTACION_MULTIPAGINA.md)**
- [Notebook de análisis y modelado](SPAIN_2035_Malaga.ipynb)

## Qué aporta esta versión

El proyecto se amplía desde un atlas de alquiler a una aplicación de ocho páginas
que conecta vivienda, perfiles salariales, presupuesto, compra, economía,
bienestar y evaluación de modelos. El objetivo es estudiar la asequibilidad de
vivir en Málaga y explicar cómo se pasa de los datos a una herramienta interactiva.

El código y la exposición distinguen datos observados, estimaciones del modelo y
escenarios hasta 2035. No se interpreta un escenario de diez años como una
predicción validada a ese horizonte.

| Página | Trabajo que permite examinar |
|---|---|
| Dashboard | Indicadores, serie municipal y margen mensual por perfil salarial. |
| Simulador original | Atlas conservado con mapa, código postal, año y consultas de alquiler. |
| Vivienda y territorio | Evolución, cobertura, distribución, mapa y cambio observado 2023–2024. |
| Presupuesto y ahorro | Neto orientativo, gastos editables, saldo, objetivo de ahorro y escenarios. |
| Acceso a la compra | Tasación u oferta municipal, entrada, provisión de gastos, ahorro y cuota. |
| Economía y bienestar | PIB y WHR de siete países, escenarios de España y contexto local ESMA. |
| Modelo y evaluación | Comparación de métodos, MAE, RMSE, R², residuos y brechas de rendimiento. |
| El proyecto · Exposición | Pregunta, autoría, organización, fuentes y proceso completo hasta la app. |

## Recorrido recomendado para la evaluación

1. Consultar el **notebook** para examinar el EDA y el razonamiento analítico.
2. Abrir **Modelo y evaluación** para revisar los errores y las limitaciones.
3. Explorar **Presupuesto**, **Compra** y **Economía y bienestar** para comprobar
   cómo se conectan los datos y los supuestos con preguntas de uso.
4. Leer **El proyecto · Exposición** y la [memoria técnica](DOCUMENTACION_MULTIPAGINA.md)
   para entender las decisiones y la arquitectura del trabajo.

La profundidad del proyecto se documenta mediante cálculos reproducibles,
comparaciones y decisiones justificadas; el número de páginas no sustituye la
evaluación del modelo ni acredita por sí solo una rúbrica académica.

## Datos y modelo principal

- Panel de **6.104 registros sección–año**, **436 secciones** y **5.182 medianas
  publicadas**; se documentan **922 ausencias de mediana**.
- Objetivo: **alquiler mediano mensual declarado por sección censal**, en euros.
- Entradas del ensemble: alquiler anterior, cambio previo de la sección y cambio
  previo del municipio. El modelo aprende el cambio respecto al alquiler anterior.
- Ajuste hasta 2022 y búsqueda de hiperparámetros con cinco cortes temporales
  de 2018 a 2022. Evaluación retrospectiva sobre **786 filas de 2023–2024**.
- Se comparan una referencia de persistencia, tres regresiones lineales y el
  Gradient Boosting que conserva el simulador.

| Método | MAE · €/mes | RMSE · €/mes | R² |
|---|---:|---:|---:|
| Repetir el último alquiler | 47,67 | 59,69 | 0,8601 |
| Lineal · alquiler previo | 31,65 | 44,25 | 0,9231 |
| Lineal · tendencia local | 31,85 | 44,27 | 0,9231 |
| Lineal · tendencia local y municipal | **27,12** | **39,90** | **0,9375** |
| Gradient Boosting del simulador | 30,52 | 43,90 | 0,9244 |

La lineal con tendencia local y municipal obtiene menor MAE en esta evaluación.
La ampliación hace visible esa comparación y mantiene el ensemble del atlas.
Estos resultados proceden de los datos y versiones probados al preparar la
ampliación; la página de evaluación los recalcula al ejecutarse.

## Ejecución en VS Code

Desde la carpeta del repositorio, con Python 3.11 o posterior:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app_streamlit.py
```

Abrir la dirección local indicada por Streamlit. El callejero del simulador usa
teselas de OpenStreetMap y requiere Internet. Las bases de datos se distribuyen
en `datos/Atlas_Malaga_datos.zip`, que debe mantenerse comprimido.

## Archivos principales y conservación del trabajo

| Archivo | Función |
|---|---|
| `app_streamlit.py` | Entrada y navegación de las ocho páginas. |
| `analisis.py` | Datos, validación temporal, modelos y cálculos de escenarios. |
| `vistas.py` | Interfaz, gráficas, explicaciones e inventario de fuentes. |
| `simulador_original.py` | Implementación del atlas reutilizada por la multipágina. |
| `app_streamlit_antes_multipagina.py` | Copia del archivo de entrada local anterior a la integración. |
| `autor.json` | Datos editables de autoría y organización. |
| `datos/Atlas_Malaga_datos.zip` | Bases originales y documentación de procedencia. |
| `recursos/panorama.jpg` | Recurso visual de Málaga. |
| `SPAIN_2035_Malaga.ipynb` | Análisis exploratorio, experimentos y conclusiones. |
| `requirements.txt` | Dependencias de ejecución y análisis. |

El notebook y los archivos previos no se eliminaron al integrar la ampliación.
Además de la copia del simulador, se creó un respaldo completo fuera del
repositorio antes de incorporar los cambios.

## Límites que deben tenerse presentes

- La evaluación 2023–2024 es retrospectiva: esos años se inspeccionaron durante
  el desarrollo. Una evaluación definitiva requiere un periodo posterior independiente.
- Una brecha relativa de R² inferior al 5 % no implica que la brecha de MAE también
  cumpla ese umbral. No se afirma ausencia universal de sobreajuste.
- Los valores posteriores a 2025 del alquiler de sección son escenarios del 2 %
  anual desde 2024. No están validados como previsión de mercado hasta 2035.
- Los resúmenes de CP son medianas sin ponderar de medianas de sus secciones
  asociadas. No son precios postales oficiales ni estiman oferta disponible.
- Salarios, neto orientativo y gastos parten de referencias de 2024. La compra usa
  referencias municipales; no hay precios de venta verificados para cada CP.
- PIB, evaluación general de vida y satisfacción con vivir en Málaga son indicadores
  distintos. Sus relaciones descriptivas no prueban causalidad individual.
- No se ha implementado registro persistente ni reentrenamiento automático en
  la aplicación multipágina.

## Fuentes y trazabilidad

SERPAVI y estadísticas de tasación del Ministerio de Vivienda; INE; Ayuntamiento
de Málaga; IndesIA/TalentHackers; Eurostat; BCE; Banco Mundial; World Happiness
Report; Universidad de Málaga/ESMA; referencias municipales de oferta de Idealista.

El inventario de la página **El proyecto · Exposición** distingue las bases usadas
en cálculos, las fuentes contextuales y la documentación conservada. Incluye
enlaces de procedencia y descargas. Renta INE, indicadores SIMA y paro se conservan
como contexto y no se atribuyen como entradas del modelo de alquiler.

**La memoria técnica amplía estas decisiones:** [DOCUMENTACION_MULTIPAGINA.md](DOCUMENTACION_MULTIPAGINA.md).
