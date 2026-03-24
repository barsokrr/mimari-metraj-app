import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os
from roboflow import Roboflow
from io import BytesIO

# --- 1. OTURUM KONTROLÜ VE SAYFA AYARI ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

st.set_page_config(page_title="SaaS Metraj Pro v2", layout="wide")

# CSS: Profil alanı ve tablo özelleştirmeleri
st.markdown("""
    <style>
    .profile-area { text-align: center; padding: 10px; margin-bottom: 20px; }
    .profile-img { border-radius: 50%; width: 80px; height: 80px; object-fit: cover; border: 2px solid #FF4B4B; margin-bottom: 10px; }
    .user-name { font-weight: bold; font-size: 1.1em; color: white; margin-bottom: 0px; }
    .company-name { font-size: 0.9em; color: #888; margin-top: -5px; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GELİŞMİŞ GEOMETRİ MOTORU ---
def get_comprehensive_metraj(path, wall_layer="DUVAR", floor_layer="ZEMIN", door_layer="KAPI", window_layer="PENCERE"):
    results = {"wall_len": 0, "floor_area": 0, "door_count": 0, "window_count": 0, "geometries": []}
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        
        # 1. Duvar Uzunluğu (Lineer)
        walls = msp.query(f'LINE LWPOLYLINE[layer=="{wall_layer}"]')
        for e in walls:
            if e.dxftype() == "LINE":
                results["wall_len"] += math.dist(e.dxf.start, e.dxf.end)
            else:
                pts = list(e.get_points())
                results["wall_len"] += sum(math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1))

        # 2. Zemin Alanı (Poligon - Shoelace Formula)
        floors = msp.query(f'LWPOLYLINE[layer=="{floor_layer}"]')
        for e in floors:
            pts = [(p[0], p[1]) for p in e.get_points()]
            if len(pts) > 2:
                area = 0.5 * abs(sum(pts[i][0]*pts[i+1][1] - pts[i+1][0]*pts[i][1] for i in range(len(pts)-1)) 
                                 + (pts[-1][0]*pts[0][1] - pts[0][0]*pts[-1][1]))
                results["floor_area"] += area

        # 3. Kapı ve Pencere Sayımı (Block Reference veya Layer)
        results["door_count"] = len(msp.query(f'*[layer=="{door_layer}"]'))
        results["window_count"] = len(msp.query(f'*[layer=="{window_layer}"]'))
        
        # Görselleştirme için tüm datayı al
        for e in msp.query('LINE LWPOLYLINE'):
            if e.dxftype() == "LINE": results["geometries"].append([(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])])
            else: results["geometries"].append([(p[0], p[1]) for p in e.get_points()])
            
        return results
    except Exception as e:
        st.error(f"DXF Okuma Hatası: {e}")
        return None

# --- 3. GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    st.title("🏗️ SaaS Metraj Pro Giriş")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            user_input = st.text_input("Kullanıcı Adı")
            pass_input = st.text_input("Şifre", type="password")
            if st.form_submit_button("Sisteme Giriş"):
                if user_input == "admin" and pass_input == "1234":
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("Hatalı Kimlik Bilgileri!")

# --- 4. ANA PROGRAM ---
else:
    with st.sidebar:
        st.markdown(f"""<div class="profile-area"><img src="https://www.w3schools.com/howto/img_avatar.png" class="profile-img">
                    <p class="user-name">Barış KORKMAZ</p><p class="company-name">Fi-le Yazılım A.Ş.</p></div>""", unsafe_allow_html=True)
        st.write("---")
        uploaded = st.file_uploader("DXF Projesi Yükle", type=["dxf"])
        
        st.subheader("Katman Ayarları")
        l_wall = st.text_input("Duvar Katmanı", "DUVAR")
        l_floor = st.text_input("Zemin Katmanı", "ZEMIN")
        l_door = st.text_input("Kapı Katmanı", "KAPI")
        l_win = st.text_input("Pencere Katmanı", "PENCERE")
        
        kat_yuk = st.number_input("Kat Yüksekliği (m)", 2.85)
        birim_bolen = {"cm": 100, "mm": 1000, "m": 1}[st.selectbox("Çizim Birimi", ["cm", "mm", "m"])]
        
        if st.button("Güvenli Çıkış"):
            st.session_state.logged_in = False
            st.rerun()

    st.title("📊 Gelişmiş Metraj Analizi")

    if uploaded:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            tmp.write(uploaded.getbuffer())
            data = get_comprehensive_metraj(tmp.name, l_wall, l_floor, l_door, l_win)
        
        if data:
            # Birim Dönüşümleri
            w_len = (data["wall_len"] / 2) / birim_bolen # Aks ortalaması
            w_area = w_len * kat_yuk
            f_area = data["floor_area"] / (birim_bolen**2)

            # Metrik Gösterimi
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Toplam Duvar (m²)", f"{w_area:.2f}")
            m2.metric("Toplam Zemin (m²)", f"{f_area:.2f}")
            m3.metric("Kapı Adedi", data["door_count"])
            m4.metric("Pencere Adedi", data["window_count"])

            # Grafik Alanı
            fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0e1117')
            for g in data["geometries"]:
                xs, ys = zip(*g)
                ax.plot(xs, ys, color="gray", lw=0.5, alpha=0.3)
            ax.set_aspect("equal"); ax.axis("off")
            st.pyplot(fig)

            # Hakediş Tablosu
            st.subheader("📋 Metraj Cetveli")
            df = pd.DataFrame([
                {"İmalat Kalemi": "Tuğla Duvar Örülmesi", "Miktar": round(w_area, 2), "Birim": "m²"},
                {"İmalat Kalemi": "Zemin Kaplama (Şap/Parke)", "Miktar": round(f_area, 2), "Birim": "m²"},
                {"İmalat Kalemi": "İç/Dış Kapı Montajı", "Miktar": data["door_count"], "Birim": "Adet"},
                {"İmalat Kalemi": "Doğrama ve Cam İşleri", "Miktar": data["window_count"], "Birim": "Adet"}
            ])
            st.table(df)
            st.download_button("📥 Excel Formatında İndir", df.to_csv(index=False).encode('utf-8'), "metraj_raporu.csv")
            
        os.remove(tmp.name)
    else:
        st.info("Analiz için sol menüden bir DXF dosyası yükleyin.")
