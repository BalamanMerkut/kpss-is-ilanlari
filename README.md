# KPSS İş İlanları

KPSS ile başvurulabilen kamu iş ilanlarını **resmî devlet sitelerinden** toplayıp
mezuniyetinize ve puanınıza göre listeleyen **ücretsiz Windows programı**.

## 📥 Kurulum

1. **[⬇ PROGRAMI İNDİR](https://github.com/BalamanMerkut/kpss-is-ilanlari/releases/latest/download/KPSS-Is-Ilanlari.exe)** yazısına tıkla.
2. Tarayıcı uyarı verirse **Sakla**'ya tıkla.
3. İnen **KPSS-Is-Ilanlari.exe** dosyasına çift tıkla.
4. *"Windows bilgisayarınızı korudu"* çıkarsa **Ek bilgi → Yine de çalıştır**'a tıkla.
5. Açılan sayfada mezuniyetini seç, puanını yaz.

*Sadece Windows bilgisayarda çalışır.*

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
