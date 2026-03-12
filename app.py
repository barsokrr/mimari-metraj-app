import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import numpy as np
import cv2
import pandas as pd
from inference_sdk import InferenceHTTPClient
import io

# --- 1. AYARLAR VE GİRİŞ SİSTEMİ ---
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Giriş paneli
authenticator.login(location='main')

# --- KİMLİK DOĞRULAMA KONTROLÜ ---
if st.session_state.get("authentication_status"):
  # --- YAN MENÜ (SIDEBAR) ---
    with st.sidebar:
        st.markdown("### 👤 Profil")
        st.write(f"**Kullanıcı:** {st.session_state.get('name')}")
        st.divider()
        
        # Seçim menüsü
        sayfa = st.radio("Menü", ["🏠 Ana Sayfa", "📂 Eski Projelerim"])
        
        st.divider()
        # logout sadece BURADA (sidebar içinde) kalsın
        authenticator.logout('Çıkış Yap', 'sidebar')

    # --- SAYFA İÇERİKLERİ ---
    if sayfa == "🏠 Ana Sayfa":
        # Başlık sadece buranın içinde olsun!
        st.title("🏗️ Akıllı Duvar Ölçüm Sistemi")
        # --- MALİYET AYARLARI (Sidebar) ---
        st.sidebar.header("💰 Maliyet Ayarları")
        cizim_birimi = st.sidebar.selectbox("Çizim Birimi", ["Metre", "Santimetre", "Milimetre"])
        kat_yuksekligi = st.sidebar.number_input("Kat Yüksekliği (m)", min_value=1.0, value=3.0)
        duvar_kalinligi = st.sidebar.number_input("Duvar Kalınlığı (m)", min_value=0.01, value=0.20)
        birim_fiyat = st.sidebar.number_input("Birim Fiyat (TL/m³)", min_value=0, value=2500)
        # 46. Satır: Dosya türlerine dxf ekledik
    uploaded_file = st.file_uploader("Plan Seçin (Resim veya .dxf)", type=["jpg", "png", "dxf"])
    
    if uploaded_file:
        # Dosya uzantısını kontrol et
        file_extension = uploaded_file.name.split('.')[-1].lower()

        if file_extension == 'dxf':
            st.subheader("📏 AutoCAD (DXF) Analizi")
             try:
        import ezdxf
        import tempfile
        import math
        import pandas as pd

        kat_yuksekligi = st.session_state.get("kat_yuksekligi",3.0)
        duvar_kalinligi = st.session_state.get("duvar_kalinligi",0.20)
        birim_fiyat = st.session_state.get("birim_fiyat",2500)

        with tempfile.NamedTemporaryFile(delete=False,suffix=".dxf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        doc = ezdxf.readfile(tmp_path)
        msp = doc.modelspace()

        duvar_uzunlugu = 0
        duvar_sayisi = 0

        segments=[]

        wall_keywords=["wall","duvar","a-wall","mim-wall"]

        for entity in msp:

            if entity.dxftype()=="LINE":

                start=entity.dxf.start
                end=entity.dxf.end

                x1,y1=start.x,start.y
                x2,y2=end.x,end.y

                uzunluk=math.sqrt((x2-x1)**2+(y2-y1)**2)

                layer=entity.dxf.layer.lower()

                segments.append((x1,y1,x2,y2))

                if any(k in layer for k in wall_keywords):
                    duvar_uzunlugu+=uzunluk
                    duvar_sayisi+=1


            elif entity.dxftype()=="LWPOLYLINE":

                layer=entity.dxf.layer.lower()

                pts=entity.get_points()

                for i in range(len(pts)-1):

                    x1,y1=pts[i][0],pts[i][1]
                    x2,y2=pts[i+1][0],pts[i+1][1]

                    uzunluk=math.sqrt((x2-x1)**2+(y2-y1)**2)

                    segments.append((x1,y1,x2,y2))

                    if any(k in layer for k in wall_keywords):
                        duvar_uzunlugu+=uzunluk
                        duvar_sayisi+=1


        duvar_alani=duvar_uzunlugu*kat_yuksekligi
        duvar_hacmi=duvar_alani*duvar_kalinligi
        maliyet=duvar_hacmi*birim_fiyat


        xs=[]
        ys=[]

        for s in segments:
            xs.extend([s[0],s[2]])
            ys.extend([s[1],s[3]])

        if len(xs)>0:

            genislik=max(xs)-min(xs)
            yukseklik=max(ys)-min(ys)

            plan_alani=genislik*yukseklik

        else:

            plan_alani=0


        ortalama_oda=20
        oda_sayisi=int(plan_alani/ortalama_oda)


        st.success(f"Toplam Duvar Uzunluğu: {round(duvar_uzunlugu,2)} m")

        col1,col2,col3=st.columns(3)

        col1.metric("Duvar Alanı m²",round(duvar_alani,2))
        col2.metric("Duvar Hacmi m³",round(duvar_hacmi,2))
        col3.metric("Tahmini Maliyet TL",round(maliyet,2))

        st.subheader("Plan Analizi")

        col4,col5=st.columns(2)

        col4.metric("Plan Alanı",round(plan_alani,2))
        col5.metric("Tahmini Oda Sayısı",oda_sayisi)


        data={

        "Kalem":[
        "Duvar Uzunluğu",
        "Duvar Alanı",
        "Duvar Hacmi",
        "Tahmini Maliyet"
        ],

        "Değer":[
        round(duvar_uzunlugu,2),
        round(duvar_alani,2),
        round(duvar_hacmi,2),
        round(maliyet,2)
        ]

        }

        df=pd.DataFrame(data)

        st.subheader("Metraj Tablosu")

        st.dataframe(df)

        csv=df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Metraj Raporunu İndir (CSV)",
            csv,
            "metraj_raporu.csv",
            "text/csv"
        )

        st.info(f"Tespit edilen duvar sayısı: {duvar_sayisi}")

    except Exception as e:
        st.error(f"DXF dosyası okunurken hata oluştu: {e}")
        else:
            # BURASI SENİN MEVCUT ROBOFLOW ANALİZ KODLARIN (Resimler için)
            st.subheader("🖼️ Yapay Zeka (Görsel) Analizi")
            st.success("Dosya yüklendi, Roboflow analizi başlatılıyor...")
            # Mevcut analiz fonksiyonlarını buraya çağır
    elif sayfa == "📂 Eski Projelerim":
        st.title("📂 Kayıtlı Projeler")
        st.info("Burası henüz yapım aşamasında.")  
    try:
        API_KEY = st.secrets["ROBOFLOW_API_KEY"]

        WORKSPACE = "bars-workspace-tcviv"
        WORKFLOW = "custom-workflow-2"
        PIXEL_TO_METER_RATIO = 0.02

        if uploaded_file is not None:

            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, 1)

            st.image(image, caption="Yüklenen Plan", use_container_width=True)

            if st.button("Metrajı Hesapla ve Analiz Et"):

                with st.spinner('Model analiz ediyor, lütfen bekleyin...'):

                    client = InferenceHTTPClient(
                        api_url="https://serverless.roboflow.com",
                        api_key=API_KEY
                    )

                    result = client.run_workflow(
                        workspace_name=WORKSPACE,
                        workflow_id=WORKFLOW,
                        images={"image": image}
                    )

                    predictions = result[0]['predictions']['predictions']

                    metraj_listesi = []

                    for i, wall in enumerate(predictions):

                        w = wall['width']
                        h = wall['height']

                        m_w = round(w * PIXEL_TO_METER_RATIO, 2)
                        m_h = round(h * PIXEL_TO_METER_RATIO, 2)

                        metraj_listesi.append({
                            "Duvar_ID": f"Duvar-{i+1}",
                            "Genişlik (m)": m_w,
                            "Yükseklik (m)": m_h,
                            "Alan (m2)": round(m_w * m_h, 2)
                        })

                    if metraj_listesi:

                        df = pd.DataFrame(metraj_listesi)

                        st.write("### Metraj Sonuçları")
                        st.dataframe(df)

                    else:
                        st.warning("Hiç duvar tespit edilemedi.")

    except Exception as e:
        st.error(f"Hata oluştu: {e}")


elif st.session_state.get("authentication_status") is False:

    st.error('Kullanıcı adı veya şifre hatalı')

else:

    st.info('Lütfen kullanıcı adı ve şifrenizi giriniz')












