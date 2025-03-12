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
    """Find the nearest location from a dataframe to a given point.

    Args:
        point (tuple): (latitude, longitude) of the reference point
        df (pandas.DataFrame): DataFrame containing locations
        type_name (str): Type of location ('school', 'demolition', or 'pothole')

    Returns:
        tuple: (name, address, distance, type_name) of the nearest location
    """
    if df is None or df.empty:
        return None, None, None, None

    # Calculate distances in a vectorized way if possible
    if 'latitude' in df.columns and 'longitude' in df.columns:
        # Create a function to calculate distances
        calc_distance = lambda row: geopy.distance.distance(
            point, (row['latitude'], row['longitude'])).m

        # Apply the function to each row and find the minimum
        df['distance'] = df.apply(calc_distance, axis=1)
        nearest = df.loc[df['distance'].idxmin()]
        min_distance = nearest['distance']

        # Get name and address based on type
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

    # Fallback to the original method if columns are different
    nearest = None
    min_distance = float('inf')

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
    """Generate a warning message using OpenAI API.

    Args:
        api_key (str): OpenAI API key
        location_type (str): Type of location
        address (str): Address of the location
        name (str): Name of the location

    Returns:
        str: Generated warning message
    """
    try:
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=api_key)

        # Prepare a prompt that is clear and concise
        prompt = (
            f"Generate a brief warning message for a food delivery driver approaching {address}. "
            f"There is an active {location_type} site operated by {name}. "
            "Keep the message under 100 words, clear and cautionary."
        )

        # Make API call with optimized parameters
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
    """Convert text to audio using gTTS.

    Args:
        text (str): Text to convert to speech
        filename (str): Output filename

    Returns:
        str: Path to the audio file or None if error
    """
    try:
        from gtts import gTTS
        # Create gTTS object with optimized settings
        tts = gTTS(text=text, lang='en', slow=False)
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

# Main application title
st.title("Driver Warning System")

# Sidebar for settings
st.sidebar.header("Settings")

# API key input with apply button
api_key = st.sidebar.text_input("Enter your OpenAI API Key", type="password")
apply_key = st.sidebar.button("Apply API Key")

# Load data up front, not based on button click
school_df, demolition_df, pothole_df = load_data()

if school_df is not None and demolition_df is not None and pothole_df is not None:
    # Create base map
    base_location = (40.700000, -73.900000)
    map_object = folium.Map(location=base_location, zoom_start=14)

    # Add reference points
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
            st.warning("HAZARD ALERT")

            st.write(f"**Location Type:** {nearest_location[3].title()}")
            st.write(f"**Name:** {nearest_location[0]}")
            st.write(f"**Address:** {nearest_location[1]}")
            st.write(f"**Distance:** {nearest_location[2]:.2f}m")

            if api_key:
                with st.spinner("Generating warning..."):
                    warning_message = generate_warning_message(api_key, nearest_location[3], nearest_location[1],
                                                               nearest_location[0])

                st.subheader("Generated Message")
                st.info(warning_message)

                # Generate audio
                audio_file = text_to_audio(warning_message)
                if audio_file:
                    st.subheader("Audio Alert")
                    st.audio(audio_file, format="audio/mp3")
            else:
                st.warning("Please enter your OpenAI API Key to generate detailed warnings.")
        else:
            st.success("No nearby hazards detected within 500 meters.")

    # Add button to reset selection
    if st.session_state.map_clicked:
        if st.button("Reset Selection"):
            st.session_state.map_clicked = False
            st.session_state.selected_point = None
            st.experimental_rerun()
else:
    st.error("Failed to load necessary data files. Please check if all required CSV files exist.")