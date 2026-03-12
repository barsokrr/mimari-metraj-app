import streamlit as st
import ezdxf
import numpy as np
import matplotlib.pyplot as plt
import tempfile
import math

# -------------------------
# GEOMETRİ FONKSİYONLARI
# -------------------------

def line_length(l):
    x1,y1,x2,y2=l
    return math.dist((x1,y1),(x2,y2))

def line_angle(l):
    x1,y1,x2,y2=l
    return abs(math.degrees(math.atan2(y2-y1,x2-x1)))

def line_vector(l):
    x1,y1,x2,y2=l
    return np.array([x2-x1,y2-y1])

def parallel(l1,l2):

    v1=line_vector(l1)
    v2=line_vector(l2)

    if np.linalg.norm(v1)==0 or np.linalg.norm(v2)==0:
        return False

    cos=np.dot(v1,v2)/(np.linalg.norm(v1)*np.linalg.norm(v2))

    return abs(cos)>0.995


def line_distance(l1,l2):

    x1,y1,x2,y2=l1
    x3,y3,x4,y4=l2

    num=abs((x3-x1)*(y2-y1)-(y3-y1)*(x2-x1))
    den=math.dist((x1,y1),(x2,y2))

    if den==0:
        return 999

    return num/den


# -------------------------
# DXF OKUMA
# -------------------------

def read_dxf_lines(path,target_layers):

    doc=ezdxf.readfile(path)
    msp=doc.modelspace()

    lines=[]

    for e in msp:

        layer=e.dxf.layer.upper()

        if not any(t.upper() in layer for t in target_layers):
            continue

        if e.dxftype()=="LINE":

            x1,y1,_=e.dxf.start
            x2,y2,_=e.dxf.end

            l=(x1,y1,x2,y2)

            if line_length(l)>200:
                lines.append(l)


        if e.dxftype()=="LWPOLYLINE":

            pts=list(e.get_points())

            for i in range(len(pts)-1):

                x1,y1=pts[i][0],pts[i][1]
                x2,y2=pts[i+1][0],pts[i+1][1]

                l=(x1,y1,x2,y2)

                if line_length(l)>200:
                    lines.append(l)

    return lines


# -------------------------
# YATAY / DİKEY AYIR
# -------------------------

def split_orientation(lines):

    h=[]
    v=[]

    for l in lines:

        a=line_angle(l)

        if a<10:
            h.append(l)

        elif abs(a-90)<10:
            v.append(l)

    return h,v


# -------------------------
# DUVAR TESPİT
# -------------------------

def detect_walls(lines,wall_thickness):

    walls=[]

    tol=wall_thickness*0.5

    for i in range(len(lines)):

        for j in range(i+1,len(lines)):

            l1=lines[i]
            l2=lines[j]

            if not parallel(l1,l2):
                continue

            d=line_distance(l1,l2)

            if abs(d-wall_thickness)<tol:

                length=min(line_length(l1),line_length(l2))

                if length>800:
                    walls.append((l1,l2))

    return walls


# -------------------------
# DUVAR EKSENİ
# -------------------------

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


# -------------------------
# SEGMENT BİRLEŞTİRME
# -------------------------

def merge_segments(lines):

    merged=[]
    used=[False]*len(lines)

    gap=1500

    for i in range(len(lines)):

        if used[i]:
            continue

        x1,y1,x2,y2=lines[i]

        for j in range(i+1,len(lines)):

            if used[j]:
                continue

            l2=lines[j]

            if parallel(lines[i],l2):

                if line_distance(lines[i],l2)<10:

                    x3,y3,x4,y4=l2

                    if abs(x2-x3)<gap or abs(y2-y3)<gap:

                        x1=min(x1,x3)
                        y1=min(y1,y3)
                        x2=max(x2,x4)
                        y2=max(y2,y4)

                        used[j]=True

        merged.append((x1,y1,x2,y2))

    return merged


# -------------------------
# RECTANGLE DUVAR ÇİZİMİ
# -------------------------

def draw_wall(ax,line,thickness):

    x1,y1,x2,y2=line

    dx=x2-x1
    dy=y2-y1

    L=math.sqrt(dx*dx+dy*dy)

    nx=-dy/L
    ny=dx/L

    t=thickness/2

    p1=(x1+nx*t,y1+ny*t)
    p2=(x2+nx*t,y2+ny*t)
    p3=(x2-nx*t,y2-ny*t)
    p4=(x1-nx*t,y1-ny*t)

    xs=[p1[0],p2[0],p3[0],p4[0],p1[0]]
    ys=[p1[1],p2[1],p3[1],p4[1],p1[1]]

    ax.fill(xs,ys,color="#f1c40f",alpha=0.8)


# -------------------------
# STREAMLIT
# -------------------------

st.set_page_config(page_title="AI Mimari Metraj",layout="wide")

st.title("🏗️ Akıllı Duvar Metrajı")

with st.sidebar:

    st.header("Analiz Ayarları")

    uploaded=st.file_uploader("DXF yükle",type=["dxf"])

    kat=st.number_input("Kat yüksekliği (m)",value=3.0)

    duvar_kalinligi=st.number_input("Duvar kalınlığı (mm)",value=200.0)

    birim=st.selectbox("Çizim birimi",["mm","cm","m"])

    katman=st.text_input("Duvar katmanları","DUVAR,WALL,A-WALL")

    target_layers=[x.strip() for x in katman.split(",")]


if uploaded:

    birim_bolen=1000 if birim=="mm" else (100 if birim=="cm" else 1)

    with tempfile.NamedTemporaryFile(delete=False,suffix=".dxf") as tmp:

        tmp.write(uploaded.read())
        path=tmp.name


    lines=read_dxf_lines(path,target_layers)

    h,v=split_orientation(lines)

    walls_h=detect_walls(h,duvar_kalinligi)
    walls_v=detect_walls(v,duvar_kalinligi)

    walls=walls_h+walls_v

    centers=build_centerlines(walls)

    centers=merge_segments(centers)


    total=sum([line_length(c) for c in centers])

    duvar_m=total/birim_bolen

    alan=duvar_m*kat


    fig,ax=plt.subplots(figsize=(12,10))

    for c in centers:
        draw_wall(ax,c,duvar_kalinligi)

    ax.set_aspect("equal")
    ax.axis("off")

    st.pyplot(fig)


    st.divider()

    col1,col2=st.columns(2)

    col1.metric("Toplam Duvar Uzunluğu (m)",round(duvar_m,2))
    col2.metric("Toplam Duvar Alanı (m²)",round(alan,2))
