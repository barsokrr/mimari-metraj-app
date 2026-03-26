import streamlit as st
import streamlit.components.v1 as components
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os

# =============================================================================
# SAYFA KONFİGÜRASYONU
# =============================================================================
st.set_page_config(page_title="Fi-le Metraj Pro", layout="wide", page_icon="🏗️")

# CSS - Senin profil kartın ve modern dokunuşlar
st.markdown("""
    <style>
    .profile-card { text-align: center; padding: 1.5rem; background: rgba(255,255,255,0.05); border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 1rem; }
    .profile-img { border-radius: 50%; width: 100px; height: 100px; border: 3px solid #2563EB; margin-bottom: 0.5rem; object-fit: cover; }
    .stButton>button { border-radius: 8px; transition: all 0.3s; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2); }
    [data-testid="stSidebar"] { background-color: #0f172a; }
    </style>
""", unsafe_allow_html=True)

# Durum Yönetimi (Session State)
if 'page' not in st.session_state:
    st.session_state.page = 'landing' # İlk açılış: Tasarım Ekranı
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# =============================================================================
# 1. SAYFA: LANDING PAGE (TASARIM EKRANI)
# =============================================================================
if st.session_state.page == 'landing':
    # Tasarım HTML'i (Sana daha önce gönderdiğim stili buraya gömüyoruz)
    landing_html = """
    <div style="background: #020617; height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; font-family: 'Inter', sans-serif; color: white; margin: -100px -50px;">
        <div style="text-align: center; z-index: 10;">
            <h1 style="font-size: 4rem; margin-bottom: 0; background: linear-gradient(90deg, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800;">Fi-le Metraj Pro</h1>
            <p style="color: #94a3b8; font-size: 1.2rem; margin-top: 10px; letter-spacing: 2px;">MİMARİ ANALİZ VE HAKEDİŞ SİSTEMİ v3.0</p>
            <div style="margin-top: 40px;">
                <p style="color: #64748b; margin-bottom: 20px;">Hassas hesaplama, modern arayüz ve DXF entegrasyonu.</p>
            </div>
        </div>
        <div style="position: absolute; width: 100%; height: 100%; background-image: radial-gradient(#1e293b 1px, transparent 1px); background-size: 30px 30px; opacity: 0.3;"></div>
    </div>
    """
    components.html(landing_html, height=600)
    
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("Sisteme Giriş Yap 🚀", use_container_width=True):
            st.session_state.page = 'login'
            st.rerun()

# =============================================================================
# 2. SAYFA: GİRİŞ FORMU
# =============================================================================
elif st.session_state.page == 'login' and not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("""<div style='text-align: center;'><h2>🏗️ Kimlik Doğrulama</h2></div>""", unsafe_allow_html=True)
        with st.form("login_form"):
            u_name = st.text_input("Kullanıcı Adı", placeholder="admin")
            u_pass = st.text_input("Şifre", type="password", placeholder="****")
            submit = st.form_submit_button("Giriş Yap", use_container_width=True)
            
            if submit:
                if u_name == "admin" and u_pass == "1234":
                    st.session_state.logged_in = True
                    st.session_state.page = 'main'
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre!")
        
        if st.button("← Geri Dön", size="small"):
            st.session_state.page = 'landing'
            st.rerun()

# =============================================================================
# 3. SAYFA: ANA UYGULAMA (ANALİZ)
# =============================================================================
elif st.session_state.logged_in:
    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown(f"""
            <div class="profile-card">
                <img src="https://ui-avatars.com/api/?name=Baris+Oker&background=2563EB&color=fff" class="profile-img">
                <h4 style="color: white; margin: 0;">Barış Öker</h4>
                <p style="color: #3b82f6; margin: 0; font-size: 0.8em; font-weight: bold;">Fi-le Yazılım A.Ş.</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        uploaded = st.file_uploader("📁 DXF Dosyası Yükle", type=["dxf"])
        katman_secimi = st.text_input("🧱 Duvar Katmanı (Layer)", value="DUVAR")
        kat_yuksekligi = st.number_input("📏 Kat Yüksekliği (m)", value=2.85, step=0.01)
        birim = st.selectbox("📐 Çizim Birimi", ["cm", "mm", "m"], index=0)
        
        st.divider()
        if st.button("🚪 Güvenli Çıkış", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.page = 'landing'
            st.rerun()

    # --- ANA PANEL ---
    st.title("🏗️ Duvar Metraj Analizi")

    if uploaded is None:
        st.info("👈 Lütfen sol menüden bir DXF dosyası yükleyerek analizi başlatın.")
        # Tanıtım kartları koyabilirsin
        c1, c2 = st.columns(2)
        with c1: st.help("DXF dosyalarınızdaki LINE ve LWPOLYLINE objeleri otomatik olarak taranır.")
        with c2: st.help("Belirlediğiniz katman ismine göre filtreleme yapılır.")
        st.stop()

    # DXF İŞLEME VE HESAPLAMA (Senin Orijinal Mantığın)
    try:
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
                        x1, y1 = pts[i][0], pts[i][1]
                        x2, y2 = pts[i+1][0], pts[i+1][1]
                        total_length += math.sqrt((x2-x1)**2 + (y2-y1)**2)
                    entity_count += 1
            except: continue
        
        aks_uzunluk = (total_length / 2.0) / birim_carpani
        toplam_alan = aks_uzunluk * kat_yuksekligi
        
        # Sonuç Kartları
        st.subheader("📊 Analiz Özet Verileri")
        m1, m2, m3 = st.columns(3)
        m1.metric("İşlenen Duvar Objesi", f"{entity_count} Adet")
        m2.metric("Net Aks Uzunluğu", f"{aks_uzunluk:.2f} m")
        m3.metric("Toplam Duvar Alanı", f"{toplam_alan:.2f} m²")
        
        # Görselleştirme
        with st.expander("🔍 Çizim Önizlemesi", expanded=True):
            fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0e1117')
            ax.set_facecolor('#161b22')
            for entity in doc.modelspace():
                try:
                    color = "#30363d"; lw = 0.3
                    if hedef_katman in getattr(entity.dxf, 'layer', '').upper():
                        color = "#2563EB"; lw = 1.5
                    
                    if entity.dxftype() == "LINE":
                        s, e = entity.dxf.start, entity.dxf.end
                        ax.plot([s[0], e[0]], [s[1], e[1]], color=color, lw=lw)
                    elif entity.dxftype() == "LWPOLYLINE":
                        pts = list(entity.get_points('xy'))
                        xs, ys = zip(*pts)
                        ax.plot(xs, ys, color=color, lw=lw)
                except: continue
            ax.set_aspect('equal')
            ax.axis('off')
            st.pyplot(fig)
        
        # Rapor ve Tablo
        st.divider()
        df = pd.DataFrame({
            "Parametre": ["Seçili Katman", "Birim Sistemi", "Kat Yüksekliği", "Hesaplanan Aks", "Metraj Sonucu"],
            "Değer": [katman_secimi, birim, f"{kat_yuksekligi} m", f"{aks_uzunluk:.2f} m", f"{toplam_alan:.2f} m²"]
        })
        st.table(df)
        
        csv = f"Katman,Aks_Uzunluk_m,Kat_Yuksekligi_m,Toplam_Alan_m2\n{katman_secimi},{aks_uzunluk:.2f},{kat_yuksekligi},{toplam_alan:.2f}"
        st.download_button("📥 Hakediş Raporunu İndir (CSV)", csv, f"Fi-le_Metraj_{uploaded.name}.csv", use_container_width=True)
        
        os.remove(tmp_path)
    except Exception as e:
        st.error(f"⚠️ Dosya işlenirken bir hata oluştu: {str(e)}")
