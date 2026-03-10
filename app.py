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
    
    # API Anahtarını alırken hata almamak için güvenli yöntem
    try:
        API_KEY = st.secrets["my238ZSyFyxbwEVQHISP"]
    except KeyError:
        st.error("Hata: Secrets ayarlarında 'ROBOFLOW_API_KEY' bulunamadı.")
        st.stop()

    WORKSPACE = "bars-workspace-tcviv"
    WORKFLOW = "custom-workflow-2"
    PIXEL_TO_METER_RATIO = 0.02 

    # Dosya yükleyici
    uploaded_file = st.file_uploader("Mimari Planı Seçin (JPG, PNG)...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        # Görüntüyü oku
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, 1)
        
        st.image(image, caption="Yüklenen Plan", use_container_width=True)

        if st.button("Metrajı Hesapla ve Analiz Et"):
            with st.spinner('Model analiz ediyor, lütfen bekleyin...'):
                try:
                    client = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key=API_KEY)
                    
                    # Geçici dosya oluşturmadan doğrudan byte üzerinden gönderim
                    _, buffer = cv2.imencode(".jpg", image)
                    img_bytes = buffer.tobytes()
                    
                    result = client.run_workflow(
                        workspace_name=WORKSPACE,
                        workflow_id=WORKFLOW,
                        images={"image": image} # SDK bazen doğrudan numpy dizisini kabul eder
                    )

                    predictions = result[0]['predictions']['predictions']
                    metraj_listesi = []

                    for i, wall in enumerate(predictions):
                        w, h = wall['width'], wall['height']
                        m_w = round(w * PIXEL_TO_METER_RATIO, 2)
                        m_h = round(h * PIXEL_TO_METER_RATIO, 2)

                        metraj_listesi.append({
                            "Duvar_ID": f"Duvar-{i+1}",
                            "Genişlik (m)": m_w,
                            "Yükseklik (m)": m_h,
                            "Alan (m2)": round(m_w * m_h, 2)
                        })

                    if metraj_listesi:
                        df = pd.DataFrame(metraj_listesi)
                        st.write("### Metraj Sonuçları")
                        st.dataframe(df)
                    else:
                        st.warning("Hiç duvar tespit edilemedi.")
                        
                except Exception as e:
                    st.error(f"Analiz sırasında bir hata oluştu: {e}")

elif st.session_state.get("authentication_status") is False:
    st.error('Kullanıcı adı veya şifre hatalı')
else:
    st.info('Lütfen kullanıcı adı ve şifrenizi giriniz')

