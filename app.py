"""
Fi-le Duvar Metraj Pro v1.0
Sadece Duvar Metrajı - Barış Öker / Fi-le Yazılım A.Ş.
"""
import streamlit as st
import ezdxf
import math
import pandas as pd
import tempfile
import os

# Sayfa ayarı
st.set_page_config(page_title="Fi-le Duvar Metraj", layout="wide")

# CSS
st.markdown("""
    <style>
    .profile-card { 
        text-align: center; 
        padding: 1rem; 
        background-color: #262730; 
        border-radius: 10px; 
        margin-bottom: 1rem; 
    }
    .metric-box { 
        background-color: #f0f2f6; 
        padding: 1.5rem; 
        border-radius: 10px; 
        border-left: 5px solid #FF4B4B; 
        text-align: center;
    }
    .big-number {
        font-size: 2rem;
        font-weight: bold;
        color: #FF4B4B;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# GİRİŞ KONTROLÜ
# =============================================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏗️ Fi-le Duvar Metraj")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login"):
            st.markdown("<h3 style='text-align: center;'>Giriş Yap</h3>", unsafe_allow_html=True)
            username = st.text_input("Kullanıcı", value="admin")
            password = st.text_input("Şifre", type="password", value="1234")
            
            if st.form_submit_button("Giriş", use_container_width=True):
                if username == "admin" and password == "1234":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Hatalı giriş!")
    st.stop()

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("""
        <div class="profile-card">
            <h4 style="color: white; margin: 0;">Barış Öker</h4>
            <p style="color: #888; font-size: 0.9em;">Fi-le Yazılım A.Ş.</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Dosya yükleme
    uploaded = st.file_uploader("📁 DXF Yükle", type=["dxf"])
    
    # Katman seçimi (dosya yüklenince güncellenir)
    duvar_katmani = st.text_input("🧱 Duvar Katmanı", value="DUVAR", 
                                  help="Örnek: DUVAR, WALL, A-WALL")
    
    # Parametreler
    kat_yuksekligi = st.number_input("📏 Kat Yüksekliği (m)", 
                                     min_value=1.0, max_value=10.0, 
                                     value=2.85, step=0.01)
    
    birim = st.selectbox("📐 Çizim Birimi", 
                         options=["cm", "mm", "m"], 
                         index=0)
    
    st.divider()
    
    if st.button("🚪 Çıkış", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# =============================================================================
# ANA EKRAN
# =============================================================================
st.title("🏗️ Duvar Metraj Analizi")
st.caption("Sadece duvar uzunluğu ve alanı hesaplama")

if uploaded is None:
    st.info("👈 Sol menüden DXF dosyası yükleyin")
    
    # Nasıl çalışır
    st.markdown("""
    ### 💡 Nasıl Çalışır?
    
    1. **DXF Yükleyin** - AutoCAD dosyanızı seçin
    2. **Katman Yazın** - Duvar çizgilerinin olduğu katman adı (örn: "DUVAR")
    3. **Yükseklik Girin** - Metraj için kat yüksekliği
    4. **Birim Seçin** - Çizim hangi birimde yapıldı (cm/mm/m)
    
    **Hesaplama Mantığı:**
    - Tüm LINE ve LWPOLYLINE uzunlukları toplanır
    - Çift çizgili duvarlar için **2'ye bölünür** (aks uzunluğu)
    - **Aks uzunluğu × Kat yüksekliği = Duvar alanı (m²)**
    """)
    st.stop()

# =============================================================================
# DUVAR METRAJ HESAPLAMA
# =============================================================================
try:
    # Geçici dosya
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name
    
    # DXF oku
    doc = ezdxf.readfile(tmp_path)
    
    # Birim çarpanı
    carpani = {"mm": 1000.0, "cm": 100.0, "m": 1.0}.get(birim, 100.0)
    
    # Hedef katman (büyük harf, boşluk temizle)
    hedef = duvar_katmani.strip().upper()
    
    # Hesaplama
    toplam_uzunluk = 0.0  # Ham çizgi uzunluğu
    entity_sayisi = 0
    
    for entity in doc.modelspace():
        try:
            # Katman kontrolü
            layer = getattr(entity.dxf, 'layer', '').upper()
            if hedef not in layer:
                continue
            
            tip = entity.dxftype()
            
            # LINE hesaplama
            if tip == "LINE":
                s = entity.dxf.start
                e = entity.dxf.end
                uzunluk = math.sqrt((e[0]-s[0])**2 + (e[1]-s[1])**2)
                toplam_uzunluk += uzunluk
                entity_sayisi += 1
            
            # LWPOLYLINE hesaplama
            elif tip == "LWPOLYLINE":
                points = list(entity.get_points('xy'))
                for i in range(len(points)-1):
                    x1, y1 = points[i][0], points[i][1]
                    x2, y2 = points[i+1][0], points[i+1][1]
                    segment = math.sqrt((x2-x1)**2 + (y2-y1)**2)
                    toplam_uzunluk += segment
                entity_sayisi += 1
                
        except:
            continue
    
    # SONUÇLAR
    # 1. Ham uzunluğu metreye çevir
    ham_metre = toplam_uzunluk / carpani
    
    # 2. Aks uzunluğu (çift çizgi / 2)
    aks_metre = ham_metre / 2.0
    
    # 3. Duvar alanı
    duvar_alani = aks_metre * kat_yuksekligi
    
    # BAŞARILI MESAJI
    st.success(f"✅ {entity_sayisi} duvar çizgisi işlendi")
    
    # METRİKLER
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="metric-box">
                <p>Ham Uzunluk</p>
                <p class="big-number">{ham_metre:,.2f}</p>
                <small>metre</small>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="metric-box">
                <p>🔥 Aks Uzunluğu</p>
                <p class="big-number">{aks_metre:,.2f}</p>
                <small>metre (Ham/2)</small>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="metric-box">
                <p>Kat Yüksekliği</p>
                <p class="big-number">{kat_yuksekligi:,.2f}</p>
                <small>metre</small>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="metric-box">
                <p>🎯 Duvar Alanı</p>
                <p class="big-number">{duvar_alani:,.2f}</p>
                <small>m²</small>
            </div>
        """, unsafe_allow_html=True)
    
    # DETAY TABLOSU
    st.divider()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📋 Hesaplama Detayı")
        
        detay_data = {
            'Parametre': [
                'DXF Dosyası',
                'Duvar Katmanı',
                'Çizim Birimi',
                'İşlenen Çizgi Sayısı',
                'Ham Toplam Uzunluk',
                'Aks Uzunluğu (÷2)',
                'Kat Yüksekliği',
                'Toplam Duvar Alanı'
            ],
            'Değer': [
                uploaded.name,
                duvar_katmani,
                birim,
                f"{entity_sayisi} adet",
                f"{ham_metre:,.2f} m",
                f"{aks_metre:,.2f} m",
                f"{kat_yuksekligi} m",
                f"{duvar_alani:,.2f} m²"
            ]
        }
        
        df_detay = pd.DataFrame(detay_data)
        st.table(df_detay)
    
    with col2:
        st.subheader("💾 İndir")
        
        # CSV raporu
        csv_data = f"""Parametre,Değer
Proje,{uploaded.name}
Katman,{duvar_katmani}
Birim,{birim}
Entity Sayısı,{entity_sayisi}
Ham Uzunluk (m),{ham_metre:.2f}
Aks Uzunlugu (m),{aks_metre:.2f}
Kat Yuksekligi (m),{kat_yuksekligi}
Duvar Alani (m2),{duvar_alani:.2f}
"""
        
        st.download_button(
            "📥 CSV İndir",
            csv_data,
            f"duvar_metraj_{uploaded.name.replace('.dxf', '')}.csv",
            use_container_width=True
        )
        
        # TXT raporu
        txt_rapor = f"""DUVAR METRAJ RAPORU
====================
Proje: {uploaded.name}
Tarih: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

PARAMETRELER
-----------
Duvar Katmanı: {duvar_katmani}
Çizim Birimi: {birim}
Kat Yüksekliği: {kat_yuksekligi} m

SONUÇLAR
--------
İşlenen Çizgi: {entity_sayisi} adet
Ham Uzunluk: {ham_metre:.2f} m
Aks Uzunluğu: {aks_metre:.2f} m
Toplam Duvar Alanı: {duvar_alani:.2f} m²

Hesaplayan: Barış Öker
Firma: Fi-le Yazılım A.Ş.
"""
        
        st.download_button(
            "📄 TXT Rapor İndir",
            txt_rapor,
            f"rapor_{uploaded.name.replace('.dxf', '.txt')}",
            use_container_width=True
        )
        
        # Formül açıklaması
        st.info(f"""
        **Formül:**
        
        Aks Uzunluğu = {ham_metre:.2f} ÷ 2 = **{aks_metre:.2f} m**
        
        Duvar Alanı = {aks_metre:.2f} × {kat_yuksekligi} = **{duvar_alani:.2f} m²**
        """)
    
    # Temizlik
    del doc
    try:
        os.remove(tmp_path)
    except:
        pass

except Exception as e:
    st.error(f"❌ Hata: {str(e)}")
    st.info("💡 Kontrol edin: DXF bozuk olabilir veya katman adı yanlış")
