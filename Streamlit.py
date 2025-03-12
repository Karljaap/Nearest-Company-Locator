# --------------------------------------------------------------------------------
import pandas as pd
import requests
from io import StringIO
from concurrent.futures import ThreadPoolExecutor

# Base parameters
BASE_URL = "https://data.cityofnewyork.us/resource/cspg-yi7g.csv?$query="
QUERY_TEMPLATE = """SELECT created, account_name, address, latitude, longitude
 WHERE created >= '{start_date}' AND created <= '{end_date}' ORDER BY created DESC NULL FIRST"""

LIMIT = 5000  # Number of records per request

# Function to fetch data with pagination and date filtering
def fetch_data(offset, start_date, end_date):
    query = QUERY_TEMPLATE.format(start_date=start_date, end_date=end_date)
    url = f"{BASE_URL}{query} LIMIT {LIMIT} OFFSET {offset}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        return df if not df.empty else None
    except Exception as e:
        print(f"Error fetching data at offset {offset}: {e}")
        return None

# Main function to retrieve and consolidate the data
def get_filtered_data(start_date, end_date):
    print(f"Fetching data from {start_date} to {end_date}...")

    # Fetch the first batch to verify if there is data available
    initial_df = fetch_data(0, start_date, end_date)
    if initial_df is None:
        print("No data found within the specified date range.")
        return None

    # List to store results
    all_data = [initial_df]
    total_records = len(initial_df)

    print(f"First batch retrieved: {total_records} records.")

    # Create a list of offsets for pagination
    offsets = list(range(LIMIT, 1000000, LIMIT))  # Up to 1 million records

    # Fetch data in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda offset: fetch_data(offset, start_date, end_date), offsets))

    # Add only the results that contain data
    for result in results:
        if result is not None:
            all_data.append(result)

    # Combine all data into a single DataFrame
    data = pd.concat(all_data, ignore_index=True)
    print(f"Total records retrieved: {len(data)}")

    return data

# Example usage with specific date range
start_date = "2025-02-01"
end_date = "2025-03-06"
filtered_data = get_filtered_data(start_date, end_date)

# Convert the 'created' column to datetime format if it is not already
filtered_data['created'] = pd.to_datetime(filtered_data['created'])

# Filter the data for March 3, 2025
filtered_data_march = filtered_data[(filtered_data['created'].dt.year == 2025) &
                     (filtered_data['created'].dt.month == 3)][['latitude', 'longitude', 'account_name', 'address']]

# Remove rows where latitude or longitude are NaN
demolition  = filtered_data_march.dropna(subset=['latitude', 'longitude'])

# --------------------------------------------------------------------------------
import pandas as pd
import requests
from io import StringIO
from concurrent.futures import ThreadPoolExecutor

# Base parameters
BASE_URL = "https://data.cityofnewyork.us/resource/8586-3zfm.csv?$query="
QUERY_TEMPLATE = """SELECT name AS school_name, latitude, longitude, building_address
                    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                    ORDER BY school_name ASC"""
LIMIT = 5000  # Number of records per request

# Function to fetch data with pagination
def fetch_data(offset):
    url = f"{BASE_URL}{QUERY_TEMPLATE} LIMIT {LIMIT} OFFSET {offset}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        return df if not df.empty else None
    except Exception as e:
        print(f"Error fetching data at offset {offset}: {e}")
        return None

# Main function to retrieve and consolidate the data
def get_all_data():
    print("Fetching **ALL** available school construction projects data...")

    # Fetch the first batch to verify if there is data available
    initial_df = fetch_data(0)
    if initial_df is None:
        print("No data found in the dataset.")
        return None

    # List to store results
    all_data = [initial_df]
    total_records = len(initial_df)

    print(f"First batch retrieved: {total_records} records.")

    # Create a list of offsets for pagination
    offsets = list(range(LIMIT, 1000000, LIMIT))  # Up to 1 million records

    # Fetch data in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_data, offsets))

    # Add only the results that contain data
    for result in results:
        if result is not None:
            all_data.append(result)

    # Combine all data into a single DataFrame
    data = pd.concat(all_data, ignore_index=True)
    print(f"Total records retrieved: {len(data)}")

    return data

# Fetch ALL available data
school = get_all_data()

# --------------------------------------------------------------------------------
import requests
import pandas as pd
from io import StringIO
from concurrent.futures import ThreadPoolExecutor

# Base URL del API
BASE_URL = "https://data.cityofnewyork.us/resource/fed5-ydvq.csv?$query="

# Consulta SQL para extraer todas las columnas con filtro de fecha
QUERY_TEMPLATE = """SELECT created_date, complaint_type,	descriptor, incident_address, longitude, latitude
WHERE created_date BETWEEN '{start_date}' AND '{end_date}'
ORDER BY created_date DESC"""

LIMIT = 5000  # Número de registros por solicitud

# Función para obtener datos con paginación y filtrado de fechas
def fetch_data(offset, start_date, end_date):
    query = QUERY_TEMPLATE.format(start_date=start_date, end_date=end_date)
    url = f"{BASE_URL}{query} LIMIT {LIMIT} OFFSET {offset}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        return df if not df.empty else None
    except Exception as e:
        print(f"Error obteniendo datos en el offset {offset}: {e}")
        return None

# Función principal para obtener y consolidar los datos filtrados
def get_filtered_data(start_date, end_date):
    print(f"Obteniendo datos desde {start_date} hasta {end_date}...")

    # Obtener el primer lote de datos
    initial_df = fetch_data(0, start_date, end_date)
    if initial_df is None:
        print("No se encontraron datos en el rango de fechas especificado.")
        return None

    # Lista para almacenar los resultados
    all_data = [initial_df]
    total_records = len(initial_df)

    print(f"Primer lote recuperado: {total_records} registros.")

    # Crear lista de offsets para paginación
    offsets = list(range(LIMIT, 1000000, LIMIT))  # Hasta 1 millón de registros

    # Obtener datos en paralelo
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda offset: fetch_data(offset, start_date, end_date), offsets))

    # Agregar solo los resultados que contienen datos
    for result in results:
        if result is not None:
            all_data.append(result)

    # Combinar todos los datos en un solo DataFrame
    data = pd.concat(all_data, ignore_index=True)
    print(f"Total de registros recuperados: {len(data)}")

    return data

# Uso con el rango de fechas especificado
start_date = "2025-02-01"
end_date = "2025-03-06"
filtered_data = get_filtered_data(start_date, end_date)

# Convert the 'created_date' column to datetime format if it is not already
filtered_data['created_date'] = pd.to_datetime(filtered_data['created_date'])

# Filter the data for March 3, 2025
filtered_data_march = filtered_data[(filtered_data['created_date'].dt.year == 2025) &
                     (filtered_data['created_date'].dt.month == 3)][['complaint_type',	'descriptor', 'incident_address', 'latitude', 'longitude']]

# Remove rows where latitude or longitude are NaN
pothole = filtered_data_march.dropna(subset=['latitude', 'longitude'])

# --------------------------------------------------------------------------------
import streamlit as st
import pandas as pd
import geopy.distance
import openai
import folium
from streamlit_folium import st_folium
from getpass import getpass

# Cargar datos desde los CSV (ajustar nombres de archivos si es necesario)
school_df = school
demolition_df = demolition
pothole_df = pothole

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
