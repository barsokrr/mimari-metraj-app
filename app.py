import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import numpy as np
from inference_sdk import InferenceHTTPClient


# ---------------- CONFIG ----------------

with open("config.yaml") as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)


# ---------------- LOGIN ----------------

authenticator.login()

if st.session_state["authentication_status"]:


    authenticator.logout("Çıkış Yap", "sidebar")

    st.title("🏗️ DUVAR METRAJ PANELİ")

    st.sidebar.success(f"Hoş geldin {st.session_state['name']}")


    # ---------------- AYARLAR ----------------

    with st.sidebar:

        st.header("⚙️ Ayarlar")

        uploaded = st.file_uploader(
            "DXF plan yükle",
            type=["dxf"]
        )

        kat_yuk = st.number_input(
            "Kat Yüksekliği (m)",
            value=2.85
        )

        birim = st.selectbox(
            "Çizim Birimi",
            ["cm","mm","m"]
        )

        katman = st.text_input(
            "Duvar Katmanı",
            "DUVAR"
        )


    # ---------------- DXF OKUMA ----------------

    def read_dxf(path, layer_filter):

        doc = ezdxf.readfile(path)
        msp = doc.modelspace()

        geometries=[]

        for e in msp.query("LINE LWPOLYLINE"):

            layer = e.dxf.layer.upper()

            if layer_filter.upper() not in layer:
                continue

            if e.dxftype()=="LINE":

                p1=e.dxf.start
                p2=e.dxf.end

                geometries.append([(p1[0],p1[1]),(p2[0],p2[1])])


            if e.dxftype()=="LWPOLYLINE":

                pts=e.get_points()

                poly=[(p[0],p[1]) for p in pts]

                geometries.append(poly)


        return geometries


    def total_length(geos):

        length=0

        for g in geos:

            for i in range(len(g)-1):

                length+=math.dist(g[i],g[i+1])

        return length


    # ---------------- ANALİZ ----------------

    if uploaded:

        with tempfile.NamedTemporaryFile(delete=False,suffix=".dxf") as tmp:

            tmp.write(uploaded.getbuffer())

            path=tmp.name


        geos = read_dxf(path, katman)

        if geos:

            raw_len = total_length(geos)

            bolen = 100 if birim=="cm" else 1000 if birim=="mm" else 1

            final_length = (raw_len/2)/bolen


            col1,col2 = st.columns([2,1])


            # PLAN GÖRSEL

            with col1:

                st.subheader("Plan Görünümü")

                fig,ax = plt.subplots(figsize=(8,6))

                for g in geos:

                    xs,ys = zip(*g)

                    ax.plot(xs,ys,color="orange")

                ax.set_aspect("equal")

                ax.axis("off")

                st.pyplot(fig)



            # SONUÇ

            with col2:

                st.subheader("Metraj")

                st.metric("Duvar Uzunluğu", f"{round(final_length,2)} m")

                st.metric("Duvar Alanı", f"{round(final_length*kat_yuk,2)} m²")


        else:

            st.warning("Duvar katmanı bulunamadı.")



elif st.session_state["authentication_status"] == False:

    st.error("Kullanıcı adı veya şifre hatalı")


else:

    st.warning("Lütfen giriş yapınız")
