import streamlit as st
import pandas as pd
import folium
import geopy.distance
import openai
import requests
import os
from streamlit_folium import st_folium
from gtts import gTTS

# Función para cargar datos
def load_data():
    files = {
        "school": "school.csv",
        "demolition": "demolition.csv",
        "pothole": "pothole.csv"
    }
    dataframes = {}

    for key, file in files.items():
        if not os.path.exists(file):
            st.error(f"Error: El archivo {file} no fue encontrado.")
            return None, None, None
        try:
            df = pd.read_csv(file)
            df.columns = df.columns.str.strip().str.lower()
            dataframes[key] = df
        except Exception as e:
            st.error(f"Error cargando {file}: {e}")
            return None, None, None

    return dataframes["school"], dataframes["demolition"], dataframes["pothole"]

# Buscar ubicación más cercana
def find_nearest_location(point, df, type_name):
    if df is None or df.empty:
        return None, None, None, None, None, None

    df['distance'] = df.apply(lambda row: geopy.distance.distance(
        point, (row['latitude'], row['longitude'])).m, axis=1)
    nearest = df.loc[df['distance'].idxmin()]
    min_distance = nearest['distance']

    name = nearest.get("school_name", "Unnamed location") if type_name == "school" else nearest.get("account_name", "Unnamed demolition site") if type_name == "demolition" else "Pothole"
    address = nearest.get("building_address", "Address not available") if type_name == "school" else nearest.get("address", "Address not available") if type_name == "demolition" else nearest.get("incident_address", "Address not available")

    return name, address, min_distance, type_name, nearest['latitude'], nearest['longitude']

# Generar advertencia con OpenAI
def generate_warning_message(api_key, location_type, address, name):
    try:
        client = openai.OpenAI(api_key=api_key)
        prompt = (f"Generate a brief warning message for a food delivery driver approaching {address}. "
                  f"There is an active {location_type} site operated by {name}. "
                  "Keep the message under 100 words, clear and cautionary.")

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are an assistant that creates concise driver warnings."},
                      {"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.7
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error generando mensaje: {e}")
        return f"¡Precaución! Te acercas a un {location_type} en {address}, operado por {name}."

# Convertir texto a audio
def text_to_audio(text, filename="warning.mp3"):
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(filename)
        return filename
    except Exception as e:
        st.error(f"Error generando audio: {e}")
        return None

# Configuración de Streamlit
st.title("Sistema de Advertencia para Conductores")
st.sidebar.header("Configuración")
api_key = st.sidebar.text_input("Ingrese su OpenAI API Key", type="password")

# Cargar datos
school_df, demolition_df, pothole_df = load_data()

if school_df is not None and demolition_df is not None and pothole_df is not None:
    base_location = (40.700000, -73.900000)
    map_object = folium.Map(location=base_location, zoom_start=14)

    # Agregar puntos en el mapa
    for df, color, tooltip in [(school_df, 'blue', 'school_name'),
                               (demolition_df, 'red', 'account_name'),
                               (pothole_df, 'orange', 'incident_address')]:
        for _, row in df.iterrows():
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=5,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                tooltip=row.get(tooltip, 'Unknown')
            ).add_to(map_object)

    map_data = st_folium(map_object, height=500, width=700, key="map_widget")

    # ✅ Evitar error cuando `map_data` es None o `last_clicked` no está disponible
    if map_data and isinstance(map_data, dict) and 'last_clicked' in map_data and map_data['last_clicked']:
        lat = map_data['last_clicked'].get('lat')
        lon = map_data['last_clicked'].get('lng')

        if lat is not None and lon is not None:
            user_location = (lat, lon)
            st.write(f"Ubicación seleccionada: {lat}, {lon}")

            nearest_school = find_nearest_location(user_location, school_df, "school")
            nearest_demolition = find_nearest_location(user_location, demolition_df, "demolition")
            nearest_pothole = find_nearest_location(user_location, pothole_df, "pothole")

            nearest_all = sorted([nearest_school, nearest_demolition, nearest_pothole],
                                key=lambda x: x[2] if x[2] else float('inf'))
            nearest_location = nearest_all[0]

            if nearest_location[2] and nearest_location[2] <= 500:
                st.warning("⚠️ ALERTA DE PELIGRO ⚠️")

                st.write(f"**Tipo:** {nearest_location[3].title()}")
                st.write(f"**Nombre:** {nearest_location[0]}")
                st.write(f"**Dirección:** {nearest_location[1]}")
                st.write(f"**Distancia:** {nearest_location[2]:.2f}m")

                waze_url = f"https://waze.com/ul?ll={nearest_location[4]},{nearest_location[5]}&navigate=yes"
                st.markdown(f"[🗺️ Abrir en Waze]({waze_url})", unsafe_allow_html=True)

                if api_key:
                    with st.spinner("Generando advertencia..."):
                        warning_message = generate_warning_message(api_key, nearest_location[3], nearest_location[1], nearest_location[0])

                    st.subheader("Mensaje generado")
                    st.info(warning_message)

                    audio_file = text_to_audio(warning_message)
                    if audio_file:
                        st.audio(audio_file, format="audio/mp3")
                else:
                    st.warning("Ingrese su OpenAI API Key para generar advertencias detalladas.")
            else:
                st.success("✅ No hay peligros cercanos dentro de 500 metros.")
        else:
            st.warning("⚠️ No se pudo capturar la ubicación seleccionada en el mapa. Intenta hacer clic nuevamente.")
    else:
        st.warning("⚠️ Esperando selección en el mapa... Haz clic en una ubicación para obtener información.")

else:
    st.error("Error al cargar archivos CSV.")
