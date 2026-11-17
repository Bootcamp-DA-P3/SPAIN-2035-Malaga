"""Páginas visibles y explicaciones de SPAIN 2035.

Los cálculos viven en analisis.py. Las gráficas indican unidades, fechas y
ámbito para evitar mezclar precios de oferta con alquileres declarados.
"""
import base64
import html
import json
import re
from zipfile import ZipFile
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import analisis as a
import simulador_original as original

AZUL, CIAN, ORO = "#0755ac", "#00a8bb", "#bc9146"
COLORES = [AZUL, CIAN, ORO, "#6381bf", "#d07e66", "#63a391", "#9169ad"]


def euros(x):
    return f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def aplicar_estilo():
    """Marco azul, transparencias y esquinas suaves del diseño aprobado."""
    st.html("""<style>
    .stApp{background:linear-gradient(145deg,#edfaff 0%,#e0f2fc 45%,#c9e9f6 100%);color:#12334f}
    [data-testid="stSidebar"]{background:linear-gradient(170deg,#082c68,#065b8b);}
    [data-testid="stSidebar"] *{color:#f1fbff!important}
    [data-testid="stSidebarNavLink"][aria-current="page"]{background:#ffffff22;border-radius:12px}
    [data-testid="stMetric"]{background:#ffffffb8;border:1px solid #ffffff;border-radius:20px;padding:18px;box-shadow:0 8px 30px #135c8e0a}
    [data-testid="stMetricLabel"]{color:#375574}
    [data-testid="stMainBlockContainer"]{max-width:1450px;padding-top:2rem}
    h1,h2,h3{color:#064a83;letter-spacing:-.025em}
    .hero{border:1px solid #ffffff88;border-radius:28px;padding:34px;margin-bottom:24px;background:linear-gradient(110deg,#06326be8,#097a9cc7);color:white;box-shadow:0 15px 40px #0a51821c}
    .hero h1,.hero h2{color:white;margin:6px 0 10px}.hero p{max-width:800px;color:#e7faff}.eyebrow{font-size:12px;letter-spacing:.19em;text-transform:uppercase;color:#a4f1f4}
    .card{background:#ffffffbb;border:1px solid white;border-radius:20px;padding:23px;margin:10px 0 18px;min-height:165px;box-shadow:0 8px 25px #04588d08}
    .card h3{font-size:1.15rem;margin:0 0 10px}.card p{font-size:.98rem;margin:0;line-height:1.65}
    .step{color:#05899d;font-weight:700;font-size:.8rem;letter-spacing:.12em}
    [data-testid="stPlotlyChart"]{border-radius:20px;overflow:hidden;border:1px solid #ffffff}
    </style>""")


def cabecera(titulo, texto, etiqueta="SPAIN 2035 · MÁLAGA"):
    foto = base64.b64encode((a.RAIZ / "recursos" / "panorama.jpg").read_bytes()).decode()
    st.html(f'<style>.hero{{background:linear-gradient(100deg,#052c65ee,#066785aa),url("data:image/jpeg;base64,{foto}") center 45% / cover}}</style>')
    st.html(f'<div class="hero"><div class="eyebrow">{html.escape(etiqueta)}</div><h1>{html.escape(titulo)}</h1><p>{html.escape(texto)}</p></div>')


def tarjeta(titulo, texto, numero=""):
    st.html(f'<article class="card"><div class="step">{html.escape(numero)}</div><h3>{html.escape(titulo)}</h3><p>{html.escape(texto)}</p></article>')


def grafica(fig, texto=None):
    """Presenta todos los gráficos con el mismo lenguaje visual y descarga PNG."""
    fig.update_layout(template="plotly_white", colorway=COLORES, paper_bgcolor="rgba(255,255,255,.72)",
                      plot_bgcolor="rgba(255,255,255,.1)", margin=dict(l=25, r=25, t=60, b=40),
                      font=dict(family="Segoe UI, sans-serif", color="#16456b"),
                      legend=dict(orientation="h", y=-.22), height=370)
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
    if texto:
        st.caption(texto)


def controles():
    """Comparte año y CP entre páginas analíticas; el atlas mantiene sus controles."""
    postales, _ = a.geografia()
    codigos = sorted(postales["codigos"])
    st.session_state.setdefault("anio_analisis", 2025)
    st.session_state.setdefault("cp_analisis", "29012" if "29012" in codigos else codigos[0])
    c1, c2 = st.columns([1, 1])
    with c1:
        anio = st.selectbox("Año de consulta", list(range(2023, 2036)), key="anio_analisis")
    with c2:
        cp = st.selectbox("Código postal de referencia", codigos, key="cp_analisis")
    s, tipo = a.seleccion(anio, cp)
    st.caption(f"{tipo}. El resumen del CP es la mediana sin ponderar de las medianas de sus secciones asociadas; no es un precio postal publicado. Cobertura: {len(s)} secciones con dato.")
    return anio, cp, s


def dashboard():
    cabecera("¿Podré quedarme en Málaga?", "Vivienda, ingresos y bienestar en una misma mirada. Explora los datos, comprueba los errores del modelo y compara escenarios hasta 2035.", "DASHBOARD · MEDITERRÁNEO DE CRISTAL")
    anio, cp, s = controles()
    if s.empty:
        st.info("Este código postal no tiene datos suficientes para este año. Prueba otra selección.")
        return
    perfiles = a.perfiles()
    neto = perfiles.iloc[0]["Neto mensual"]
    saldo = neto - a.gastos_base() - 100 - s.median()
    m = a.modelos()["metricas"].query("Modelo == 'Gradient Boosting' and Periodo == 'Validación 2023–2024'").iloc[0]
    w = a.leer("bienestar_whr_siete_paises").query("`Country name` == 'Spain'").sort_values("Year").iloc[-1]
    cols = st.columns(4)
    for col, label, val, ayuda in [
        (cols[0], f"Alquiler · CP {cp} · {anio}", euros(s.median()), "Resumen territorial sin ponderación; no es una oferta de piso."),
        (cols[1], "Saldo mensual · perfil júnior", euros(saldo), "Neto y gastos de referencia 2024 constantes; suministros supuestos: 100 €/mes."),
        (cols[2], "Error medio del modelo", euros(m.MAE), "MAE por sección en 2023–2024; no mide el error de los escenarios de 2035."),
        (cols[3], f"España · WHR {int(w.Year)}", f"{w[a.VIDA]:.3f}".replace(".", ",") + " / 10", "Evaluación agregada de vida, media de tres años; no es felicidad individual.")]:
        col.metric(label, val, help=ayuda)
    c1, c2 = st.columns(2)
    with c1:
        ciudad = a.leer("alquiler_municipio_malaga")
        grafica(px.line(ciudad, x="anio", y=a.OBJETIVO, markers=True,
                        title="El alquiler declarado ha cambiado", labels={"anio": "Año observado", a.OBJETIVO: "Mediana municipal · €/mes"}),
                "SERPAVI · serie municipal propia, no promedio de secciones. No equivale al precio de los anuncios actuales.")
    with c2:
        p = perfiles[["Perfil", "Neto mensual"]].copy()
        p["Saldo mensual"] = p["Neto mensual"] - a.gastos_base() - 100 - s.median()
        fig = px.bar(p, x="Perfil", y="Saldo mensual", color="Perfil", title=f"¿Qué margen deja ese alquiler? · {anio}", labels={"Saldo mensual": "€/mes"})
        fig.add_hline(y=200, line_dash="dot", line_color=ORO, annotation_text="Objetivo ilustrativo: 200 €")
        grafica(fig, "Punto central de cada banda salarial 2024, neto Eurostat interpolado y gastos regionales 2024. Supuesto de una persona que paga todo el alquiler.")
    c1, c2, c3 = st.columns(3)
    with c1:
        tarjeta("Explora la vivienda", "Consulta el atlas original y compara evolución, cobertura y distribución territorial.")
        st.markdown("[Ir al simulador](simulador)")
    with c2:
        tarjeta("Haz tus números", "Cambia ingresos, gastos, entrada y financiación para ver cómo varía el margen.")
        st.markdown("[Ver presupuesto](presupuesto)")
    with c3:
        tarjeta("Comprende el proyecto", "Recorre la pregunta, los datos, el modelo y el proceso de construcción de la aplicación.")
        st.markdown("[Ver exposición](proyecto)")


def simulador():
    st.caption("Simulador original · conserva sus propios controles de código postal, mapa y año.")
    # Se reutiliza el HTML exacto, los datos y el ajuste del original. No se llama
    # a main(), porque su configuración de página pertenece a la entrada antigua.
    st.iframe(original.construir_atlas(), height=1050, alt="Atlas original Mediterráneo de Cristal")


def vivienda():
    cabecera("Vivienda y territorio", "Cómo cambia el alquiler declarado, dónde hay datos y cuánta heterogeneidad se esconde tras una sola cifra.")
    anio, cp, s = controles()
    panel, ciudad = a.leer("alquiler_seccion_malaga"), a.leer("alquiler_municipio_malaga")
    c1, c2 = st.columns(2)
    with c1:
        grafica(px.line(ciudad, x="anio", y=a.OBJETIVO, markers=True, title="Mediana municipal observada · 2011–2024", labels={"anio": "Año", a.OBJETIVO: "€/mes"}))
    with c2:
        cobertura = panel.groupby("anio")[a.OBJETIVO].count().reset_index(name="Secciones con dato")
        grafica(px.bar(cobertura, x="anio", y="Secciones con dato", title="Cobertura del panel", labels={"anio": "Año"}), "Un vacío es ausencia de dato publicado; no un alquiler de cero euros.")
    c1, c2 = st.columns(2)
    with c1:
        # El mapa usa polígonos incluidos: funciona sin mapa de teselas externo.
        _, geo = a.geografia()
        fig = go.Figure(go.Choropleth(geojson=geo, featureidkey="properties.CUSEC", locations=s.index.tolist(),
                        z=s.tolist(), colorscale="Teal", marker_line_width=.3, colorbar_title="€/mes",
                        hovertemplate="Sección %{location}<br>%{z:.2f} €/mes<extra></extra>"))
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(title=f"Secciones asociadas al CP {cp} · {anio}")
        if len(s):
            grafica(fig, "Geografía INE 2021 y cruce postal del atlas. Las secciones sin valor no se colorean.")
        else:
            st.info("Sin datos para dibujar esta selección.")
    with c2:
        grafica(px.histogram(x=s.values, nbins=15, title="Distribución dentro de la selección", labels={"x": "Alquiler · €/mes", "y": "Secciones"}), "Cada sección tiene el mismo peso; no mide anuncios disponibles ni la proporción de viviendas asequibles.")
    # Se recupera una tabla de comparación territorial ya coherente con el EDA.
    pares = panel[panel.anio.isin([2023, 2024])].pivot(index="zona", columns="anio", values=a.OBJETIVO).dropna()
    pares["Cambio €/mes"] = pares[2024] - pares[2023]
    pares = pares.reindex(s.index).dropna().sort_values("Cambio €/mes", ascending=False)
    st.subheader("Cambio observado 2023 → 2024 en las secciones de esta selección")
    st.dataframe(pares.rename(columns={2023: "2023 · €/mes", 2024: "2024 · €/mes"}).round(2), width="stretch")
    st.download_button("Descargar esta comparación · CSV", pares.to_csv().encode("utf-8-sig"), "cambio_alquiler_2023_2024.csv", "text/csv")


def presupuesto():
    cabecera("Presupuesto y ahorro", "Convierte el alquiler de referencia en una pregunta personal: cuánto queda a fin de mes y qué cambia si suben los gastos.")
    anio, cp, s = controles()
    if s.empty:
        st.info("Selecciona un código postal con datos.")
        return
    p = a.perfiles()
    c1, c2, c3 = st.columns(3)
    with c1:
        perfil = st.selectbox("Perfil salarial · bandas de 2024", p.Perfil.tolist())
        b = p[p.Perfil.eq(perfil)].iloc[0]
        bruto = st.slider("Bruto anual dentro de su banda", int(b.banda_inferior_eur_anuales), int(b.banda_superior_eur_anuales), int(b["Bruto central"]), step=50)
    with c2:
        otros = st.number_input("Gastos mensuales sin vivienda ni suministros (€)", min_value=0., value=round(a.gastos_base(), 2), step=25.)
        suministros = st.number_input("Suministros y otros gastos de vivienda (€)", min_value=0., value=100., step=10.)
    with c3:
        renta = st.number_input("Alquiler mensual que quieres simular (€)", min_value=0., value=round(float(s.median()), 2), step=25.)
        ahorro = st.number_input("Objetivo de ahorro mensual (€)", min_value=0., value=200., step=25.)
    neto = a.neto_mensual(bruto)
    saldo = neto - otros - suministros - renta
    c1, c2, c3 = st.columns(3)
    c1.metric("Neto equivalente · 12 meses", euros(neto))
    c2.metric("Saldo después de gastos", euros(saldo))
    c3.metric("Margen sobre tu objetivo", euros(saldo - ahorro))
    fig = go.Figure(go.Waterfall(x=["Neto", "Alquiler", "Otros gastos", "Suministros", "Saldo"],
                        measure=["absolute", "relative", "relative", "relative", "total"],
                        y=[neto, -renta, -otros, -suministros, 0], connector={"line": {"color": "#adc3d3"}}))
    fig.update_layout(title="De los ingresos al dinero disponible", yaxis_title="€/mes")
    grafica(fig, "El neto es una interpolación orientativa de Eurostat 2024 para persona sola sin hijos. No se aplican aumentos salariales ni inflación a los valores de 2024.")
    limite = neto - otros - suministros - ahorro
    st.write(f"Para conservar tu objetivo de ahorro, el alquiler máximo bajo estos supuestos sería **{euros(limite)}**.")
    compatibles = int(s.le(limite).sum())
    st.write(f"**{compatibles} de {len(s)} secciones** asociadas al CP {cp} tienen una mediana compatible en {anio}. Esto describe secciones, no pisos disponibles.")
    años = np.arange(anio, 2036)
    escenarios = pd.DataFrame({"Año": años, **{f"Alquiler +{t:.0%}/año": neto - otros - suministros - renta * (1+t)**(años-anio) for t in [0, .02, .04]}})
    grafica(px.line(escenarios, x="Año", y=escenarios.columns[1:], title="Sensibilidad del saldo hasta 2035", labels={"value": "Saldo · €/mes", "variable": "Supuesto"}), "Todos los ingresos y gastos distintos del alquiler permanecen constantes. Son escenarios sin probabilidades asignadas.")


def compra():
    cabecera("Acceso a la compra", "Del precio por metro cuadrado a la entrada, los meses de ahorro y la cuota de una hipoteca hipotética.")
    tasaciones = a.leer("compra_malaga").sort_values(["anio", "trimestre"])
    c1, c2 = st.columns([1, 2])
    with c1:
        referencia = st.selectbox("Referencia de precio", ["Tasación municipal · 2024 T4", "Oferta municipal · octubre 2026"])
        eur_m2 = float(tasaciones.query("anio == 2024 and trimestre == 4").valor_tasado_eur_m2.iloc[0]) if referencia.startswith("Tasación") else 3941.
        superficie = st.number_input("Superficie de referencia (m²)", min_value=10., max_value=500., value=75., step=5.)
        financiado = st.slider("Porcentaje financiado · supuesto", 0, 100, 80, 5) / 100
        gastos_pct = st.slider("Provisión de gastos de compra (%)", 0, 25, 10) / 100
        inicial = st.number_input("Ahorros iniciales (€)", min_value=0., value=0., step=1000.)
        mensual = st.number_input("Ahorro mensual para la entrada (€)", min_value=0., value=200., step=25.)
        tipos = a.leer("hipotecas_nuevas_espana")
        t_base = float(tipos[tipos.TIME_PERIOD.eq("2024-12")].OBS_VALUE.iloc[0])
        tipo = st.number_input("Tipo nominal anual constante (%)", min_value=0., max_value=20., value=t_base, step=.1)
        plazo = st.slider("Plazo de hipoteca (años)", 5, 40, 30)
    precio = eur_m2 * superficie
    entrada, gastos, capital = precio * (1-financiado), precio*gastos_pct, precio*financiado
    meses = a.plazo_ahorro(entrada+gastos, inicial, mensual)
    pago = a.cuota(capital, tipo, plazo)
    with c2:
        c3, c4 = st.columns(2)
        c3.metric("Precio de referencia", euros(precio))
        c4.metric("Entrada + provisión de gastos", euros(entrada+gastos))
        c3.metric("Tiempo para reunir el importe", "Sin plazo finito" if meses is None else f"{meses//12} años · {meses%12} meses")
        c4.metric("Cuota mensual hipotética", euros(pago))
        grafica(px.bar(x=["Entrada", "Provisión de gastos", "Capital financiado"], y=[entrada, gastos, capital],
                        title="Cómo se compone la compra", labels={"x": "Concepto", "y": "Euros"}))
        valores = np.linspace(max(0, tipo-2), tipo+2, 25)
        grafica(px.line(x=valores, y=[a.cuota(capital, t, plazo) for t in valores], title="¿Qué pasa si cambia el tipo al contratar?", labels={"x": "Tipo nominal anual · %", "y": "Cuota · €/mes"}))
    st.caption(f"Referencia elegida: {referencia} · {euros(eur_m2)}/m². La tasación y el precio de oferta miden cosas distintas; ambos son municipales, sin desglose por CP o dormitorios. El tipo inicial procede del BCE, diciembre 2024. Los gastos son una provisión editable, no un cálculo tributario. Ahorro y objetivo permanecen constantes, sin intereses. La cuota no incluye seguros, comunidad, IBI ni mantenimiento y no implica aprobación bancaria.")
    st.subheader("Serie de tasación disponible · 2005–2026")
    t = tasaciones.copy()
    t["Periodo"] = t.anio.astype(str) + " T" + t.trimestre.astype(str)
    grafica(px.line(t, x="Periodo", y="valor_tasado_eur_m2", title="Valor tasado medio de vivienda libre · Málaga", labels={"valor_tasado_eur_m2": "€/m²"}))


def bienestar():
    cabecera("Economía y bienestar", "El crecimiento económico y la evaluación de vida aportan contexto; no explican por sí solos si una persona puede permitirse vivir en Málaga.")
    d = a.contexto()
    d["País"] = d["Country name"].map(a.NOMBRES)
    escogidos = st.multiselect("Países de comparación", list(a.NOMBRES.values()), default=["España", "Alemania", "Dinamarca"])
    d = d[d.País.isin(escogidos)].copy()
    # Reindexar por años conserva los huecos como NaN para no dibujar una
    # continuidad ficticia cuando faltan observaciones de una edición.
    completos = []
    for pais, grupo in d.groupby("País"):
        g = grupo.set_index("anio").reindex(range(2011, 2026))
        g["País"] = pais
        completos.append(g.reset_index())
    mostrar = pd.concat(completos, ignore_index=True) if completos else d
    c1, c2 = st.columns(2)
    with c1:
        grafica(px.line(mostrar, x="anio", y="valor", color="País", markers=True, title="PIB real por habitante · PPA", labels={"anio": "Año", "valor": "Dólares internacionales constantes de 2021"}))
    with c2:
        grafica(px.line(mostrar, x="anio", y=a.VIDA, color="País", markers=True, title="Evaluación de vida · WHR", labels={"anio": "Año", a.VIDA: "Puntos sobre 10 · media trianual"}))
    st.caption("Banco Mundial y WHR · comparación descriptiva agregada. No identifica causalidad ni permite convertir un PIB futuro en felicidad personal.")
    c1, c2 = st.columns(2)
    with c1:
        pib = a.leer("economia_siete_paises").query("iso3 == 'ESP' and codigo == 'NY.GDP.PCAP.PP.KD'").set_index("anio").valor.dropna()
        anios = np.arange(2025, 2036)
        esc = pd.DataFrame({"Año": anios, "Sin crecimiento": 100.})
        for desde in [2011, 2015]:
            ritmo = (pib.loc[2025]/pib.loc[desde])**(1/(2025-desde))-1
            esc[f"Ritmo {desde}–2025"] = 100*(1+ritmo)**(anios-2025)
        grafica(px.line(esc, x="Año", y=esc.columns[1:], title="PIB de España · escenarios hasta 2035", labels={"value": "Índice · 2025 = 100", "variable": "Supuesto"}), "Se prolongan ritmos históricos constantes. No son pronósticos con probabilidades asignadas.")
    with c2:
        local = a.leer("bienestar_esma")
        satisfaccion = local[local.respuesta.str.contains("satisfecho", case=False)]
        grafica(px.bar(satisfaccion, x="porcentaje_esma", y="respuesta", orientation="h", title="Satisfacción con vivir en Málaga · ESMA 2023", labels={"porcentaje_esma": "% de respuestas", "respuesta": ""}), "UMA · muy satisfecho (57,1 %) y bastante satisfecho (35,4 %) suman 92,5 %. Es una pregunta distinta de la evaluación general de vida del WHR.")
        st.caption("En otra pregunta de la encuesta, el 33 % identificó la vivienda como problema principal; no se suma a las categorías de satisfacción.")
    st.info("La tarjeta de felicidad futura del simulador original extrapola linealmente su serie de ediciones 2015–2025. Esta página recupera la serie del EDA del WHR. Son referencias temporales distintas y no se han fusionado como si fueran una sola serie.")


def modelo():
    cabecera("Modelo y evaluación", "Un modelo útil debe demostrar cuánto se equivoca. Comparamos métodos sobre las mismas observaciones y explicamos qué se ha evaluado.")
    r = a.modelos()
    v = r["metricas"].query("Periodo == 'Validación 2023–2024'")
    gb = v[v.Modelo.eq("Gradient Boosting")].iloc[0]
    referencia = v[v.Modelo.eq("Repetir último alquiler")].iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("MAE · Gradient Boosting", euros(gb.MAE))
    c2.metric("R² · Gradient Boosting", f"{gb['R²']:.3f}")
    c3.metric("Mejora frente a repetir el alquiler", f"{100*(1-gb.MAE/referencia.MAE):.1f} %")
    st.write("**Objetivo:** mediana mensual de alquiler por sección. **Entradas:** alquiler del año anterior, cambio previo de la sección y cambio previo de Málaga. El ensemble aprende el cambio y lo suma al último alquiler.")
    st.write("**División temporal:** ajuste hasta 2022; búsqueda interna con cinco cortes 2018–2022; evaluación retrospectiva en 2023–2024. No se mezclan aleatoriamente años pasados y futuros.")
    c1, c2 = st.columns(2)
    with c1:
        grafica(px.bar(v.sort_values("MAE"), x="MAE", y="Modelo", orientation="h", title="Error medio en las mismas filas · 2023–2024", labels={"MAE": "MAE · €/mes"}), "La regresión lineal puede tener menos error que el ensemble. La aplicación original conserva Gradient Boosting; no se afirma que sea el mejor de todos.")
    nombre = st.selectbox("Modelo para inspeccionar sus errores", v.Modelo.tolist(), index=list(v.Modelo).index("Gradient Boosting"))
    p = r["predicciones"].copy()
    p["Residuo"] = p.real - p[nombre]
    with c2:
        fig = px.scatter(p, x="real", y=nombre, color=p.anio.astype(str), title="Observado frente a predicho", labels={"real": "Observado · €/mes", nombre: "Predicho · €/mes", "color": "Año"}, opacity=.5)
        lo, hi = min(p.real.min(), p[nombre].min()), max(p.real.max(), p[nombre].max())
        fig.add_shape(type="line", x0=lo, y0=lo, x1=hi, y1=hi, line=dict(dash="dot", color=ORO))
        grafica(fig, "La línea representa coincidencia perfecta. Cada punto corresponde a una sección y un año.")
    c1, c2 = st.columns(2)
    with c1:
        grafica(px.histogram(p, x="Residuo", nbins=35, title="Distribución de residuos", labels={"Residuo": "Observado − predicho · €/mes"}), "Residuo positivo: el modelo se quedó corto. Negativo: estimó por encima del dato observado.")
    with c2:
        grafica(px.scatter(p, x=nombre, y="Residuo", opacity=.45, title="¿Dónde cambia el error?", labels={nombre: "Predicho · €/mes"}))
    st.subheader("Métricas completas y brecha de generalización")
    st.dataframe(r["metricas"].round(4), hide_index=True, width="stretch")
    train = r["metricas"].query("Modelo == 'Gradient Boosting' and Periodo == 'Entrenamiento'").iloc[0]
    st.write(f"Brecha relativa de MAE: **{100*abs(gb.MAE-train.MAE)/abs(train.MAE):.2f} %**. Brecha relativa de R²: **{100*abs(gb['R²']-train['R²'])/abs(train['R²']):.2f} %**. Una brecha pequeña de R² no demuestra ausencia de sobreajuste en todas las métricas.")
    st.caption(f"Configuración GB: 40 árboles, pérdida Huber, semilla 42; selección {r['parametros']}. MAE interno: {euros(r['mae_cv_gb'])}. Variante lineal elegida solo por cortes internos: {r['lineal_elegida']}.")
    st.warning("2023–2024 ya se inspeccionó durante el desarrollo: hace falta un periodo posterior completamente independiente para una evaluación definitiva. Estos errores no validan las proyecciones hasta 2035.")


# La procedencia se documenta desde el inventario entregado con el proyecto.
# No se sustituyen fuentes originales por enlaces genéricos de terceros.
FUENTES = [
    ("alquiler_seccion_malaga.csv", "SERPAVI · Ministerio de Vivienda", "Modelo y vivienda", "https://cdn.mivau.gob.es/portal-web-mivau/vivienda/serpavi/2026-03_09_bd_SERPAVI_2011-2024%20-%20DEFINITIVO%20WEB_v2.xlsx"),
    ("alquiler_municipio_malaga.csv", "SERPAVI · Ministerio de Vivienda", "Modelo y serie municipal", "https://cdn.mivau.gob.es/portal-web-mivau/vivienda/serpavi/2026-03_09_bd_SERPAVI_2011-2024%20-%20DEFINITIVO%20WEB_v2.xlsx"),
    ("diccionario_serpavi.csv", "SERPAVI", "Documentación de variables", "https://cdn.mivau.gob.es/portal-web-mivau/vivienda/serpavi/2026-03_09_bd_SERPAVI_2011-2024%20-%20DEFINITIVO%20WEB_v2.xlsx"),
    ("mapa_secciones_malaga_2021.geojson", "INE · seccionado 2021", "Mapa y unión por CUSEC", "https://www.ine.es/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=WMS_INE_SECCIONES_G01%3ASecciones_2021&outputFormat=application%2Fjson&srsName=EPSG%3A4326&CQL_FILTER=CUSEC%20LIKE%20%2729067%25%27"),
    ("renta_ine_malaga.csv", "INE · Atlas de renta · tabla 31106", "Fuente contextual conservada; no entra en el modelo", "https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/31106.csv"),
    ("compra_malaga.csv", "Ministerio de Vivienda · tasación", "Compra y serie trimestral", "https://apps.fomento.gob.es/BoletinOnline2/sedal/35103500.XLS"),
    ("salario_data_analyst.csv", "IndesIA / TalentHackers · informe 2024, p. 70", "Bandas de perfiles", "https://www.indesia.org/wp-content/uploads/2024/06/Informe-Mercado-talento-2024.pdf"),
    ("gastos_andalucia.csv", "INE · EPF · tabla 73991", "Presupuesto regional de referencia", "https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/73991.csv"),
    ("fiscalidad_siete_paises.csv", "Eurostat · earn_nt_net", "Interpolación bruto → neto", "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/earn_nt_net?format=TSV&compressed=true"),
    ("hipotecas_nuevas_espana.csv", "BCE · MIR", "Tipo de referencia · escenario de compra", "https://data-api.ecb.europa.eu/service/data/MIR/M.ES.B.A2C.A.R.A.2250.EUR.N?format=csvdata"),
    ("indicadores_municipales_sima.csv", "IECA · SIMA", "Fuente contextual conservada; no entra en el modelo", "https://ws089.juntadeandalucia.es/sima/ficha.htm?mun=29067"),
    ("bienestar_esma.csv", "Universidad de Málaga · ESMA 2023", "Satisfacción local agregada", "https://www.uma.es/sala-de-prensa/noticias/la-cuarta-esma-de-la-uma-refleja-una-amplia-satisfaccion-de-los-ciudadanos-por-vivir-en-malaga/"),
    ("WHR26_Data_Figure_2.1.xlsx", "World Happiness Report · original del Proyecto 6", "Original conservado; selección en CSV", "https://www.worldhappiness.report/data-sharing/"),
    ("bienestar_whr_siete_paises.csv", "World Happiness Report", "Comparación de bienestar", "https://www.worldhappiness.report/data-sharing/"),
    ("economia_siete_paises.csv", "Banco Mundial · PIB PPA y paro OIT", "Comparación de PIB; paro conservado como contexto", "https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.KD"),
]


def inventario():
    """Recuenta las tablas reales; no presenta cada consulta como modelo usado."""
    filas = []
    for archivo, fuente, uso, enlace in FUENTES:
        fila = {"Archivo": archivo, "Fuente": fuente, "Uso en esta versión": uso, "Enlace original": enlace}
        if archivo.endswith(".csv"):
            d = a.leer(archivo[:-4])
            fila["Filas"] = len(d)
            campo = next((c for c in ["anio", "Year", "Periodo", "TIME_PERIOD", "anio_informe", "oleada"] if c in d), None)
            fila["Periodo"] = f"{d[campo].min()}–{d[campo].max()}" if campo else "Según indicador"
        elif archivo.endswith(".geojson"):
            fila.update({"Filas": len(a.geografia()[1]["features"]), "Periodo": "2021"})
        else:
            fila.update({"Filas": None, "Periodo": "Edición WHR 2026"})
        filas.append(fila)
    return pd.DataFrame(filas)


def proyecto():
    cabecera("De una pregunta a una aplicación", "Una exposición del proyecto completo: qué investigamos, cómo trabajamos los datos, qué aprendimos y cómo convertimos el análisis en una herramienta interactiva.", "PROYECTO 7 · AUTORÍA, MÉTODO Y FUENTES")
    config = json.loads((a.RAIZ / "autor.json").read_text(encoding="utf-8"))
    c1, c2, c3 = st.columns(3)
    with c1:
        tarjeta("Autoría", config["nombre"], "QUIÉN")
    with c2:
        tarjeta("Organización", config["organizacion"] + " · " + config["formacion"], "DÓNDE")
    with c3:
        tarjeta("Propósito", "Entender la asequibilidad de vivir en Málaga y explorar escenarios hasta 2035.", "PARA QUÉ")
    st.subheader("Presentación breve · el hilo de la exposición")
    st.write("SPAIN 2035 nace de una pregunta: ¿podré quedarme en Málaga, pagar una vivienda y ahorrar? Para investigarla reunimos datos de alquiler declarado, salarios, gastos, compra y bienestar. Primero exploramos las series y su cobertura; después comparamos regresiones que estiman el alquiler de una sección a un año. Finalmente convertimos los resultados en un atlas interactivo y en escenarios de presupuesto y compra. La aplicación permite consultar, comparar y comprender los resultados, distinguiendo siempre lo observado de lo supuesto.")
    st.subheader("Cómo llegamos hasta aquí")
    pasos = [
        ("Delimitamos el problema", "Elegimos Málaga y una variable medible: el alquiler mediano mensual de una sección censal. El contexto nacional de PIB y bienestar ayuda a formular la pregunta, pero no sustituye el análisis local."),
        ("Buscamos y entendimos los datos", "Identificamos fuentes, fechas, unidades y ámbitos. SERPAVI describe contratos declarados; las ofertas de Idealista y las tasaciones municipales describen referencias diferentes. No mezclamos estas medidas como si fueran equivalentes."),
        ("Preparamos las tablas", "Conservamos los códigos territoriales como texto, comprobamos duplicados sección–año y documentamos los valores ausentes. Para entrenar excluimos objetivos sin publicar; en los gráficos de cobertura mantenemos esos vacíos visibles."),
        ("Exploramos antes de predecir", "Representamos la evolución municipal y las diferencias territoriales. Revisamos cuántas secciones tienen dato cada año. Las medianas de sección no se convierten automáticamente en una mediana municipal o postal."),
        ("Construimos variables del pasado", "Usamos el último alquiler conocido y los cambios previos de la sección y del municipio. Evitamos introducir el alquiler por m² o los cuartiles del mismo año objetivo: revelarían información de lo que queremos predecir."),
        ("Entrenamos y comparamos", "Comparamos repetir el último alquiler, regresiones lineales y Gradient Boosting. El ensemble combina árboles que corrigen errores sucesivos y aprende el cambio de alquiler. La búsqueda de hiperparámetros usa cortes temporales de 2018 a 2022."),
        ("Evaluamos con años posteriores", "Ajustamos hasta 2022 y medimos errores en 2023–2024. MAE expresa el error medio en euros; RMSE penaliza más los errores grandes; R² compara con una referencia constante. Miramos también los residuos y la brecha entre entrenamiento y validación."),
        ("Convertimos el análisis en una app", "Separamos cálculos, datos e interfaz. Python y pandas preparan tablas; scikit-learn ajusta modelos; Streamlit organiza páginas y controles; Plotly representa resultados. El atlas original usa HTML, CSS, JavaScript y Leaflet para el mapa y sus tarjetas."),
        ("Diseñamos un recorrido comprensible", "El dashboard resume; el simulador permite explorar; presupuesto y compra traducen cifras a decisiones; bienestar aporta contexto; evaluación muestra la fiabilidad. Esta exposición explica las decisiones y enlaza las fuentes."),
        ("Probamos y conservamos versiones", "Antes de sustituir una app se comprueban datos, cálculos, navegación y ejecución. Conservamos el archivo original como respaldo. Git registra cambios; GitHub comparte el código; el alojamiento ejecuta la app. La ampliación se entrega aparte y no actualiza por sí sola la publicación anterior."),
    ]
    for i in range(0, len(pasos), 2):
        cols = st.columns(2)
        for j in range(2):
            if i+j < len(pasos):
                with cols[j]:
                    tarjeta(*pasos[i+j], numero=f"{i+j+1:02d}")
    st.subheader("Cómo funcionan los cálculos principales")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Saldo mensual** = neto mensual − alquiler − otros gastos − suministros.\n\n**Entrada y provisión** = precio × (1 − fracción financiada + fracción de gastos).\n\n**Meses de ahorro** = redondeo al alza del importe pendiente / ahorro mensual. Con ahorro nulo o negativo no hay plazo finito, salvo que el objetivo ya esté cubierto.")
    with c2:
        st.markdown("**Escenario de alquiler** = valor de 2024 × (1 + tasa)ⁿ. La tasa del atlas es un supuesto del 2 %.\n\n**Modelo a un año** = alquiler anterior + cambio estimado por el ensemble.\n\n**Cuota hipotecaria**: amortización con pagos mensuales constantes; depende del capital, tipo supuesto y plazo.")
    r = a.modelos()
    m = r["metricas"].query("Periodo == 'Validación 2023–2024'")
    gb = m[m.Modelo.eq("Gradient Boosting")].iloc[0]
    mejor = m.sort_values("MAE").iloc[0]
    panel = a.leer("alquiler_seccion_malaga")
    st.subheader("Qué resultados podemos defender")
    st.write(f"El panel contiene **{len(panel):,} registros**, **{panel.zona.nunique()} secciones** y **{panel[a.OBJETIVO].isna().sum()} medianas ausentes**. Gradient Boosting obtiene un MAE de **{euros(gb.MAE)}** y un R² de **{gb['R²']:.3f}** sobre **{int(gb.n)} observaciones de 2023–2024**. En esa misma comparación, **{mejor.Modelo}** registra el menor MAE, **{euros(mejor.MAE)}**. Mantener el ensemble original no implica que sea el ganador en todos los criterios.")
    st.write("El aprendizaje central es que una cifra necesita contexto: el alquiler declarado no es un anuncio disponible, el promedio nacional de bienestar no describe a cada persona y un escenario para 2035 no es una predicción validada a diez años. La aplicación hace visibles esas diferencias y permite explorar cómo cambian los resultados al modificar supuestos.")
    st.subheader("Límites y mejoras pendientes")
    st.markdown("- La evaluación 2023–2024 es retrospectiva; falta comprobar un periodo posterior que no haya intervenido en el desarrollo.\n- El neto fiscal y los gastos son referencias de 2024; los presupuestos no representan circunstancias individuales ni incorporan inflación automáticamente.\n- Las secciones asociadas a un código postal pueden solaparse con otros códigos. El resumen no pondera por viviendas y no representa disponibilidad.\n- Las referencias de compra y alquiler de oferta son municipales. No hay precios de venta verificados para cada código postal.\n- Los escenarios no asignan probabilidades. Una brecha de R² inferior al 5 % no basta para afirmar que toda medida de sobreajuste cumple ese umbral.\n- La ampliación no incorpora registro persistente de observaciones nuevas ni reentrenamiento automático.")
    st.subheader("Todas las bases y su función")
    inv = inventario()
    st.dataframe(inv, column_config={"Enlace original": st.column_config.LinkColumn("Fuente original"), "Filas": st.column_config.NumberColumn(format="%d")}, hide_index=True, width="stretch")
    st.markdown("**Recursos auxiliares del simulador:** [límites postales del Ayuntamiento de Málaga](https://datosabiertos.malaga.eu/dataset/sistema-de-informacion-cartografica-distrito-postal), cartografía de fondo [OpenStreetMap](https://www.openstreetmap.org/copyright) y biblioteca [Leaflet](https://leafletjs.com/). La versión original incluye referencias municipales de [venta](https://www.idealista.com/sala-de-prensa/informes-precio-vivienda/venta/andalucia/malaga-provincia/malaga/historico/) y [alquiler](https://www.idealista.com/sala-de-prensa/informes-precio-vivienda/alquiler/andalucia/malaga-provincia/malaga/historico/) de Idealista, además de la [serie de ediciones WHR para España](https://datosmacro.expansion.com/demografia/indice-felicidad/espana).")
    st.caption("Se distingue entre fuente incorporada a los cálculos, referencia contextual y documentación conservada. El inventario refleja el paquete disponible; no afirma que todas sus variables hayan sido utilizadas para entrenar.")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("Descargar inventario de fuentes · CSV", inv.to_csv(index=False).encode("utf-8-sig"), "SPAIN2035_fuentes.csv", "text/csv")
    with c2:
        st.download_button("Descargar bases originales · ZIP", a.ARCHIVO.read_bytes(), "Atlas_Malaga_datos.zip", "application/zip")
    st.caption("Autoría editable en autor.json. Se conserva el nombre conocido sin añadir apellidos ni datos personales no confirmados.")
