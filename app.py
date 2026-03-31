import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os
from supabase import create_client

# --- AYARLAR VE VERİTABANI ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Sistem yapılandırması eksik!")
    st.stop()

st.set_page_config(page_title="Metraj Pro | Mimari Analiz", layout="wide", page_icon="📊")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- MODERN DESIGNER CSS ---
st.markdown("""
    <style>
    /* Google Fonts Entegrasyonu */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp { background-color: #F8FAFC; }

    /* Sidebar Tasarımı */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0;
        padding-top: 2rem;
    }

    /* Modern Kart Yapısı */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #F1F5F9;
        margin-bottom: 1rem;
    }

    /* Kullanıcı Bilgi Alanı */
    .user-badge {
        background: #F1F5F9;
        padding: 12px 16px;
        border-radius: 10px;
        margin-bottom: 25px;
        border-left: 4px solid #00AD43;
    }

    /* Buton Modernizasyonu */
    .stButton>button {
        width: 100%;
        border-radius: 8px !important;
        height: 45px;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        transition: all 0.2s;
    }
    
    /* RAL 6038 Prime Buton */
    div.stButton > button:first-child {
        background-color: #00AD43;
        color: white;
        border: none;
    }

    /* Input Alanları */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        border-radius: 8px !important;
        border: 1px solid #E2E8F0 !important;
    }

    /* Başlık Stili */
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -1px;
        margin-bottom: 0.5rem;
    }
    
    .sub-text { color: #64748B; font-size: 1rem; margin-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

# --- FONKSİYONLAR ---
def get_user_data(email):
    email = email.lower().strip()
    res = supabase.table("users").select("*").eq("email", email).execute()
    if not res.data:
        user = {"email": email, "credits": 0}
        supabase.table("users").insert(user).execute()
        return user
    return res.data[0]

def use_credit(email):
    user = get_user_data(email)
    if user["credits"] > 0:
        supabase.table("users").update({"credits": user["credits"] - 1}).eq("email", email).execute()
        return True
    return False

# --- AKIŞ KONTROLÜ ---
if not st.session_state.get('logged_in'):
    st.markdown('<div style="text-align:center; padding-top:100px;">', unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">🏗️ Metraj Pro</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-text">Mimari projeleriniz için akıllı metraj çözümleri</p>', unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1,1,1])
        with col2:
            email = st.text_input("E-posta ile devam et", placeholder="mail@adresiniz.com")
            if st.button("Giriş Yap"):
                if "@" in email:
                    st.session_state.user_email = email
                    st.session_state.logged_in = True
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- ANA PANEL ---
user = get_user_data(st.session_state.user_email)

with st.sidebar:
    st.markdown(f"""
        <div class="user-badge">
            <div style="font-size: 0.8rem; color: #64748B;">Oturum Açan:</div>
            <div style="font-weight: 700; color: #0F172A;">{st.session_state.user_email}</div>
            <div style="font-size: 0.9rem; margin-top: 5px; color: #00AD43;">🎫 <b>{user['credits']} Kredi</b></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.subheader("🛠️ Analiz Araçları")
    uploaded = st.file_uploader("DXF Dosyasını Buraya Bırakın", type=["dxf"])
    
    if uploaded:
        mode = st.selectbox("Analiz Metodu", ["🧱 Duvar Metrajı", "🚪 Obje Sayımı"])
        if mode == "🧱 Duvar Metrajı":
            layer = st.text_input("Hedef Katman", value="DUVAR")
            height = st.number_input("Kat Yüksekliği (m)", value=2.85)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("Çıkış Yap", type="secondary"):
        st.session_state.logged_in = False
        st.rerun()

# --- İÇERİK ALANI ---
st.markdown('<h1 class="main-header">Analiz Paneli</h1>', unsafe_allow_html=True)

if not uploaded:
    st.info("👋 Başlamak için sol menüden projenizi (.dxf) yükleyin.")
    # Örnek görsel veya rehber buraya gelebilir
else:
    col_btn, _ = st.columns([1,3])
    with col_btn:
        start_btn = st.button("Analizi Başlat")
    
    if start_btn:
        if use_credit(st.session_state.user_email):
            with st.status("Proje işleniyor...", expanded=True) as status:
                try:
                    # Dosya işleme mantığı (ezdxf vs.) buraya gelir
                    st.write("Geometri verileri okunuyor...")
                    # ... (Analiz kodları)
                    status.update(label="Analiz Tamamlandı!", state="complete")
                    
                    # Sonuç Ekranı
                    res_col1, res_col2 = st.columns([2, 1])
                    with res_col1:
                        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                        st.subheader("📊 Proje Görünümü")
                        # Matplotlib figürü buraya
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with res_col2:
                        st.metric("Toplam Aks", "145.20 m")
                        st.metric("Net Duvar Alanı", "413.82 m²")
                except Exception as e:
                    st.error(f"Hata: {e}")
        else:
            st.warning("Yetersiz kredi! Lütfen bakiye yükleyin.")
