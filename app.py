Siz şunu dediniz:
"""
Mimari Duvar Metraj Uygulaması - Profesyonel SaaS Sürümü
Geliştirici: Barış Öker - Fi-le Yazılım 
Özellik: Küçük Fontlu Yasal Metinler ve Ekranın En Altına Sabitlenmiş Footer
"""
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
    st.error("Veritabanı anahtarları eksik! Lütfen Streamlit Secrets ayarlarını kontrol edin.")
    st.stop()

st.set_page_config(page_title="Duvar Metraj Pro", layout="wide", page_icon="🏗️")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""

# =============================================================================
# 🎨 GELİŞMİŞ CSS (SABİT FOOTER VE KÜÇÜK FONT)
# =============================================================================
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    
    /* Giriş Başlığını Ortala */
    .centered-title {
        text-align: center;
        margin-top: 5vh;
        margin-bottom: 2rem;
        font-weight: 700;
    }
    
    /* Expander Başlık Fontunu Küçült */
    .st-emotion-cache-p5mtransition {
        font-size: 13px !important;
        font-weight: 500 !important;
    }
    
    /* Footer Çizgisi ve Alanı */
    .footer-container {
        margin-top: 100px;
        padding-bottom: 100px; /* Sabit footer için boşluk */
    }
    
    /* EKranın En Altına Sabitlenmiş Telif Yazısı */
    .fixed-footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #0e1117;
        color: #666;
        text-align: center;
        padding: 20px 0;
        font-size: 11px;
        border-top: 1px solid #333;
        z-index: 999;
    }
    
    .profile-card { text-align: center; padding: 1rem; background-color: #1e2130; border-radius: 12px; border: 1px solid #333; margin-bottom: 1.5rem; }
    .profile-img { border-radius: 50%; width: 90px; height: 90px; border: 3px solid #FF4B4B; margin-bottom: 0.5rem; }
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
# 🏢 YASAL FOOTER FONKSİYONU
# =============================================================================
def show_footer():
    # Üstteki yasal kutular için konteyner
    st.markdown('<div class="footer-container"></div>', unsafe_allow_html=True)
    
    # 3 Sütunlu Küçük Başlıklı Alan
    col_leg1, col_leg2, col_leg3 = st.columns(3)
    
    with col_leg1:
        with st.expander("🔐 Gizlilik ve KVKK"):
            st.write("Verileriniz 6698 sayılı KVKK uyarınca korunmaktadır. DXF dosyaları analiz sonrası silinir.")
            
    with col_leg2:
        with st.expander("📜 Satış Sözleşmesi"):
            st.write("Dijital biletler anında ifa edilen hizmetlerdir. Her bilet 1 analiz hakkı sağlar.")
            
    with col_leg3:
        with st.expander("🔄 İade Politikası"):
            st.write("Dijital ürünlerde cayma hakkı bulunmamaktadır. Teknik sorunlarda destekle iletişime geçiniz.")
    
    # EKRANIN EN ALTINA ÇİVİLENMİŞ TELİF YAZISI
    st.markdown("""
        <div class="fixed-footer">
            © 2026 Fi-le Yazılım. Tüm hakları saklıdır. <br>
            Bu uygulama mühendislik ön inceleme aracıdır.
        </div>
    """, unsafe_allow_html=True)

# =============================================================================
# 1. GİRİŞ EKRANI (Login)
# =============================================================================
if not st.session_state.logged_in:
    st.markdown('<h1 class="centered-title">🏗️ İnşaat Metraj Sistemi Giriş</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        email_input = st.text_input("E-posta Adresiniz", placeholder="ornek@mail.com")
        if st.button("Giriş Yap", use_container_width=True):
            if "@" in email_input and "." in email_input:
                user = get_user_data(email_input)
                st.session_state.user_email = user["email"]
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Lütfen geçerli bir e-posta adresi girin.")
    
    show_footer()
    st.stop()

# =============================================================================
# 2. ANALİZ PANELI (Dashboard)
# =============================================================================
user_info = get_user_data(st.session_state.user_email)
bilet_sayisi = user_info['credits']
has_credits = bilet_sayisi > 0

with st.sidebar:
    st.markdown(f"""
        <div class="profile-card">
            <img src="https://api.dicebear.com/7.x/bottts/svg?seed={st.session_state.user_email}" class="profile-img">
            <h4>{st.session_state.user_email.split('@')[0]}</h4>
            <p>🎫 {bilet_sayisi} Bilet</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    if has_credits:
        uploaded = st.file_uploader("📁 DXF Dosyası Yükle", type=["dxf"])
        katman_secimi = st.text_input("🧱 Duvar Katmanı", value="DUVAR")
        kat_yuksekligi = st.number_input("📏 Kat Yüksekliği (m)", value=2.85, step=0.01)
        birim = st.selectbox("📐 Çizim Birimi", ["cm", "mm", "m"], index=0)
    else:
        st.error("📉 Biletiniz Bulunmuyor")
        st.link_button("💳 Hemen Bilet Al (99 TL)", "https://paytr.com/link-buraya", use_container_width=True)
        uploaded = None

    if st.button("🚪 Güvenli Çıkış", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.title("🏗️ Metraj Analiz Paneli")

if not has_credits:
    st.warning("### 🛑 Dosya Yükleme Kilitli")
    st.write("Analiz yapmak için lütfen bilet satın alınız.")
    st.stop()

if uploaded is None:
    st.info(f"Hoş geldiniz **{st.session_state.user_email}**. Lütfen sol taraftan analiz için DXF dosyasını yükleyin.")
else:
    try:
        with st.spinner("Dosya analiz ediliyor..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                tmp.write(uploaded.getvalue())
                tmp_path = tmp.name
            
            # Analiz Motoru...
            st.success(f"✅ Analiz Hazır: {uploaded.name}")
            if st.button("📥 Analizi Onayla ve 1 Bilet Kullan", type="primary"):
                if use_credit(st.session_state.user_email):
                    st.balloons()
            os.remove(tmp_path)
    except Exception as e:
        st.error(f"Hata: {e}")

show_footer()
