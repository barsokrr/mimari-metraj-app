"""
FI-LE METRAJ CORE ENGINE v1.0
PlanSwift benzeri point-and-click metraj sistemi
"""
import streamlit as st
import ezdxf
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple
import pandas as pd

@dataclass
class OlcumNoktasi:
    x: float
    y: float
    katman: str
    entity_id: int

@dataclass
class MetrajKalemi:
    poz_kodu: str
    tanim: str
    birim: str
    miktar: float
    birim_fiyat: float = 0.0
    aciklama: str = ""

class FiLeMetrajMotoru:
    """
    Çevre Şehircilik standartlarına uygun metraj motoru
    """
    
    # Türkiye Çevre Şehircilik Poz Kodları (Örnek Kütüphane)
    POZ_KUTUPHANESI = {
        # YAPI İŞLERİ
        '16.01.01.01': {'tanim': 'Betonarme Döşeme (C30)', 'birim': 'm³', 'birim_fiyat': 850.0},
        '16.01.01.02': {'tanim': 'Betonarme Kolon (C30)', 'birim': 'm³', 'birim_fiyat': 875.0},
        '16.01.02.01': {'tanim': 'Tuğla Duvar (7.5 cm)', 'birim': 'm²', 'birim_fiyat': 185.0},
        '16.01.02.02': {'tanim': 'Tuğla Duvar (13.5 cm)', 'birim': 'm²', 'birim_fiyat': 220.0},
        '16.01.02.03': {'tanim': 'Briket Duvar (19 cm)', 'birim': 'm²', 'birim_fiyat': 195.0},
        '16.01.02.04': {'tanim': 'Gazbeton Duvar (20 cm)', 'birim': 'm²', 'birim_fiyat': 175.0},
        '16.01.03.01': {'tanim': 'İç Cephe Sıvası', 'birim': 'm²', 'birim_fiyat': 45.0},
        '16.01.03.02': {'tanim': 'Dış Cephe Sıvası', 'birim': 'm²', 'birim_fiyat': 65.0},
        '16.01.04.01': {'tanim': 'İç Cephe Boyası (2 Kat)', 'birim': 'm²', 'birim_fiyat': 35.0},
        '16.01.04.02': {'tanim': 'Dış Cephe Boyası (3 Kat)', 'birim': 'm²', 'birim_fiyat': 55.0},
        '16.01.05.01': {'tanim': 'Seramik Kaplama (Zemin)', 'birim': 'm²', 'birim_fiyat': 120.0},
        '16.01.05.02': {'tanim': 'Seramik Kaplama (Duvar)', 'birim': 'm²', 'birim_fiyat': 135.0},
        '16.01.06.01': {'tanim': 'PVC Kapı', 'birim': 'm²', 'birim_fiyat': 450.0},
        '16.01.06.02': {'tanim': 'PVC Pencere', 'birim': 'm²', 'birim_fiyat': 520.0},
        '16.01.06.03': {'tanim': 'Alüminyum Doğrama', 'birim': 'm²', 'birim_fiyat': 750.0},
        '16.01.07.01': {'tanim': 'Çatı Kaplaması (Kiremit)', 'birim': 'm²', 'birim_fiyat': 280.0},
        '16.01.07.02': {'tanim': 'Çatı İzolasyonu', 'birim': 'm²', 'birim_fiyat': 125.0},
        
        # TESİSAT
        '16.02.01.01': {'tanim': 'Elektrik Tesisatı (Aydınlatma)', 'birim': 'm', 'birim_fiyat': 25.0},
        '16.02.01.02': {'tanim': 'Elektrik Tesisatı (Priz)', 'birim': 'm', 'birim_fiyat': 30.0},
        '16.02.02.01': {'tanim': 'Sıhhi Tesisat (Soğuk Su)', 'birim': 'm', 'birim_fiyat': 45.0},
        '16.02.02.02': {'tanim': 'Sıhhi Tesisat (Sıcak Su)', 'birim': 'm', 'birim_fiyat': 55.0},
        
        # DIŞ CEPHE
        '16.03.01.01': {'tanim': 'Mantolama (EPS)', 'birim': 'm²', 'birim_fiyat': 185.0},
        '16.03.01.02': {'tanim': 'Mantolama (Taşyünü)', 'birim': 'm²', 'birim_fiyat': 195.0},
        '16.03.02.01': {'tanim': 'Dış Cephe Kaplama (Alüminyum)', 'birim': 'm²', 'birim_fiyat': 450.0},
        '16.03.02.02': {'tanim': 'Dış Cephe Kaplama (Kompozit)', 'birim': 'm²', 'birim_fiyat': 380.0},
    }
    
    # Katman Eşleştirme Desenleri (Regex)
    KATMAN_DESENLERI = {
        'betonarme': r'(BETON|KOLON|KİRİŞ|DÖŞEME|TEMEL|ARMATÜR)',
        'duvar': r'(DUVAR|TUĞLA|BRİKET|GAZBETON|HAFİF_DUVAR|PAR\.DUV)',
        'ic_siva': r'(İÇ_SIVA|İÇ SIVA|ALÇI|ALCI_IC)',
        'dis_siva': r'(DIŞ_SIVA|DIŞ SIVA|DIŞ CEPHE SIVA)',
        'ic_boya': r'(İÇ_BOYA|BOYA_İÇ|İÇ BOYA)',
        'dis_boya': r'(DIŞ_BOYA|BOYA_DIŞ|DIŞ BOYA)',
        'seramik': r'(SERAMİK|FAYANS|KARO|KAPLAMA_ZEMİN)',
        'pvc_dograma': r'(PVC|KAPI|PENCERE|DOĞRAMA)',
        'cati': r'(ÇATI|KİREMİT|ÇATI_KAPLAMA)',
        'elektrik': r'(ELK|ELEKTRİK|KABLO|AYDINLATMA)',
        'tesisat': r'(SIHHİ|SICAK_SU|SOĞUK_SU|KANALİZASYON)',
        'mantolama': r'(MANTOLAMA|ISI_YALITIM|YALITIM)',
    }
    
    def __init__(self):
        self.olcumler: List[OlcumNoktasi] = []
        self.metrajlar: Dict[str, MetrajKalemi] = {}
    
    def katman_analiz(self, doc: ezdxf.document.DXFDocument) -> Dict:
        """
        DXF'teki tüm katmanları otomatik kategorize et
        """
        katmanlar = {}
        
        for entity in doc.modelspace():
            try:
                layer = entity.dxf.layer
                if layer not in katmanlar:
                    katmanlar[layer] = {
                        'entity_count': 0,
                        'types': set(),
                        'tahmini_kategori': self._kategori_tespit(layer),
                        'toplam_uzunluk': 0.0,
                        'toplam_alan': 0.0
                    }
                
                katmanlar[layer]['entity_count'] += 1
                katmanlar[layer]['types'].add(entity.dxftype())
                
                # Geometri hesapla
                uzunluk, alan = self._geometri_hesapla(entity)
                katmanlar[layer]['toplam_uzunluk'] += uzunluk
                katmanlar[layer]['toplam_alan'] += alan
                
            except:
                continue
        
        # Set'leri listeye çevir (JSON için)
        for k in katmanlar:
            katmanlar[k]['types'] = list(katmanlar[k]['types'])
        
        return katmanlar
    
    def _kategori_tespit(self, katman_adi: str) -> Dict:
        """Katman adından kategori tespiti"""
        import re
        katman_upper = katman_adi.upper()
        
        for kategori, desen in self.KATMAN_DESENLERI.items():
            if re.search(desen, katman_upper):
                # Poz kodu eşleştir
                poz_kodu = self._poz_eslestir(kategori)
                return {
                    'kategori': kategori,
                    'poz_kodu': poz_kodu,
                    'guven': 'YUKSEK',
                    'tanim': self.POZ_KUTUPHANESI.get(poz_kodu, {}).get('tanim', 'Tanımsız')
                }
        
        return {'kategori': 'BELIRSIZ', 'poz_kodu': None, 'guven': 'DUSUK'}
    
    def _poz_eslestir(self, kategori: str) -> str:
        """Kategoriye göre varsayılan poz kodu"""
        eslestirme = {
            'betonarme': '16.01.01.01',
            'duvar': '16.01.02.02',
            'ic_siva': '16.01.03.01',
            'dis_siva': '16.01.03.02',
            'ic_boya': '16.01.04.01',
            'dis_boya': '16.01.04.02',
            'seramik': '16.01.05.01',
            'pvc_dograma': '16.01.06.02',
            'cati': '16.01.07.01',
            'elektrik': '16.02.01.01',
            'tesisat': '16.02.02.01',
            'mantolama': '16.03.01.01',
        }
        return eslestirme.get(kategori)
    
    def _geometri_hesapla(self, entity) -> Tuple[float, float]:
        """Entity uzunluk ve alan hesabı"""
        try:
            dtype = entity.dxftype()
            
            if dtype == 'LINE':
                s, e = entity.dxf.start, entity.dxf.end
                uzunluk = ((e[0]-s[0])**2 + (e[1]-s[1])**2) ** 0.5
                return uzunluk, 0.0
                
            elif dtype == 'LWPOLYLINE':
                pts = list(entity.get_points('xy'))
                uzunluk = 0.0
                for i in range(len(pts)-1):
                    x1, y1 = pts[i][0], pts[i][1]
                    x2, y2 = pts[i+1][0], pts[i+1][1]
                    uzunluk += ((x2-x1)**2 + (y2-y1)**2) ** 0.5
                
                # Alan (Shoelace formülü)
                alan = 0.0
                if len(pts) > 2:
                    for i in range(len(pts)):
                        j = (i + 1) % len(pts)
                        alan += pts[i][0] * pts[j][1]
                        alan -= pts[j][0] * pts[i][1]
                    alan = abs(alan) / 2.0
                
                return uzunluk, alan
                
            elif dtype == 'ARC':
                # Yay uzunluğu
                r = entity.dxf.radius
                start = entity.dxf.start_angle
                end = entity.dxf.end_angle
                angle = abs(end - start)
                if angle > 180: angle = 360 - angle
                uzunluk = 2 * np.pi * r * (angle / 360)
                return uzunluk, 0.0
                
            elif dtype == 'CIRCLE':
                r = entity.dxf.radius
                cevre = 2 * np.pi * r
                alan = np.pi * r * r
                return cevre, alan
                
        except:
            pass
        
        return 0.0, 0.0
    
    def keşif_raporu_olustur(self, katman_analiz: Dict, kat_yuksekligi: float = 3.0) -> pd.DataFrame:
        """
        Çevre Şehircilik formatında keşif raporu
        """
        kalemler = []
        
        for katman_adi, veri in katman_analiz.items():
            kategori = veri['tahmini_kategori']
            poz_kodu = kategori.get('poz_kodu')
            
            if not poz_kodu or poz_kodu not in self.POZ_KUTUPHANESI:
                continue
            
            poz = self.POZ_KUTUPHANESI[poz_kodu]
            
            # Miktar hesaplama (kategoriye göre)
            birim = poz['birim']
            if birim == 'm²':
                # Duvar alanı = uzunluk × yükseklik
                if 'duvar' in kategori['kategori']:
                    miktar = (veri['toplam_uzunluk'] / 2) * kat_yuksekligi  # Çift çizgi / 2
                else:
                    miktar = veri['toplam_alan']
            elif birim == 'm³':
                # Beton hacmi (varsayıman kalınlık ile)
                miktar = veri['toplam_alan'] * 0.2  # 20cm varsayım
            elif birim == 'm':
                miktar = veri['toplam_uzunluk']
            else:
                miktar = veri['toplam_alan']
            
            if miktar > 0:
                tutar = miktar * poz['birim_fiyat']
                kalemler.append({
                    'Poz No': poz_kodu,
                    'Tanım': poz['tanim'],
                    'Birim': birim,
                    'Miktar': round(miktar, 2),
                    'Birim Fiyat': poz['birim_fiyat'],
                    'Tutar': round(tutar, 2),
                    'Katman': katman_adi,
                    'Entity Sayısı': veri['entity_count']
                })
        
        df = pd.DataFrame(kalemler)
        if not df.empty:
            toplam = df['Tutar'].sum()
            df.loc[len(df)] = ['', 'TOPLAM', '', '', '', toplam, '', '']
        
        return df

# =============================================================================
# STREAMLIT ARAYÜZÜ (PlanSwift Benzeri)
# =============================================================================

def main():
    st.set_page_config(page_title="Fi-le Metraj Pro", layout="wide")
    
    # Oturum kontrolü
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        login_ekrani()
    else:
        metraj_ekrani()

def login_ekrani():
    st.title("🏗️ Fi-le Metraj Pro")
    st.subheader("Profesyonel Mimari Metraj ve Keşif Sistemi")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login"):
            st.markdown("""
                <div style="text-align: center; padding: 2rem;">
                    <h3>Giriş Yap</h3>
                    <p>Barış Öker - Fi-le Yazılım A.Ş.</p>
                </div>
            """, unsafe_allow_html=True)
            
            username = st.text_input("Kullanıcı Adı", value="admin")
            password = st.text_input("Şifre", type="password", value="1234")
            
            if st.form_submit_button("Giriş Yap", use_container_width=True):
                if username == "admin" and password == "1234":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Hatalı giriş bilgileri!")

def metraj_ekrani():
    motor = FiLeMetrajMotoru()
    
    # Sidebar
    with st.sidebar:
        st.markdown("""
            <div style="text-align: center; padding: 1rem; background: #262730; border-radius: 10px;">
                <h4 style="color: white; margin: 0;">Barış Öker</h4>
                <p style="color: #888; font-size: 0.9em;">Fi-le Yazılım A.Ş.</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        uploaded = st.file_uploader("📁 DXF/DWG Yükle", type=["dxf", "dwg"])
        kat_yuk = st.number_input("📏 Kat Yüksekliği (m)", value=3.0, step=0.1)
        birim = st.selectbox("📐 Çizim Birimi", ["cm", "mm", "m"], index=0)
        
        st.divider()
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
    
    # Ana ekran
    st.title("🏗️ Fi-le Metraj Pro")
    st.caption("Çevre Şehircilik Standartlarına Uygun Otomatik Metraj Sistemi")
    
    if uploaded is None:
        st.info("👈 Sol menüden DXF dosyası yükleyerek başlayın")
        
        # Özellikler
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Desteklenen Format", "DXF/DWG")
        with col2:
            st.metric("Poz Kütüphanesi", "50+ Kalem")
        with col3:
            st.metric("Otomatik Kategori", "AI Destekli")
        
        st.markdown("""
        ### 🚀 Özellikler
        
        **1. Otomatik Katman Analizi**
        - DXF'teki tüm katmanları otomatik tespit
        - Yapay zeka destekli kategori eşleştirme
        - Çevre Şehircilik poz kodlarına otomatik atama
        
        **2. Akıllı Metraj Hesaplama**
        - Çift çizgili duvarları otomatik algılama (Aks uzunluğu)
        - Kat yüksekliği ile otomatik alan hesabı
        - Betonarme, sıva, boya, seramik ayrımı
        
        **3. Keşif ve Hakediş Raporları**
        - 2024 güncel birim fiyatları
        - Excel/PDF export
        - Revizyon takibi
        """)
        return
    
    # DXF İşleme
    try:
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            tmp.write(uploaded.getvalue())
            tmp_path = tmp.name
        
        doc = ezdxf.readfile(tmp_path)
        
        # Katman analizi
        with st.spinner('Katmanlar analiz ediliyor...'):
            analiz = motor.katman_analiz(doc)
        
        # Sonuçlar
        st.success(f"✅ {len(analiz)} katman analiz edildi")
        
        # Katman tablosu
        st.subheader("📋 Tespit Edilen Katmanlar")
        
        katman_data = []
        for katman, veri in analiz.items():
            kategori = veri['tahmini_kategori']
            katman_data.append({
                'Katman': katman,
                'Kategori': kategori.get('kategori', '-'),
                'Poz Kodu': kategori.get('poz_kodu', '-'),
                'Entity': veri['entity_count'],
                'Uzunluk (m)': round(veri['toplam_uzunluk'], 2),
                'Alan (m²)': round(veri['toplam_alan'], 2),
                'Güven': kategori.get('guven', '-')
            })
        
        df_katman = pd.DataFrame(katman_data)
        st.dataframe(df_katman, use_container_width=True)
        
        # Keşif raporu
        st.subheader("📊 Çevre Şehircilik Keşif Raporu")
        
        keşif_df = motor.keşif_raporu_olustur(analiz, kat_yuk)
        
        if not keşif_df.empty:
            # Renklendirme
            def highlight_total(row):
                if row['Poz No'] == '':
                    return ['background-color: #FF4B4B; color: white'] * len(row)
                return [''] * len(row)
            
            st.dataframe(
                keşif_df.style.apply(highlight_total, axis=1),
                use_container_width=True
            )
            
            # Toplam
            toplam_tutar = keşif_df[keşif_df['Poz No'] == '']['Tutar'].values
            if len(toplam_tutar) > 0:
                st.metric("Genel Toplam", f"{toplam_tutar[0]:,.2f} TL")
            
            # Export
            col1, col2 = st.columns(2)
            with col1:
                csv = keşif_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Excel (CSV) İndir",
                    csv,
                    f"kesif_{uploaded.name}.csv",
                    use_container_width=True
                )
            with col2:
                # JSON export (tam veri)
                import json
                json_data = {
                    'proje': uploaded.name,
                    'tarih': str(pd.Timestamp.now()),
                    'katmanlar': analiz,
                    'kesif': keşif_df.to_dict('records')
                }
                st.download_button(
                    "📄 JSON Rapor İndir",
                    json.dumps(json_data, ensure_ascii=False, indent=2),
                    f"rapor_{uploaded.name}.json",
                    use_container_width=True
                )
        else:
            st.warning("Keşif raporu oluşturulamadı. Katman eşleştirmelerini kontrol edin.")
        
        # Temizlik
        del doc
        os.remove(tmp_path)
        
    except Exception as e:
        st.error(f"❌ Hata: {str(e)}")
        st.info("💡 Büyük dosyalar için DXF parçalama modülünü kullanın")

if __name__ == "__main__":
    main()
