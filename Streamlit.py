import streamlit as st
import pandas as pd
import geopy.distance
import openai
import folium
from streamlit_folium import st_folium
from getpass import getpass

# Cargar datos desde los CSV (ajustar nombres de archivos si es necesario)
school_df = pd.read_csv("school.csv")
demolition_df = pd.read_csv("demolition.csv")
pothole_df = pd.read_csv("pothole.csv")

# Configuración de API Key de OpenAI
api_key = getpass("Enter API key: ")
openai.api_key = api_key


# Encontrar la ubicación más cercana
def find_nearest_location(point, df, type_name):
    nearest_name, nearest_address = None, None
    min_distance = float("inf")

    for _, row in df.iterrows():
        location = (row["latitude"], row["longitude"])
        distance = geopy.distance.distance(point, location).m

        if distance < min_distance:
            min_distance = distance
            nearest_name = row.get("account_name", row.get("school_name", "Unknown"))
            nearest_address = row.get("address", row.get("building_address", row.get("incident_address", "Unknown")))

    return nearest_name, nearest_address, min_distance, type_name


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
st.write("Haga clic en el mapa para seleccionar una ubicación y recibir advertencias de zonas de riesgo cercanas.")

# Crear mapa con folium
base_location = (40.700000, -73.900000)
map_ = folium.Map(location=base_location, zoom_start=12)

# Agregar puntos de datos
for _, row in school_df.iterrows():
    folium.Marker([row["latitude"], row["longitude"]], tooltip=row["school_name"],
                  icon=folium.Icon(color="blue")).add_to(map_)
for _, row in demolition_df.iterrows():
    folium.Marker([row["latitude"], row["longitude"]], tooltip=row["account_name"],
                  icon=folium.Icon(color="red")).add_to(map_)
for _, row in pothole_df.iterrows():
    folium.Marker([row["latitude"], row["longitude"]], tooltip="Pothole", icon=folium.Icon(color="orange")).add_to(map_)

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
