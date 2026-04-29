# Mağaza sürümü (iOS / Android)

Bu klasör, **yayında olan Streamlit uygulamanızı** native bir WebView içinde açan [Capacitor](https://capacitorjs.com/) kabuğudur. İş mantığı Streamlit sunucusunda kalır; mağazada indirilen ürün bu kabuktur.

## Önkoşullar

1. [Node.js](https://nodejs.org/) LTS (npm ile birlikte gelir).
2. **Android:** [Android Studio](https://developer.android.com/studio) (SDK, emülatör veya cihaz).
3. **iOS (yalnızca macOS):** Xcode, Apple Developer Program üyeliği (App Store için).

## Kurulum

```bash
cd mobile
npm install
```

## Kritik: Streamlit adresi

`capacitor.config.json` dosyasında `server.url` değerini **HTTPS** ile yayınladığınız Streamlit adresiyle değiştirin (örnek: `https://xxxx.streamlit.app` veya kendi alan adınız).

```json
"server": {
  "url": "https://SIZIN-YAYIN-ADRESINIZ",
  "cleartext": false
}
```

Yerel test için geçici olarak `http://10.0.2.2:8501` (Android emülatör → bilgisayarınızdaki Streamlit) kullanılabilir; o zaman `"cleartext": true` gerekir ve Android’de ağ güvenliği ayarına dikkat edin.

## Native projeleri oluşturma (bir kez)

```bash
cd mobile
npx cap add android
npx cap add ios
npx cap sync
```

Sonrasında:

- Android: `npm run open:android` → Android Studio’da imzalama ve **Google Play** yükleme.
- iOS: `npm run open:ios` → Xcode’da takım, sürüm, ikonlar ve **App Store Connect** yükleme.

## Uygulama kimliği ve görünen ad

- **Bundle ID / applicationId:** `capacitor.config.json` içindeki `appId` (şu an `com.filemimarlik.metrajpro`). Kendi ters alan adınızla değiştirin.
- **Görünen ad:** `appName` alanı.

`npx cap sync` sonrası native tarafta da yansır; değişiklikten sonra tekrar `sync` çalıştırın.

## İkon ve splash (mağaza zorunluluğu)

Varsayılan Capacitor görseli mağaza için yetersizdir. Öneri:

```bash
npm install @capacitor/assets --save-dev
```

Kök dizinde `icon.png` (1024×1024) ve `splash.png` hazırlayıp [Capacitor Assets](https://capacitorjs.com/docs/guides/splash-screens-and-icons) dokümantasyonundaki komutla tüm çözünürlükleri üretin; ardından `npx cap sync`.

## Mağaza incelemesi için notlar

- **Gizlilik politikası URL’si:** KVKK / veri toplama metninizi barındıran bir sayfa bağlayın (Streamlit alt bilgisi veya şirket siteniz).
- **Apple:** “Yalnızca web sitesi” kabuğu bazen reddedilebilir. Uygulamanın metraj aracı olarak net faydası, ekran görüntüleri ve gerekirse küçük native iyileştirmeler (ör. paylaşım, bildirim) incelemeyi kolaylaştırır.
- **Ödeme:** Harici ödeme (PayTR linki) ile ilgili mağaza kurallarını güncel metinlerden kontrol edin; gerektiğinde uygulama içi açıklama metni ekleyin.

## Sorun giderme

- `npx cap doctor` ortamı kontrol eder.
- Streamlit yanıt vermiyorsa WebView boş kalır; önce tarayıcıdan aynı URL’yi doğrulayın.
- Ana depodaki `app.py` güvenli alan ve kenar çubuğu renkleri mobil WebView ile uyumludur; sunucuyu güncelledikten sonra mağaza kullanıcıları yeni arayüzü görür (kabuk güncellemesi gerekmez).

### iOS: Xcode lisansı, `xcode-select`, CocoaPods

Hata örnekleri: `xcodebuild requires Xcode`, `active developer directory ... CommandLineTools`, `Skipping pod install because CocoaPods is not installed`, `You have not agreed to the Xcode license`.

1. **Tam Xcode** (App Store) kurulu olsun; yalnızca Command Line Tools yetmez.
2. Geliştirici yolunu Xcode’a çevirin (bir kez):
   ```bash
   sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
   ```
3. **Lisans:** Terminalde `sudo xcodebuild -license` (veya kabul için `sudo xcodebuild -license accept`).
4. **CocoaPods** (iOS bağımlılıkları için):
   ```bash
   brew install cocoapods
   cd mobile/ios/App && pod install && cd ../../..
   ```
5. Sonra: `cd mobile && npm run sync` veya `npx cap sync`.

`android/` ve `ios/` zaten varsa **`npm run setup:native`** yalnızca `npm install && cap sync` yapar. İlk kez platform eklemek için: **`npm run bootstrap:native`**.

### Terminalde `command not found: Saving`

Bu genelde bozuk bir `~/.zsh_sessions/*.session` dosyasından kaynaklanır; ilgili oturum dosyasını silmek veya `zsh`’i yeniden başlatmak sorunu giderir; projeyle ilgili değildir.

---

## Yayına kadar tam sıra (iOS + Android)

Aşağıdaki sırayı kendi makinenizde (Node.js ve Xcode/Android Studio kurulu) uygulayın. Bu repoda otomatik `npm` çalıştırılamadığı için komutları siz çalıştıracaksınız.

### A — Ortak (önce bunlar)

1. **Streamlit’i HTTPS ile yayınlayın** (Streamlit Community Cloud, kendi sunucunuz veya ters vekil ile TLS). Mağaza WebView’ları güvenilir HTTPS bekler.
2. `capacitor.config.json` içinde `server.url` değerini bu adrese yazın; `cleartext` yalnızca HTTP testinde `true` olmalı.
3. Terminal: `cd mobile` → `npm install`
4. **İlk kez `android/` ve `ios/` yoksa:** `npm run bootstrap:native`  
   (Platformları ekler ve `cap sync` çalıştırır.) Klasörler zaten varsa yalnızca **`npm run setup:native`** (`npm install` + `cap sync`) yeterlidir.
5. **Gizlilik politikası:** KVKK / veri işleme metninizin URL’sini hazır tutun (mağaza formları ve uygulama içi link için).
6. **İkon ve splash:** Mağaza için en az 1024×1024 uygulama ikonu ve splash ekranı üretin (`@capacitor/assets` veya manuel); ardından `npx cap sync`.

### B — Android (Google Play)

7. `npm run open:android` ile Android Studio’yu açın.
8. **applicationId:** `android/app/build.gradle` içinde `applicationId` ile `capacitor.config.json` `appId` uyumlu olsun.
9. **İmzalama:** Play Console “App signing” için bir **upload key** oluşturup Studio’da release yapılandırması ekleyin.
10. Emülatör veya cihazda **Release** veya **Debug** ile WebView’da Streamlit açıldığını doğrulayın.
11. **Play Console:** Uygulama oluşturma, mağaza girişi (açıklama, ekran görüntüsü, içerik derecelendirmesi), gizlilik beyanı URL’si.
12. **AAB** üretip iç test → üretim sırasıyla yükleyin.

### C — iOS (App Store, yalnızca Mac)

13. `npm run open:ios` ile Xcode’u açın.
14. **Signing & Capabilities:** Takım seçin, benzersiz **Bundle Identifier** (`appId` ile aynı mantıkta) ayarlayın.
15. **App Store Connect**’te uygulama kaydı; gizlilik URL’si ve veri toplama sorularını doldurun.
16. **Archive** → **Distribute** ile TestFlight veya incelemeye gönderin.
17. Apple, “yalnızca web içeriği” uygulamalarında ek sorular sorabilir; uygulamanın **Duvar Metraj** aracı olduğunu ve ekran görüntülerini net sunun.

### D — Güncelleme döngüsü

18. Streamlit tarafı (`app.py`) değişince kullanıcılar sunucudan yeni arayüzü görür; **kabuk değişmediyse** mağazaya yeniden yükleme zorunlu değildir.
19. `appId`, `appName`, ikon veya `server.url` değişirse: `npx cap sync` → native projede tekrar derleme / mağaza sürüm numarası artırma.
20. Sorun çıkarsa: `npm run doctor`, ardından tarayıcıda `server.url` adresini test edin.

### Tek komut özeti (ilk kurulum)

```bash
cd mobile
npm install
npm run bootstrap:native
# capacitor.config.json → server.url düzenle
npm run ios:pod        # yalnızca iOS — CocoaPods kuruluysa
npm run open:android   # veya open:ios
```

Sonraki güncellemelerde: `npm run setup:native` veya `npx cap sync`.
