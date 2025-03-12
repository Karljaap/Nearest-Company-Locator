import streamlit as st
import pandas as pd
import folium
import geopy.distance
import openai
import numpy as np
from streamlit_folium import st_folium
from pydub import AudioSegment
from pydub.playback import play
import os


def load_data():
    """Carga los datos de ubicaciones desde CSV verificando su existencia"""
    files = ["school.csv", "demolition.csv", "pothole.csv"]
    for file in files:
        if not os.path.exists(file):
            st.error(f"Error: El archivo {file} no se encontró. Verifica su ubicación.")
            return None, None, None

    school_df = pd.read_csv("school.csv")
    demolition_df = pd.read_csv("demolition.csv")
    pothole_df = pd.read_csv("pothole.csv")

    return school_df, demolition_df, pothole_df


def find_nearest_location(point, df, type_name):
    nearest = None
    min_distance = float('inf')

    if df is None:
        return None, None, None, None

    for _, row in df.iterrows():
        location = (row['latitude'], row['longitude'])
        distance = geopy.distance.distance(point, location).m

        if distance < min_distance:
            min_distance = distance
            nearest = row

    if nearest is not None:
        return nearest['name'], nearest['address'], min_distance, type_name
    return None, None, None, None


def generate_warning_message(api_key, location_type, address, name):
    openai.api_key = api_key
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an assistant that warns delivery drivers about hazards."},
            {"role": "user",
             "content": f"Generate a warning message for a driver approaching {address}. There is an active {location_type} site operated by {name}. The message should be clear and cautionary."}
        ]
    )
    return response['choices'][0]['message']['content']


def text_to_audio(text, filename="warning.mp3"):
    from gtts import gTTS
    tts = gTTS(text=text, lang='en')
    tts.save(filename)
    return filename


# Streamlit UI
st.title("Sistema de Advertencias para Conductores")
st.sidebar.header("Configuración")
api_key = st.sidebar.text_input("Ingresa tu API Key de OpenAI", type="password")

# Cargar datos
school_df, demolition_df, pothole_df = load_data()

if school_df is not None and demolition_df is not None and pothole_df is not None:
    # Crear mapa base
    base_location = (40.700000, -73.900000)
    mapa = folium.Map(location=base_location, zoom_start=14)

    # Agregar puntos de referencia
    for _, row in school_df.iterrows():
        folium.Marker([row['latitude'], row['longitude']], tooltip=row['name'], icon=folium.Icon(color="blue")).add_to(
            mapa)
    for _, row in demolition_df.iterrows():
        folium.Marker([row['latitude'], row['longitude']], tooltip=row['name'], icon=folium.Icon(color="red")).add_to(
            mapa)
    for _, row in pothole_df.iterrows():
        folium.Marker([row['latitude'], row['longitude']], tooltip=row['name'],
                      icon=folium.Icon(color="orange")).add_to(mapa)

    # Mostrar mapa interactivo
    selected_point = st_folium(mapa, height=500)

    # Extraer la ubicación seleccionada
    if selected_point and selected_point['last_clicked']:
        lat = selected_point['last_clicked']['lat']
        lon = selected_point['last_clicked']['lng']
        user_location = (lat, lon)

        st.write(f"Ubicación seleccionada: {lat}, {lon}")

        # Buscar ubicaciones cercanas
        nearest_school = find_nearest_location(user_location, school_df, "school")
        nearest_demolition = find_nearest_location(user_location, demolition_df, "demolition")
        nearest_pothole = find_nearest_location(user_location, pothole_df, "pothole")

        nearest_all = sorted([nearest_school, nearest_demolition, nearest_pothole],
                             key=lambda x: x[2] if x[2] else float('inf'))
        nearest_location = nearest_all[0]

        if nearest_location[2] and nearest_location[2] <= 500:
            st.success(
                f"Advertencia: Cerca de {nearest_location[0]} ({nearest_location[3]}) en {nearest_location[1]}. Distancia: {nearest_location[2]:.2f}m")

            if api_key:
                warning_message = generate_warning_message(api_key, nearest_location[3], nearest_location[1],
                                                           nearest_location[0])
                st.write("Mensaje generado:")
                st.info(warning_message)

                # Generar audio
                audio_file = text_to_audio(warning_message)
                st.audio(audio_file, format="audio/mp3")
            else:
                st.warning("Por favor, ingresa tu API Key para generar advertencias.")
        else:
            st.info("No hay advertencias cercanas.")