import streamlit as st
import streamlit_authenticator as stauth
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import numpy as np
from inference_sdk import InferenceHTTPClient

# --- 1. OTURUM TEMİZLİĞİ VE HATA ÖNLEME ---
# Eğer tarayıcıda bozuk veri kalmışsa, her şeyi sıfırlamaya zorlarız.
if 'name' not in st.session_state or st.session_state.name is None:
    for key in ['authentication_status', 'name', 'username']:
        st.session_state[key] = None

# --- 2. KİMLİK DOĞRULAMA YAPILANDIRMASI ---
try:
    # Secrets'ı sözlüğe çevirerek güvenli okuma yapıyoruz.
    config = st.secrets.to_dict()
    
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
except Exception as e:
    st.error(f"Yapılandırma Hatası: {e}")
    st.stop()

# --- 3. LOGIN PANELİ (Hata Yakalayıcı Sistem) ---
# Burası KeyError: 'name' hatasını yutar ve giriş ekranını zorla gösterir.
try:
    name, authentication_status, username = authenticator.login('Giriş Yap', 'main')
except Exception:
    st.session_state['authentication_status'] = None
    name, authentication_status, username = None, None, None

# --- 4. UYGULAMA MANTIĞI ---
if st.session_state["authentication_status"]:
    authenticator.logout('Çıkış Yap', 'sidebar')
    
    # API Ayarları
    ROBO_API_KEY = st.secrets.get("ROBOFLOW_API_KEY", "Bulunamadi")
    MODEL_ID = "mimari_duvar_tespiti-2/8"
    CLIENT = InferenceHTTPClient(api_url="https://detect.roboflow.com", api_key=ROBO_API_KEY)

    st.title("🏗️ DUVAR METRAJ PANELİ")
    st.sidebar.success(f"Hoş geldin, {st.session_state['name']}")
    
    # Analiz bölümü burada devam eder...
    uploaded = st.sidebar.file_uploader("DXF Yükle", type=["dxf"])
    if uploaded:
        st.write("Dosya başarıyla yüklendi, analiz ediliyor...")

elif st.session_state["authentication_status"] is False:
    st.error('❌ Kullanıcı adı veya şifre hatalı')
elif st.session_state["authentication_status"] is None:
    # Bu mesaj geliyorsa ama login butonu çalışmıyorsa çerezleri silmelisin.
    st.warning('🔐 Lütfen kullanıcı adı ve şifrenizi giriniz')
