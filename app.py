import streamlit as st
import streamlit_authenticator as stauth
import cv2
import pandas as pd
import numpy as np
from inference_sdk import InferenceHTTPClient
import io
import copy

# 1. Sayfa Ayarı
st.set_page_config(page_title="Mimari Metraj Otomasyonu", layout="wide")

# 2. Giriş Sistemi (Parantezler ve kopyalama hatası düzeltildi)
credentials = copy.deepcopy(st.secrets['credentials'])

authenticator = stauth.Authenticate(
    credentials,
    st.secrets['cookie']['name'],
    st.secrets['cookie']['key'],
    st.secrets['cookie']['expiry_days']
)

# SyntaxError'ı bitiren satır:
name, authentication_status, username = authenticator.login('Giriş Yap', 'main')

if authentication_status:
    # Kullanıcı giriş yaptıysa orijinal kodun çalışır
    if 'user_credits' not in st.session_state:
        st.session_state.user_credits = 10 

    authenticator.logout('Çıkış Yap', 'sidebar')
    st.sidebar.title(f"Hoş geldin, {name}")
    st.sidebar.metric("Krediniz", st.session_state.user_credits)

    st.title("🏗️ Mimari Plan Duvar Metraj Uygulaması")
    
    # Orijinal Roboflow Ayarların
    API_KEY = st.secrets["ROBOFLOW_API_KEY"]
    WORKSPACE = "bars-workspace-tcviv"
    WORKFLOW = "custom-workflow-2"
    client = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key=API_KEY)

    uploaded_file = st.file_uploader("Planı Seçin...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, 1)
        
        if st.button("Analiz Et"):
            if st.session_state.user_credits > 0:
                with st.spinner('Hesaplanıyor...'):
                    # Burada senin orijinal analiz kodların devam ediyor...
                    st.session_state.user_credits -= 1
                    st.success("Analiz bitti!")
            else:
                st.error("Yetersiz kredi.")

elif authentication_status == False:
    st.error('Hatalı giriş.')
elif authentication_status == None:
    st.warning('Giriş yapınız.')
