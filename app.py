import streamlit as st
import streamlit_authenticator as stauth
import cv2
import pandas as pd
import numpy as np
from inference_sdk import InferenceHTTPClient
import io

# --- 1. SAYFA AYARLARI ---
# Bu komut her zaman en üstte olmalıdır
st.set_page_config(page_title="Mimari Metraj Otomasyonu", layout="wide")

# --- 2. GİRİŞ SİSTEMİ ---
authenticator = stauth.Authenticate(
    st.secrets['credentials'],
    st.secrets['cookie']['name'],
    st.secrets['cookie']['key'],
    st.secrets['cookie']['expiry_days']
)

name, authentication_status, username = authenticator.login('Giriş Yap', 'main')

# --- 3. UYGULAMA MANTIĞI ---
if authentication_status:
    # Giriş başarılıysa kredi sistemini başlat
    if 'user_credits' not in st.session_state:
        st.session_state.user_credits = 10  # Yeni kullanıcıya 10 kredi tanımla

    # Yan panel (Sidebar) ayarları
    authenticator.logout('Çıkış Yap', 'sidebar')
    st.sidebar.title(f"Hoş geldin, {name}")
    st.sidebar.metric("Kalan Analiz Krediniz", st.session_state.user_credits)
    st.sidebar.info("Krediniz bittiğinde yeni paket satın almalısınız.")

    # Ana sayfa başlıkları
    st.title("🏗️ Mimari Plan Duvar Metraj Uygulaması")
    st.write("Planınızı yükleyin, duvarları otomatik tespit edelim ve metrajı Excel olarak verelim.")

    # Ayarlar (Roboflow)
    API_KEY = st.secrets["ROBOFLOW_API_KEY"]
    WORKSPACE = "bars-workspace-tcviv"
    WORKFLOW = "custom-workflow-2"
    PIXEL_TO_METER_RATIO = 0.02
    
    client = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key=API_KEY)

    # Dosya Yükleme
    uploaded_file = st.file_uploader("Mimari Planı Seçin (JPG, PNG)...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        # Resmi oku ve göster
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, 1)
        
        col1, col2 = st.columns(2)
        with col1:
            st.image(image, caption="Yüklenen Plan", use_column_width=True)

        # Analiz Butonu ve Kredi Kontrolü
        if st.button("Metrajı Hesapla ve Analiz Et"):
            if st.session_state.user_credits > 0:
                with st.spinner('AI Modeli analiz ediyor, lütfen bekleyin...'):
                    # Geçici olarak dosyayı kaydet ve Roboflow'a gönder
                    cv2.imwrite("temp.jpg", image)
                    result = client.run_workflow(
                        workspace_name=WORKSPACE,
                        workflow_id=WORKFLOW,
                        images={"image": "temp.jpg"}
                    )

                    # Veriyi İşleme
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
                        # Resme çizim yap
                        x1, y1 = int(x - w/2), int(y - h/2)
                        x2, y2 = int(x + w/2), int(y + h/2)
                        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 3)

                    with col2:
                        st.image(image, caption="Tespit Edilen Alanlar", use_column_width=True)

                    # Sonuçları Göster
                    df = pd.DataFrame(metraj_listesi)
                    st.write("### 📊 Metraj Sonuçları")
                    st.dataframe(df)

                    # Excel İndirme Butonu
                    towrite = io.BytesIO()
                    df.to_excel(towrite, index=False, engine='openpyxl')
                    towrite.seek(0)
                    st.download_button(
                        label="📥 Excel Listesini İndir",
                        data=towrite,
                        file_name="mimari_metraj.xlsx",
                        mime="application/vnd.ms-excel"
                    )

                    # KREDİ DÜŞÜRME
                    st.session_state.user_credits -= 1
                    st.success(f"Analiz tamamlandı! 1 kredi kullanıldı. Kalan: {st.session_state.user_credits}")
            else:
                st.error("🚫 Krediniz yetersiz! Lütfen yeni kredi yükleyin.")

elif authentication_status == False:
    st.error('❌ Kullanıcı adı veya şifre hatalı')
elif authentication_status == None:
    st.warning('👋 Lütfen kullanıcı adı ve şifrenizi girerek uygulamayı başlatın.')
