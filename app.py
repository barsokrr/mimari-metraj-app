import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import numpy as np
import cv2
import pandas as pd
from inference_sdk import InferenceHTTPClient
import tempfile
import math
import matplotlib.pyplot as plt

# --- CONFIG ---
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

authenticator.login(location='main')

# --- AUTH CONTROL ---
if st.session_state.get("authentication_status"):

    # SIDEBAR
    with st.sidebar:
        st.markdown("### 👤 Profil")
        st.write(f"**Kullanıcı:** {st.session_state.get('name')}")

        sayfa = st.radio("Menü", ["🏠 Ana Sayfa", "📂 Eski Projelerim"])

        st.divider()
        authenticator.logout('Çıkış Yap', 'sidebar')

    if sayfa == "🏠 Ana Sayfa":

        st.title("🏗️ Akıllı Duvar Ölçüm Sistemi")

        st.sidebar.header("💰 Maliyet Ayarları")

        kat_yuksekligi = st.sidebar.number_input("Kat Yüksekliği (m)", 1.0, value=3.0)
        duvar_kalinligi = st.sidebar.number_input("Duvar Kalınlığı (m)", 0.01, value=0.20)
        birim_fiyat = st.sidebar.number_input("Birim Fiyat (TL/m³)", 0, value=2500)

        uploaded_file = st.file_uploader(
            "Plan Seçin (Resim veya .dxf)",
            type=["jpg","png","jpeg","dxf"]
        )

        if uploaded_file:

            file_extension = uploaded_file.name.split('.')[-1].lower()

            # ================= DXF ANALİZİ =================
            if file_extension == "dxf":

                st.subheader("📏 AutoCAD (DXF) Analizi")

                try:

                    import ezdxf

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                        tmp.write(uploaded_file.read())
                        tmp_path = tmp.name

                    doc = ezdxf.readfile(tmp_path)
                    msp = doc.modelspace()

                    duvar_uzunlugu = 0
                    duvar_sayisi = 0

                    wall_keywords = ["wall","duvar","a-wall","mim-wall"]

                    # ---------- DUVARLARI GÖRSELLEŞTİR ----------
                    fig, ax = plt.subplots(figsize=(10,10))

                    for entity in msp:

                        if entity.dxftype() == "LINE":

                            start = entity.dxf.start
                            end = entity.dxf.end

                            x1,y1 = start.x,start.y
                            x2,y2 = end.x,end.y

                            x = [x1,x2]
                            y = [y1,y2]

                            uzunluk = math.sqrt((x2-x1)**2 + (y2-y1)**2)

                            layer = entity.dxf.layer.lower()

                            if any(k in layer for k in wall_keywords):

                                duvar_uzunlugu += uzunluk
                                duvar_sayisi += 1

                                # DUVARLARI KIRMIZI ÇİZ
                                ax.plot(x,y,color="red",linewidth=2)

                            else:

                                # DİĞER ÇİZGİLERİ GRİ ÇİZ
                                ax.plot(x,y,color="gray",linewidth=0.5,alpha=0.3)

                    ax.set_aspect('equal')
                    ax.set_title("Kırmızı Çizgiler = Programın Duvar Kabul Ettikleri")

                    st.pyplot(fig)

                    # ---------- METRAJ HESAPLAMA ----------

                    duvar_alani = duvar_uzunlugu * kat_yuksekligi
                    duvar_hacmi = duvar_alani * duvar_kalinligi
                    maliyet = duvar_hacmi * birim_fiyat

                    st.success(f"Toplam Duvar Uzunluğu: {round(duvar_uzunlugu,2)} m")

                    col1,col2,col3 = st.columns(3)

                    col1.metric("Duvar Alanı m²",round(duvar_alani,2))
                    col2.metric("Duvar Hacmi m³",round(duvar_hacmi,2))
                    col3.metric("Tahmini Maliyet TL",round(maliyet,2))

                    data = {
                        "Kalem":[
                            "Duvar Uzunluğu",
                            "Duvar Alanı",
                            "Duvar Hacmi",
                            "Tahmini Maliyet"
                        ],
                        "Değer":[
                            round(duvar_uzunlugu,2),
                            round(duvar_alani,2),
                            round(duvar_hacmi,2),
                            round(maliyet,2)
                        ]
                    }

                    df = pd.DataFrame(data)

                    st.dataframe(df)

                    csv = df.to_csv(index=False).encode("utf-8")

                    st.download_button(
                        "Metraj Raporunu İndir (CSV)",
                        csv,
                        "metraj_raporu.csv",
                        "text/csv"
                    )

                except Exception as e:
                    st.error(f"Hata oluştu: {e}")

            # ================= GÖRSEL ANALİZ =================
            if file_extension in ["jpg","jpeg","png"]:

                st.subheader("🖼 Yapay Zeka Analizi")

                API_KEY = st.secrets["ROBOFLOW_API_KEY"]
                WORKSPACE = "bars-workspace-tcviv"
                WORKFLOW = "custom-workflow-2"

                PIXEL_TO_METER_RATIO = 0.02

                file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                image = cv2.imdecode(file_bytes, 1)

                st.image(image, caption="Yüklenen Plan")

                if st.button("Metrajı Hesapla"):

                    try:

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

                        for i,wall in enumerate(predictions):

                            w = wall['width']
                            h = wall['height']

                            m_w = round(w*PIXEL_TO_METER_RATIO,2)
                            m_h = round(h*PIXEL_TO_METER_RATIO,2)

                            metraj_listesi.append({
                                "Duvar":f"Duvar-{i+1}",
                                "Genişlik":m_w,
                                "Yükseklik":m_h,
                                "Alan":round(m_w*m_h,2)
                            })

                        df = pd.DataFrame(metraj_listesi)

                        st.dataframe(df)

                    except Exception as e:
                        st.error(e)

elif st.session_state.get("authentication_status") is False:
    st.error("Kullanıcı adı veya şifre hatalı")

else:
    st.info("Lütfen giriş yapınız")
