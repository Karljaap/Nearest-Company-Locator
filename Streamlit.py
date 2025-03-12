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
    """Carga los datos de ubicaciones desde CSV verificando su existencia y estructura."""
    files = {
        "school": "school.csv",
        "demolition": "demolition.csv",
        "pothole": "pothole.csv"
    }
    dataframes = {}

    for key, file in files.items():
        if not os.path.exists(file):
            st.error(f"Error: El archivo {file} no se encontró.")
            return None, None, None
        try:
            df = pd.read_csv(file)
            df.columns = df.columns.str.strip().str.lower()

            # Asegúrate de que existan las columnas necesarias
            if key == "school":
                # Renombra school_name a name
                if 'school_name' in df.columns:
                    df.rename(columns={"school_name": "name"}, inplace=True)
                else:
                    # Si no existe la columna name, créala
                    df['name'] = df['school_name'] if 'school_name' in df.columns else "Escuela sin nombre"

                # Renombra building_address a address
                if 'building_address' in df.columns:
                    df.rename(columns={"building_address": "address"}, inplace=True)
                else:
                    df['address'] = "Dirección no disponible"

            elif key == "demolition":
                # Renombra account_name a name
                if 'account_name' in df.columns:
                    df.rename(columns={"account_name": "name"}, inplace=True)
                else:
                    df['name'] = "Demolición sin nombre"

                # Asegúrate de que exista la columna address
                if 'address' not in df.columns:
                    df['address'] = df['address'] if 'address' in df.columns else "Dirección no disponible"

            elif key == "pothole":
                # Crea columna name para pothole
                df['name'] = "Bache"

                # Renombra incident_address a address
                if 'incident_address' in df.columns:
                    df.rename(columns={"incident_address": "address"}, inplace=True)
                else:
                    df['address'] = "Dirección no disponible"

            # Verifica las columnas de latitud y longitud
            if not {'latitude', 'longitude'}.issubset(df.columns):
                st.error(f"Error: El archivo {file} no tiene las columnas de latitud y longitud.")
                return None, None, None

            dataframes[key] = df
        except Exception as e:
            st.error(f"Error al cargar {file}: {e}")
            return None, None, None

    return dataframes["school"], dataframes["demolition"], dataframes["pothole"]


def find_nearest_location(point, df, type_name):
    nearest = None
    min_distance = float('inf')

    if df is None or df.empty:
        return None, None, None, None

    for _, row in df.iterrows():
        location = (row['latitude'], row['longitude'])
        distance = geopy.distance.distance(point, location).m

        if distance < min_distance:
            min_distance = distance
            nearest = row

    if nearest is not None:
        # Usa get method para acceder a columnas que podrían no existir
        name = nearest.get('name', f'Ubicación {type_name}')
        address = nearest.get('address', 'Dirección no disponible')
        return name, address, min_distance, type_name
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

if st.sidebar.button("Ejecutar Programa"):
    school_df, demolition_df, pothole_df = load_data()

    if school_df is not None and demolition_df is not None and pothole_df is not None:
        # Muestra las primeras filas para depuración
        with st.expander("Ver datos cargados (depuración)"):
            st.write("Columnas en school_df:", school_df.columns.tolist())
            st.write("Columnas en demolition_df:", demolition_df.columns.tolist())
            st.write("Columnas en pothole_df:", pothole_df.columns.tolist())
            st.write("Primeras filas de school_df:")
            st.write(school_df.head(2))
            st.write("Primeras filas de demolition_df:")
            st.write(demolition_df.head(2))
            st.write("Primeras filas de pothole_df:")
            st.write(pothole_df.head(2))

        # Crear mapa base
        base_location = (40.700000, -73.900000)
        mapa = folium.Map(location=base_location, zoom_start=14)

        # Agregar puntos de referencia
        for _, row in school_df.iterrows():
            folium.Marker([row['latitude'], row['longitude']],
                          tooltip=row.get('name', 'Escuela sin nombre'),
                          icon=folium.Icon(color="blue")).add_to(mapa)
        for _, row in demolition_df.iterrows():
            folium.Marker([row['latitude'], row['longitude']],
                          tooltip=row.get('name', 'Demolición sin nombre'),
                          icon=folium.Icon(color="red")).add_to(mapa)
        for _, row in pothole_df.iterrows():
            folium.Marker([row['latitude'], row['longitude']],
                          tooltip=row.get('name', 'Bache'),
                          icon=folium.Icon(color="orange")).add_to(mapa)

        # Mostrar mapa interactivo
        selected_point = st_folium(mapa, height=500)

        # Extraer la ubicación seleccionada
        if selected_point and selected_point.get('last_clicked'):
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