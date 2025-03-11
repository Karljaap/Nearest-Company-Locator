import streamlit as st
import folium
import pandas as pd
from streamlit_folium import st_folium

"""
# Data Description
This dataset contains information about companies registered by the Business Integrity Commission (BIC) to collect and dispose of waste materials resulting exclusively from demolition, construction, alterations, or excavations in New York City.
Each record represents an entity approved to operate under the classification of Class 2 C&D Registrants. The information is updated daily and has been publicly available since April 4, 2017.

# Dictionary Column
| **Column Name**      | **Description**                                          | **API Field Name**    | **Data Type**        |
|----------------------|----------------------------------------------------------|----------------------|----------------------|
| **CREATED**          | Timestamp of when data is processed for OpenData         | `created`            | Floating Timestamp  |
| **BIC NUMBER**       | Unique BIC file number assigned to the entity            | `bic_number`         | Text                |
| **ACCOUNT NAME**     | Name of the entity                                       | `account_name`       | Text                |
| **TRADE NAME**       | Name under which the entity operates                     | `trade_name`         | Text                |
| **ADDRESS**          | Mailing address of the entity                            | `address`            | Text                |
| **CITY**            | City where the entity is located                         | `city`               | Text                |
| **STATE**            | State where the entity is located                        | `state`              | Text                |
| **POSTCODE**        | Postal code of the entity’s mailing address              | `postcode`           | Text                |
| **PHONE**           | Phone number of the entity                               | `phone`              | Text                |
| **EMAIL**           | Email contact of the entity                              | `email`              | Text                |
| **APPLICATION TYPE** | Type of application filed by the entity                  | `application_type`   | Text                |
| **DISPOSITION DATE** | Date of resolution of the application                   | `disposition_date`   | Text                |
| **EFFECTIVE DATE**   | Date when the registration becomes effective             | `effective_date`     | Text                |
| **EXPIRATION DATE**  | Date when the registration expires                       | `expiration_date`    | Text                |
| **RENEWAL**         | Indicates if the registration is renewable               | `renewal`            | Checkbox            |
| **EXPORT DATE**      | Date when the data was last exported by BIC              | `export_date`        | Floating Timestamp  |
| **LATITUDE**         | Latitude of the mailing address                          | `latitude`           | Text                |
| **LONGITUDE**        | Longitude of the mailing address                         | `longitude`          | Text                |
| **COMMUNITY BOARD**  | Community board based on the mailing address            | `community_board`    | Text                |
| **COUNCIL DISTRICT** | Council district where the entity is located            | `council_district`   | Text                |
| **CENSUS TRACT**     | Census tract associated with the mailing address        | `census_tract`      | Text                |
| **BIN**             | Building Identification Number (BIN)                     | `bin`                | Text                |
| **BBL**             | Borough-Block-Lot (BBL) number                           | `bbl`                | Text                |
| **NTA**             | Neighborhood Tabulation Area                             | `nta`                | Text                |
| **BORO**            | Borough where the entity is located                      | `boro`               | Text                |
"""


# Load the CSV data file
def load_data(path):
    return pd.read_csv(path)


DATA_PATH = "filtered_data_march_clean.csv"
df = load_data(DATA_PATH)


# Create a map focused on New York City with a construction-related icon
def create_map(data):
    nyc_coordinates = [40.7128, -74.0060]  # Center of New York City
    mapa = folium.Map(location=nyc_coordinates, zoom_start=12, tiles="OpenStreetMap")

    for _, row in data.iterrows():
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=f"<b>{row['account_name']}</b><br>Lat: {row['latitude']}, Lon: {row['longitude']}",
            tooltip=f"{row['account_name']} ({row['latitude']}, {row['longitude']})",
            icon=folium.Icon(icon="wrench", prefix="fa", color="orange")
        ).add_to(mapa)

    return mapa


# Display the map in Streamlit
st.title("Interactive Map of NYC with Construction Sites")
st_folium(create_map(df), width=700, height=500)
