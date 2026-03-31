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
    st.error("Veritabanı anahtarları eksik! Lütfen secrets.toml dosyasını kontrol edin.")
    st.stop()

st.set_page_config(page_title="Duvar Metraj Pro", layout="wide", page_icon="🏗️")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""

# --- MODERN VE AÇIK RENK CSS ---
st.markdown("""
    <style>
    /* Genel Uygulama Zemini */
    .stApp { background-color: #FBFBFB; color: #2E2E2E; }
    
    /* Sol Panel (Sidebar) Modern Görünüm */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #EDEDED;
    }
    
    /* Profil Kartı (Resimsiz, Modern Minimalist) */
    .profile-card-modern {
        padding: 1.5rem;
        background: #F1F3F4;
        border-radius: 15px;
        text-align: left;
        border: 1px solid #E0E0E0;
        margin-bottom: 20px;
    }
    
    /* Başlıklar ve Metrikler */
    h1, h2, h3 { color: #1A1A1A; font-weight: 700; }
    .centered-title { text-align: center; margin-top: 5vh !important; }
    
    /* Input Alanları Özelleştirme */
    div[data-baseweb="input"], div[data-baseweb="select"] {
        border-radius: 10px !important;
        border: 1px solid #DCDCDC !important;
    }
    
    /* Butonlar (RAL 6038 Vurgusu) */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        border-color: #00AD43;
        color: #00AD43;
    }

    /* Footer */
    .footer-fixed-section { 
        position: fixed; left: 0; bottom: 0; width: 100%; 
        background-color: #FFFFFF; padding: 15px; 
        border-top: 1px solid #EDEDED; z-index: 999; 
    }
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

def show_login_footer():
    st.markdown('<div class="footer-fixed-section">', unsafe_allow_html=True)
    col_leg1, col_leg2, col_leg3 = st.columns(3)
    with col_leg1:
        with st.expander("🔐 Gizlilik ve KVKK"): st.write("Verileriniz KVKK uyarınca korunmaktadır.")
    with col_leg2:
        with st.expander("📜 Satış Sözleşmesi"): st.write("Dijital biletler anında ifa edilen hizmetlerdir.")
    with col_leg3:
        with st.expander("🔄 İade Politikası"): st.write("Cayma hakkı bulunmamaktadır.")
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# 1. GİRİŞ EKRANI
# =============================================================================
if not st.session_state.logged_in:
    st.markdown('<h1 class="centered-title">🏗️ Duvar Metraj Sistemi</h1>', unsafe_allow_html=True)
    st.markdown('<div style="max-width: 400px; margin: auto;">', unsafe_allow_html=True)
    email_input = st.text_input("E-posta Adresiniz", placeholder="ornek@mail.com")
    if st.button("Giriş Yap", use_container_width=True):
        if "@" in email_input and "." in email_input:
            user = get_user_data(email_input)
            st.session_state.user_email = user["email"]
            st.session_state.logged_in = True
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    show_login_footer()
    st.stop()

# =============================================================================
# 2. ANALİZ PANELİ
# =============================================================================
user_info = get_user_data(st.session_state.user_email)

with st.sidebar:
    # Profil resmi kaldırıldı, daha modern isim/bilet kartı eklendi
    st.markdown(f"""
        <div class="profile-card-modern">
            <small style="color: #666;">Kullanıcı</small>
            <div style="font-size: 1.1rem; font-weight: bold; margin-bottom: 5px;">{st.session_state.user_email.split('@')[0]}</div>
            <div style="color: #00AD43; font-weight: bold;">🎫 {user_info['credits']} Bilet Mevcut</div>
        </div>
    """, unsafe_allow_html=True)
    
    if user_info['credits'] > 0:
        uploaded = st.file_uploader("📁 DXF Dosyası Yükle", type=["dxf"])
        mode = st.selectbox("🎯 Analiz Tipi", ["🧱 Duvar Metrajı", "🚪 Kapı/Pencere Sayımı"])
        if mode == "🧱 Duvar Metrajı":
            katman_secimi = st.text_input("🧱 Duvar Katmanı", value="DUVAR")
            kat_yuksekligi = st.number_input("📏 Kat (m)", value=2.85, step=0.01)
            birim = st.selectbox("📐 Birim", ["cm", "mm", "m"])
    else:
        st.error("📉 Bakiye Yetersiz")
        st.link_button("💳 Bilet Satın Al", "https://paytr.com/...", use_container_width=True)
        uploaded = None

    if st.button("🚪 Güvenli Çıkış", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.title("📊 Metraj Analiz Paneli")

if uploaded:
    if st.button("📥 Analizi Başlat (1 Bilet)", type="primary"):
        if use_credit(st.session_state.user_email):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                    tmp.write(uploaded.getvalue())
                    tmp_path = tmp.name
                
                doc = ezdxf.readfile(tmp_path)
                msp = doc.modelspace()
                
                # --- GÖRSELLEŞTİRME (MODERN BEYAZ TEMA) ---
                fig, ax = plt.subplots(figsize=(10, 8), facecolor='#FBFBFB')
                ax.set_facecolor('#FBFBFB')
                
                total_length = 0.0
                entity_count = 0
                hedef_katman = katman_secimi.strip().upper() if mode == "🧱 Duvar Metrajı" else ""

                for entity in msp:
                    try:
                        layer = getattr(entity.dxf, 'layer', '').upper()
                        color = "#D1D1D1"; lw = 0.4
                        is_target = (mode == "🧱 Duvar Metrajı" and hedef_katman in layer)
                        
                        if is_target:
                            color = "#00AD43" # RAL 6038 Yeşil Duvarlar
                            lw = 1.6

                        if entity.dxftype() == "LINE":
                            s, e = entity.dxf.start, entity.dxf.end
                            ax.plot([s[0], e[0]], [s[1], e[1]], color=color, lw=lw)
                            if is_target: total_length += math.sqrt((e[0]-s[0])**2 + (e[1]-s[1])**2); entity_count += 1
                        elif entity.dxftype() == "LWPOLYLINE":
                            pts = list(entity.get_points('xy'))
                            xs, ys = zip(*pts); ax.plot(xs, ys, color=color, lw=lw)
                            if is_target:
                                for i in range(len(pts)-1):
                                    total_length += math.sqrt((pts[i+1][0]-pts[i][0])**2 + (pts[i+1][1]-pts[i][1])**2)
                                entity_count += 1
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
                        st.metric("🧱 Toplam Alan", f"{(aks * kat_yuksekligi):.2f} m²")
                    else:
                        st.write("### Blok Sayımı Sonuçları")
                        # Blok sayım mantığı...

                os.remove(tmp_path)
            except Exception as e: st.error(f"Hata: {e}")
else:
    st.info("Analize başlamak için lütfen sol panelden bir DXF dosyası seçin.")

st.markdown('<div style="text-align:center; color:#AAA; font-size:10px; margin-top:50px;">© 2026 Fi-le Mimarlık</div>', unsafe_allow_html=True)
