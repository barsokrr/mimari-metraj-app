"""
Mimari Duvar Metraj Uygulaması - Profesyonel SaaS Sürümü
Geliştirici: Barış Öker - Fi-le Yazılım 
Özellik: Önce Bilet Kontrolü, Sonra Dosya Yükleme
"""
import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os
from supabase import create_client

# =============================================================================
# VERİTABANI VE OTURUM AYARLARI
# =============================================================================
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Veritabanı anahtarları eksik! Lütfen Streamlit Secrets ayarlarını kontrol edin.")
    st.stop()

# Sayfa Konfigürasyonu
st.set_page_config(page_title="Duvar Metraj Pro", layout="wide")

# Oturum Değişkenleri
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""

# CSS Tasarımı
st.markdown("""
    <style>
    .profile-card { text-align: center; padding: 1rem; background-color: #262730; border-radius: 10px; margin-bottom: 1rem; }
    .profile-img { border-radius: 50%; width: 80px; height: 80px; border: 3px solid #FF4B4B; margin-bottom: 0.5rem; }
    .stButton>button { border-radius: 5px; font-weight: bold; }
    .status-box { padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================
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
    st.title("🏗️ Duvar Metraj Sistemi Giriş")
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
                st.error("Lütfen geçer lı bir e-posta adresi girin.")
    st.stop()

# =============================================================================
# 2. SIDEBAR VE KONTROL MERKEZİ
# =============================================================================
user_info = get_user_data(st.session_state.user_email)
bilet_sayisi = user_info['credits']
has_credits = bilet_sayisi > 0

with st.sidebar:
    st.markdown(f"""
        <div class="profile-card">
            <img src="https://api.dicebear.com/7.x/bottts/svg?seed={st.session_state.user_email}" class="profile-img">
            <h4 style="color: white; margin: 0;">{st.session_state.user_email.split('@')[0]}</h4>
            <p style="color: #FF4B4B; margin: 0; font-weight: bold; font-size: 1.2em;">🎫 {bilet_sayisi} Bilet</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # --- KRİTİK KONTROL: BİLET VARSA YÜKLEME ALANINI GÖSTER ---
    if has_credits:
        st.success("✅ Erişim İzni Verildi")
        uploaded = st.file_uploader("📁 DXF Dosyası Yükle", type=["dxf"])
        katman_secimi = st.text_input("🧱 Duvar Katmanı", value="DUVAR")
        kat_yuksekligi = st.number_input("📏 Kat Yüksekliği (m)", value=2.85, step=0.01)
        birim = st.selectbox("📐 Çizim Birimi", ["cm", "mm", "m"], index=0)
    else:
        st.error("📉 Biletiniz Bulunmuyor")
        st.info("Sistemi kullanabilmek için bilet satın almalısınız.")
        st.link_button("💳 Hemen Bilet Al (99 TL)", "https://paytr.com/link-buraya", use_container_width=True)
        uploaded = None

    st.divider()
    if st.button("🚪 Güvenli Çıkış", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()

# =============================================================================
# 3. ANA ANALİZ PANELI
# =============================================================================
st.title("🏗️ Metraj Analiz Paneli")

# Kullanıcının bileti yoksa ana ekranı da kilitle
if not has_credits:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.warning("### 🛑 Dosya Yükleme Kilitli")
        st.write("""
        Görünüşe göre mevcut bir kullanım hakkınız (bilet) bulunmuyor. 
        Analiz yapmak ve rapor indirmek için bilet almanız gerekmektedir.
        
        **Neden bilet almalıyım?**
        - Otomatik metraj hesabı.
        - Detaylı metraj raporu.
        - Görsel analiz çıktısı ve CSV indirme imkanı.
        """)
    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/261/261168.png", width=150)
    st.stop()

# Bilet varsa ama dosya yüklenmediyse
if uploaded is None:
    st.info(f"Hoş geldiniz **{st.session_state.user_email}**. Biletiniz tanımlı. Analize başlamak için lütfen sol taraftan bir DXF dosyası yükleyin.")
    st.stop()

# --- ANALİZ SÜRECİ ---
try:
    with st.spinner("Dosya okunuyor ve analiz ediliyor..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            tmp.write(uploaded.getvalue())
            tmp_path = tmp.name
        
        doc = ezdxf.readfile(tmp_path)
        birim_carpani = {"mm": 1000.0, "cm": 100.0, "m": 1.0}.get(birim, 100.0)
        hedef_katman = katman_secimi.strip().upper()
        
        total_length = 0.0
        entity_count = 0
        for entity in doc.modelspace():
            try:
                layer = getattr(entity.dxf, 'layer', '').upper()
                if hedef_katman not in layer: continue
                dtype = entity.dxftype()
                if dtype == "LINE":
                    s, e = entity.dxf.start, entity.dxf.end
                    total_length += math.sqrt((e[0]-s[0])**2 + (e[1]-s[1])**2)
                    entity_count += 1
                elif dtype == "LWPOLYLINE":
                    pts = list(entity.get_points('xy'))
                    for i in range(len(pts)-1):
                        total_length += math.sqrt((pts[i+1][0]-pts[i][0])**2 + (pts[i+1][1]-pts[i][1])**2)
                    entity_count += 1
            except: continue

        aks_uzunluk = (total_length / 2.0) / birim_carpani 
        toplam_alan = aks_uzunluk * kat_yuksekligi

    # SONUÇ GÖSTERİMİ
    st.success(f"✅ Analiz Hazır: {uploaded.name}")
    
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Tespit Edilen Obje", f"{entity_count} ad")
    with c2: st.metric("Aks Uzunluğu", f"{aks_uzunluk:.2f} m")
    with c3: st.metric("Toplam Alan", f"{toplam_alan:.2f} m²")

    # GRAFİK
    st.subheader("🖼️ Analiz Grafiği")
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0e1117')
    ax.set_facecolor('#0e1117')
    for entity in doc.modelspace():
        try:
            color = "#333"; lw = 0.5
            if hedef_katman in getattr(entity.dxf, 'layer', '').upper():
                color = "#FF4B4B"; lw = 2.0
            if entity.dxftype() == "LINE":
                s, e = entity.dxf.start, entity.dxf.end
                ax.plot([s[0], e[0]], [s[1], e[1]], color=color, lw=lw)
            elif entity.dxftype() == "LWPOLYLINE":
                pts = list(entity.get_points('xy'))
                xs, ys = zip(*pts)
                ax.plot(xs, ys, color=color, lw=lw)
        except: continue
    ax.set_aspect('equal'); ax.axis('off')
    st.pyplot(fig)

    # BİLET DÜŞME VE RAPOR İNDİRME
    st.divider()
    if st.button("📥 Analizi Tamamla ve Raporu İndir (1 Bilet)", use_container_width=True, type="primary"):
        if use_credit(st.session_state.user_email):
            st.balloons()
            csv = f"Parametre,Deger\nKatman,{katman_secimi}\nBirim,{birim}\nAks Uzunlugu,{aks_uzunluk:.2f} m\nToplam Alan,{toplam_alan:.2f} m2"
            st.download_button("📥 Dosyayı Kaydet (CSV)", csv, f"metraj_{uploaded.name}.csv", use_container_width=True)
            st.success("İşlem başarılı! 1 bilet düşüldü.")
        else:
            st.error("Beklenmedik bir hata oluştu veya biletiniz yetersiz.")

    os.remove(tmp_path)

except Exception as e:
    st.error(f"❌ Teknik Hata: {str(e)}")
