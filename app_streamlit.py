"""Entrada multipágina. Ejecutar: python -m streamlit run app_streamlit.py.

La versión previa se guarda intacta en simulador_original.py y respaldo/.
La navegación se añade por fuera del simulador, sin reescribir su interfaz.
"""
import streamlit as st
import vistas

st.set_page_config(page_title="SPAIN 2035 · Mediterráneo de Cristal", page_icon="🌊", layout="wide")
vistas.aplicar_estilo()

paginas = [
    st.Page(vistas.dashboard, title="Dashboard", icon=":material/dashboard:", default=True),
    st.Page(vistas.simulador, title="Simulador original", icon=":material/map:", url_path="simulador"),
    st.Page(vistas.vivienda, title="Vivienda y territorio", icon=":material/home:", url_path="vivienda"),
    st.Page(vistas.presupuesto, title="Presupuesto y ahorro", icon=":material/account_balance_wallet:", url_path="presupuesto"),
    st.Page(vistas.compra, title="Acceso a la compra", icon=":material/key:", url_path="compra"),
    st.Page(vistas.bienestar, title="Economía y bienestar", icon=":material/sunny:", url_path="bienestar"),
    st.Page(vistas.modelo, title="Modelo y evaluación", icon=":material/monitoring:", url_path="modelo"),
    st.Page(vistas.proyecto, title="El proyecto · Exposición", icon=":material/school:", url_path="proyecto"),
]
pagina = st.navigation(paginas)
with st.sidebar:
    st.markdown("### SPAIN 2035")
    st.caption("Málaga · Mediterráneo de Cristal")
    st.caption("Proyecto 7 · Regresión · Factoría F5")
pagina.run()
