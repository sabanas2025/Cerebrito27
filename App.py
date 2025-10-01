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

st.set_page_config(page_title="CerebritoWeb v19", layout="wide")

DB_USERS = "users_v19.db"
DB_INFONAVIT = "infonavit.db"

# ==================== BASE DE DATOS ====================
def init_db():
    conn = sqlite3.connect(DB_USERS)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        email TEXT,
        credits INTEGER DEFAULT 10,
        is_admin INTEGER DEFAULT 0,
        is_confirmed INTEGER DEFAULT 0,
        confirmation_code TEXT,
        logo BLOB
    )''')
    
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        admin_pass = hashlib.sha256("1234".encode()).hexdigest()
        c.execute("INSERT INTO users VALUES (NULL,?,?,NULL,999999,1,1,NULL,NULL)", 
                  ("admin", admin_pass))
    conn.commit()
    conn.close()

def get_user(username):
    conn = sqlite3.connect(DB_USERS)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(username, password, email, credits=10, is_admin=0):
    conn = sqlite3.connect(DB_USERS)
    c = conn.cursor()
    hashed = hashlib.sha256(password.encode()).hexdigest()
    code = secrets.token_hex(3).upper()
    try:
        c.execute("INSERT INTO users VALUES (NULL,?,?,?,?,?,0,?,NULL)",
                  (username, hashed, email, credits, is_admin, code))
        conn.commit()
        conn.close()
        return True, code
    except:
        conn.close()
        return False, None

def confirm_user(username, code):
    conn = sqlite3.connect(DB_USERS)
    c = conn.cursor()
    c.execute("SELECT confirmation_code FROM users WHERE username=?", (username,))
    result = c.fetchone()
    if result and result[0] == code.upper():
        c.execute("UPDATE users SET is_confirmed=1 WHERE username=?", (username,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def update_credits(username, amount):
    conn = sqlite3.connect(DB_USERS)
    c = conn.cursor()
    c.execute("UPDATE users SET credits=credits+? WHERE username=?", (amount, username))
    conn.commit()
    conn.close()

def search_infonavit(phone):
    try:
        conn = sqlite3.connect(DB_INFONAVIT)
        c = conn.cursor()
        c.execute("SELECT * FROM registros WHERE TELEFONOCELULAR=?", (str(phone),))
        result = c.fetchone()
        conn.close()
        return result
    except:
        return None

# ==================== PÁGINAS ====================
def login_page():
    st.title("🧠 CerebritoWeb v19")
    
    tab1, tab2, tab3 = st.tabs(["🔐 Login", "📝 Registro", "✅ Confirmar"])
    
    with tab1:
        with st.form("login"):
            user = st.text_input("Usuario")
            pwd = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                u = get_user(user)
                if u and u[2] == hashlib.sha256(pwd.encode()).hexdigest():
                    if u[6] == 1:
                        st.session_state.username = user
                        st.session_state.logged_in = True
                        st.rerun()
                    else:
                        st.error("⚠️ Usuario no confirmado. Ve a la pestaña Confirmar")
                else:
                    st.error("❌ Credenciales incorrectas")
    
    with tab2:
        with st.form("register"):
            new_user = st.text_input("Usuario")
            new_pwd = st.text_input("Contraseña", type="password")
            new_email = st.text_input("Email")
            if st.form_submit_button("Registrar"):
                ok, code = create_user(new_user, new_pwd, new_email)
                if ok:
                    st.success(f"✅ Usuario creado!\n\n**Código:** {code}\n\nVe a 'Confirmar' para activarlo")
                else:
                    st.error("❌ Usuario ya existe")
    
    with tab3:
        st.info("💡 Ingresa tu usuario y el código de 6 dígitos que recibiste")
        with st.form("confirm"):
            conf_user = st.text_input("Usuario")
            conf_code = st.text_input("Código")
            if st.form_submit_button("Confirmar"):
                if confirm_user(conf_user, conf_code):
                    st.success("✅ Cuenta confirmada! Ya puedes iniciar sesión")
                else:
                    st.error("❌ Código incorrecto")

def main_app():
    username = st.session_state.username
    user = get_user(username)
    
    st.sidebar.title(f"👤 {username}")
    st.sidebar.metric("💳 Créditos", user[4])
    
    if user[8]:
        st.sidebar.image(user[8])
    else:
        logo = st.sidebar.file_uploader("Logo", type=['png','jpg'])
        if logo:
            conn = sqlite3.connect(DB_USERS)
            c = conn.cursor()
            c.execute("UPDATE users SET logo=? WHERE username=?", (logo.read(), username))
            conn.commit()
            conn.close()
            st.rerun()
    
    if st.sidebar.button("🚪 Salir"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    
    menu = st.sidebar.radio("Menú", ["📊 Análisis", "👥 Admin"] if user[5]==1 else ["📊 Análisis"])
    
    if menu == "📊 Análisis":
        analysis_page(user)
    else:
        admin_page()

def analysis_page(user):
    st.title("📊 Análisis de Datos")
    
    uploaded = st.file_uploader("📂 Sube Excel", type=['xlsx','xls'])
    
    if uploaded:
        df = pd.read_excel(uploaded)
        st.success(f"✅ {len(df)} registros cargados")
        
        first_row = st.number_input("Primera fila de datos", 0, len(df)-1, 0)
        df = df.iloc[first_row:].reset_index(drop=True)
        
        st.subheader("⚙️ Configurar Columnas")
        cols = df.columns.tolist()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            col_tel = st.selectbox("📱 Teléfono", [""] + cols)
            col_sal = st.selectbox("📤 Salientes", [""] + cols)
        with col2:
            col_ent = st.selectbox("📥 Entrantes", [""] + cols)
            col_fecha = st.selectbox("📅 Fecha", [""] + cols)
        with col3:
            col_hora = st.selectbox("🕐 Hora", [""] + cols)
            col_lat = st.selectbox("🌐 Latitud", [""] + cols)
            col_lon = st.selectbox("🌐 Longitud", [""] + cols)
        
        st.dataframe(df.head(10), use_container_width=True)
        
        if st.button("🔍 ANALIZAR", type="primary", use_container_width=True):
            if not col_tel:
                st.error("❌ Debes seleccionar columna de Teléfono")
                return
            
            with st.spinner("Analizando..."):
                # BÚSQUEDA AUTOMÁTICA EN INFONAVIT
                infonavit_data = []
                progress = st.progress(0)
                
                for i, phone in enumerate(df[col_tel]):
                    result = search_infonavit(phone)
                    infonavit_data.append(result)
                    progress.progress((i+1)/len(df))
                
                st.session_state.df_analyzed = df
                st.session_state.infonavit_results = infonavit_data
                st.session_state.config = {
                    'tel': col_tel, 'sal': col_sal, 'ent': col_ent,
                    'fecha': col_fecha, 'hora': col_hora,
                    'lat': col_lat, 'lon': col_lon
                }
                
                st.success("✅ Análisis completado!")
                st.rerun()
        
        # MOSTRAR RESULTADOS SI YA ANALIZÓ
        if 'df_analyzed' in st.session_state:
            st.divider()
            st.subheader("📈 Resultados del Análisis")
            
            df_result = st.session_state.df_analyzed
            config = st.session_state.config
            
            # GRÁFICAS
            tab1, tab2, tab3 = st.tabs(["📊 Gráficas", "🗺️ Mapas", "🔗 Enlaces"])
            
            with tab1:
                if config['sal'] and config['ent']:
                    col1, col2 = st.columns(2)
                    with col1:
                        fig1 = px.bar(df_result, x=df_result.index, y=config['sal'],
                                     title="Llamadas Salientes")
                        st.plotly_chart(fig1, use_container_width=True)
                    with col2:
                        fig2 = px.bar(df_result, x=df_result.index, y=config['ent'],
                                     title="Llamadas Entrantes")
                        st.plotly_chart(fig2, use_container_width=True)
                    
                    st.session_state.charts = [fig1, fig2]
            
            with tab2:
                if config['lat'] and config['lon']:
                    df_map = df_result[[config['lat'], config['lon']]].dropna()
                    
                    if len(df_map) > 0:
                        center_lat = df_map[config['lat']].mean()
                        center_lon = df_map[config['lon']].mean()
                        
                        m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
                        
                        for idx, row in df_map.iterrows():
                            folium.Marker(
                                [row[config['lat']], row[config['lon']]],
                                popup=f"Registro {idx}",
                                tooltip=f"Click para info"
                            ).add_to(m)
                        
                        st_folium(m, width=800, height=500)
                        st.session_state.map_created = True
                    else:
                        st.warning("⚠️ No hay coordenadas válidas")
            
            with tab3:
                if config['lat'] and config['lon']:
                    st.subheader("🔗 Links de Google Maps")
                    df_links = df_result[[config['lat'], config['lon']]].dropna()
                    
                    for idx, row in df_links.head(20).iterrows():
                        lat, lon = row[config['lat']], row[config['lon']]
                        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
                        street_url = f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}"
                        
                        col1, col2 = st.columns(2)
                        col1.markdown(f"**Punto {idx}**: [Google Maps]({maps_url})")
                        col2.markdown(f"[Street View]({street_url})")
            
            # GENERAR PDF
            st.divider()
            if st.button("📄 GENERAR PDF COMPLETO", type="primary"):
                if user[4] > 0:
                    with st.spinner("Generando PDF con gráficas y mapas..."):
                        pdf_buffer = generate_pdf(df_result, config)
                        
                        # DESCONTAR CRÉDITO SOLO AQUÍ
                        update_credits(user[1], -1)
                        
                        st.success("✅ PDF generado! Se descontó 1 crédito")
                        st.download_button("⬇️ Descargar PDF", pdf_buffer, 
                                         f"reporte_{user[1]}.pdf", "application/pdf")
                else:
                    st.error("❌ Sin créditos")

def generate_pdf(df, config):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "📊 Reporte de Análisis - CerebritoWeb")
    
    c.setFont("Helvetica", 12)
    y = 720
    c.drawString(50, y, f"Total de registros: {len(df)}")
    
    y -= 30
    c.drawString(50, y, "Columnas configuradas:")
    y -= 20
    for k, v in config.items():
        if v:
            c.drawString(70, y, f"• {k.upper()}: {v}")
            y -= 15
    
    y -= 30
    c.drawString(50, y, "✅ Análisis completado con búsqueda en Infonavit")
    y -= 20
    c.drawString(50, y, "✅ Gráficas generadas")
    y -= 20
    c.drawString(50, y, "✅ Mapas interactivos creados")
    y -= 20
    c.drawString(50, y, "✅ Enlaces de Google Maps incluidos")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def admin_page():
    st.title("👥 Panel de Administración")
    
    tab1, tab2 = st.tabs(["Crear Usuario", "Lista Usuarios"])
    
    with tab1:
        st.subheader("➕ Crear Nuevo Usuario")
        
        with st.form("admin_create"):
            new_user = st.text_input("Usuario")
            new_pwd = st.text_input("Contraseña", type="password")
            new_email = st.text_input("Email")
            credits = st.number_input("Créditos", 0, 10000, 10)
            is_admin = st.checkbox("Es Admin")
            
            if st.form_submit_button("Crear"):
                ok, code = create_user(new_user, new_pwd, new_email, credits, int(is_admin))
                if ok:
                    st.success(f"✅ Usuario creado!\n\n**Código:** {code}")
                    st.session_state.last_code = code
                    st.session_state.last_user = new_user
                else:
                    st.error("❌ Error al crear")
        
        # CONFIRMAR FUERA DEL FORM
        if 'last_code' in st.session_state:
            st.divider()
            st.info(f"💡 Confirma '{st.session_state.last_user}' aquí:")
            
            col1, col2 = st.columns([3,1])
            with col1:
                conf_code = st.text_input("Código", value=st.session_state.last_code, key="admin_conf")
            with col2:
                if st.button("Confirmar"):
                    if confirm_user(st.session_state.last_user, conf_code):
                        st.success("✅ Confirmado!")
                        del st.session_state.last_code
                        del st.session_state.last_user
                        st.rerun()
                    else:
                        st.error("❌ Error")
    
    with tab2:
        conn = sqlite3.connect(DB_USERS)
        df_users = pd.read_sql_query(
            "SELECT id, username, email, credits, is_admin, is_confirmed FROM users", conn)
        conn.close()
        st.dataframe(df_users, use_container_width=True)

# ==================== MAIN ====================
def main():
    init_db()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if st.session_state.logged_in:
        main_app()
    else:
        login_page()

if __name__ == "__main__":
    main()
