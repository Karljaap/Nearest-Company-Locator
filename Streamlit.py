import streamlit as st
import pandas as pd
import folium
import geopy.distance
from streamlit_folium import st_folium

# Cargar los datos solo una vez
@st.cache_data
def load_data():
    files = {
        "school": "school.csv",
        "demolition": "demolition.csv",
        "pothole": "pothole.csv"
    }
    dataframes = {}

    for key, file in files.items():
        try:
            df = pd.read_csv(file)
            df.columns = df.columns.str.strip().str.lower()
            dataframes[key] = df
        except Exception as e:
            st.error(f"Error al cargar {file}: {e}")
            return None, None, None
    return dataframes["school"], dataframes["demolition"], dataframes["pothole"]

# Inicializar variables en la sesión
if "mapa" not in st.session_state:
    st.session_state["mapa"] = None
if "last_location" not in st.session_state:
    st.session_state["last_location"] = None

# Configuración de UI
st.title("Sistema de Advertencias para Conductores")
st.sidebar.header("Configuración")
api_key = st.sidebar.text_input("Ingresa tu API Key de OpenAI", type="password")

if st.sidebar.button("Ejecutar Programa"):
    school_df, demolition_df, pothole_df = load_data()

    if school_df is not None and demolition_df is not None and pothole_df is not None:
        # Si el mapa aún no ha sido creado, inicializarlo
        if st.session_state["mapa"] is None:
            base_location = (40.700000, -73.900000)
            mapa = folium.Map(location=base_location, zoom_start=14)

            # Agregar marcadores
            for _, row in school_df.iterrows():
                folium.Marker([row['latitude'], row['longitude']],
                              tooltip=row.get('school_name', 'Escuela sin nombre'),
                              icon=folium.Icon(color="blue")).add_to(mapa)
            for _, row in demolition_df.iterrows():
                folium.Marker([row['latitude'], row['longitude']],
                              tooltip=row.get('account_name', 'Demolición sin nombre'),
                              icon=folium.Icon(color="red")).add_to(mapa)
            for _, row in pothole_df.iterrows():
                folium.Marker([row['latitude'], row['longitude']],
                              tooltip="Bache",
                              icon=folium.Icon(color="orange")).add_to(mapa)

            # Guardar el mapa en session_state
            st.session_state["mapa"] = mapa

        # Mostrar el mapa sin reiniciarlo
        selected_point = st_folium(st.session_state["mapa"], height=500, key="mapa")

        # Si se selecciona un punto, almacenarlo
        if selected_point and selected_point.get('last_clicked'):
            lat = selected_point['last_clicked']['lat']
            lon = selected_point['last_clicked']['lng']
            st.session_state["last_location"] = (lat, lon)

        # Mostrar la última ubicación seleccionada
        if st.session_state["last_location"]:
            lat, lon = st.session_state["last_location"]
            st.write(f"Ubicación seleccionada: {lat}, {lon}")
        else:
            st.info("Haz clic en el mapa para seleccionar una ubicación.")
