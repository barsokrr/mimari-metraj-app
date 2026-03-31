"""
Mimari Metraj Uygulaması - Profesyonel SaaS Sürümü
Geliştirici: Barış Öker - Fi-le Mimarlık & Yazılım
Özellikler: Duvar Metrajı + Kapı/Pencere Sayımı + 200 TL Biletleme
"""
import streamlit as st
import ezdxf
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
# 🎨 PROFESYONEL CSS
# =============================================================================
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    
    .centered-title {
        text-align: center;
        margin-top: 5vh !important;
        margin-bottom: 0px !important;
        font-weight: 700;
    }
    
    .pushed-up-form {
        max-width: 400px;
        margin: -20px auto 0 auto !important;
    }

    .footer-fixed-section {
        position: fixed;
        left: 0; bottom: 0; width: 100%;
        background-color: #0e1117;
        padding: 20px 5% 15px 5%;
        border-top: 1px solid #333;
        z-index: 999;
    }
    
    .copyright-text {
        text-align: center;
        color: #666;
        font-size: 11px;
        margin-top: 10px;
    }

    .profile-card { text-align: center; padding: 1rem; background-color: #1e2130; border-radius: 12px; border: 1px solid #333; }
    .profile-img { border-radius: 50%; width: 80px; height: 80px; border: 2px solid #FF4B4B; margin-bottom: 0.5rem; }
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

def analyze_dxf(file_path, mode, layer_name=None, height=2.85):
    """DXF Analiz Motoru"""
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()
    
    if mode == "🧱 Duvar Metrajı":
        entities = msp.query(f'*[layer=="{layer_name}"]')
        total_len = 0
        for e in entities:
            if e.dxftype() == 'LINE':
                total_len += math.sqrt((e.dxf.start.x - e.dxf.end.x)**2 + (e.dxf.start.y - e.dxf.end.y)**2)
            elif e.dxftype() == 'LWPOLYLINE':
                points = e.get_points()
                for i in range(len(points)-1):
                    total_len += math.sqrt((points[i][0] - points[i+1][0])**2 + (points[i][1] - points[i+1][1])**2)
        
        # Basit bir birim düzeltme (Örn: cm çizildiyse m'ye çevir - Projeye göre ayarlanabilir)
        area = total_len * height
        return pd.DataFrame({
            "Analiz": ["Toplam Uzunluk", "Toplam Duvar Alanı"],
            "Değer": [round(total_len, 2), round(area, 2)],
            "Birim": ["m", "m²"]
        })

    elif mode == "🚪 Kapı/Pencere Sayımı":
        blocks = msp.query('INSERT')
        counts = {}
        for b in blocks:
            name = b.dxf.name
            counts[name] = counts.get(name, 0) + 1
        
        if not counts:
            return pd.DataFrame(columns=["Blok Adı", "Adet"])
        
        return pd.DataFrame(list(counts.items()), columns=["Blok Adı", "Adet"]).sort_values("Adet", ascending=False)

def show_login_footer():
    st.markdown('<div class="footer-fixed-section">', unsafe_allow_html=True)
    col_leg1, col_leg2, col_leg3 = st.columns(3)
    with col_leg1:
        with st.expander("🔐 Gizlilik ve KVKK"):
            st.write("Verileriniz 6698 sayılı KVKK uyarınca korunmaktadır.")
    with col_leg2:
        with st.expander("📜 Satış Sözleşmesi"):
            st.write("Dijital biletler anında ifa edilen hizmetlerdir.")
    with col_leg3:
        with st.expander("🔄 İade Politikası"):
            st.write("Dijital ürünlerde cayma hakkı bulunmamaktadır.")
    st.markdown("""<div class="copyright-text">© 2026 Fi-le Mimarlık & Yazılım. Tüm hakları saklıdır. <br> Destek: barsokrr@gmail.com</div></div>""", unsafe_allow_html=True)

# =============================================================================
# 1. GİRİŞ EKRANI
# =============================================================================
if not st.session_state.logged_in:
    st.markdown('<h1 class="centered-title">🏗️ Duvar Metraj Sistemi Giriş</h1>', unsafe_allow_html=True)
    st.markdown('<div class="pushed-up-form">', unsafe_allow_html=True)
    email_input = st.text_input("E-posta Adresiniz", placeholder="ornek@mail.com")
    if st.button("Giriş Yap ve Kontrol Et", use_container_width=True):
        if "@" in email_input and "." in email_input:
            user = get_user_data(email_input)
            st.session_state.user_email = user["email"]
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Lütfen geçerli bir e-posta adresi girin.")
    st.markdown('</div>', unsafe_allow_html=True)
    show_login_footer()
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
            <p style="color:#FF4B4B; font-weight:bold;">🎫 {bilet_sayisi} Bilet</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    if has_credits:
        uploaded = st.file_uploader("📁 DXF Dosyası Yükle", type=["dxf"])
        # MOD SEÇİMİ
        analiz_modu = st.selectbox("🎯 Analiz Tipi", ["🧱 Duvar Metrajı", "🚪 Kapı/Pencere Sayımı"])
        
        if analiz_modu == "🧱 Duvar Metrajı":
            katman_secimi = st.text_input("🧱 Duvar Katmanı", value="DUVAR")
            kat_yuksekligi = st.number_input("📏 Kat Yüksekliği (m)", value=2.85, step=0.01)
        else:
            st.info("💡 Projedeki tüm bloklar isimlerine göre adet bazlı sayılacaktır.")
    else:
        st.error("📉 Analiz Hakkınız Kalmadı")
        st.link_button("💳 Hemen Bilet Al (200 TL)", "https://paytr.com/link-buraya", use_container_width=True)
        uploaded = None

    if st.button("🚪 Güvenli Çıkış", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.title("🏗️ Metraj Analiz Paneli")

if not has_credits:
    st.warning("### 🛑 Bakiyeniz Yetersiz")
    st.write("Analiz yapabilmek için bilet satın almanız gerekmektedir.")
else:
    if uploaded:
        st.success(f"✅ Dosya Hazır: {uploaded.name} | Mod: {analiz_modu}")
        if st.button("📥 Analizi Başlat (1 Bilet)", type="primary"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                tmp.write(uploaded.getvalue())
                tmp_path = tmp.name
            
            try:
                if use_credit(st.session_state.user_email):
                    if analiz_modu == "🧱 Duvar Metrajı":
                        res = analyze_dxf(tmp_path, analiz_modu, katman_secimi, kat_yuksekligi)
                    else:
                        res = analyze_dxf(tmp_path, analiz_modu)
                    
                    st.balloons()
                    st.subheader(f"📊 {analiz_modu} Sonuçları")
                    st.dataframe(res, use_container_width=True)
                os.remove(tmp_path)
            except Exception as e:
                st.error(f"Analiz sırasında hata oluştu: {e}")
    else:
        st.info(f"Hoş geldiniz **{st.session_state.user_email}**. Lütfen sol taraftan bir DXF dosyası yükleyip analiz tipini seçin.")

st.markdown("""
    <hr style="border:0.1px solid #333; margin-top: 50px;">
    <div style="text-align: center; color: #666; font-size: 11px;">
        © 2026 Fi-le Yazılım. Tüm hakları saklıdır. Bu uygulama bir mühendislik ön inceleme aracıdır.
    </div>
""", unsafe_allow_html=True)
