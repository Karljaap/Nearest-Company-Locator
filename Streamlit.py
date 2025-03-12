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
    """Loads location data from CSV files, verifying their existence and structure."""
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
        if type_name == "school":
            name = nearest.get("school_name", "Unnamed school")
            address = nearest.get("building_address", "Address not available")
        elif type_name == "demolition":
            name = nearest.get("account_name", "Unnamed demolition site")
            address = nearest.get("address", "Address not available")
        else:  # pothole
            name = "Pothole"
            address = nearest.get("incident_address", "Address not available")

        return name, address, min_distance, type_name
    return None, None, None, None


def generate_warning_message(api_key, location_type, address, name):
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an assistant that warns delivery drivers about hazards."},
                {"role": "user",
                 "content": f"Generate a warning message for a driver approaching {address}. There is an active {location_type} site operated by {name}. The message should be clear and cautionary."}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating message: {e}")
        return f"Caution! You are approaching a {location_type} site at {address}, operated by {name}."


def text_to_audio(text, filename="warning.mp3"):
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang='en')
        tts.save(filename)
        return filename
    except Exception as e:
        st.error(f"Error generating audio: {e}")
        return None


# Initialize session state to maintain map selection
if 'map_clicked' not in st.session_state:
    st.session_state.map_clicked = False
if 'selected_point' not in st.session_state:
    st.session_state.selected_point = None

# Streamlit UI
st.title("Driver Warning System")
st.sidebar.header("Settings")
api_key = st.sidebar.text_input("Enter your OpenAI API Key", type="password")

# Load data up front, not based on button click
school_df, demolition_df, pothole_df = load_data()

if school_df is not None and demolition_df is not None and pothole_df is not None:
    # Create base map
    base_location = (40.700000, -73.900000)
    map_object = folium.Map(location=base_location, zoom_start=14)

    # Add reference points
    for _, row in school_df.iterrows():
        folium.Marker([row['latitude'], row['longitude']],
                      tooltip=row.get('school_name', 'Unnamed school'),
                      icon=folium.Icon(color="blue")).add_to(map_object)
    for _, row in demolition_df.iterrows():
        folium.Marker([row['latitude'], row['longitude']],
                      tooltip=row.get('account_name', 'Unnamed demolition site'),
                      icon=folium.Icon(color="red")).add_to(map_object)
    for _, row in pothole_df.iterrows():
        folium.Marker([row['latitude'], row['longitude']],
                      tooltip="Pothole",
                      icon=folium.Icon(color="orange")).add_to(map_object)

    # Display interactive map with return_map_bounds=True to capture clicks
    map_data = st_folium(map_object, height=500, width=700, key="map_widget")

    # Check if map was clicked
    if map_data and 'last_clicked' in map_data:
        st.session_state.selected_point = map_data['last_clicked']
        st.session_state.map_clicked = True

    # Process the selected location if available
    if st.session_state.map_clicked and st.session_state.selected_point:
        lat = st.session_state.selected_point['lat']
        lon = st.session_state.selected_point['lng']
        user_location = (lat, lon)

        st.write(f"Selected location: {lat}, {lon}")

        # Find nearest locations
        nearest_school = find_nearest_location(user_location, school_df, "school")
        nearest_demolition = find_nearest_location(user_location, demolition_df, "demolition")
        nearest_pothole = find_nearest_location(user_location, pothole_df, "pothole")

        nearest_all = sorted([nearest_school, nearest_demolition, nearest_pothole],
                             key=lambda x: x[2] if x[2] else float('inf'))
        nearest_location = nearest_all[0]

        if nearest_location[2] and nearest_location[2] <= 500:
            st.success(
                f"Warning: Near {nearest_location[0]} ({nearest_location[3]}) at {nearest_location[1]}. Distance: {nearest_location[2]:.2f}m")

            if api_key:
                warning_message = generate_warning_message(api_key, nearest_location[3], nearest_location[1],
                                                           nearest_location[0])
                st.write("Generated message:")
                st.info(warning_message)

                # Generate audio
                audio_file = text_to_audio(warning_message)
                if audio_file:
                    st.audio(audio_file, format="audio/mp3")
            else:
                st.warning("Please enter your API Key to generate warnings.")
        else:
            st.info("No nearby warnings.")

    # Add button to reset selection
    if st.session_state.map_clicked:
        if st.button("Reset Selection"):
            st.session_state.map_clicked = False
            st.session_state.selected_point = None
            st.experimental_rerun()
else:
    st.error("Failed to load necessary data files. Please check if all required CSV files exist.")