import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math

def read_dxf_geometry(path, target_layers):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    polygons = []

    for e in msp:
        # Sadece kullanıcının seçtiği veya içinde "DUVAR/WALL" geçen katmanları al
        layer_name = e.dxf.layer.upper()
        is_target_layer = any(t.upper() in layer_name for t in target_layers)

        if is_target_layer:
            if e.dxftype() == "LWPOLYLINE":
                pts = [(p[0], p[1]) for p in e.get_points()]
                if len(pts) > 2:
                    if e.is_closed:
                        polygons.append(pts)
            
            elif e.dxftype() == "POLYLINE":
                pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
                if len(pts) > 2:
                    if e.is_closed:
                        polygons.append(pts)
                
    return polygons

def polygon_perimeter(poly):
    L = 0
    for i in range(len(poly) - 1):
        L += math.dist(poly[i], poly[i+1])
    return L

# --- ARAYÜZ ---
st.set_page_config(page_title="Pro Metraj", layout="wide")
st.title("🏗️ Mimari Duvar Metrajı (Katman Odaklı)")

with st.sidebar:
    st.header("⚙️ Ayarlar")
    uploaded = st.file_uploader("DXF Dosyası Seç", type=["dxf"])
    kat_yuksekligi = st.number_input("Kat Yüksekliği (m)", value=3.0)
    birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    
    # Buraya AutoCAD'deki duvar katman isimlerini yazmalısın
    katman_input = st.text_input("Duvar Katman İsimleri (Virgülle ayır)", "DUVAR, WALL, MIM_DUVAR")
    target_layers = [x.strip() for x in katman_input.split(",")]

if uploaded:
    birim_bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.read())
        path = tmp.name

    # Sadece hedeflenen katmanlardaki poligonları oku
    polygons = read_dxf_geometry(path, target_layers)

    if not polygons:
        st.error(f"Seçilen katmanlarda ({katman_input}) kapalı poligon bulunamadı! Lütfen katman isimlerini kontrol edin.")
    else:
        fig, ax = plt.subplots(figsize=(10, 8))
        total_raw_perimeter = 0

        for poly in polygons:
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            # Sadece duvarları boyuyoruz
            ax.fill(xs, ys, color="#2ecc71", alpha=0.8, edgecolor="black", linewidth=0.7)
            total_raw_perimeter += polygon_perimeter(poly)

        ax.set_aspect("equal")
        ax.axis("off")
        st.pyplot(fig)
        plt.close(fig)

        # Hesaplamalar (Çevre/2 mantığı ile aks uzunluğu)
        duvar_m = (total_raw_perimeter / 2) / birim_bolen
        alan = duvar_m * kat_yuksekligi

        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("📏 Toplam Duvar Uzunluğu", f"{round(duvar_m, 2)} m")
        c2.metric("🧱 Toplam Duvar Alanı", f"{round(alan, 2)} m²")
        
        st.success(f"Analiz tamamlandı. {len(polygons)} adet duvar objesi hesaplandı.")
