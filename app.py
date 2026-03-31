import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os
from supabase import create_client

# --- VERİTABANI VE OTURUM AYARLARI ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Veritabanı anahtarları eksik!")
    st.stop()

st.set_page_config(page_title="Duvar Metraj Pro", layout="wide", page_icon="🏗️")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""

# --- AYDINLIK TEMA VE RAL 6038 ÖZEL CSS ---
st.markdown("""
    <style>
    /* Ana Arka Plan Beyaz */
    .stApp { background-color: #FFFFFF; color: #31333F; }
    
    /* Sol Menü Tasarımı */
    [data-testid="stSidebar"] {
        background-color: #F8F9FB;
        border-right: 1px solid #E6E9EF;
    }

    /* RAL 6038 Yeşil Uygulaması - Girdi Alanları ve Butonlar */
    /* Dosya Yükleme Kutusu ve Text Inputlar */
    div[data-testid="stFileUploader"], 
    div[data-baseweb="input"], 
    div[data-baseweb="select"] {
        background-color: #00AD43 !important; /* RAL 6038 Yaklaşık Değeri */
        border-radius: 8px !important;
    }
    
    /* Input Metin Renklerini Beyaz Yapma (Yeşil üzerinde okunması için) */
    input, label, p, span {
        color: #31333F;
    }
    
    div[data-baseweb="input"] input {
        color: white !important;
    }

    /* Profil Kartı */
    .profile-card { 
        text-align: center; 
        padding: 1rem; 
        background-color: #FFFFFF; 
        border-radius: 12px; 
        border: 1px solid #E6E9EF;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .profile-img { border-radius: 50%; width: 80px; height: 80px; border: 2px solid #00AD43; margin-bottom: 0.5rem; }
    
    .centered-title { text-align: center; margin-top: 5vh !important; font-weight: 700; color: #1E1E1E; }
    </style>
""", unsafe_allow_html=True)

# --- YARDIMCI FONKSİYONLAR ---
def get_user_data(email):
    email = email.lower().strip()
    response = supabase.table("users").select("*").eq("email", email).execute()
    if len(response.data) == 0:
        new_user = {"email": email, "credits": 0}
        supabase.table("users").insert(new_user).execute()
        return new_user
    return response.data[0]

def use_credit(email):
    user = get_user_data(email)
    if user["credits"] > 0:
        new_credits = user["credits"] - 1
        supabase.table("users").update({"credits": new_credits}).eq("email", email).execute()
        return True
    return False

# =============================================================================
# 1. GİRİŞ EKRANI
# =============================================================================
if not st.session_state.logged_in:
    st.markdown('<h1 class="centered-title">🏗️ Duvar Metraj Sistemi Giriş</h1>', unsafe_allow_html=True)
    st.markdown('<div style="max-width:400px; margin:auto;">', unsafe_allow_html=True)
    email_input = st.text_input("E-posta Adresiniz", placeholder="ornek@mail.com")
    if st.button("Giriş Yap", use_container_width=True):
        if "@" in email_input:
            user = get_user_data(email_input)
            st.session_state.user_email = user["email"]; st.session_state.logged_in = True; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# =============================================================================
# 2. ANALİZ PANELİ
# =============================================================================
user_info = get_user_data(st.session_state.user_email)

with st.sidebar:
    st.markdown(f"""
        <div class="profile-card">
            <img src="https://api.dicebear.com/7.x/bottts/svg?seed={st.session_state.user_email}" class="profile-img">
            <h4 style="color: #31333F;">{st.session_state.user_email.split('@')[0]}</h4>
            <p style="color:#00AD43; font-weight:bold;">🎫 {user_info['credits']} Bilet</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    if user_info['credits'] > 0:
        uploaded = st.file_uploader("📁 DXF Dosyası Yükle", type=["dxf"])
        mode = st.selectbox("🎯 Analiz Tipi", ["🧱 Duvar Metrajı", "🚪 Kapı/Pencere Sayımı"])
        if mode == "🧱 Duvar Metrajı":
            katman_secimi = st.text_input("🧱 Duvar Katmanı", value="DUVAR")
            kat_yuksekligi = st.number_input("📏 Kat Yüksekliği (m)", value=2.85)
            birim = st.selectbox("📐 Çizim Birimi", ["cm", "mm", "m"], index=0)
    else:
        st.error("📉 Bakiye Yetersiz")
        st.link_button("💳 Bilet Al (200 TL)", "https://paytr.com/link-buraya", use_container_width=True)
        uploaded = None
    
    if st.button("🚪 Güvenli Çıkış", use_container_width=True):
        st.session_state.logged_in = False; st.rerun()

st.title("🏗️ Metraj Analiz Paneli")

if uploaded:
    if st.button("📥 Analizi Başlat (1 Bilet)", type="primary"):
        if use_credit(st.session_state.user_email):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                    tmp.write(uploaded.getvalue()); tmp_path = tmp.name
                
                doc = ezdxf.readfile(tmp_path)
                msp = doc.modelspace()
                
                # --- GÖRSELLEŞTİRME ---
                fig, ax = plt.subplots(figsize=(10, 8), facecolor='#FFFFFF')
                ax.set_facecolor('#FFFFFF')
                
                total_length = 0.0
                hedef_katman = katman_secimi.strip().upper() if mode == "🧱 Duvar Metrajı" else ""

                for entity in msp:
                    try:
                        layer = getattr(entity.dxf, 'layer', '').upper()
                        color = "#D1D1D1"; lw = 0.3
                        is_target = (mode == "🧱 Duvar Metrajı" and hedef_katman in layer)
                        
                        if is_target: color = "#00AD43"; lw = 1.5 # Duvarları da RAL 6038 yaptık

                        if entity.dxftype() == "LINE":
                            s, e = entity.dxf.start, entity.dxf.end
                            ax.plot([s[0], e[0]], [s[1], e[1]], color=color, lw=lw)
                            if is_target: total_length += math.sqrt((e[0]-s[0])**2 + (e[1]-s[1])**2)
                        elif entity.dxftype() == "LWPOLYLINE":
                            pts = list(entity.get_points('xy'))
                            xs, ys = zip(*pts)
                            ax.plot(xs, ys, color=color, lw=lw)
                            if is_target:
                                for i in range(len(pts)-1):
                                    total_length += math.sqrt((pts[i+1][0]-pts[i][0])**2 + (pts[i+1][1]-pts[i][1])**2)
                    except: continue

                ax.set_aspect('equal'); ax.axis('off')
                
                st.balloons()
                col_l, col_r = st.columns([2, 1])
                with col_l: st.pyplot(fig, use_container_width=True)
                with col_r:
                    if mode == "🧱 Duvar Metrajı":
                        birim_carpani = {"mm": 1000.0, "cm": 100.0, "m": 1.0}.get(birim, 100.0)
                        aks = (total_length / 2.0) / birim_carpani
                        st.metric("📏 Aks Uzunluğu", f"{aks:.2f} m")
                        st.metric("🧱 Toplam Alan", f"{aks * kat_yuksekligi:.2f} m²")
                    else:
                        blocks = msp.query('INSERT')
                        counts = {b.dxf.name: 0 for b in blocks}
                        for b in blocks: counts[b.dxf.name] += 1
                        st.table(pd.DataFrame(list(counts.items()), columns=["Blok", "Adet"]))

                os.remove(tmp_path)
            except Exception as e: st.error(f"Hata: {e}")
else:
    st.info("Hoş geldiniz. Lütfen sol taraftan bir DXF dosyası yükleyerek başlayın.")
