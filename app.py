import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os
import numpy as np

# -------------------------------------------------
# SAYFA AYARI
# -------------------------------------------------
st.set_page_config(page_title="Metraj Pro | Barış Öker", layout="wide", page_icon="🏢")

st.markdown("""
<style>
.stApp { background-color:#0e1117; }
[data-testid="stMetricValue"],[data-testid="stMetricLabel"]{color:#000!important;}
div[data-testid="stMetric"]{background:#fff;border:1px solid #dcdde1;padding:20px;border-radius:12px;}
h1,h2,h3,p{color:#fff!important;}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# LOGIN
# -------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in=False

if not st.session_state.logged_in:

    _,c,_=st.columns([1,1.2,1])

    with c:
        st.title("🏢 Metraj Pro Giriş")

        with st.form("login"):
            u=st.text_input("Kullanıcı")
            p=st.text_input("Şifre",type="password")
            s=st.form_submit_button("Başlat")

            if s:
                if u=="admin" and p=="123":
                    st.session_state.logged_in=True
                    st.rerun()
                else:
                    st.error("Giriş hatalı")

    st.stop()

# -------------------------------------------------
# DXF SEGMENT OKUMA
# -------------------------------------------------
def read_segments(path,scale,layers):

    doc=ezdxf.readfile(path)
    msp=doc.modelspace()

    segments=[]

    targets=[l.upper().strip() for l in layers.split(",") if l.strip()]

    for e in msp.query("LINE LWPOLYLINE POLYLINE INSERT"):

        if targets:
            if not any(t in e.dxf.layer.upper() for t in targets):
                continue

        temp=[]

        if e.dxftype()=="LINE":
            temp.append(((e.dxf.start.x,e.dxf.start.y),(e.dxf.end.x,e.dxf.end.y)))

        elif e.dxftype() in ("LWPOLYLINE","POLYLINE"):
            pts=list(e.get_points())
            for i in range(len(pts)-1):
                temp.append(((pts[i][0],pts[i][1]),(pts[i+1][0],pts[i+1][1])))

        elif e.dxftype()=="INSERT":
            for sub in e.virtual_entities():
                if sub.dxftype()=="LINE":
                    temp.append(((sub.dxf.start.x,sub.dxf.start.y),(sub.dxf.end.x,sub.dxf.end.y)))

        for s in temp:

            p1=(s[0][0]/scale,s[0][1]/scale)
            p2=(s[1][0]/scale,s[1][1]/scale)

            ln=math.dist(p1,p2)

            if ln>0.20:
                segments.append({"p1":p1,"p2":p2,"len":ln})

    return segments

# -------------------------------------------------
# PARALEL DUVAR TESPİTİ
# -------------------------------------------------
def detect_walls(segments):

    walls=[]
    used=set()

    ANGLE_TOL=5
    DIST_TOL=0.35

    for i,a in enumerate(segments):

        if i in used:
            continue

        ax=a["p2"][0]-a["p1"][0]
        ay=a["p2"][1]-a["p1"][1]

        ang1=math.degrees(math.atan2(ay,ax))

        for j,b in enumerate(segments):

            if i==j or j in used:
                continue

            bx=b["p2"][0]-b["p1"][0]
            by=b["p2"][1]-b["p1"][1]

            ang2=math.degrees(math.atan2(by,bx))

            if abs(abs(ang1-ang2))<ANGLE_TOL:

                d=np.linalg.norm(np.array(a["p1"])-np.array(b["p1"]))

                if d<DIST_TOL:

                    mid1=((a["p1"][0]+b["p1"][0])/2,(a["p1"][1]+b["p1"][1])/2)
                    mid2=((a["p2"][0]+b["p2"][0])/2,(a["p2"][1]+b["p2"][1])/2)

                    ln=math.dist(mid1,mid2)

                    walls.append({
                        "path":(mid1,mid2),
                        "len":ln
                    })

                    used.add(i)
                    used.add(j)

                    break

    return walls

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
st.sidebar.title("📊 Metraj Kontrol Paneli")

with st.sidebar:

    st.success("👤 Kullanıcı: Barış Öker")

    dxf_file=st.file_uploader("DXF Yükle",type=["dxf"])

    layer=st.text_input("Katman","DUVAR")

    unit=st.selectbox("Birim",["cm","mm","m"],index=0)

    height=st.number_input("Yükseklik (m)",value=2.85,step=0.01)

    if st.button("Çıkış"):
        st.session_state.logged_in=False
        st.rerun()

# -------------------------------------------------
# ANALİZ
# -------------------------------------------------
if dxf_file:

    with tempfile.NamedTemporaryFile(delete=False,suffix=".dxf") as tmp:
        tmp.write(dxf_file.getbuffer())
        path=tmp.name

    scale=100 if unit=="cm" else 1000 if unit=="mm" else 1

    segments=read_segments(path,scale,layer)

    walls=detect_walls(segments)

    if walls:

        total=sum(w["len"] for w in walls)

        st.subheader("Analiz Raporu")

        c1,c2,c3=st.columns(3)

        c1.metric("Net Uzunluk",f"{round(total,2)} m")

        c2.metric("Toplam Alan",f"{round(total*height,2)} m²")

        c3.metric("Duvar Sayısı",len(walls))

        # -------------------------------------------------
        # GÖRSEL
        # -------------------------------------------------
        st.subheader("Analiz Önizleme")

        v1,v2=st.columns(2)

        with v1:

            fig,ax=plt.subplots(figsize=(8,6),facecolor="#0e1117")

            doc=ezdxf.readfile(path)
            msp=doc.modelspace()

            for e in msp.query("LINE LWPOLYLINE POLYLINE"):

                if e.dxftype()=="LINE":

                    ax.plot(
                        [e.dxf.start.x,e.dxf.end.x],
                        [e.dxf.start.y,e.dxf.end.y],
                        color="#576574",
                        lw=0.5
                    )

                elif e.dxftype() in ("LWPOLYLINE","POLYLINE"):

                    pts=list(e.get_points())

                    for i in range(len(pts)-1):

                        ax.plot(
                            [pts[i][0],pts[i+1][0]],
                            [pts[i][1],pts[i+1][1]],
                            color="#576574",
                            lw=0.5
                        )

            ax.set_aspect("equal")
            ax.axis("off")

            st.pyplot(fig)

        with v2:

            fig,ax=plt.subplots(figsize=(8,6),facecolor="#0e1117")

            for w in walls:

                p1,p2=w["path"]

                ax.plot(
                    [p1[0]*scale,p2[0]*scale],
                    [p1[1]*scale,p2[1]*scale],
                    color="#00d2ff",
                    lw=2
                )

            ax.set_aspect("equal")
            ax.axis("off")

            st.pyplot(fig)

        # -------------------------------------------------
        # TABLO
        # -------------------------------------------------
        st.subheader("📋 Metraj Listesi")

        df=pd.DataFrame([{
            "No":i+1,
            "Uzunluk (m)":round(w["len"],2),
            "Alan (m²)":round(w["len"]*height,2)
        } for i,w in enumerate(walls)])

        st.dataframe(df,use_container_width=True)

    os.remove(path)
