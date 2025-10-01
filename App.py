import streamlit as st
import sqlite3
import hashlib
import secrets
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import base64
import logging
import os
from datetime import datetime

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

# Configuración de la página
st.set_page_config(page_title="CerebritoWeb v19", layout="wide")

# Variables de entorno
DB_USERS = os.getenv('DB_USERS', 'users_v19.db')
DB_INFONAVIT = os.getenv('DB_INFONAVIT', 'infonavit.db')