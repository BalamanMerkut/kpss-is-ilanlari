# KPSS İş İlanları

KPSS ile başvurulabilen kamu iş ilanlarını **resmî devlet sitelerinden** toplayıp
mezuniyetinize ve puanınıza göre listeleyen **ücretsiz Windows ve Mac programı**.

## 📥 Kurulum

### 🪟 Windows

1. **[⬇ WINDOWS İÇİN İNDİR](https://github.com/BalamanMerkut/kpss-is-ilanlari/releases/latest/download/KPSS-Is-Ilanlari.exe)** yazısına tıkla.
2. İnen **KPSS-Is-Ilanlari.exe** dosyasına çift tıkla.
3. Mavi bir uyarı penceresi çıkarsa: **Ek bilgi** (*More info*) yazısına, sonra **Yine de çalıştır** (*Run anyway*) düğmesine tıkla.
4. Açılan sayfada mezuniyetini seç, puanını yaz.

*Tarayıcı dosyayı indirmeden engellerse: indirilenler listesinde dosyanın yanındaki **Sakla** (*Keep*) seçeneğine tıkla.*

### 🍎 Mac

1. Mac'ine uygun olanı indir:
   - **[⬇ MAC İÇİN İNDİR — M1, M2, M3, M4…](https://github.com/BalamanMerkut/kpss-is-ilanlari/releases/latest/download/KPSS-Is-Ilanlari-Mac.zip)**
   - **[⬇ MAC İÇİN İNDİR — Intel işlemci](https://github.com/BalamanMerkut/kpss-is-ilanlari/releases/latest/download/KPSS-Is-Ilanlari-Mac-Intel.zip)**

   *Hangisi? Ekranın sol üstündeki elma simgesi → **Bu Mac Hakkında**: "Çip: Apple M…" yazıyorsa ilki, "İşlemci: Intel" yazıyorsa ikincisi.*
2. İnen zip'e çift tıkla, çıkan **KPSS-Is-Ilanlari** uygulamasına çift tıkla.
3. "Açılamıyor" uyarısı çıkarsa **Bitti** (*Done*) de. Sonra **Sistem Ayarları → Gizlilik ve Güvenlik**'e gir, aşağı kaydır, **Yine de Aç** (*Open Anyway*)'a tıkla.
4. Açılan sayfada mezuniyetini seç, puanını yaz.

*Mac'te yeni sürüm çıkınca program haber verir; aynı bağlantıdan tekrar indir.*

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

**Yeni sürüm yayımlama:** `guncelle.py` içindeki `SURUM`'u artırın → PyInstaller ile tek dosya exe derleyin
(`--onefile --noconsole --add-data arayuz.html --collect-all pymupdf`) → aynı numarayla (ör. `v1.2`) Release açıp
`KPSS-Is-Ilanlari.exe` ekleyin.

</details>
