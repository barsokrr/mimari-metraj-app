import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import numpy as np
import pandas as pd
import tempfile
import math
import matplotlib.pyplot as plt
import ezdxf


# ------------------------------------------------
# GEOMETRY
# ------------------------------------------------

def line_length(l):
    x1,y1,x2,y2 = l
    return math.dist((x1,y1),(x2,y2))


def line_angle(l):
    x1,y1,x2,y2 = l
    return abs(math.degrees(math.atan2(y2-y1,x2-x1)))


def line_vector(l):
    x1,y1,x2,y2 = l
    return np.array([x2-x1,y2-y1])


def parallel(l1,l2):

    v1=line_vector(l1)
    v2=line_vector(l2)

    if np.linalg.norm(v1)==0 or np.linalg.norm(v2)==0:
        return False

    cos=np.dot(v1,v2)/(np.linalg.norm(v1)*np.linalg.norm(v2))

    return abs(cos)>0.98


def line_distance(l1,l2):

    x1,y1,x2,y2=l1
    x3,y3,x4,y4=l2

    num=abs((x3-x1)*(y2-y1)-(y3-y1)*(x2-x1))
    den=math.dist((x1,y1),(x2,y2))

    if den==0:
        return 999

    return num/den


# ------------------------------------------------
# DXF PARSER
# ------------------------------------------------

def extract_lines_from_dxf(path):

    doc = ezdxf.readfile(path)
    msp = doc.modelspace()

    lines=[]

    for e in msp:

        if e.dxftype()=="LINE":

            x1,y1,_ = e.dxf.start
            x2,y2,_ = e.dxf.end

            l=(x1,y1,x2,y2)

            if line_length(l)>5:   # küçük çizgileri filtrele

                angle=line_angle(l)

                if angle<10 or abs(angle-90)<10:
                    lines.append(l)


        if e.dxftype()=="LWPOLYLINE":

            pts=list(e.get_points())

            for i in range(len(pts)-1):

                x1,y1=pts[i][0],pts[i][1]
                x2,y2=pts[i+1][0],pts[i+1][1]

                l=(x1,y1,x2,y2)

                if line_length(l)>5:

                    angle=line_angle(l)

                    if angle<10 or abs(angle-90)<10:
                        lines.append(l)

    return lines


# ------------------------------------------------
# WALL DETECTION
# ------------------------------------------------

def detect_wall_pairs(lines,wall_thickness):

    walls=[]
    tolerance=wall_thickness*0.5

    for i in range(len(lines)):

        for j in range(i+1,len(lines)):

            l1=lines[i]
            l2=lines[j]

            if not parallel(l1,l2):
                continue

            d=line_distance(l1,l2)

            if abs(d-wall_thickness)<tolerance:

                length=min(line_length(l1),line_length(l2))

                if length>100:   # ölçü çizgilerini filtrele
                    walls.append((l1,l2))

    return walls


# ------------------------------------------------
# CENTERLINE
# ------------------------------------------------

def centerline(l1,l2):

    x1,y1,x2,y2=l1
    x3,y3,x4,y4=l2

    cx1=(x1+x3)/2
    cy1=(y1+y3)/2
    cx2=(x2+x4)/2
    cy2=(y2+y4)/2

    return (cx1,cy1,cx2,cy2)


def build_centerlines(walls):

    centers=[]

    for w in walls:
        centers.append(centerline(w[0],w[1]))

    return centers


# ------------------------------------------------
# MERGE WALL SEGMENTS
# ------------------------------------------------

def merge_segments(lines):

    merged=[]
    used=[False]*len(lines)

    gap=1200   # kapı boşluğu toleransı (mm)

    for i in range(len(lines)):

        if used[i]:
            continue

        x1,y1,x2,y2=lines[i]

        for j in range(i+1,len(lines)):

            if used[j]:
                continue

            l2=lines[j]

            if parallel(lines[i],l2):

                if line_distance(lines[i],l2)<5:

                    x3,y3,x4,y4=l2

                    if abs(x2-x3)<gap or abs(y2-y3)<gap:

                        x1=min(x1,x3)
                        y1=min(y1,y3)
                        x2=max(x2,x4)
                        y2=max(y2,y4)

                        used[j]=True

        merged.append((x1,y1,x2,y2))

    return merged


# ------------------------------------------------
# AUTH
# ------------------------------------------------

with open("config.yaml") as file:
    config=yaml.load(file,Loader=SafeLoader)

authenticator=stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

authenticator.login(location="main")


# ------------------------------------------------
# APP
# ------------------------------------------------

if st.session_state.get("authentication_status"):

    with st.sidebar:

        st.title("Profil")

        st.write(st.session_state.get("name"))

        kat_yuksekligi=st.number_input("Kat Yüksekliği",value=3.0)

        duvar_kalinligi=st.number_input("Duvar Kalınlığı",value=200.0)

        birim_fiyat=st.number_input("Birim Fiyat",value=2500)

        authenticator.logout("Çıkış Yap","sidebar")


    st.title("AI Mimari Metraj")


    uploaded_file=st.file_uploader("Plan yükle",type=["dxf"])


    if uploaded_file:

        with tempfile.NamedTemporaryFile(delete=False,suffix=".dxf") as tmp:

            tmp.write(uploaded_file.read())
            path=tmp.name


        lines=extract_lines_from_dxf(path)

        walls=detect_wall_pairs(lines,duvar_kalinligi)

        centers=build_centerlines(walls)

        centers=merge_segments(centers)


        duvar_uzunlugu=sum([line_length(c) for c in centers])


        # ------------------------------------------------
        # VISUAL
        # ------------------------------------------------

        fig,ax=plt.subplots(figsize=(10,10))

        for c in centers:

            x1,y1,x2,y2=c

            ax.plot([x1,x2],[y1,y2],color="red",linewidth=3)

        ax.set_aspect("equal")

        st.pyplot(fig)


        # ------------------------------------------------
        # METRAJ
        # ------------------------------------------------

        duvar_uzunlugu_m=duvar_uzunlugu/1000

        alan=duvar_uzunlugu_m*kat_yuksekligi

        hacim=alan*(duvar_kalinligi/1000)

        maliyet=hacim*birim_fiyat


        col1,col2,col3=st.columns(3)

        col1.metric("Duvar Uzunluğu (m)",round(duvar_uzunlugu_m,2))

        col2.metric("Duvar Alanı (m²)",round(alan,2))

        col3.metric("Maliyet",round(maliyet,2))


elif st.session_state.get("authentication_status") is False:

    st.error("Kullanıcı adı veya şifre hatalı")

else:

    st.info("Lütfen giriş yapınız")
