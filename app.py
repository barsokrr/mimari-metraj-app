import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os
import subprocess
from roboflow import Roboflow
from io import BytesIO

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="SaaS Metraj Pro", layout="wide")

st.markdown("""
<style>
.profile-area { text-align: center; padding: 10px; margin-bottom: 20px; }
.profile-img { border-radius: 50%; width: 80px; height: 80px; object-fit: cover;
border: 2px solid #FF4B4B; margin-bottom: 10px; }
.user-name { font-weight: bold; font-size: 1.1em; color: white; margin-bottom: 0px; }
.company-name { font-size: 0.9em; color: #888; margin-top: -5px; }
.stButton>button { width: 100%; border-radius: 5px; height: 3em;
background-color: #262730; color: white; }
.stDownloadButton>button { width: 100%; background-color: #00c853; color: white; }
</style>
""", unsafe_allow_html=True)

# --- ROBOFLOW AI ---
def run_roboflow_ai(image_bytes):
    try:
        rf = Roboflow(api_key=st.secrets["ROBO_API_KEY"])
        project = rf.workspace("bars-workspace-tcviv").project("mimari_duvar_tespiti-2")
        model = project.version(8).model
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(image_bytes.getvalue())
            path = tmp.name
        result = model.predict(path, confidence=0.4).json()
        os.remove(path)
        return result.get("predictions", [])
    except Exception as ex:
        st.error(f"AI doğrulama hatası: {ex}")
        return []

# --- DWG TO DXF DÖNÜŞÜM ---
def convert_dwg_to_dxf(input_path):
    """DWG dosyasını ODA Converter kullanarak geçici DXF'e çevirir"""
    output_path = input_path.replace(".dwg", ".dxf")
    try:
        subprocess.run([
            "ODAFileConverter", input_path, os.path.dirname(input_path),
            "ACAD2013", "DXF", "0", "1", "0"
        ], capture_output=True, check=True)
        if os.path.exists(output_path):
            return output_path
        else:
            st.error("DWG dosyası dönüştürülemedi! Lütfen manuel DXF yükleyin.")
            return None
    except Exception as ex:
        st.error(f"DWG dönüşüm hatası: {ex}")
        return None

# --- DXF OKUMA & HESAPLAMA ---
def clean_points(points, tol=1e-3):
    cleaned = [points[0]]
    for p in points[1:]:
        if abs(p[0]-cleaned[-1][0]) > tol or abs(p[1]-cleaned[-1][1]) > tol:
            cleaned.append(p)
    return cleaned

def get_dxf_geometry(path, target_layers=None):
    geometries = []
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        for e in msp.query("LINE LWPOLYLINE POLYLINE"):
            if target_layers:
                layer = e.dxf.layer.upper()
                if not any(t.upper() in layer for t in target_layers):
                    continue
            if e.dxftype() == "LINE":
                geometries.append([
                    (e.dxf.start[0], e.dxf.start[1]),
                    (e.dxf.end[0], e.dxf.end[1])
                ])
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = [(p[0], p[1]) for p in e]
                if len(pts) > 1:
                    geometries.append(clean_points(pts))
    except Exception as ex:
        st.error(f"DXF okunamadı: {ex}")
    return geometries

# --- UYGULAMA GİRİŞİ ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏗️ Metraj Analiz Giriş")
    with st.form("login_form"):
        u = st.text_input("Kullanıcı Adı")
        p = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            if u == "admin" and p == "1234":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")

# --- ANA UYGULAMA ---
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
        uploaded = st.file_uploader("Plan Dosyası (.dxf / .dwg)", type=["dxf", "dwg"])
        katmanlar = st.text_input("Katman Filtresi (örn: DUVAR, PERDE)", "DUVAR")
        kat_yuk = st.number_input("Kat Yüksekliği (m)", 2.85, step=0.01)
        birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
        double_line = st.checkbox("Duvarlar çift çizgiyle çizilmiş", True)
        st.markdown("<br>"*3, unsafe_allow_html=True)
        if st.button("Çıkış Yap"):
            st.session_state.logged_in = False
            st.rerun()

    st.title("🏗️ Metraj Analizi")

    if uploaded:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded.name.split('.')[-1]}") as tmp:
            tmp.write(uploaded.getbuffer())
            file_path = tmp.name

        # --- DWG ise DXF'e dönüştür ---
        if file_path.lower().endswith(".dwg"):
            st.info("DWG dosyası algılandı, DXF'e dönüştürülüyor...")
            dxf_path = convert_dwg_to_dxf(file_path)
            if not dxf_path:
                st.stop()
            current_path = dxf_path
        else:
            current_path = file_path

        try:
            targets = [x.strip() for x in katmanlar.split(",") if x.strip()]
            full_dxf = get_dxf_geometry(current_path)
            walls = get_dxf_geometry(current_path, targets)

            if not walls:
                st.warning("Seçilen katmanda eleman bulunamadı.")
            else:
                raw_len = sum(math.dist(g[i], g[i+1]) for g in walls for i in range(len(g)-1))
                bolen = 100 if birim == "cm" else 1000 if birim == "mm" else 1
                net_uzunluk = (raw_len / 2 if double_line else raw_len) / bolen
                toplam_alan = net_uzunluk * kat_yuk

                c1, c2 = st.columns(2)
                with c1:
                    plt.style.use("dark_background")
                    fig, ax = plt.subplots(figsize=(10,10))
                    for g in full_dxf:
                        xs, ys = zip(*g)
                        ax.plot(xs, ys, color="gray", lw=0.4)
                    ax.set_aspect("equal"); ax.axis("off")
                    st.subheader("Orijinal Plan")
                    st.pyplot(fig)

                with c2:
                    fig2, ax2 = plt.subplots(figsize=(10,10))
                    for g in walls:
                        xs, ys = zip(*g)
                        ax2.plot(xs, ys, color="#FF4B4B", lw=1.5)
                    ax2.set_aspect("equal"); ax2.axis("off")
                    st.subheader("Duvar Analizi (AI Doğrulama + CAD)")

                    if st.button("🤖 AI ile Doğrula"):
                        buffer = BytesIO()
                        fig2.savefig(buffer, format="png")
                        preds = run_roboflow_ai(buffer)
                        for p in preds:
                            try:
                                x, y, w, h = p["x"], p["y"], p["width"], p["height"]
                                rect = plt.Rectangle((x - w/2, y - h/2), w, h,
                                                     edgecolor="lime", lw=1.0, facecolor="none")
                                ax2.add_patch(rect)
                            except:
                                continue
                        st.info(f"AI {len(preds)} adet duvar bölgesi tespit etti.")
                        st.pyplot(fig2)
                    else:
                        st.pyplot(fig2)

                st.divider()
                m1, m2 = st.columns(2)
                m1.metric("Toplam Uzunluk", f"{net_uzunluk:.2f} m")
                m2.metric("Toplam Alan", f"{toplam_alan:.2f} m²")

                df = pd.DataFrame({
                    "İmalat": ["Duvar Metrajı"],
                    "Miktar": [round(toplam_alan, 2)],
                    "Birim": ["m²"],
                    "Kat Yüksekliği (m)": [kat_yuk],
                    "Çizgi Tipi": ["Çift" if double_line else "Tek"]
                })
                st.table(df)

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Metraj Cetveli (CSV)", csv, "rapor.csv")

        finally:
            try:
                os.remove(file_path)
                if file_path.lower().endswith(".dwg") and os.path.exists(current_path):
                    os.remove(current_path)
            except:
                pass
    else:
        st.info("Lütfen sol menüden bir DXF veya DWG dosyası yükleyin.")
