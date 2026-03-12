import streamlit as st
import ezdxf
import math
import numpy as np
import matplotlib.pyplot as plt
import tempfile

# -----------------------------
# GEOMETRY
# -----------------------------

def length(l):
    x1,y1,x2,y2=l
    return math.dist((x1,y1),(x2,y2))

def angle(l):
    x1,y1,x2,y2=l
    return abs(math.degrees(math.atan2(y2-y1,x2-x1)))

def vector(l):
    x1,y1,x2,y2=l
    return np.array([x2-x1,y2-y1])

def parallel(l1,l2):

    v1=vector(l1)
    v2=vector(l2)

    if np.linalg.norm(v1)==0 or np.linalg.norm(v2)==0:
        return False

    cos=np.dot(v1,v2)/(np.linalg.norm(v1)*np.linalg.norm(v2))

    return abs(cos)>0.99


def distance(l1,l2):

    x1,y1,x2,y2=l1
    x3,y3,x4,y4=l2

    num=abs((x3-x1)*(y2-y1)-(y3-y1)*(x2-x1))
    den=math.dist((x1,y1),(x2,y2))

    if den==0:
        return 999

    return num/den


# -----------------------------
# DXF OKUMA
# -----------------------------

def read_dxf(path):

    doc=ezdxf.readfile(path)
    msp=doc.modelspace()

    lines=[]

    for e in msp:

        if e.dxftype()=="LINE":

            x1,y1,_=e.dxf.start
            x2,y2,_=e.dxf.end

            l=(x1,y1,x2,y2)

            if length(l)>200:
                lines.append(l)

        if e.dxftype()=="LWPOLYLINE":

            pts=list(e.get_points())

            for i in range(len(pts)-1):

                x1,y1=pts[i][0],pts[i][1]
                x2,y2=pts[i+1][0],pts[i+1][1]

                l=(x1,y1,x2,y2)

                if length(l)>200:
                    lines.append(l)

    return lines


# -----------------------------
# YATAY / DİKEY AYIR
# -----------------------------

def split_orientation(lines):

    h=[]
    v=[]

    for l in lines:

        a=angle(l)

        if a<10:
            h.append(l)

        elif abs(a-90)<10:
            v.append(l)

    return h,v


# -----------------------------
# DUVAR ÇİFTİ BUL
# -----------------------------

def detect_wall_pairs(lines,wall_thickness):

    walls=[]

    tol=wall_thickness*0.4

    for i in range(len(lines)):

        for j in range(i+1,len(lines)):

            l1=lines[i]
            l2=lines[j]

            if not parallel(l1,l2):
                continue

            d=distance(l1,l2)

            if abs(d-wall_thickness)<tol:

                if min(length(l1),length(l2))>800:

                    walls.append((l1,l2))

    return walls


# -----------------------------
# DUVAR EKSENİ
# -----------------------------

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


# -----------------------------
# DUVAR BİRLEŞTİR
# -----------------------------

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

                if distance(lines[i],l2)<10:

                    x3,y3,x4,y4=l2

                    if abs(x2-x3)<gap or abs(y2-y3)<gap:

                        x1=min(x1,x3)
                        y1=min(y1,y3)
                        x2=max(x2,x4)
                        y2=max(y2,y4)

                        used[j]=True

        merged.append((x1,y1,x2,y2))

    return merged


# -----------------------------
# RECTANGLE DUVAR
# -----------------------------

def draw_wall_rect(ax,line,thickness):

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

    ax.fill(xs,ys,color="yellow",alpha=0.8)


# -----------------------------
# STREAMLIT
# -----------------------------

st.title("AI Mimari Duvar Metrajı")

uploaded=st.file_uploader("DXF Plan Yükle",type=["dxf"])

kat_yuksekligi=st.number_input("Kat Yüksekliği (m)",value=3.0)

duvar_kalinligi=st.number_input("Duvar Kalınlığı (mm)",value=200.0)


if uploaded:

    with tempfile.NamedTemporaryFile(delete=False,suffix=".dxf") as tmp:

        tmp.write(uploaded.read())
        path=tmp.name


    lines=read_dxf(path)

    h,v=split_orientation(lines)

    walls1=detect_wall_pairs(h,duvar_kalinligi)
    walls2=detect_wall_pairs(v,duvar_kalinligi)

    walls=walls1+walls2

    centers=build_centerlines(walls)

    centers=merge_segments(centers)


    total=sum([length(c) for c in centers])

    total_m=total/1000

    area=total_m*kat_yuksekligi


    # -----------------------------
    # ÇİZİM
    # -----------------------------

    fig,ax=plt.subplots(figsize=(10,10))

    for c in centers:
        draw_wall_rect(ax,c,duvar_kalinligi)

    ax.set_aspect("equal")
    ax.axis("off")

    st.pyplot(fig)


    col1,col2=st.columns(2)

    col1.metric("Duvar Uzunluğu (m)",round(total_m,2))
    col2.metric("Duvar Alanı (m²)",round(area,2))
