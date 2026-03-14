import streamlit as st
import streamlit_authenticator as stauth
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import numpy as np
from inference_sdk import InferenceHTTPClient

# --- 1. OTURUM HATALARI ÖNLEME (KeyError: 'name' FIX) ---
# Kütüphane çerezleri kontrol etmeden önce bu alanları zorla tanımlıyoruz.
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None
if 'name' not in st.session_state:
    st.session_state['name'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

# --- 2. KİMLİK DOĞRULAMA YAPILANDIRMASI ---
try:
    # Secrets objesi doğrudan değiştirilemez, bu yüzden kopya alıyoruz.
    # image_13b2de.png üzerindeki TOML yapısına göre veriler çekilir.
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

# --- 3. LOGIN PANELİ (Hatasız Sürüm v0.2.3) ---
# image_08d0fa.jpg ve image_07c671.png görsellerindeki hataları önlemek için
try:
    # v0.2.3 sürümü login() fonksiyonunda bu 3 değişkeni döndürür.
    name, authentication_status, username = authenticator.login('Giriş Yap', 'main')
except KeyError:
    # Bozuk çerez durumunda state'i sıfırlayıp kullanıcıyı temiz panele yönlendirir.
    st.session_state['authentication_status'] = None
    st.warning("Oturum süresi dolmuş, lütfen tekrar giriş yapın.")
    name, authentication_status, username = None, None, None

# --- 4. UYGULAMA MANTIĞI ---
if st.session_state["authentication_status"]:
    authenticator.logout('Çıkış Yap', 'sidebar')
    
    # image_092b8b.png dosyasındaki API anahtarı kullanımı.
    ROBO_API_KEY = st.secrets["ROBOFLOW_API_KEY"]
    MODEL_ID = "mimari_duvar_tespiti-2/8"
    CLIENT = InferenceHTTPClient(api_url="https://detect.roboflow.com", api_key=ROBO_API_KEY)

    # Mimari Metraj Fonksiyonları ve UI burada devam eder...
    st.title("🏗️ DUVAR METRAJ PANELİ")
    st.sidebar.success(f"Hoş geldin, {st.session_state['name']}")

elif st.session_state["authentication_status"] is False:
    st.error('Kullanıcı adı veya şifre hatalı')
elif st.session_state["authentication_status"] is None:
    st.warning('Lütfen kullanıcı adı ve şifrenizi giriniz') #
