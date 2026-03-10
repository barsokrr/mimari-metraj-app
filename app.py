import streamlit as st
import streamlit_authenticator as stauth
import cv2
import pandas as pd
import numpy as np
from inference_sdk import InferenceHTTPClient
import io

# 1. Sayfa Ayarları (En üstte)
st.set_page_config(page_title="Mimari Metraj Otomasyonu", layout="wide")

# 2. Giriş Sistemi (Recursion ve TypeError çözümü)
# st.secrets'ı doğrudan sözlüğe çevirerek döngüyü kırıyoruz
config = st.secrets.to_dict()

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Giriş panelini çağır (SyntaxError düzeltildi)
name, authentication_status, username = authenticator.login('Giriş Yap', 'main')

if authentication_status:
    if 'user_credits' not in st.session_state:
        st.session_state.user_credits = 10 

    authenticator.logout('Çıkış Yap', 'sidebar')
    st.sidebar.title(f"Hoş geldin, {name}")
    st.sidebar.metric("Kalan Krediniz", st.session_state.user_credits)

    st.title("🏗️ Mimari Plan Duvar Metraj Uygulaması")
    
    # Roboflow Ayarları
    API_KEY = st.secrets["ROBOFLOW_API_KEY"]
    WORKSPACE = "bars-workspace-tcviv"
    WORKFLOW = "custom-workflow-2"
    PIXEL_TO_METER_RATIO = 0.02
    
    client = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key=API_KEY)

    uploaded_file = st.file_uploader("Mimari Planı Seçin...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, 1)
        
        col1, col2 = st.columns(2)
        with col1:
            st.image(image, caption="Yüklenen Plan", use_container_width=True)

        if st.button("Analiz Et"):
            if st.session_state.user_credits > 0:
                with st.spinner('Analiz ediliyor...'):
                    # Orijinal Analiz Kodun
                    cv2.imwrite("temp.jpg", image)
                    result = client.run_workflow(
                        workspace_name=WORKSPACE,
                        workflow_id=WORKFLOW,
                        images={"image": "temp.jpg"}
                    )

                    predictions = result[0]['predictions']['predictions']
                    metraj_listesi = []

                    for i, wall in enumerate(predictions):
                        x, y, w, h = wall['x'], wall['y'], wall['width'], wall['height']
                        m_w = round(w * PIXEL_TO_METER_RATIO, 2)
                        m_h = round(h * PIXEL_TO_METER_RATIO, 2)
                        metraj_listesi.append({
                            "Duvar_ID": f"Duvar-{i+1}",
                            "Genişlik (m)": m_w,
                            "Yükseklik (m)": m_h,
                            "Alan (m2)": round(m_w * m_h, 2)
                        })
                        x1, y1 = int(x - w/2), int(y - h/2)
                        x2, y2 = int(x + w/2), int(y + h/2)
                        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 3)

                    with col2:
                        st.image(image, caption="Analiz Sonucu", use_container_width=True)

                    df = pd.DataFrame(metraj_listesi)
                    st.dataframe(df)

                    st.session_state.user_credits -= 1
                    st.success(f"Analiz tamamlandı! Kalan kredi: {st.session_state.user_credits}")
            else:
                st.error("Krediniz kalmadı!")

elif authentication_status == False:
    st.error('Hatalı giriş.')
elif authentication_status == None:
    st.warning('Lütfen giriş yapın.')
