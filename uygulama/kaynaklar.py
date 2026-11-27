"""Resmî kaynaklardan ilan toplama.

Kaynaklar (yalnızca devlet siteleri):
  1) ilan.gov.tr  – T.C. Basın İlan Kurumu resmî ilan portalı. Resmî Gazete'de yayımlanan
                    kamu personel alım ilanlarının tam metni burada yayımlanır.
  2) kariyerkapisi.gov.tr – T.C. Cumhurbaşkanlığı İnsan Kaynakları Ofisi "Kamu İşe Alım"
                    platformu. Başvuruların büyük kısmı buradan / e-Devlet'ten alınır.
"""
import json
import os
import re
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone

import ayristir as A

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KPSS-Ilan-Takip/1.0"
ILAN_API = "https://www.ilan.gov.tr/api/api/services/app/"
KK_API = "https://api.kariyerkapisi.gov.tr/api/"
TR_SAAT = timezone(timedelta(hours=3))
AYNI_ANDA = 4  # aynı anda en fazla kaç indirme (sunucuları yormamak için düşük tutuldu)

# Bu kategorideki ilanlar KPSS ile iş başvurusu değildir (akademik kadro, sertifika sınavı vb.)
HARIC_KATEGORI = re.compile(
    r"öğretim üyesi|araştırma görevlisi|akademik personel|sertifikasyon|yeterlilik sınavı|"
    r"öğrenci alım|yeminli mali|aktüer|lisanslama", re.I)
HARIC_KK_TUR = re.compile(r"öğretim|araştırma görevlisi|yurt dışı eğitim|görevde yükselme|belge başvurusu|yeterlik", re.I)
ISCI_RE = re.compile(r"işçi|isci", re.I)


def _istek(url, veri=None, basliklar=None, zaman=40):
    h = {"User-Agent": UA}
    h.update(basliklar or {})
    govde = json.dumps(veri).encode("utf-8") if veri is not None else None
    req = urllib.request.Request(url, data=govde, headers=h, method="POST" if govde is not None else "GET")
    son_hata = None
    for deneme in range(3):
        try:
            with urllib.request.urlopen(req, timeout=zaman) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # ağ hatası: biraz bekleyip tekrar dene
            son_hata = e
            time.sleep(1.5 * (deneme + 1))
    raise son_hata


def _ilan_basliklar():
    return {"Content-Type": "application/json-patch+json", "Accept": "text/plain",
            "X-Requested-With": "XMLHttpRequest", "X-Request-Origin": "IGT-UI",
            "Referer": "https://www.ilan.gov.tr/ilan/tum-ilanlar/personel-alimi?ats=5"}


def _kk_basliklar():
    return {"Content-Type": "application/json", "Origin": "https://kariyerkapisi.gov.tr",
            "Referer": "https://kariyerkapisi.gov.tr/isealim"}


class Onbellek:
    """İlan detaylarını diske kaydeder; aynı ilan tekrar tekrar indirilmez."""

    def __init__(self, klasor):
        self.klasor = klasor
        os.makedirs(klasor, exist_ok=True)

    def _yol(self, ad):
        return os.path.join(self.klasor, re.sub(r"[^A-Za-z0-9_-]", "_", ad) + ".json")

    def al(self, ad):
        try:
            with open(self._yol(ad), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def koy(self, ad, veri):
        # önce geçici dosyaya yaz, sonra yerine koy: yarım kalan yazma bozuk kayıt bırakmasın
        yol = self._yol(ad)
        gecici = f"{yol}.{os.getpid()}.{threading.get_ident()}.tmp"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False)
        os.replace(gecici, yol)


# ------------------------------------------------------------------ ilan.gov.tr
def ilan_gov_listesi(ilerleme):
    ilanlar, atla, toplam = [], 0, None
    while True:
        d = _istek(ILAN_API + "Ad/AdsByFilter",
                   {"keys": {"ats": [5]}, "skipCount": atla, "maxResultCount": 20}, _ilan_basliklar())
        r = d["result"]
        parca = r.get("ads") or []
        toplam = r.get("numFound") or toplam or 0
        ilanlar += parca
        ilerleme(f"ilan.gov.tr listesi alınıyor... ({len(ilanlar)}/{toplam})")
        atla += 20
        if not parca or atla >= toplam or atla > 2000:
            break
        time.sleep(0.15)
    return ilanlar


def ilan_gov_detay(ilan_id, onbellek):
    anahtar = f"ilan_{ilan_id}"
    d = onbellek.al(anahtar)
    if d is None:
        d = _istek(ILAN_API + f"AdDetail/GetAdDetail?id={ilan_id}", None, _ilan_basliklar())["result"]
        onbellek.koy(anahtar, {"content": d.get("content", ""), "title": d.get("title")})
        time.sleep(0.25)
    return d


def _yayim_tarihi(ad):
    for f in ad.get("adTypeFilters") or []:
        if "Gazete" in (f.get("key") or ""):
            try:
                return datetime.strptime(f["value"], "%d.%m.%Y").date()
            except (ValueError, KeyError):
                pass
    s = ad.get("publishStartDate")
    if s:
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(TR_SAAT).date()
        except ValueError:
            pass
    return None


# ------------------------------------------------------------------ Kariyer Kapısı
def kk_listesi():
    d = _istek(KK_API + "ilan/GetIseAlimPage", {"krM_ID": 0, "searchText": "", "il": "0", "ilanTuru": "0"}, _kk_basliklar())
    return d.get("searchIlan") or []


def kk_alt_ilanlar(guid, onbellek):
    anahtar = f"kk_{guid}"
    d = onbellek.al(anahtar)
    if d is None:
        hata = False
        try:
            d = _istek(KK_API + "altilan/GetAltIlanInfoByIlanIdPublic", {"ilanGuid": guid}, _kk_basliklar())
        except Exception:
            d, hata = [], True
        if not isinstance(d, list):
            d = []
        try:
            on = _istek(KK_API + "ilan/GetIlanPreviewPublic", {"ilanGuid": guid}, _kk_basliklar())
        except Exception:
            on, hata = {}, True
        d = {"alt": d, "onizleme": {"ilanMetni": (on or {}).get("ilanMetni", ""),
                                    "eDevletServisURL": (on or {}).get("eDevletServisURL", "")}}
        if not hata:  # geçici bir bağlantı hatasında boş sonucu kalıcı kaydetme; sonra tekrar denensin
            onbellek.koy(anahtar, d)
        time.sleep(0.25)
    return d


def _norm_kurum(s):
    s = A.tr_upper(s)
    s = re.sub(r"[^A-ZÇĞİÖŞÜ0-9 ]", " ", s)
    s = re.sub(r"\b(T C|BAŞKANLIĞI|BAŞKANLIĞINDAN|REKTÖRLÜĞÜ|REKTÖRLÜĞÜNDEN|GENEL|MÜDÜRLÜĞÜ|MÜDÜRLÜĞÜNDEN|"
               r"BAKANLIĞI|BAKANLIĞINDAN|KURUMU|KURUMUNDAN|BELEDİYE|BELEDİYESİ|İLANI|ALIM|PERSONEL|"
               r"SÖZLEŞMELİ|VE|SEKRETERLİĞİ|KOMUTANLIĞI|İLİ)\b", " ", s)
    return [w for w in s.split() if len(w) > 2]


# ------------------------------------------------------------------ birleştirme
def _seviye_listesi(puanlar, metin_seviye):
    s = []
    for p in puanlar:
        v = A.seviye_puanturunden(p)
        if v and v not in s:
            s.append(v)
    for v in metin_seviye:
        if v not in s and not puanlar:
            s.append(v)
    return s


def _pozisyonlari_tamamla(pozlar, ilan_pt, ilan_min, varsayilan_il):
    ilan_seviye = _seviye_listesi(ilan_pt, [])
    for p in pozlar:
        p["seviye"] = list(dict.fromkeys(p.get("seviye") or []))
        if not p["puan_turleri"] and len(ilan_seviye) == 1:
            p["puan_turleri"] = [x for x in ilan_pt]
            p["seviye"] = ilan_seviye[:]
        elif not p["seviye"] and ilan_seviye:
            p["seviye"] = ilan_seviye[:]
            p["puan_turleri"] = ilan_pt[:]
        if p.get("asgari_puan") is None and ilan_min is not None:
            p["asgari_puan"] = ilan_min
        if not p.get("il"):
            p["il"] = varsayilan_il
    return pozlar


def _baslik_adedi(baslik):
    m = re.search(r"(\d{1,5})\s*(?:\(\w+\)\s*)?(?:adet\s+)?(?:sözleşmeli|personel|memur|zabıta|işçi|devlet|uzman|kişi|polis|bekçi|itfaiye|koruma|güvenlik|mühendis|teknisyen|tekniker|şoför|sürekli|büro|sağlık|hemşire|öğretmen|imam|gardiyan|infaz|erbaş|er\b)",
                  A.tr_lower(baslik))
    return int(m.group(1)) if m else None


def _metin_adedi(metin):
    """'toplam 9.000 uzman erbaş', '1170 (bin yüz yetmiş) sözleşmeli personel' gibi ifadelerden toplam kişi sayısı."""
    t = A.tr_lower(metin[:4000])
    m = re.search(r"toplam(?:da)?\s+(\d{1,3}(?:\.\d{3})+|\d{1,5})\s*(?:\([^)]{0,40}\)\s*)?(?:adet\s+|kişi\s+)?[a-zçğıöşü]", t)
    if m:
        v = int(m.group(1).replace(".", ""))
        return v if 0 < v < 100000 else None
    return None


def _satir(kaynak, **k):
    k["kaynak"] = kaynak
    return k


def _osym_topla(onbellek, bugun):
    """ÖSYM verisini ayrı bir iş parçacığında toplar (ilan siteleriyle aynı anda)."""
    try:
        import osym
        return osym.topla(onbellek, bugun), None
    except Exception as e:
        return None, f"ÖSYM tercih kılavuzu okunamadı: {e}"


def _onceden_indir(isler, ilerleme, mesaj):
    """İndirmeleri aynı anda (en fazla AYNI_ANDA kadar) yapar; sonuçlar diske kaydedilir.

    Hatalar burada yutulur: asıl okuma aşaması aynı dosyayı tekrar ister ve hata orada kaydedilir.
    """
    if not isler:
        return
    biten = 0
    with ThreadPoolExecutor(max_workers=AYNI_ANDA) as havuz:
        for gelecek in as_completed([havuz.submit(f, *a) for f, *a in isler]):
            biten += 1
            ilerleme(f"{mesaj} ({biten}/{len(isler)})")
            try:
                gelecek.result()
            except Exception:
                pass


def topla(veri_klasoru, ilerleme=lambda s: None):
    onbellek = Onbellek(os.path.join(veri_klasoru, "onbellek"))
    bugun = datetime.now(TR_SAAT).date()
    hatalar = []
    ilanlar = []  # her biri bir ilan; içinde pozisyonlar

    # ÖSYM bağımsız bir kaynak: ilan siteleri okunurken arka planda aynı anda okunsun
    osym_havuz = ThreadPoolExecutor(max_workers=1)
    osym_gelecek = osym_havuz.submit(_osym_topla, onbellek, bugun)

    # --- 1) Kariyer Kapısı
    kk = []
    try:
        ilerleme("Kariyer Kapısı (Cumhurbaşkanlığı) ilanları alınıyor...")
        kk = kk_listesi()
    except Exception as e:
        hatalar.append(f"Kariyer Kapısı'na ulaşılamadı: {e}")

    # --- 2) ilan.gov.tr
    gov = []
    try:
        gov = ilan_gov_listesi(ilerleme)
    except Exception as e:
        hatalar.append(f"ilan.gov.tr'ye ulaşılamadı: {e}")

    # Daha önce okunmamış ilan metinlerini aynı anda indir (okunanlar diskte kayıtlı, tekrar inmez)
    isler = []
    for ad in gov:
        kategori = " ".join(v.get("value", "") for v in ad.get("values") or [])
        if HARIC_KATEGORI.search(kategori) or HARIC_KATEGORI.search(ad.get("title") or ""):
            continue
        if onbellek.al(f"ilan_{ad['id']}") is None:
            isler.append((ilan_gov_detay, ad["id"], onbellek))
    for k in kk:
        if k.get("guid") and onbellek.al(f"kk_{k['guid']}") is None:
            isler.append((kk_alt_ilanlar, k["guid"], onbellek))
    _onceden_indir(isler, ilerleme, "Yeni ilanlar indiriliyor...")

    kk_eslesen = set()
    gorulen = set()  # aynı ilan iki kez sayılmasın
    for i, ad in enumerate(gov):
        kategori = " ".join(v.get("value", "") for v in ad.get("values") or [])
        baslik = ad.get("title") or ""
        if HARIC_KATEGORI.search(kategori) or HARIC_KATEGORI.search(baslik):
            continue
        if re.match(r"\s*(iptal|düzeltme)", A.tr_lower(baslik)) or "hizmeti alınacak" in A.tr_lower(baslik):
            continue
        anahtar = _tekrar_anahtari(ad.get("advertiserName"), baslik)
        if ("G", ad.get("id")) in gorulen or anahtar in gorulen:
            continue
        gorulen.update({("G", ad.get("id")), anahtar})
        ilerleme(f"İlan metinleri okunuyor... ({i + 1}/{len(gov)})")
        try:
            det = ilan_gov_detay(ad["id"], onbellek)
        except Exception as e:
            hatalar.append(f"{ad.get('adNo')}: {e}")
            continue
        tablolar, metin = A.html_coz(det.get("content", ""))
        yayim = _yayim_tarihi(ad)
        son, kesin = A.son_basvuru(metin, yayim)
        ilan_pt = A.puan_turleri(metin)
        ilan_min = A.asgari_puan(metin)
        varsayilan_il = A.tr_upper(ad.get("addressCityName") or "") or None
        pozlar = A.tablolardan_pozisyonlar(tablolar)

        isci = bool(ISCI_RE.search(kategori) or ISCI_RE.search(baslik))
        basvuru_linki = None

        # Kariyer Kapısı'nda aynı ilan varsa: kesin son tarih + başvuru linki
        basvuru_baslangic = None
        j = _kk_eslestir(kk, kk_eslesen, ad.get("advertiserName") or "", baslik, yayim)
        if j is not None:
            k = kk[j]
            kk_eslesen.add(j)
            sb = A.iso_tarih(k.get("bitTarih"))
            if sb:
                son, kesin = sb, True
            bb = A.iso_tarih(k.get("basTarih"))
            if bb and bb > bugun:
                basvuru_baslangic = bb.isoformat()
            basvuru_linki = _kk_link(k)
            if not pozlar:
                alt = kk_alt_ilanlar(k["guid"], onbellek)
                pozlar = _kk_pozisyonlar(alt)

        if not pozlar:
            pozlar = [{"unvan": _kisa_baslik(baslik), "adet": _baslik_adedi(baslik) or _metin_adedi(metin), "puan_turleri": ilan_pt[:],
                       "seviye": [], "asgari_puan": ilan_min, "yer": "", "il": varsayilan_il, "ilan_geneli": True}]
            if not ilan_pt:
                pozlar[0]["seviye"] = A.seviye_metinden(metin[:3000]) if isci else []
        pozlar = _pozisyonlari_tamamla(pozlar, ilan_pt, ilan_min, varsayilan_il)

        ilanlar.append({
            "id": "G" + str(ad["id"]),
            "ilan_no": ad.get("adNo"),
            "kurum": ad.get("advertiserName") or "",
            "baslik": baslik,
            "kategori": kategori,
            "isci": isci,
            "il": varsayilan_il,
            "yayim": yayim.isoformat() if yayim else None,
            "son_basvuru": son.isoformat() if son else None,
            "son_kesin": kesin,
            "kaynak": "ilan.gov.tr (Basın İlan Kurumu – Resmî Gazete ilanı)",
            "kaynak_link": "https://www.ilan.gov.tr" + (ad.get("urlStr") or ""),
            "basvuru_link": basvuru_linki,
            "basvuru_baslangic": basvuru_baslangic,
            "metin": metin[:60000],
            "sartlar": A.ilan_sartlari(metin),
            "pozisyonlar": pozlar,
        })

    # --- Kariyer Kapısı'nda olup ilan.gov.tr'de bulunamayanlar
    for j, k in enumerate(kk):
        if j in kk_eslesen:
            continue
        tur = k.get("ilanTuru") or ""
        if HARIC_KK_TUR.search(tur) and not ISCI_RE.search(tur):
            continue
        if re.search(r"merkezi yerleştirme|ösym", tur, re.I):
            continue  # ÖSYM bölümünde zaten gösteriliyor
        anahtar = _tekrar_anahtari(k.get("kurumAdi"), k.get("ilanBaslik"))
        if ("K", k.get("guid")) in gorulen or anahtar in gorulen:
            continue
        gorulen.update({("K", k.get("guid")), anahtar})
        ilerleme(f"Kariyer Kapısı ilan ayrıntıları okunuyor... ({j + 1}/{len(kk)})")
        alt = kk_alt_ilanlar(k["guid"], onbellek)
        metin = A.bbcode_temizle(alt.get("onizleme", {}).get("ilanMetni", ""))
        alt_metin = "\n\n".join(A.bbcode_temizle(a.get("ilanMetni", "")) for a in alt.get("alt") or [])
        tum_metin = (metin + "\n\n" + alt_metin).strip()
        ilan_pt = A.puan_turleri(tum_metin)
        ilan_min = A.asgari_puan(tum_metin)
        pozlar = _kk_pozisyonlar(alt)
        baslik = k.get("ilanBaslik") or ""
        if not pozlar:
            pozlar = [{"unvan": _kisa_baslik(baslik), "adet": _baslik_adedi(baslik) or _metin_adedi(tum_metin), "puan_turleri": ilan_pt[:],
                       "seviye": [], "asgari_puan": ilan_min, "yer": "", "il": None, "ilan_geneli": True}]
        il = None
        pozlar = _pozisyonlari_tamamla(pozlar, ilan_pt, ilan_min, il)
        sb = A.iso_tarih(k.get("bitTarih"))
        bb = A.iso_tarih(k.get("basTarih"))
        ilanlar.append({
            "id": "K" + k["guid"],
            "ilan_no": None,
            "kurum": k.get("kurumAdi") or "",
            "baslik": baslik,
            "kategori": tur.strip(", "),
            "isci": bool(ISCI_RE.search(tur) or ISCI_RE.search(baslik)),
            "il": il,
            "yayim": (A.iso_tarih(k.get("basTarih")) or bugun).isoformat(),
            "son_basvuru": sb.isoformat() if sb else None,
            "son_kesin": True,
            "kaynak": "Kariyer Kapısı (Cumhurbaşkanlığı İnsan Kaynakları Ofisi)",
            "kaynak_link": _kk_link(k),
            "basvuru_link": _kk_link(k),
            "basvuru_baslangic": bb.isoformat() if bb and bb > bugun else None,
            "metin": tum_metin[:60000],
            "sartlar": A.ilan_sartlari(tum_metin),
            "pozisyonlar": pozlar,
        })

    # her kadronun şart metnini kısa maddelere çevir (ekranda "Şartlar" listesi)
    for ilan in ilanlar:
        for p in ilan["pozisyonlar"]:
            p["sartlar"] = A.kadro_nitelikleri(p.pop("nitelik", ""))

    # bir ilanın içinde aynı kadro satırı iki kez okunduysa tek say
    for ilan in ilanlar:
        tekil, gor = [], set()
        for p in ilan["pozisyonlar"]:
            k = (A.tr_upper(p.get("unvan")), A.tr_upper(p.get("yer")), p.get("adet"), tuple(p.get("puan_turleri") or []))
            if k not in gor:
                gor.add(k)
                tekil.append(p)
        ilan["pozisyonlar"] = tekil

    # --- 3) ÖSYM merkezi yerleştirme (tercih kılavuzu kadroları) – arka planda okunuyordu
    if not osym_gelecek.done():
        ilerleme("ÖSYM tercih kılavuzu okunuyor...")
    osym_veri, osym_hata = osym_gelecek.result()
    osym_havuz.shutdown()
    if osym_hata:
        hatalar.append(osym_hata)
    elif osym_veri and osym_veri.get("hata"):
        hatalar.append(osym_veri["hata"])

    ilerleme("Hazırlanıyor...")
    return {
        "guncelleme": datetime.now(TR_SAAT).strftime("%d.%m.%Y %H:%M"),
        "bugun": bugun.isoformat(),
        "hatalar": hatalar,
        "ilanlar": ilanlar,
        "osym": osym_veri,
    }


def _tekrar_anahtari(kurum, baslik):
    """Aynı kurumun aynı başlıklı ilanı → aynı anahtar (büyük/küçük harf, noktalama farkı önemsiz)."""
    b = re.sub(r"[^a-zçğıöşü0-9]+", " ", A.tr_lower(baslik or "")).strip()
    k = " ".join(sorted(_norm_kurum(kurum or "")))
    return ("T", k, b)


def _kok(kelimeler):
    return {w[:6] for w in kelimeler}


def _kk_eslestir(kk, kullanilan, kurum, baslik, yayim):
    """ilan.gov.tr ilanına karşılık gelen Kariyer Kapısı ilanını bulur (yoksa None)."""
    gov_kurum = _kok(_norm_kurum(kurum))
    gov_hepsi = gov_kurum | _kok(_norm_kurum(baslik))
    en_iyi, en_iyi_puan = None, 0.0
    for j, k in enumerate(kk):
        if j in kullanilan:
            continue
        kk_kurum = _kok(_norm_kurum(k.get("kurumAdi") or ""))
        if not kk_kurum:
            continue
        oran = len(kk_kurum & gov_hepsi) / len(kk_kurum)
        kk_baslik = _kok(_norm_kurum(k.get("ilanBaslik") or "")) - kk_kurum
        ek = len(kk_baslik & (gov_hepsi - gov_kurum))
        if not (oran >= 0.75 or (oran >= 0.5 and ek >= 1)):
            continue
        # Kariyer Kapısı'ndaki tarih başvurunun başladığı gündür; Resmî Gazete'den birkaç hafta sonra olabilir
        kb = A.iso_tarih(k.get("basTarih"))
        if yayim and kb and not (-7 <= (kb - yayim).days <= 40):
            continue
        puan = oran + 0.5 * ek
        if puan > en_iyi_puan:
            en_iyi, en_iyi_puan = j, puan
    return en_iyi


def _kk_link(k):
    if k.get("ilanTipi") == 2 and k.get("basvuruLinki"):
        return k["basvuruLinki"]
    return f"https://kariyerkapisi.gov.tr/IlanDetay?i={k.get('guid')}"


def _kk_pozisyonlar(alt):
    pozlar = []
    for a in alt.get("alt") or []:
        m = A.bbcode_temizle(a.get("ilanMetni", ""))
        pt = A.puan_turleri(m)
        mezun = re.search(r"MEZUN[İI]YET\s*:\s*([^\n]+)", m, re.I)
        sev = A.seviye_metinden(mezun.group(1)) if mezun else []
        if pt:
            sev = [x for x in (A.seviye_puanturunden(p) for p in pt) if x]
        unvan = (a.get("unvan") or a.get("ilanBaslik") or "").strip()
        nitelik = _kk_nitelik(m)
        kont = a.get("kontenjanList") or []
        if not kont:
            pozlar.append({"unvan": unvan, "adet": None, "puan_turleri": pt, "seviye": sev,
                           "asgari_puan": A.asgari_puan(m), "yer": "", "il": None, "nitelik": nitelik})
        for kk in kont:
            yer = kk.get("il") or ""
            pozlar.append({"unvan": unvan, "adet": kk.get("kontenjan") or None, "puan_turleri": pt, "seviye": sev,
                           "asgari_puan": A.asgari_puan(m), "yer": yer, "il": A.il_bul(yer), "nitelik": nitelik})
    return pozlar


def _kk_nitelik(m):
    """Kariyer Kapısı kadro metninden mezuniyet, cinsiyet ve 'ÖZEL ŞARTLAR' maddeleri."""
    satirlar = []
    for etiket in ("MEZUN[İI]YET", "C[İI]NS[İI]YET"):
        x = re.search(etiket + r"\s*:\s*([^\n]+)", m, re.I)
        if x and A.bosluk(x.group(1)) not in ("", "-"):
            satirlar.append(("Mezuniyet: " if etiket.startswith("MEZUN") else "Cinsiyet: ") + A.bosluk(x.group(1)))
    ozel = re.search(r"ÖZEL\s*ŞARTLAR\s*\n(.*)", m, re.I | re.S)
    if ozel:
        for s in ozel.group(1).splitlines():
            s = s.strip()
            if re.match(r"^[-•*]\s*\S", s):
                satirlar.append(s.lstrip("-•* ").strip())
            elif s and satirlar and not re.match(r"^[A-ZÇĞİÖŞÜ\s]{6,}$", s) and len(satirlar) > 2:
                continue
            elif re.match(r"^[A-ZÇĞİÖŞÜ\s]{6,}$", s):
                break  # yeni büyük harfli başlık: özel şartlar bitti
    return "\n".join(satirlar)[:4000]


def _kisa_baslik(b):
    b = re.sub(r"\s*(alım|alim)\s*(ilanı|ilani|duyurusu)\s*$", " alımı", A.bosluk(b), flags=re.I).strip()
    return b[:160]
