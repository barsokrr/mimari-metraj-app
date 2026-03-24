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

st.set_page_config(page_title="SaaS Metraj Pro", layout="wide")

st.markdown("""
<style>
.profile-area { text-align: center; padding: 10px; margin-bottom: 20px; }
.profile-img { border-radius: 50%; width: 80px; height: 80px; object-fit: cover; border: 2px solid #FF4B4B; margin-bottom: 10px; }
.user-name { font-weight: bold; font-size: 1.1em; color: white; margin-bottom: 0px; }
.company-name { font-size: 0.9em; color: #888; margin-top: -5px; }
.stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #262730; color: white; }
.stDownloadButton>button { width: 100%; background-color: #00c853; color: white; }
</style>
""", unsafe_allow_html=True)

# --- 2. YARDIMCI FONKSİYONLAR ---

def run_roboflow_ai(image_bytes):
    """Roboflow AI tahmini (Bars Workspace)"""
    try:
        rf = Roboflow(api_key=st.secrets["ROBO_API_KEY"])
        project = rf.workspace("bars-workspace-tcviv").project("mimari_duvar_tespiti")
        model = project.version(8).model
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(image_bytes.getvalue())
            path = tmp.name
        prediction = model.predict(path, confidence=0.4).json()
        os.remove(path)
        return prediction.get('predictions', [])
    except Exception as ex:
        st.error(f"AI doğrulama hatası: {ex}")
        return []

def get_dxf_geometry(path, target_layers=None):
    """Belirtilen katmanlardan çizgi verilerini döndürür"""
    geometries = []
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        for e in msp.query('LINE LWPOLYLINE POLYLINE'):
            if target_layers:
                layer_name = e.dxf.layer.upper()
                if not any(t.upper() in layer_name for t in target_layers):
                    continue

            if e.dxftype() == "LINE":
                geometries.append([
                    (e.dxf.start[0], e.dxf.start[1]),
                    (e.dxf.end[0], e.dxf.end[1])
                ])
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = [(p[0], p[1]) for p in e]
                if len(pts) > 1:
                    geometries.append(pts)
    except Exception as ex:
        st.error(f"DXF okunamadı: {ex}")
    return geometries


# --- 3. GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    st.title("🏗️ Metraj Analiz Giriş")
    with st.form("login_form"):
        user_input = st.text_input("Kullanıcı Adı")
        pass_input = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            if user_input == "admin" and pass_input == "1234":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")

# --- 4. ANA PROGRAM (Giriş Yapıldıysa) ---
else:
    with st.sidebar:
        st.markdown(f"""
            <div class="profile-area">
                <img src="[w3schools.com](https://www.w3schools.com/howto/img_avatar.png)" class="profile-img">
                <p class="user-name">admin</p>
                <p class="company-name">Demo Firma</p>
            </div>
        """, unsafe_allow_html=True)
        st.write("---")
        uploaded = st.file_uploader("DXF Dosyası Yükle", type=["dxf"])
        katmanlar = st.text_input("Katman Filtresi (örn: DUVAR, PERDE)", "DUVAR")
        kat_yuk = st.number_input("Kat Yüksekliği (m)", value=2.85, step=0.01)
        birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
        double_line = st.checkbox("Duvarlar çift çizgi olarak çizilmiş", value=True)
        st.markdown("<br>"*4, unsafe_allow_html=True)
        if st.button("Çıkış Yap"):
            st.session_state.logged_in = False
            st.rerun()

    st.title("🏗️ Metraj Analizi")

    if uploaded:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            tmp.write(uploaded.getbuffer())
            file_path = tmp.name

        try:
            target_list = [x.strip() for x in katmanlar.split(",") if x.strip()]
            full_project = get_dxf_geometry(file_path)
            wall_analysis = get_dxf_geometry(file_path, target_list)

            if wall_analysis:
                # --- Hesaplama ---
                raw_len = sum(math.dist(g[i], g[i+1]) for g in wall_analysis for i in range(len(g)-1))
                bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
                net_uzunluk = (raw_len / 2 if double_line else raw_len) / bolen
                toplam_alan = net_uzunluk * kat_yuk

                # --- Görselleştirme ---
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Orijinal Plan")
                    fig1, ax1 = plt.subplots(figsize=(10, 10), facecolor='#0e1117')
                    for g in full_project:
                        xs, ys = zip(*g)
                        ax1.plot(xs, ys, color="gray", lw=0.5, alpha=0.5)
                    ax1.set_aspect("equal"); ax1.axis("off")
                    st.pyplot(fig1)

                with col2:
                    st.subheader("Duvar Analizi (AI & CAD)")
                    fig2, ax2 = plt.subplots(figsize=(10, 10), facecolor='#0e1117')
                    for g in wall_analysis:
                        xs, ys = zip(*g)
                        ax2.plot(xs, ys, color="#FF4B4B", lw=1.5)
                    ax2.set_aspect("equal"); ax2.axis("off")

                    if st.button("🤖 AI ile Doğrula"):
                        img_buf = BytesIO()
                        fig2.savefig(img_buf, format='png')
                        preds = run_roboflow_ai(img_buf)
                        
                        # AI kutularını çiz
                        for p in preds:
                            x, y, w, h = p.get("x"), p.get("y"), p.get("width"), p.get("height")
                            rect = plt.Rectangle(
                                (x - w/2, y - h/2), w, h,
                                edgecolor="lime", facecolor="none", lw=1.2
                            )
                            ax2.add_patch(rect)
                        st.info(f"AI {len(preds)} adet duvar bölgesi tespit etti.")
                        st.pyplot(fig2)
                    else:
                        st.pyplot(fig2)

                # --- Çıktı & Rapor ---
                st.divider()
                m1, m2 = st.columns(2)
                m1.metric("Toplam Uzunluk", f"{net_uzunluk:.2f} m")
                m2.metric("Toplam Alan", f"{toplam_alan:.2f} m²")

                df = pd.DataFrame({
                    "İmalat": ["Duvar Metrajı"],
                    "Miktar": [round(toplam_alan, 2)],
                    "Birim": ["m²"],
                    "Kat Yüksekliği": [kat_yuk],
                    "Duvar Tipi": ["Çift Çizgi" if double_line else "Tek Çizgi"]
                })
                st.table(df)

                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Metraj Cetvelini İndir (CSV)", csv, "rapor.csv")

            else:
                st.warning("Seçilen katmanda çizim bulunamadı.")

        finally:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
    else:
        st.info("Lütfen sol menüden bir DXF dosyası yükleyin.")
