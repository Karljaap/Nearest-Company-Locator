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

# Add custom CSS for minimalist styling
st.markdown("""
<style>
    .stApp {
        background-color: white;
    }
    .stButton button {
        border-radius: 4px;
    }
    h1 {
        font-size: 28px;
        margin-bottom: 20px;
    }
    div[data-testid="stSidebar"] {
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

# Minimalist UI with simple title
st.title("Driver Warning System")

# Minimalist sidebar
st.sidebar.header("Settings")

# API key input with apply button
api_key = st.sidebar.text_input("Enter your OpenAI API Key", type="password")
apply_key = st.sidebar.button("Apply API Key", key="apply_key_button")

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
            # Improved HAZARD ALERT with better color contrast for visibility
            st.markdown(f"""
            <div style="background-color:#ffebeb; padding:15px; border-radius:0px; margin:15px 0; border-left:5px solid #d9000d">
                <div style="background-color:#1a53a4; padding:8px 12px; display:inline-block; margin-bottom:15px">
                    <h3 style="color:white; margin:0; display:flex; align-items:center; font-size:18px; letter-spacing:0.5px">
                        <span style="margin-right:10px; font-size:20px">⚠️</span> HAZARD ALERT
                    </h3>
                </div>
                <p style="color:#000000; font-size:16px; margin:10px 0"><strong>Location Type:</strong> {nearest_location[3].title()}</p>
                <p style="color:#000000; font-size:16px; margin:10px 0"><strong>Name:</strong> {nearest_location[0]}</p>
                <p style="color:#000000; font-size:16px; margin:10px 0"><strong>Address:</strong> {nearest_location[1]}</p>
                <p style="color:#000000; font-size:16px; margin:10px 0"><strong>Distance:</strong> {nearest_location[2]:.2f}m</p>
            </div>
            """, unsafe_allow_html=True)

            if api_key:
                with st.spinner("Generating warning..."):
                    warning_message = generate_warning_message(api_key, nearest_location[3], nearest_location[1],
                                                               nearest_location[0])

                st.markdown("<h3 style='color:#1a53a4; margin-top:25px; font-size:18px'>Generated Message</h3>",
                            unsafe_allow_html=True)
                st.markdown(f"""
                <div style="background-color:#e6f0ff; padding:15px; border:1px solid #c2d8f7; border-radius:4px">
                    <p style="color:#003366; font-size:16px; line-height:1.5">{warning_message}</p>
                </div>
                """, unsafe_allow_html=True)

                # Generate audio
                audio_file = text_to_audio(warning_message)
                if audio_file:
                    st.markdown("<h3 style='color:#1a53a4; margin-top:25px; font-size:18px'>Audio Alert</h3>",
                                unsafe_allow_html=True)
                    st.audio(audio_file, format="audio/mp3")
            else:
                st.warning("Please enter your OpenAI API Key to generate detailed warnings.")
        else:
            st.info("No nearby hazards detected within 500 meters.")

    # Add button to reset selection
    if st.session_state.map_clicked:
        if st.button("Reset Selection"):
            st.session_state.map_clicked = False
            st.session_state.selected_point = None
            st.experimental_rerun()
else:
    st.error("Failed to load necessary data files. Please check if all required CSV files exist.")