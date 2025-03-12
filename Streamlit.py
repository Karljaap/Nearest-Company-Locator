import streamlit as st
import pandas as pd
import geopy.distance
import openai
import folium
from streamlit_folium import st_folium
from concurrent.futures import ThreadPoolExecutor
import requests
from io import StringIO

# Base URLs para los datasets
DATASETS = {
    "demolition": "https://data.cityofnewyork.us/resource/cspg-yi7g.csv?$query=SELECT created, account_name, address, latitude, longitude WHERE created >= '{start_date}' AND created <= '{end_date}' ORDER BY created DESC NULL FIRST",
    "school": "https://data.cityofnewyork.us/resource/8586-3zfm.csv?$query=SELECT name AS school_name, latitude, longitude, building_address WHERE latitude IS NOT NULL AND longitude IS NOT NULL ORDER BY school_name ASC",
    "pothole": "https://data.cityofnewyork.us/resource/fed5-ydvq.csv?$query=SELECT created_date, complaint_type, descriptor, incident_address, longitude, latitude WHERE created_date BETWEEN '{start_date}' AND '{end_date}' ORDER BY created_date DESC"
}

LIMIT = 5000


# Función para obtener datos desde el API
def fetch_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        return df if not df.empty else None
    except Exception as e:
        print(f"Error obteniendo datos: {e}")
        return None


# Función para obtener y consolidar los datos
def get_data(dataset_key, start_date="2025-02-01", end_date="2025-03-06"):
    url = DATASETS[dataset_key].format(start_date=start_date, end_date=end_date)
    return fetch_data(url)


# Cargar los datos
demolition_df = get_data("demolition")[['latitude', 'longitude', 'account_name', 'address']].dropna()
school_df = get_data("school")[['school_name', 'latitude', 'longitude', 'building_address']].dropna()
pothole_df = get_data("pothole")[['latitude', 'longitude', 'complaint_type', 'incident_address']].dropna()

# Crear la aplicación Streamlit
st.title("Sistema de Advertencia para Conductores")
st.write("Seleccione una ubicación en el mapa para recibir advertencias de zonas de riesgo cercanas.")

# Crear mapa base con folium
base_location = (40.700000, -73.900000)
map_ = folium.Map(location=base_location, zoom_start=12)


# Función para agregar marcadores al mapa
def add_markers(df, name_col, icon_color):
    for _, row in df.iterrows():
        folium.Marker(
            [row["latitude"], row["longitude"]],
            tooltip=row[name_col],
            icon=folium.Icon(color=icon_color)
        ).add_to(map_)


# Agregar datos al mapa
add_markers(school_df, "school_name", "blue")
add_markers(demolition_df, "account_name", "red")
add_markers(pothole_df, "complaint_type", "orange")

# Mostrar el mapa en Streamlit
map_data = st_folium(map_, width=700, height=500)


# Función para encontrar la ubicación más cercana
def find_nearest_location(point, df, type_name, name_col, address_col):
    if df.empty:
        return None

    df["distance"] = df.apply(lambda row: geopy.distance.distance(point, (row["latitude"], row["longitude"])).m, axis=1)
    nearest = df.nsmallest(1, "distance").iloc[0]
    return nearest[name_col], nearest[address_col], nearest["distance"], type_name


# Procesar clic en el mapa
if map_data and "last_clicked" in map_data:
    selected_point = (map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"])

    nearest_school = find_nearest_location(selected_point, school_df, "Escuela", "school_name", "building_address")
    nearest_demolition = find_nearest_location(selected_point, demolition_df, "Demolición", "account_name", "address")
    nearest_pothole = find_nearest_location(selected_point, pothole_df, "Bache", "complaint_type", "incident_address")

    nearest_locations = [loc for loc in [nearest_school, nearest_demolition, nearest_pothole] if loc]
    nearest_location = min(nearest_locations, key=lambda x: x[2], default=None)

    if nearest_location:
        st.write(f"Ubicación seleccionada: {selected_point}")
        st.write(
            f"Zona de riesgo más cercana: {nearest_location[0]} ({nearest_location[3]}) en {nearest_location[1]}, Distancia: {nearest_location[2]:.2f}m")

        if nearest_location[2] <= 500:
            st.warning(f"⚠️ Precaución: {nearest_location[3]} en {nearest_location[1]}. ¡Conduzca con cuidado!")
        else:
            st.success("No hay zonas de riesgo dentro de 500 metros.")