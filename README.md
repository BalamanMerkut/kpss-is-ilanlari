# KPSS İş İlanları

KPSS ile başvurulabilen kamu iş ilanlarını **resmî devlet sitelerinden** toplayıp
mezuniyetinize ve puanınıza göre listeleyen **ücretsiz Windows programı**.

## 📥 Kurulum

> **Şu an GitHub adlı bir sitedesiniz.** Programcıların kodlarını paylaştığı bir sitedir.
> **Üye olmanız veya giriş yapmanız gerekmez.** Sayfadaki dosya listesi ve diğer düğmeler programcılar içindir, onlara dokunmayın.

### 1️⃣ Programı indirin

## [⬇ PROGRAMI İNDİRMEK İÇİN TIKLAYIN](https://github.com/BalamanMerkut/kpss-is-ilanlari/releases/latest/download/KPSS-Is-Ilanlari.exe)

- İndirme hemen başlar.
- Tarayıcı *"yaygın olarak indirilmiyor"* diye uyarırsa: **Chrome'da "Sakla"**, **Edge'de "⋯" → "Sakla" → "Yine de sakla"** seçin.
- ⚠ Yeşil **"Code"** düğmesine basmayın. O programcılar içindir, program inmez.

### 2️⃣ İndirilen dosyayı açın

- **KPSS-Is-Ilanlari.exe** dosyası bilgisayarınızın **"İndirilenler"** klasörüne gelir.
  Tarayıcının sağ üst köşesindeki **⬇ (indirilenler)** simgesine tıklayıp oradan da açabilirsiniz.
- Dosyaya **çift tıklayın**.
- Mavi bir *"Windows bilgisayarınızı korudu"* penceresi çıkarsa: **"Ek bilgi"** yazısına, sonra **"Yine de çalıştır"** düğmesine tıklayın. *(Sadece ilk açılışta çıkar.)*

### 3️⃣ Kullanın

- Birkaç saniye sonra program **internet tarayıcınızda** açılır. İlk açılışta ilanlar 1 dakika kadar yüklenir.
- Mezuniyetinizi seçin, KPSS puanınızı yazın. Her işin yanında **"✔ Yetiyor"** ya da **"✘ Yetmiyor"** yazar.
- Sonra tekrar açmak için aynı dosyaya çift tıklamanız yeterli. İsterseniz dosyayı masaüstüne sürükleyin.
- Yeni sürüm çıkınca programın üstünde **"Şimdi güncelle"** düğmesi belirir, tekrar indirmenize gerek kalmaz.

> 📱 Program yalnızca **Windows bilgisayarda** çalışır; telefonda ve Mac'te çalışmaz.

## ✔ Güvenli mi?

- İlanlar yalnızca **ilan.gov.tr**, **Kariyer Kapısı** ve **ÖSYM** sitelerinden alınır.
- Puanınız sadece kendi bilgisayarınızda kalır, hiçbir yere gönderilmez.
- Kamu ilanlarına başvuru **ücretsizdir**. Para isteyen ilan **sahtedir**.

> Bilgiler ilan metinlerinden otomatik okunur. Başvurmadan önce ilanın aslını kontrol edin.

---

<details>
<summary>Geliştiriciler için</summary>

Python 3 + [PyMuPDF](https://pypi.org/project/PyMuPDF/) (ÖSYM PDF tabloları için).

```powershell
pip install pymupdf
python uygulama/sunucu.py
```

| Dosya | Görevi |
|---|---|
| `uygulama/sunucu.py` | Yerel sunucu (127.0.0.1), ekranı tarayıcıda açar |
| `uygulama/kaynaklar.py` | ilan.gov.tr ve Kariyer Kapısı'ndan ilan toplama, tekrar ayıklama |
| `uygulama/ayristir.py` | İlan metninden kadro, kişi sayısı, puan türü, son tarih çıkarma |
| `uygulama/osym.py`, `pdf_tablo.py` | ÖSYM tercih kılavuzu PDF tablolarını okuma |
| `uygulama/guncelle.py` | GitHub Releases'ten SHA-256 doğrulamalı otomatik güncelleme |
| `uygulama/arayuz.html` | Ekran |

**Yeni sürüm yayımlama:** `guncelle.py` içindeki `SURUM`'u artırın → `exe_yeniden_olustur.bat` →
aynı numarayla (ör. `v1.2`) Release açıp `KPSS-Is-Ilanlari.exe` ekleyin.

</details>
