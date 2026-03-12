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
        layer_name = e.dxf.layer.upper()
        # Katman kontrolü
        is_target_layer = any(t.upper() in layer_name for t in target_layers)

        if is_target_layer:
            if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                if e.dxftype() == "LWPOLYLINE":
                    pts = [(p[0], p[1]) for p in e.get_points()]
                else:
                    pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]

                if len(pts) > 1:
                    # Eğer poligon kapalı değilse ama duvarın bir parçasıysa listeye al
                    # Görselleştirme için ilk ve son noktayı birleştiriyoruz (tahmini kapatma)
                    if pts[0] != pts[-1]:
                        pts.append(pts[0]) 
                    polygons.append(pts)
            
            elif e.dxftype() == "LINE":
                # Tekil çizgileri de küçük poligonlar gibi işleyelim (opsiyonel)
                x1, y1, _ = e.dxf.start
                x2, y2, _ = e.dxf.end
                polygons.append([(x1, y1), (x2, y2), (x1, y1)])

    return polygons

def polygon_perimeter(poly):
    L = 0
    for i in range(len(poly) - 1):
        L += math.dist(poly[i], poly[i+1])
    return L

# --- ARAYÜZ ---
st.set_page_config(page_title="Pro Metraj", layout="wide")
st.title("🏗️ Akıllı Duvar Metrajı (Gelişmiş Seçim)")

with st.sidebar:
    st.header("⚙️ Analiz Ayarları")
    uploaded = st.file_uploader("DXF Dosyası Seç", type=["dxf"])
    kat_yuksekligi = st.number_input("Kat Yüksekliği (m)", value=3.0)
    birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    katman_input = st.text_input("Duvar Katmanları", "DUVAR, WALL, MIM_DUVAR")
    target_layers = [x.strip() for x in katman_input.split(",")]

if uploaded:
    birim_bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.read())
        path = tmp.name

    polygons = read_dxf_geometry(path, target_layers)

    if not polygons:
        st.error("Seçilen katmanlarda uygun obje bulunamadı. Lütfen katman ismini kontrol edin.")
    else:
        fig, ax = plt.subplots(figsize=(12, 10))
        total_raw_perimeter = 0

        for poly in polygons:
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            # Duvarları boya ve sınırları çiz
            ax.fill(xs, ys, color="#e67e22", alpha=0.7, edgecolor="black", linewidth=0.8)
            total_raw_perimeter += polygon_perimeter(poly)

        ax.set_aspect("equal")
        ax.axis("off")
        st.pyplot(fig)
        plt.close(fig)

        # Çevre/2 mantığı ile aks uzunluğu hesabı
        duvar_m = (total_raw_perimeter / 2) / birim_bolen
        alan = duvar_m * kat_yuksekligi

        st.divider()
        col1, col2 = st.columns(2)
        col1.metric("📏 Toplam Duvar Uzunluğu", f"{round(duvar_m, 2)} m")
        col2.metric("🧱 Toplam Duvar Alanı", f"{round(alan, 2)} m²")
        
        st.success("Analiz başarıyla tamamlandı.")
