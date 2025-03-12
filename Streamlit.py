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
            f"Generate a brief warning message for a driver approaching {address}. "
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

# Add custom CSS to fix the white overlay issue and improve colors
st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
        opacity: 1 !important;
    }
    .main .block-container {
        opacity: 1 !important;
        background-color: #ffffff;
    }
    .stButton button {
        border-radius: 4px;
        opacity: 1 !important;
    }
    h1 {
        font-size: 28px;
        margin-bottom: 20px;
        color: #000000 !important;
        background-color: #fdf9c4 !important;
        padding: 10px;
        border-radius: 5px;
        font-weight: bold;
        opacity: 1 !important;
    }
    div[data-testid="stSidebar"] {
        background-color: #1E1E1E !important;
        opacity: 1 !important;
    }
    p, .stTextInput label, button, .stTextInput, div {
        color: #000000 !important;
        opacity: 1 !important;
    }
    .css-6qob1r {
        opacity: 1 !important;
    }
    .css-1544g2n {
        opacity: 1 !important;
    }
    .stText {
        background-color: #ffda9e !important;
        padding: 5px;
        border-radius: 3px;
        font-weight: bold;
        color: #000000 !important;
        opacity: 1 !important;
    }
</style>
""", unsafe_allow_html=True)

# Minimalist UI with properly colored title
st.title("Driver Warning System")

# Fix the sidebar styling - improve visibility with stronger colors
st.sidebar.markdown("""
<style>
    div[data-testid="stSidebar"] {
        background-color: #2C2C2C !important;
    }
    div[data-testid="stSidebar"] p, 
    div[data-testid="stSidebar"] span,  
    div[data-testid="stSidebar"] div {
        color: #FFFFFF !important;
    }
    div[data-testid="stSidebar"] label {
        color: #FFFFFF !important;
        font-weight: bold !important;
        font-size: 16px !important;
    }
    div[data-testid="stSidebar"] h1, 
    div[data-testid="stSidebar"] h2, 
    div[data-testid="stSidebar"] h3 {
        color: #ffda9e !important;
        font-weight: bold !important;
        font-size: 20px !important;
        background-color: #333333 !important;
        padding: 10px !important;
        border-radius: 5px !important;
        margin-bottom: 15px !important;
    }
    div[data-testid="stSidebar"] button {
        background-color: #fabfb7 !important;
        color: #000000 !important;
        font-weight: bold !important;
        font-size: 16px !important;
        padding: 8px 16px !important;
        border: 2px solid #000000 !important;
        border-radius: 5px !important;
        display: block !important;
        width: 100% !important;
        margin-top: 10px !important;
    }
    /* Style for password input */
    div[data-testid="stSidebar"] input[type="password"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #fabfb7 !important;
        padding: 8px !important;
        font-size: 16px !important;
        border-radius: 5px !important;
    }
</style>
""", unsafe_allow_html=True)

# Minimalist sidebar with clear text
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
            st.markdown("""
            <div style="background-color: #fdf9c4; padding: 15px; border-radius: 5px; margin:15px 0;">
                <p style="color: #000000; font-weight: bold;">No nearby hazards detected within 500 meters.</p>
            </div>
            """, unsafe_allow_html=True)

    # Add button to reset selection
    if st.session_state.map_clicked:
        if st.button("Reset Selection"):
            st.session_state.map_clicked = False
            st.session_state.selected_point = None
            st.experimental_rerun()
else:
    st.error("Failed to load necessary data files. Please check if all required CSV files exist.")