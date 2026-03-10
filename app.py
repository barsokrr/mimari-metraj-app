import streamlit as st
import streamlit_authenticator as stauth
import yaml
import numpy as np
from inference_sdk import InferenceHTTPClient
import io
import cv2
import pandas as pd

# --- GİRİŞ SİSTEMİ AYARLARI ---
# Hata Çözümü: Veriyi manuel bir sözlüğe dökerek tüm bağları koparıyoruz
raw_creds = st.secrets['credentials']
credentials_data = {
    "usernames": {
        user: {
            "name": data["name"],
            "password": data["password"]
        } for user, data in raw_creds["usernames"].items()
    }
}

authenticator = stauth.Authenticate(
    credentials_data,
    st.secrets['cookie']['name'],
    st.secrets['cookie']['key'],
    st.secrets['cookie']['expiry_days']
)

# Giriş formunu ekranda göster
# Eski hali: name, authentication_status, username = authenticator.login('Giriş Yap', 'main')
# Yeni hali:
authentication_status = authenticator.login(location='main')

# --- UYGULAMA MANTIĞI ---
if authentication_status:
    authenticator.logout('Çıkış Yap', 'sidebar')
    # st.session_state içinde saklanan ismi kullanıyoruz
    st.write(f"Hoş geldin *{st.session_state['name']}*")

    # Sayfa Ayarları
    st.title("🏗️ Mimari Plan Duvar Metraj Uygulaması")
    st.write("Planınızı yükleyin, duvarları otomatik tespit edelim ve metrajı Excel olarak verelim.")

    API_KEY = st.secrets["ROBOFLOW_API_KEY"]
    WORKSPACE = "bars-workspace-tcviv"
    WORKFLOW = "custom-workflow-2"
    PIXEL_TO_METER_RATIO = 0.02 

    client = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key=API_KEY)

    # 2. Dosya Yükleme Alanı
    uploaded_file = st.file_uploader("Mimari Planı Seçin (JPG, PNG)...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, 1)

        col1, col2 = st.columns(2)

        with col1:
            st.image(image, caption="Yüklenen Plan", use_column_width=True)

        if st.button("Metrajı Hesapla ve Analiz Et"):
            with st.spinner('Model analiz ediyor, lütfen bekleyin...'):
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
                    st.image(image, caption="Tespit Edilen Alanlar", use_column_width=True)

                df = pd.DataFrame(metraj_listesi)
                st.write("### Metraj Sonuçları")
                st.dataframe(df)

                towrite = io.BytesIO()
                df.to_excel(towrite, index=False, engine='openpyxl')
                towrite.seek(0)
                st.download_button(
                    label="📥 Excel Listesini İndir",
                    data=towrite,
                    file_name="mimari_metraj.xlsx",
                    mime="application/vnd.ms-excel"
                )
                st.success(f"Analiz tamamlandı! {len(predictions)} adet alan tespit edildi.")

elif authentication_status == False:
    st.error('Kullanıcı adı veya şifre hatalı')
elif authentication_status == None:
    st.warning('Lütfen kullanıcı adı ve şifrenizi giriniz')




