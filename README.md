# KPSS İş İlanları

KPSS ile başvurulabilen kamu iş ilanlarını **yalnızca resmî devlet sitelerinden** toplayıp
mezuniyete (Lise P94 / Önlisans P93 / Lisans P3 / İşçi alımı) göre sade bir listede gösteren Windows programı.

Bilgisayar kullanmayı az bilen biri de rahatça kullanabilsin diye tasarlandı:
mezuniyetinizi seçin, KPSS puanınızı yazın, her işin yanında **"✔ Yetiyor" / "✘ Yetmiyor"** yazsın.

## İndir (kurulum gerekmez)

👉 [**Son sürümü indir (Releases)**](../../releases/latest) → `KPSS-Is-Ilanlari.exe` dosyasına çift tıklayın.

> Program imzasız olduğu için Windows ilk açılışta *"Windows bilgisayarınızı korudu"* diyebilir:
> **Ek bilgi → Yine de çalıştır** deyin.

## Neler gösterir?

- **Şu an başvurulabilen işler:** iş adı, kurum, şehir, kaç kişi alınacağı, en az KPSS puanı,
  son başvuru tarihi (kaç gün kaldığı) ve puanınızın yetip yetmediği.
  Bir işe tıklayınca hangi şehirde kaç kişi alınacağı, ilanın tam metni ve başvuru düğmeleri açılır.
- **ÖSYM tercih kadroları:** ÖSYM'nin son KPSS tercih kılavuzundaki kadrolar, bölüm şartları (yazıyla)
  ve o kadrolara yerleşilen **en düşük puan**. Tercih dönemi açıldığında bunu da gösterir.
- Aynı ilan iki sitede birden yayımlanmışsa **bir kez** sayılır.

## Kaynaklar (yalnızca resmî siteler)

| Kaynak | Ne alınıyor |
|---|---|
| [ilan.gov.tr](https://www.ilan.gov.tr) – T.C. Basın İlan Kurumu | Resmî Gazete'de yayımlanan kamu personel alım ilanlarının tam metni |
| [kariyerkapisi.gov.tr](https://kariyerkapisi.gov.tr/isealim) – Cumhurbaşkanlığı İK Ofisi | Kadro/kontenjan bilgileri, kesin son başvuru tarihleri, başvuru bağlantıları |
| [osym.gov.tr](https://www.osym.gov.tr) – ÖSYM | KPSS tercih kılavuzu kadro tabloları, nitelik kodları, yerleşme puanları |

Program başka hiçbir siteden ilan almaz ve adresi `.gov.tr` ile bitmeyen bağlantıları göstermez.
**Kamu ilanlarına başvuru ücretsizdir; para isteyen ilan sahtedir.**

Kişi sayısı, puan ve tarih bilgileri ilan metinlerinden otomatik okunur. Başvurmadan önce ilanın aslını kontrol edin.

## Otomatik güncelleme

Program her açılışta bu reponun son sürümünü (GitHub Releases) kontrol eder. Yeni sürüm varsa ekranda
**"Şimdi güncelle"** düğmesi çıkar; basınca yeni exe indirilir, **SHA-256 parmak izi GitHub'ın bildirdiği değerle
karşılaştırılır**, tutarsa eski exe'nin yerine konur ve program kendini yeniden açar.
Güncelleme yalnızca kullanıcı düğmeye bastığında yapılır.

Yeni sürüm yayımlamak için: `uygulama/guncelle.py` içindeki `SURUM` değerini artırın, exe'yi yeniden derleyin
ve aynı numarayla (ör. `v1.2`) bir Release açıp `KPSS-Is-Ilanlari.exe` dosyasını ekleyin.

## Gizlilik

Program yalnızca kendi bilgisayarınızda çalışır (`127.0.0.1`). Yazdığınız puan sadece tarayıcınızda saklanır,
hiçbir yere gönderilmez.

## Geliştirme

Python 3 ile yazıldı; ek kütüphane olarak yalnızca ÖSYM PDF tabloları için [PyMuPDF](https://pypi.org/project/PyMuPDF/) kullanır.

```powershell
pip install pymupdf
python uygulama/sunucu.py
```

| Dosya | Görevi |
|---|---|
| `uygulama/sunucu.py` | Yerel sunucu; ekranı tarayıcıda açar, verileri yeniler |
| `uygulama/kaynaklar.py` | ilan.gov.tr ve Kariyer Kapısı'ndan ilan toplama, birleştirme, tekrar ayıklama |
| `uygulama/ayristir.py` | İlan metinlerinden kadro, kişi sayısı, puan türü, son başvuru tarihi çıkarma |
| `uygulama/osym.py`, `uygulama/pdf_tablo.py` | ÖSYM tercih kılavuzu PDF tablolarını okuma |
| `uygulama/arayuz.html` | Ekran |

Exe'yi yeniden oluşturmak için (PyInstaller gerekir: `pip install pyinstaller`):

```powershell
.\exe_yeniden_olustur.bat
```
