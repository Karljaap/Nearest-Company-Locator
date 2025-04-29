import streamlit as st
import pandas as pd
import folium
import geopy.distance
import openai
import numpy as np
import time
from streamlit_folium import st_folium
from pydub import AudioSegment
from pydub.playback import play
import os

def load_data():
    files = {
        "school": "school.csv",
        "demolition": "demolition.csv",
        "pothole": "pothole.csv"
    }
    dataframes = {}

    for key, file in files.items():
        if not os.path.exists(file):
            st.error(f"Error: The file {file} was not found.")
            return None, None, None
        try:
            df = pd.read_csv(file)
            df.columns = df.columns.str.strip().str.lower()
            dataframes[key] = df
        except Exception as e:
            st.error(f"Error loading {file}: {e}")
            return None, None, None

    return dataframes["school"], dataframes["demolition"], dataframes["pothole"]

def find_nearest_location(point, df, type_name):
    if df is None or df.empty:
        return None, None, None, None

    if 'latitude' in df.columns and 'longitude' in df.columns:
        calc_distance = lambda row: geopy.distance.distance(
            point, (row['latitude'], row['longitude'])).m
        df['distance'] = df.apply(calc_distance, axis=1)
        nearest = df.loc[df['distance'].idxmin()]
        min_distance = nearest['distance']

        if type_name == "school":
            name = nearest.get("school_name", "Unnamed school")
            address = nearest.get("building_address", "Address not available")
        elif type_name == "demolition":
            name = nearest.get("account_name", "Unnamed demolition site")
            address = nearest.get("address", "Address not available")
        else:
            name = "Pothole"
            address = nearest.get("incident_address", "Address not available")

        return name, address, min_distance, type_name

    return None, None, None, None

def generate_warning_message(api_key, location_type, address, name):
    try:
        client = openai.OpenAI(api_key=api_key)
        prompt = (
            f"Generate a brief warning message for a food delivery driver approaching {address}. "
            f"There is an active {location_type} site operated by {name}. "
            "Keep the message under 100 words, clear and cautionary."
        )

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an assistant that creates concise driver warnings."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error generating message: {e}")
        return f"Caution! You are approaching a {location_type} site at {address}, operated by {name}."

def text_to_audio(text, filename="warning.mp3"):
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(filename)
        return filename
    except Exception as e:
        st.error(f"Error generating audio: {e}")
        return None

# Start timing for full app load
app_start_time = time.time()

if 'map_clicked' not in st.session_state:
    st.session_state.map_clicked = False
if 'selected_point' not in st.session_state:
    st.session_state.selected_point = None

st.title("Driver Warning System")
st.sidebar.header("Settings")
api_key = st.sidebar.text_input("Enter your OpenAI API Key", type="password")
st.sidebar.button("Apply API Key")

school_df, demolition_df, pothole_df = load_data()

if school_df is not None and demolition_df is not None and pothole_df is not None:
    base_location = (40.700000, -73.900000)
    map_object = folium.Map(location=base_location, zoom_start=14)

    for _, row in school_df.iterrows():
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=5,
            color='darkblue',
            fill=True,
            fill_color='blue',
            fill_opacity=0.8,
            tooltip=row.get('school_name', 'Unnamed school')
        ).add_to(map_object)

    for _, row in demolition_df.iterrows():
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=5,
            color='darkred',
            fill=True,
            fill_color='red',
            fill_opacity=0.8,
            tooltip=row.get('account_name', 'Unnamed demolition site')
        ).add_to(map_object)

    for _, row in pothole_df.iterrows():
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=5,
            color='darkorange',
            fill=True,
            fill_color='orange',
            fill_opacity=0.8,
            tooltip='Pothole'
        ).add_to(map_object)

    map_data = st_folium(map_object, height=500, width=700, key="map_widget")

    if map_data and 'last_clicked' in map_data:
        st.session_state.selected_point = map_data['last_clicked']
        st.session_state.map_clicked = True

    if st.session_state.map_clicked and st.session_state.selected_point:
        lat = st.session_state.selected_point['lat']
        lon = st.session_state.selected_point['lng']
        user_location = (lat, lon)

        st.write(f"Selected location: {lat}, {lon}")

        nearest_school = find_nearest_location(user_location, school_df, "school")
        nearest_demolition = find_nearest_location(user_location, demolition_df, "demolition")
        nearest_pothole = find_nearest_location(user_location, pothole_df, "pothole")

        nearest_all = sorted([nearest_school, nearest_demolition, nearest_pothole],
                             key=lambda x: x[2] if x[2] else float('inf'))
        nearest_location = nearest_all[0]

        if nearest_location[2] and nearest_location[2] <= 500:
            st.warning("HAZARD ALERT")

            st.write(f"**Location Type:** {nearest_location[3].title()}")
            st.write(f"**Name:** {nearest_location[0]}")
            st.write(f"**Address:** {nearest_location[1]}")
            st.write(f"**Distance:** {nearest_location[2]:.2f}m")

            if api_key:
                start_time = time.time()
                with st.spinner("Generating warning..."):
                    warning_message = generate_warning_message(api_key, nearest_location[3],
                                                               nearest_location[1], nearest_location[0])
                    audio_file = text_to_audio(warning_message)
                end_time = time.time()
                elapsed_time = end_time - start_time

                st.subheader("Generated Message")
                st.info(warning_message)

                if audio_file:
                    st.subheader("Audio Alert")
                    st.audio(audio_file, format="audio/mp3")

                st.markdown(f"### ⏱️ Tiempo total de procesamiento: **{elapsed_time:.2f} segundos**")
            else:
                st.warning("Please enter your OpenAI API Key to generate detailed warnings.")
        else:
            st.success("No nearby hazards detected within 500 meters.")

        app_end_time = time.time()
        total_app_time = app_end_time - app_start_time
        st.markdown(f"### 🕒 Tiempo total desde inicio de app: **{total_app_time:.2f} segundos**")

    if st.session_state.map_clicked:
        if st.button("Reset Selection"):
            st.session_state.map_clicked = False
            st.session_state.selected_point = None
            st.experimental_rerun()
else:
    st.error("Failed to load necessary data files. Please check if all required CSV files exist.")
