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
import ezdxf


# ---------------- CONFIG ----------------

with open("config.yaml") as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

authenticator.login(location="main")


# ---------------- AUTH ----------------

if st.session_state.get("authentication_status"):

    with st.sidebar:

        st.title("👤 Profil")
        st.write(st.session_state.get("name"))

        sayfa = st.radio(
            "Menü",
            ["Ana Sayfa", "Eski Projeler"]
        )

        st.divider()

        st.header("Maliyet Ayarları")

        kat_yuksekligi = st.number_input(
            "Kat Yüksekliği (m)",
            value=3.0
        )

        duvar_kalinligi = st.number_input(
            "Duvar Kalınlığı (m)",
            value=0.20
        )

        birim_fiyat = st.number_input(
            "Birim Fiyat (TL/m3)",
            value=2500
        )

        st.divider()

        st.header("Görsel Ölçek Ayarı")

        referans_metre = st.number_input(
            "Referans Uzunluk (m)",
            value=1.0
        )

        referans_pixel = st.number_input(
            "Referans Pixel",
            value=100
        )

        authenticator.logout("Çıkış Yap", "sidebar")

    PIXEL_TO_METER = referans_metre / referans_pixel

    # ---------------- ANA SAYFA ----------------

    if sayfa == "Ana Sayfa":

        st.title("Akıllı Mimari Metraj Sistemi")

        uploaded_file = st.file_uploader(
            "Plan yükleyin",
            type=["jpg", "png", "jpeg", "dxf"]
        )

        if uploaded_file:

            ext = uploaded_file.name.split(".")[-1].lower()

            # --------------------------------------------------
            # DXF ANALİZİ
            # --------------------------------------------------

            if ext == "dxf":

                st.subheader("DXF Plan Analizi")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:

                    tmp.write(uploaded_file.read())
                    path = tmp.name

                doc = ezdxf.readfile(path)
                msp = doc.modelspace()

                wall_layers = [
                    "wall",
                    "duvar",
                    "a-wall",
                    "mim-wall",
                    "partition",
                ]

                duvar_uzunlugu = 0

                fig, ax = plt.subplots(figsize=(8, 8))

                for entity in msp:

                    layer = entity.dxf.layer.lower()

                    if not any(k in layer for k in wall_layers):
                        continue

                    # ---------- LINE ----------

                    if entity.dxftype() == "LINE":

                        x1, y1, _ = entity.dxf.start
                        x2, y2, _ = entity.dxf.end

                        length = math.dist((x1, y1), (x2, y2))

                        duvar_uzunlugu += length

                        ax.plot([x1, x2], [y1, y2], color="red")

                    # ---------- LWPOLYLINE ----------

                    if entity.dxftype() == "LWPOLYLINE":

                        pts = entity.get_points()

                        for i in range(len(pts) - 1):

                            x1, y1 = pts[i][0], pts[i][1]
                            x2, y2 = pts[i + 1][0], pts[i + 1][1]

                            length = math.dist((x1, y1), (x2, y2))

                            duvar_uzunlugu += length

                            ax.plot([x1, x2], [y1, y2], color="red")

                    # ---------- POLYLINE ----------

                    if entity.dxftype() == "POLYLINE":

                        verts = [v.dxf.location for v in entity.vertices]

                        for i in range(len(verts) - 1):

                            x1, y1, _ = verts[i]
                            x2, y2, _ = verts[i + 1]

                            length = math.dist((x1, y1), (x2, y2))

                            duvar_uzunlugu += length

                            ax.plot([x1, x2], [y1, y2], color="red")

                ax.set_aspect("equal")

                st.pyplot(fig)

                # ----- METRAJ HESABI -----

                duvar_alani = duvar_uzunlugu * kat_yuksekligi
                duvar_hacmi = duvar_alani * duvar_kalinligi
                maliyet = duvar_hacmi * birim_fiyat

                st.success(f"Toplam Duvar Uzunluğu: {round(duvar_uzunlugu,2)} m")

                col1, col2, col3 = st.columns(3)

                col1.metric("Duvar Alanı", round(duvar_alani, 2))
                col2.metric("Duvar Hacmi", round(duvar_hacmi, 2))
                col3.metric("Maliyet", round(maliyet, 2))

                df = pd.DataFrame({

                    "Kalem": [
                        "Duvar Uzunluğu",
                        "Duvar Alanı",
                        "Duvar Hacmi",
                        "Tahmini Maliyet",
                    ],

                    "Değer": [
                        round(duvar_uzunlugu, 2),
                        round(duvar_alani, 2),
                        round(duvar_hacmi, 2),
                        round(maliyet, 2),
                    ],
                })

                st.dataframe(df)

                csv = df.to_csv(index=False).encode("utf-8")

                st.download_button(
                    "CSV indir",
                    csv,
                    "metraj.csv",
                    "text/csv",
                )

            # --------------------------------------------------
            # AI GÖRSEL ANALİZ
            # --------------------------------------------------

            if ext in ["jpg", "jpeg", "png"]:

                st.subheader("AI Plan Analizi")

                API_KEY = st.secrets["ROBOFLOW_API_KEY"]

                WORKSPACE = "bars-workspace-tcviv"
                WORKFLOW = "custom-workflow-2"

                file_bytes = np.asarray(
                    bytearray(uploaded_file.read()),
                    dtype=np.uint8
                )

                image = cv2.imdecode(file_bytes, 1)

                st.image(image)

                if st.button("AI Analizi Başlat"):

                    client = InferenceHTTPClient(
                        api_url="https://serverless.roboflow.com",
                        api_key=API_KEY,
                    )

                    result = client.run_workflow(
                        workspace_name=WORKSPACE,
                        workflow_id=WORKFLOW,
                        images={"image": image},
                    )

                    preds = result[0]["predictions"]["predictions"]

                    duvar_toplam = 0

                    rows = []

                    for i, wall in enumerate(preds):

                        w = wall["width"]
                        h = wall["height"]

                        pixel_length = max(w, h)

                        metre = pixel_length * PIXEL_TO_METER

                        duvar_toplam += metre

                        rows.append({

                            "Duvar": f"Duvar-{i+1}",
                            "Uzunluk (m)": round(metre, 2),

                        })

                    df = pd.DataFrame(rows)

                    st.dataframe(df)

                    st.success(f"Toplam Duvar Uzunluğu: {round(duvar_toplam,2)} m")

elif st.session_state.get("authentication_status") is False:

    st.error("Kullanıcı adı veya şifre hatalı")

else:

    st.info("Lütfen giriş yapınız")
