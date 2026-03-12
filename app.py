import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import numpy as np
import cv2
import pandas as pd
import tempfile
import math
import matplotlib.pyplot as plt
import ezdxf
from sklearn.cluster import DBSCAN


# ---------------- GEOMETRY UTILITIES ----------------

def line_length(l):
    x1,y1,x2,y2 = l
    return math.dist((x1,y1),(x2,y2))


def line_vector(l):
    x1,y1,x2,y2 = l
    return np.array([x2-x1,y2-y1])


def line_distance(l1,l2):

    x1,y1,x2,y2 = l1
    x3,y3,x4,y4 = l2

    num = abs((x3-x1)*(y2-y1)-(y3-y1)*(x2-x1))
    den = math.dist((x1,y1),(x2,y2))

    if den == 0:
        return 999

    return num/den


def parallel(l1,l2):

    v1 = line_vector(l1)
    v2 = line_vector(l2)

    if np.linalg.norm(v1)==0 or np.linalg.norm(v2)==0:
        return False

    cos = np.dot(v1,v2)/(np.linalg.norm(v1)*np.linalg.norm(v2))

    return abs(cos)>0.97


# ---------------- DXF PARSER ----------------

def extract_lines_from_dxf(path):

    doc = ezdxf.readfile(path)
    msp = doc.modelspace()

    unit = doc.units
    scale = 1

    if unit == 4:
        scale = 0.001
    elif unit == 5:
        scale = 0.01

    lines=[]

    for e in msp:

        if e.dxftype()=="LINE":

            x1,y1,_=e.dxf.start
            x2,y2,_=e.dxf.end

            l=(x1*scale,y1*scale,x2*scale,y2*scale)

            if line_length(l)>0.3:
                lines.append(l)

        if e.dxftype()=="LWPOLYLINE":

            pts=e.get_points()

            for i in range(len(pts)-1):

                x1,y1=pts[i][0]*scale,pts[i][1]*scale
                x2,y2=pts[i+1][0]*scale,pts[i+1][1]*scale

                l=(x1,y1,x2,y2)

                if line_length(l)>0.3:
                    lines.append(l)

    return lines


# ---------------- WALL DETECTION ----------------

def detect_wall_pairs(lines,wall_thickness):

    walls=[]

    for i in range(len(lines)):

        for j in range(i+1,len(lines)):

            l1=lines[i]
            l2=lines[j]

            if not parallel(l1,l2):
                continue

            d=line_distance(l1,l2)

            if abs(d-wall_thickness)<wall_thickness:

                length=min(line_length(l1),line_length(l2))

                walls.append((l1,l2,length))

    return walls


# ---------------- CENTERLINE EXTRACTION ----------------

def centerline(l1,l2):

    x1,y1,x2,y2=l1
    x3,y3,x4,y4=l2

    cx1=(x1+x3)/2
    cy1=(y1+y3)/2
    cx2=(x2+x4)/2
    cy2=(y2+y4)/2

    return (cx1,cy1,cx2,cy2)


# ---------------- WALL NETWORK ----------------

def build_centerlines(walls):

    centers=[]

    for w in walls:

        c=centerline(w[0],w[1])
        centers.append(c)

    return centers


# ---------------- STREAMLIT CONFIG ----------------

with open("config.yaml") as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

authenticator.login(location="main")


# ---------------- APP ----------------

if st.session_state.get("authentication_status"):

    with st.sidebar:

        st.title("Profil")
        st.write(st.session_state.get("name"))

        kat_yuksekligi = st.number_input("Kat Yüksekliği",value=3.0)
        duvar_kalinligi = st.number_input("Duvar Kalınlığı",value=0.20)
        birim_fiyat = st.number_input("Birim Fiyat",value=2500)

        authenticator.logout("Çıkış Yap","sidebar")


    st.title("AI Mimari Metraj (Togal Mantığı)")


    uploaded_file = st.file_uploader(
        "Plan yükle",
        type=["dxf"]
    )


    if uploaded_file:

        with tempfile.NamedTemporaryFile(delete=False,suffix=".dxf") as tmp:

            tmp.write(uploaded_file.read())
            path=tmp.name


        lines=extract_lines_from_dxf(path)

        walls=detect_wall_pairs(lines,duvar_kalinligi)

        centers=build_centerlines(walls)

        duvar_uzunlugu=sum([line_length(c) for c in centers])


        # --------- GÖRSEL ---------

        fig,ax=plt.subplots(figsize=(10,10))

        for c in centers:

            x1,y1,x2,y2=c

            ax.plot([x1,x2],[y1,y2],color="red",linewidth=2)

        ax.set_aspect("equal")

        st.pyplot(fig)


        # --------- METRAJ ---------

        alan=duvar_uzunlugu*kat_yuksekligi
        hacim=alan*duvar_kalinligi
        maliyet=hacim*birim_fiyat


        col1,col2,col3=st.columns(3)

        col1.metric("Duvar Uzunluğu",round(duvar_uzunlugu,2))
        col2.metric("Duvar Alanı",round(alan,2))
        col3.metric("Maliyet",round(maliyet,2))


elif st.session_state.get("authentication_status") is False:

    st.error("Kullanıcı adı veya şifre hatalı")

else:

    st.info("Lütfen giriş yapınız")
