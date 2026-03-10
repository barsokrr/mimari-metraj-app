import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import numpy as np
import cv2
import pandas as pd
from inference_sdk import InferenceHTTPClient
import io

# --- 1. AYARLAR VE GİRİŞ SİSTEMİ ---
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Giriş paneli
authenticator.login(location='main')

# --- 2. ANA UYGULAMA MANTIĞI ---
if st.session_state.get("authentication_status"):
    authenticator.logout('Çıkış Yap', 'sidebar')
    
    st.title("🏗️ Mimari Plan Duvar Metraj Uygulaması")
    st.write(f"Hoş geldin *{st.session_state.get('name', 'Kullanıcı')}*")
    
   # API Anahtarını alırken hata almamak için DOĞRU yöntem
try:
    # Buraya anahtarı değil, Secrets panelindeki ADINI yazmalısın
    API_KEY = st.secrets["ROBOFLOW_API_KEY"]


    WORKSPACE = "bars-workspace-tcviv"
    WORKFLOW = "custom-workflow-2"
# --- 1. API ANAHTARI KONTROLÜ (BAĞIMSIZ BLOK) ---
try:
    API_KEY = st.secrets["ROBOFLOW_API_KEY"]
except Exception:
    st.error("Hata: Secrets ayarlarında 'ROBOFLOW_API_KEY' bulunamadı.")
    st.stop()

# --- 2. GİRİŞ SİSTEMİ ---
# authenticator nesnesini daha önce yukarıda tanımladığını varsayıyorum
name, authentication_status, username = authenticator.login('Giriş Yap', 'main')

if st.session_state.get("authentication_status"):
    # GİRİŞ BAŞARILIYSA BURASI ÇALIŞIR
    authenticator.logout('Çıkış Yap', 'sidebar')
    st.sidebar.write(f'Hoş geldin *{st.session_state["name"]}*')
    
    st.title("Mimari Plan Duvar Metraj Uygulaması")
    
    # --- ANALİZ MANTIĞI ---
    uploaded_file = st.file_uploader("Mimari Planı Seçin (JPG, PNG)...", type=["jpg", "png", "jpeg"])
    
    if uploaded_file is not None:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, 1)
        st.image(image, caption="Yüklenen Plan", use_container_width=True)

        if st.button("Metrajı Hesapla"):
            with st.spinner('Analiz ediliyor...'):
                client = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key=API_KEY)
                result = client.run_workflow(
                    workspace_name="bars-workspace-tcviv",
                    workflow_id="custom-workflow-2",
                    images={"image": image}
                )
                st.write("Sonuçlar:")
                st.json(result)

elif st.session_state.get("authentication_status") is False:
    st.error('Kullanıcı adı veya şifre hatalı')

else:
    st.info('Lütfen kullanıcı adı ve şifrenizi giriniz')
