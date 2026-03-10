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

# --- KİMLİK DOĞRULAMA KONTROLÜ ---
if st.session_state.get("authentication_status"):
# 1. YAN MENÜ (SIDEBAR) AYARLARI
    with st.sidebar:
        st.markdown(f"### 👤 Profil")
        st.write(f"**Kullanıcı:** {st.session_state.get('name', 'Kullanıcı')}")
        st.divider() # İnce çizgi
        
        # Sayfa Seçim Menüsü
        sayfa = st.radio(
            "Uygulama Menüsü",
            ["🏠 Ana Sayfa", "📂 Eski Projelerim", "⚙️ Ayarlar"]
        )
        
        st.divider()
        # Çıkış butonunu buraya aldık
        authenticator.logout('Çıkış Yap', 'sidebar')
        
    if sayfa == "🏠 Ana Sayfa":
        st.title("🏗️ Akıllı Duvar Ölçüm Sistemi")
        st.write(f"Hoş geldin *{st.session_state.get('name', 'Kullanıcı')}*")
        
        # Mevcut analiz ve dosya yükleme kodların buraya gelecek (try-except bloğu vb.)
        # ...
        
    elif sayfa == "📂 Eski Projelerim":
        st.title("📂 Kayıtlı Projeler")
        st.info("Kayıtlı projeleriniz yakında burada listelenecek.")

    elif sayfa == "⚙️ Ayarlar":
        st.title("⚙️ Ayarlar")
        st.write("Uygulama tercihlerini buradan yönetebilirsiniz.")
    authenticator.logout('Çıkış Yap', 'sidebar')

    st.title("🏗️ Akıllı Duvar Ölçüm Sistemi")
    st.write(f"Hoş geldin *{st.session_state.get('name', 'Kullanıcı')}*")

         try:
            API_KEY = st.secrets["ROBOFLOW_API_KEY"]
    
            WORKSPACE = "bars-workspace-tcviv"
            WORKFLOW = "custom-workflow-2"
            PIXEL_TO_METER_RATIO = 0.02
    
            uploaded_file = st.file_uploader(
                "Mimari Planı Seçin (JPG, PNG)...",
                type=["jpg", "jpeg", "png"]
            )
    
            if uploaded_file is not None:
    
                file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                image = cv2.imdecode(file_bytes, 1)
    
                st.image(image, caption="Yüklenen Plan", use_container_width=True)
    
                if st.button("Metrajı Hesapla ve Analiz Et"):
    
                    with st.spinner('Model analiz ediyor, lütfen bekleyin...'):
    
                        client = InferenceHTTPClient(
                            api_url="https://serverless.roboflow.com",
                            api_key=API_KEY
                        )
    
                        result = client.run_workflow(
                            workspace_name=WORKSPACE,
                            workflow_id=WORKFLOW,
                            images={"image": image}
                        )
    
                        predictions = result[0]['predictions']['predictions']
    
                        metraj_listesi = []
    
                        for i, wall in enumerate(predictions):
    
                            w = wall['width']
                            h = wall['height']
    
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
            st.error(f"Hata oluştu: {e}")
    
    
    elif st.session_state.get("authentication_status") is False:
    
        st.error('Kullanıcı adı veya şifre hatalı')
    
    else:
    
        st.info('Lütfen kullanıcı adı ve şifrenizi giriniz')




