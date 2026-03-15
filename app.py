import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os

# --- 1. KURUMSAL YAPILANDIRMA ---
st.set_page_config(page_title="SaaS Metraj Pro | Final", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🛡️ Profesyonel Metraj Girişi")
    with st.form("login_form"):
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            if user == "admin" and pw == "123":
                st.session_state.logged_in = True
                st.rerun()
    st.stop()

# --- 2. GELİŞMİŞ GEOMETRİ MOTORU ---
def get_clean_metraj(file_path, layer_filter, scale_val, min_wall_len, wall_thickness_limit):
    """
    Dinamik duvar okuma ve aks tekilleştirme motoru.
    """
    try:
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        segments = []
        
        target = layer_filter.upper().strip()
        
        # Tüm geometriyi tara (Bloklar dahil)
        entities = msp.query('LINE LWPOLYLINE POLYLINE INSERT')
        
        for e in entities:
            # Katman Kontrolü (Dinamik)
            if target and target not in e.dxf.layer.upper():
                continue
            
            # Nesneyi çizgilere (segmentlere) parçala
            lines = []
            if e.dxftype() == "INSERT": # Bloklar
                for sub in e.virtual_entities():
                    if sub.dxftype() == "LINE": lines.append(sub)
            elif e.dxftype() == "LINE": lines.append(e)
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = list(e.get_points())
                for i in range(len(pts)-1):
                    # Segment bazlı sanal LINE oluştur
                    segments.append(((pts[i][0]/scale_val, pts[i][1]/scale_val), 
                                     (pts[i+1][0]/scale_val, pts[i+1][1]/scale_val)))
            
            for l in lines:
                p1 = (l.dxf.start.x/scale_val, l.dxf.start.y/scale_val)
                p2 = (l.dxf.end.x/scale_val, l.dxf.end.y/scale_val)
                segments.append((p1, p2))

        # --- AKILLI TEKİLLEŞTİRME ---
        # 1. Çok kısa çizgileri (kapı yanı, kalınlık çizgisi vb.) ele
        clean_segments = []
        for p1, p2 in segments:
            length = math.dist(p1, p2)
            if length >= min_wall_len:
                clean_segments.append({"path": (p1, p2), "len": length, "done": False})

        # 2. Paralel ve Yakın Hatları Birleştir (Çift çizgiyi teke düşür)
        final_metraj = 0
        final_lines = []
        
        # Uzunluğa göre sırala (Ana duvarları önce işle)
        clean_segments.sort(key=lambda x: x["len"], reverse=True)

        for i in range(len(clean_segments)):
            if clean_segments[i]["done"]: continue
            
            # Bu çizgiyi ana aks kabul et
            base = clean_segments[i]
            base["done"] = True
            final_metraj += base["len"]
            final_lines.append(base["path"])
            
            # Diğer çizgileri kontrol et, bu çizginin eşi (paraleli) olanları iptal et
            for j in range(i + 1, len(clean_segments)):
                if clean_segments[j]["done"]: continue
                
                # İki çizgi arası mesafe ve paralellik kontrolü
                dist = calculate_line_distance(base["path"], clean_segments[j]["path"])
                if dist <= wall_thickness_limit:
                    clean_segments[j]["done"] = True # Bu çizgi zaten metraja dahil edildi (eş olarak)

        return final_metraj, final_lines
    except Exception as e:
        st.error(f"Hata: {e}")
        return 0, []

def calculate_line_distance(l1, l2):
    # İki çizgi arası yaklaşık mesafe (Basitleştirilmiş orta nokta kontrolü)
    mid_p = ((l2[0][0] + l2[1][0])/2, (l2[0][1] + l2[1][1])/2)
    p1, p2 = l1
    # Noktanın doğruya uzaklığı formülü
    num = abs((p2[0]-p1[0])*(p1[1]-mid_p[1]) - (p1[0]-mid_p[0])*(p2[1]-p1[1]))
    den = math.dist(p1, p2)
    return num/den if den > 0 else 999

# --- 3. ARAYÜZ ---
st.sidebar.title("⚙️ Ölçüm Parametreleri")
with st.sidebar:
    uploaded = st.file_uploader("DXF Dosyası", type="dxf")
    unit_select = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    target_layer = st.text_input("Layer İsmi", "DUVAR")
    h_wall = st.number_input("Duvar Yüksekliği (m)", value=2.85)
    
    st.divider()
    st.write("🔧 **Hassasiyet Ayarları**")
    min_l = st.slider("Min. Duvar Boyu (m)", 0.0, 1.0, 0.30)
    max_t = st.slider("Maks. Duvar Kalınlığı (m)", 0.05, 0.60, 0.35)

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        t_path = tmp.name

    scale = 100 if unit_select == "cm" else (1000 if unit_select == "mm" else 1)
    
    # HESAPLAMA
    total_l, draw_lines = get_clean_metraj(t_path, target_layer, scale, min_l, max_t)
    
    if total_l > 0:
        st.success(f"Analiz Tamamlandı: {len(draw_lines)} adet tekil duvar tespit edildi.")
        c1, c2 = st.columns(2)
        c1.metric("📏 Toplam Uzunluk", f"{round(total_l, 2)} m")
        c2.metric("🧱 Toplam Alan", f"{round(total_l * h_wall, 2)} m²")

        # GÖRSEL ÖNİZLEME
        fig, ax = plt.subplots()
        for ln in draw_lines:
            ax.plot([ln[0][0], ln[1][0]], [ln[0][1], ln[1][1]], color="red", lw=2)
        ax.set_aspect("equal")
        st.pyplot(fig)
    else:
        st.warning("Seçilen layer veya ayarlarda veri bulunamadı.")
    
    os.remove(t_path)
