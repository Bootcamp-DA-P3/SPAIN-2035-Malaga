# Memoria técnica · Ampliación multipágina de SPAIN 2035

## 1. Problema y evolución del trabajo

El proyecto conecta una pregunta económica y personal: ¿es viable vivir en
Málaga, asumir una vivienda y ahorrar? El atlas inicial ya permitía consultar
alquileres. La ampliación integra análisis antes presentes en el notebook,
incorpora controles de sensibilidad y permite revisar la metodología desde
la propia aplicación.

El dashboard actúa como entrada. Las páginas temáticas desarrollan la evidencia
y los supuestos; la última página explica y permite defender el proceso. El
simulador original sigue disponible como parte del recorrido.

## 2. Preparación de los datos y control de calidad

La unidad del panel es una sección y un año. Los identificadores se conservan
como texto para evitar conversiones que dañen las uniones. Se comprueba la
ausencia de duplicados sección–año y se separan valores publicados de ausencias.
Una mediana no publicada no se sustituye por cero ni se inventa para entrenar.

El panel contiene 6.104 filas, 436 secciones y 5.182 medianas publicadas. La
serie municipal se utiliza desde su tabla propia: no se reconstruye promediando
las medianas de sección. La cartografía de referencia es del INE de 2021 y el
cruce postal se reutiliza del atlas.

Cada sección asociada a un CP tiene el mismo peso en los resúmenes analíticos.
Las secciones pueden solaparse con varios CP; sus resultados no equivalen a una
mediana postal oficial ni al porcentaje de pisos disponibles.

## 3. Modelos y prevención de fugas de información

Se define un objetivo numérico: alquiler mediano mensual declarado por sección.
Las tres entradas del ensemble son el último alquiler, su cambio previo local
y el cambio previo municipal. No se emplean cuartiles o alquiler por m² del año
objetivo, que contendrían información de lo que se quiere predecir.

Se comparan cinco métodos sobre las mismas filas: repetir el último alquiler,
tres variantes de regresión lineal y Gradient Boosting. El ensemble combina
árboles sucesivos y estima el cambio respecto al último alquiler.

La búsqueda de Gradient Boosting usa pérdida Huber, 40 árboles y semilla 42;
explora profundidad 1 o 2 y mínimo de muestras por hoja 15 o 45. La configuración
seleccionada en el paquete probado es profundidad 2 y 15 muestras por hoja.

Los modelos se ajustan hasta 2022. Los hiperparámetros y variantes lineales se
comparan con cortes temporales internos 2018–2022. La evaluación posterior usa
2023–2024: no se divide el panel aleatoriamente mezclando futuro y pasado.
Este planteamiento supone disponibles los alquileres previos al hacer cada
consulta; no reproduce el calendario real de publicación de cada estadística.

## 4. Interpretación de la evaluación

- **MAE:** magnitud media del error absoluto en euros al mes. Es la medida
  principal para comparar el error práctico de predicción.
- **RMSE:** raíz de la media del error cuadrático; da mayor peso a errores grandes.
- **R²:** compara la suma de errores con una predicción constante basada en la
  media de la muestra evaluada. No es un porcentaje de predicciones correctas.
- **Residuo:** observado menos predicho. Un valor positivo indica infraestimación.

Gradient Boosting obtiene aproximadamente MAE 30,52 €, RMSE 43,90 € y R² 0,9244
en 786 filas de 2023–2024. La referencia de persistencia tiene MAE 47,67 €.
La lineal con tendencia local y municipal obtiene MAE 27,12 € en esas mismas
filas. Se muestra esta diferencia y no se presenta el ensemble como ganador
de todos los criterios.

La brecha relativa de MAE del ensemble ronda el 42,78 %, mientras que la de R²
ronda el 2,39 %. Ambas comparan entrenamiento y validación, pero no significan
lo mismo. No basta elegir la cifra menor para concluir que no hay sobreajuste.
Además, 2023–2024 ya se había inspeccionado durante el desarrollo. La página
explica por qué hace falta un periodo posterior independiente.

## 5. Del modelo a las preguntas de presupuesto

Las bandas salariales de Data Analyst en Málaga proceden del informe 2024 de
IndesIA/TalentHackers. El neto se aproxima interpolando referencias de Eurostat
para una persona sola sin hijos, dentro del rango disponible, y dividiéndolo
entre doce meses. No es un cálculo de IRPF personalizado.

Para gastos se usa EPF de Andalucía 2024. Se excluyen el índice general y el
grupo 04 de vivienda para evitar doble contabilización del alquiler. Los
suministros se añaden como supuesto explícito, inicialmente 100 €/mes.

Saldo mensual = neto − alquiler − otros gastos − suministros.

La interfaz permite cambiar el alquiler de referencia, los gastos y el objetivo
de ahorro. Los escenarios mantienen constantes las referencias salariales y
otros gastos; modificar solo el alquiler no simula toda la economía futura.

## 6. Acceso a compra y sensibilidad

Se permite elegir tasación municipal 2024 T4 u oferta municipal octubre 2026,
conceptos diferentes que se identifican expresamente. El precio se aproxima
como superficie por valor por metro cuadrado. La superficie inicial de la
ampliación y del simulador recuperado es 75 m²; puede cambiarse en la página
de compra. No se utiliza una muestra filtrada de anuncios por dormitorios.

Entrada = precio × (1 − fracción financiada).
Provisión de gastos = precio × fracción de gastos.
Objetivo pendiente = máximo entre cero y entrada + provisión − ahorros iniciales.

El plazo redondea al alza objetivo pendiente / ahorro mensual. Si el ahorro es
nulo o negativo no existe un plazo finito, salvo si el objetivo ya está cubierto.
La hipoteca se simula con cuota mensual constante, incluyendo el caso de tipo
cero. La referencia inicial del tipo procede del BCE de diciembre 2024.
Estos cálculos no determinan concesión bancaria ni liquidan impuestos reales.

## 7. Economía y bienestar: conservar la pregunta inicial

Se recuperan PIB real por persona en PPA y evaluación de vida WHR para España,
Alemania, Países Bajos, Dinamarca, Suiza, Noruega y Suecia. Se conservan los huecos
temporales, sin crear observaciones ficticias para dibujar las curvas.

Los escenarios de PIB prolongan ritmos históricos constantes. La encuesta ESMA
aporta satisfacción con vivir en Málaga; el WHR mide evaluación general de vida.
No se confunden estas preguntas ni se presenta una relación descriptiva como
causa de la felicidad individual.

La serie de ediciones del simulador y la serie del EDA tienen referencias
temporales distintas. La aplicación advierte que no se han fusionado como
si constituyeran una sola serie homogénea.

## 8. Arquitectura y construcción de la aplicación

- `app_streamlit.py`: configuración y navegación mediante Streamlit.
- `analisis.py`: lectura de datos, cacheado, ajustes, métricas y escenarios.
- `vistas.py`: páginas, controles, gráficos, textos metodológicos e inventario.
- `simulador_original.py`: atlas existente, reutilizado sin reescribir su interfaz.
- `autor.json`: datos de autoría separados de los cálculos.

Se utilizan pandas y NumPy para tablas y operaciones; scikit-learn para ajustar
modelos; Plotly para gráficos; Streamlit para los controles y la navegación.
El atlas conserva HTML, CSS, JavaScript y Leaflet. Los comentarios de los
módulos nuevos explican en español los cálculos y sus límites.

La separación permite revisar un cálculo sin modificar el diseño y añadir
vistas sin rehacer el modelo. El cacheado evita recalcular los ajustes en cada
interacción. El CP y el año se comparten entre páginas analíticas; el simulador
mantiene sus propios controles, sin sincronización automática con ellas.

## 9. Comprobaciones realizadas y alcance

Durante la preparación se ejecutaron las ocho páginas con Streamlit AppTest,
la entrada de navegación y casos límite de ahorro, financiación y selección de
países. Se probaron 104 combinaciones analíticas: 26 CP por cuatro años
(2023, 2024, 2025 y 2035). Se contrastaron las tablas del atlas con las del ZIP
y la integridad del simulador conservado con el archivo recuperado entonces.

En la integración se creó un respaldo completo del proyecto local y una copia
de su entrada anterior. El usuario confirmó el funcionamiento local; tras la
publicación se observó en la web la carga del dashboard, el simulador y la
exposición. Esto no equivale a una prueba exhaustiva de todos los controles
en todos los navegadores ni a una validación futura del modelo.

No se han añadido pruebas continuas automáticas en GitHub. Tampoco se han
implementado una base persistente de observaciones nuevas o reentrenamiento.

## 10. Fuentes y distinción de usos

El ZIP `datos/Atlas_Malaga_datos.zip` conserva el inventario original y los
archivos de procedencia. La exposición ofrece una tabla con función y enlaces
para las tablas de SERPAVI, cartografía INE, renta INE, tasación, salarios,
EPF, Eurostat, BCE, SIMA, ESMA, WHR y Banco Mundial.

El inventario distingue lo empleado en cálculos de lo conservado para contexto.
Renta INE, SIMA y paro no se presentan como entradas del modelo de alquiler.
El mapa postal, las referencias de Idealista y la serie auxiliar del simulador
se documentan por separado. Las referencias de oferta de 2026 se conservaron
del simulador; no se verificaron de nuevo al preparar esta documentación.

## 11. Qué puede defenderse y qué queda abierto

Puede defenderse la trazabilidad desde una pregunta hasta datos preparados,
modelos comparados, errores medidos y una aplicación con controles explicables.
Las páginas conectan partes del análisis que antes no quedaban visibles en
el atlas. Su aportación es analítica y de comunicación, además de visual.

Quedan abiertas una evaluación temporal posterior independiente, la actualización
de fuentes y supuestos, y la incorporación futura de observaciones verificadas.
Los escenarios 2030–2035 no tienen probabilidades asignadas. La evaluación
académica corresponde al profesor y a su rúbrica, no al número de funciones.
