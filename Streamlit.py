import streamlit as st
import pandas as pd
import folium
import geopy.distance
import openai
import numpy as np
from streamlit_folium import st_folium
import os

# Configuración de la página
st.set_page_config(layout="wide", page_title="Sistema de Advertencias")

# Título de la aplicación
st.title("Sistema de Advertencias para Conductores")

# Debugging information
st.write("Verificando archivos disponibles:")
st.write(os.listdir())


# Función para cargar datos (simplificada)
def load_data():
    try:
        # Cargar los DataFrames
        school_df = pd.read_csv("school.csv")
        demolition_df = pd.read_csv("demolition.csv")
        pothole_df = pd.read_csv("pothole.csv")

        # Convertir los nombres de columnas a minúsculas
        school_df.columns = school_df.columns.str.strip().str.lower()
        demolition_df.columns = demolition_df.columns.str.strip().str.lower()
        pothole_df.columns = pothole_df.columns.str.strip().str.lower()

        # Mostrar las columnas para depuración
        st.write("Columnas en school_df:", school_df.columns.tolist())
        st.write("Columnas en demolition_df:", demolition_df.columns.tolist())
        st.write("Columnas en pothole_df:", pothole_df.columns.tolist())

        # Crear columnas necesarias si no existen
        if 'name' not in school_df.columns:
            school_df['name'] = school_df['school_name'] if 'school_name' in school_df.columns else "Escuela"

        if 'name' not in demolition_df.columns:
            demolition_df['name'] = demolition_df[
                'account_name'] if 'account_name' in demolition_df.columns else "Demolición"

        if 'name' not in pothole_df.columns:
            pothole_df['name'] = "Bache"

        return school_df, demolition_df, pothole_df
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return None, None, None


# Cargar datos
school_df, demolition_df, pothole_df = load_data()

# Verificar si los datos se cargaron correctamente
if school_df is not None and demolition_df is not None and pothole_df is not None:
    # Crear mapa base
    base_location = (40.700000, -73.900000)
    mapa = folium.Map(location=base_location, zoom_start=14)

    # Mostrar primeras filas para depuración
    st.write("Primeras filas de school_df:")
    st.write(school_df.head(2))
    st.write("Primeras filas de demolition_df:")
    st.write(demolition_df.head(2))
    st.write("Primeras filas de pothole_df:")
    st.write(pothole_df.head(2))

    # Agregar marcadores - CLAVE: Aquí es donde ocurre el error
    # Modificamos para usar .get() en lugar de acceso directo
    for _, row in school_df.iterrows():
        folium.Marker(
            [row.get('latitude'), row.get('longitude')],
            tooltip=row.get('name', 'Escuela'),
            icon=folium.Icon(color="blue")
        ).add_to(mapa)

    for _, row in demolition_df.iterrows():
        folium.Marker(
            [row.get('latitude'), row.get('longitude')],
            tooltip=row.get('name', 'Demolición'),
            icon=folium.Icon(color="red")
        ).add_to(mapa)

    for _, row in pothole_df.iterrows():
        folium.Marker(
            [row.get('latitude'), row.get('longitude')],
            tooltip=row.get('name', 'Bache'),
            icon=folium.Icon(color="orange")
        ).add_to(mapa)

    # Mostrar mapa
    st_folium(mapa, height=500)
else:
    st.error("No se pudieron cargar los datos correctamente")