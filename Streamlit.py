import streamlit as st
import pandas as pd
import geopy.distance
import folium
from streamlit_folium import st_folium
from getpass import getpass
import openai
import requests
from io import StringIO
from concurrent.futures import ThreadPoolExecutor

# Configuración de API Key de OpenAI
api_key = getpass("Enter API key: ")
openai.api_key = api_key

# Función para cargar datos desde API
BASE_URLS = {
    "demolition": "https://data.cityofnewyork.us/resource/cspg-yi7g.csv?$query=",
    "school": "https://data.cityofnewyork.us/resource/8586-3zfm.csv?$query=",
    "pothole": "https://data.cityofnewyork.us/resource/fed5-ydvq.csv?$query="
}

QUERIES = {
    "demolition": "SELECT created, account_name, address, latitude, longitude WHERE created >= '2025-02-01' AND created <= '2025-03-06' ORDER BY created DESC",
    "school": "SELECT name AS school_name, latitude, longitude, building_address WHERE latitude IS NOT NULL AND longitude IS NOT NULL ORDER BY school_name ASC",
    "pothole": "SELECT created_date, complaint_type, descriptor, incident_address, longitude, latitude WHERE created_date BETWEEN '2025-02-01' AND '2025-03-06' ORDER BY created_date DESC"
}

LIMIT = 5000


def fetch_data(dataset):
    url = f"{BASE_URLS[dataset]}{QUERIES[dataset]} LIMIT {LIMIT}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return pd.read_csv(StringIO(response.text))
    except Exception as e:
        st.error(f"Error cargando datos de {dataset}: {e}")
        return pd.DataFrame()


# Cargar los datos
st.write("Cargando datos...")
school_df = fetch_data("school")

demolition_df = fetch_data("demolition")
demolition_df["created"] = pd.to_datetime(demolition_df["created"])
demolition_df = demolition_df[(demolition_df["created"].dt.year == 2025) & (demolition_df["created"].dt.month == 3)][
    ['latitude', 'longitude', 'account_name', 'address']]
demolition_df = demolition_df.dropna(subset=['latitude', 'longitude'])

pothole_df = fetch_data("pothole")
pothole_df["created_date"] = pd.to_datetime(pothole_df["created_date"])
pothole_df = pothole_df[(pothole_df["created_date"].dt.year == 2025) & (pothole_df["created_date"].dt.month == 3)][
    ['complaint_type', 'descriptor', 'incident_address', 'latitude', 'longitude']]
pothole_df = pothole_df.dropna(subset=['latitude', 'longitude'])

st.write("Datos cargados exitosamente.")


# Función para encontrar la ubicación más cercana
def find_nearest_location(point, df, type_name):
    if df.empty:
        return None, None, float("inf"), type_name
    df["distance"] = df.apply(lambda row: geopy.distance.distance(point, (row["latitude"], row["longitude"])).m, axis=1)
    nearest = df.nsmallest(1, "distance").iloc[0]
    return nearest.get("account_name", nearest.get("school_name", "Unknown")), nearest.get("address", nearest.get(
        "building_address", nearest.get("incident_address", "Unknown"))), nearest["distance"], type_name


# Generar mensaje de advertencia
def generate_warning_message(location_type, address, name):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an assistant that warns delivery drivers about hazards."},
            {"role": "user",
             "content": f"Generate a warning message for a delivery driver approaching {address}. There is an active {location_type} site operated by {name}. The message should be clear and cautionary."}
        ]
    )
    return response["choices"][0]["message"]["content"]


# Crear la aplicación Streamlit
st.title("Sistema de Advertencia para Conductores")
st.write("Seleccione una ubicación en el mapa para recibir advertencias de zonas de riesgo cercanas.")

# Crear mapa con folium
base_location = (40.700000, -73.900000)
map_ = folium.Map(location=base_location, zoom_start=12)


# Agregar puntos al mapa
def add_markers(df, color, tooltip):
    for _, row in df.iterrows():
        folium.Marker([row["latitude"], row["longitude"]], tooltip=row.get(tooltip, "Unknown"),
                      icon=folium.Icon(color=color)).add_to(map_)


add_markers(school_df, "blue", "school_name")
add_markers(demolition_df, "red", "account_name")
add_markers(pothole_df, "orange", "complaint_type")

# Mostrar el mapa en Streamlit
map_data = st_folium(map_, width=700, height=500)

# Procesar clic en el mapa
if map_data and "last_clicked" in map_data:
    selected_point = (map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"])
    nearest_school = find_nearest_location(selected_point, school_df, "school")
    nearest_demolition = find_nearest_location(selected_point, demolition_df, "demolition")
    nearest_pothole = find_nearest_location(selected_point, pothole_df, "pothole")
    nearest_all = sorted([nearest_school, nearest_demolition, nearest_pothole], key=lambda x: x[2])
    nearest_location = nearest_all[0]

    st.write(f"Ubicación seleccionada: {selected_point}")
    st.write(
        f"Zona de riesgo más cercana: {nearest_location[0]} ({nearest_location[3]}) en {nearest_location[1]}, Distancia: {nearest_location[2]:.2f}m")

    if nearest_location[2] <= 500:
        warning_message = generate_warning_message(nearest_location[3], nearest_location[1], nearest_location[0])
        st.warning(warning_message)
    else:
        st.success("No hay zonas de riesgo dentro de 500 metros.")