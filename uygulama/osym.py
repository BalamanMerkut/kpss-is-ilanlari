"""ÖSYM KPSS merkezi yerleştirme (tercih kılavuzu) kadroları.

Kaynak: osym.gov.tr → KPSS duyuruları
  - "KPSS-YYYY/N ... Tercih Kılavuzu ve Tablolar"  → Tablo-1 (Ortaöğretim), Tablo-2 (Önlisans), Tablo-3 (Lisans) PDF
  - "KPSS-YYYY/N ... Adaylardan Tercih Alınması"    → tercih tarihleri
  - "KPSS-YYYY/N ... Sonuçlarına İlişkin Sayısal Bilgiler" → En küçük / en büyük puanlar PDF
"""
import html
import json
import os
import re
import time
import urllib.request
from datetime import date

import ayristir as A
import pdf_tablo

OSYM = "https://www.osym.gov.tr"
KPSS_SAYFA = OSYM + "/SinavGrubu/Index/3"
# Programın kendi kimliği (tarayıcı taklidi yapılmaz)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KPSS-Ilan-Takip/1.0"

SEVIYELER = {
    "lise": {"tablo": r"TABLO-1", "sonuc": r"ORTA", "puan": "P94", "nitelik": r"^Ortaöğretim.*Nitelik"},
    "onlisans": {"tablo": r"TABLO-2", "sonuc": r"ÖN\s*L", "puan": "P93", "nitelik": r"^Ön Lisans.*Nitelik"},
    "lisans": {"tablo": r"TABLO-3", "sonuc": r"\(L[İI]SANS\)|\bL[İI]SANS\)", "puan": "P3", "nitelik": r"^Lisans.*Nitelik"},
}


def _nitelikler(url, onbellek):
    anahtar = "osymnit_" + re.sub(r"[^A-Za-z0-9]", "_", url)[-120:]
    v = onbellek.al(anahtar)
    if v is None:
        v = pdf_tablo.nitelik_kodlari(_indir(url, 120))
        onbellek.koy(anahtar, v)
    return v


def _indir(url, zaman=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9"})
    son = None
    for deneme in range(3):
        try:
            with urllib.request.urlopen(req, timeout=zaman) as r:
                veri = r.read()
            if url.lower().endswith(".pdf") and not veri.startswith(b"%PDF"):
                raise RuntimeError("ÖSYM sunucusu belgeyi vermedi (erişim engeli)")
            return veri
        except Exception as e:
            son = e
            time.sleep(2 * (deneme + 1))
    raise son


def _sayfa(url):
    return _indir(url).decode("utf-8", "replace")


def _baglantilar(sayfa_html):
    out = []
    for h, metin in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', sayfa_html, re.S):
        metin = A.bosluk(html.unescape(re.sub(r"<[^>]+>", " ", metin)))
        out.append((html.unescape(h), metin))
    return out


def _duz_metin(sayfa_html):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", sayfa_html, flags=re.S)
    return A.bosluk(html.unescape(re.sub(r"<[^>]+>", " ", t)))


def _donem(href):
    m = re.search(r"kpss-?(20\d\d)(\d)-", href)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _tam(href):
    return href if href.startswith("http") else OSYM + href


def duyurulari_bul():
    """KPSS sayfasından dönemlere göre kılavuz / tercih / sonuç duyuru bağlantıları."""
    s = _sayfa(KPSS_SAYFA)
    donemler = {}
    for h, _ in _baglantilar(s):
        d = _donem(h)
        if not d:
            continue
        k = donemler.setdefault(d, {})
        if "tercih-kilavuzu" in h:
            k["kilavuz"] = _tam(h)
        elif "tercih-alinmasi" in h:
            k["tercih"] = _tam(h)
        elif "sayisal-bilgiler" in h:
            k["sonuc"] = _tam(h)
        elif "sonuclari-aciklandi" in h:
            k["sonuc_aciklandi"] = _tam(h)
    return donemler


def _tercih_tarihleri(url):
    try:
        t = _duz_metin(_sayfa(url))
    except Exception:
        return None, None
    m = re.search(r"tercihlerini,?\s*(\d{1,2})\s*(?:([a-zçğıöşüA-ZÇĞİÖŞÜ]+)\s*)?(?:(20\d\d)\s*)?[-–]\s*(\d{1,2})\s+([a-zçğıöşüA-ZÇĞİÖŞÜ]+)\s+(20\d\d)", t, re.I)
    if not m:
        return None, None
    try:
        ay2 = A.AYLAR[A.tr_lower(m.group(5))]
        yil2 = int(m.group(6))
        ay1 = A.AYLAR[A.tr_lower(m.group(2))] if m.group(2) else ay2
        yil1 = int(m.group(3)) if m.group(3) else yil2
        return date(yil1, ay1, int(m.group(1))), date(yil2, ay2, int(m.group(4)))
    except (KeyError, ValueError):
        return None, None


def _alan(satir, *desenler):
    for k, v in satir.items():
        for d in desenler:
            if re.search(d, k, re.I):
                return v
    return ""


def _pdf_tablo(url, onbellek):
    anahtar = "osym_" + re.sub(r"[^A-Za-z0-9]", "_", url)[-120:]
    v = onbellek.al(anahtar)
    if v is None:
        _, satirlar = pdf_tablo.tablo_oku(_indir(url, 120))
        v = satirlar
        onbellek.koy(anahtar, v)
    return v


def _puan(s):
    try:
        return float(s.replace(".", "").replace(",", ".")) if s else None
    except ValueError:
        return None


def topla(onbellek, bugun, ilerleme=lambda s: None):
    sonuc = {"durum": None, "hata": None, "kadrolar": [], "donem": None, "pdfler": {}}
    if not pdf_tablo.kullanilabilir():
        sonuc["hata"] = "PDF okuyucu (PyMuPDF) kurulu olmadığı için ÖSYM tabloları okunamadı."
        return sonuc
    ilerleme("ÖSYM duyuruları kontrol ediliyor...")
    donemler = duyurulari_bul()
    kilavuzlu = sorted((d for d in donemler if "kilavuz" in donemler[d]), reverse=True)
    if not kilavuzlu:
        sonuc["hata"] = "ÖSYM sayfasında tercih kılavuzu duyurusu bulunamadı."
        return sonuc
    d = kilavuzlu[0]
    bilgi = donemler[d]
    sonuc["donem"] = f"KPSS-{d[0]}/{d[1]}"
    sonuc["kilavuz_link"] = bilgi["kilavuz"]

    bas, bit = _tercih_tarihleri(bilgi["tercih"]) if bilgi.get("tercih") else (None, None)
    sonuc["tercih_baslangic"] = bas.isoformat() if bas else None
    sonuc["tercih_bitis"] = bit.isoformat() if bit else None
    if "sonuc" in bilgi or "sonuc_aciklandi" in bilgi or (bit and bit < bugun):
        sonuc["durum"] = "kapandi"
    elif bas and bas > bugun:
        sonuc["durum"] = "yakinda"
    else:
        sonuc["durum"] = "acik"

    # kılavuz tabloları
    ilerleme(f"ÖSYM {sonuc['donem']} tercih kılavuzu okunuyor...")
    kilavuz_html = _sayfa(bilgi["kilavuz"])
    linkler = [(h, t) for h, t in _baglantilar(kilavuz_html) if h.lower().endswith(".pdf")]

    # yerleşme puanları: bu dönemin sonuçları, yoksa bir önceki dönemin sonuçları (fikir vermesi için)
    puanlar, puan_donemi = {}, None
    sonuclu = sorted((x for x in donemler if "sonuc" in donemler[x] and x <= d), reverse=True)
    puan_linkleri = []
    if sonuclu:
        puan_donemi = sonuclu[0]
        try:
            puan_linkleri = [(h, t) for h, t in _baglantilar(_sayfa(donemler[puan_donemi]["sonuc"]))
                             if h.lower().endswith(".pdf") and "küçük" in A.tr_lower(t)]
        except Exception:
            puan_linkleri = []

    # Özel koşullar (6xxx/7xxx kodları: cinsiyet, ehliyet, sertifika vb.) tüm seviyeler için ortak
    ozel_sozluk = {}
    ozel_url = next((h for h, t in linkler if re.search(r"Özel Koşul", t, re.I)), None)
    if ozel_url:
        try:
            ozel_sozluk = _nitelikler(ozel_url, onbellek)
        except Exception:
            ozel_sozluk = {}

    for seviye, ayar in SEVIYELER.items():
        tablo_url = next((h for h, t in linkler if re.search(ayar["tablo"], t, re.I)), None)
        if not tablo_url:
            continue
        sonuc["pdfler"][seviye] = tablo_url
        ilerleme(f"ÖSYM {sonuc['donem']} kadro tablosu okunuyor ({seviye})...")
        try:
            satirlar = _pdf_tablo(tablo_url, onbellek)
        except Exception as e:
            sonuc["hata"] = f"ÖSYM tablosu okunamadı: {e}"
            continue

        puan_url = next((h for h, t in puan_linkleri if re.search(ayar["sonuc"], t, re.I)), None)
        seviye_puanlari = {}
        if puan_url:
            try:
                for p in _pdf_tablo(puan_url, onbellek):
                    kod = _alan(p, r"kodu")
                    ad = _alan(p, r"program ad")
                    parca = [A.bosluk(x) for x in ad.split("/")]
                    kayit = {"en_kucuk": _puan(_alan(p, r"küçük")), "en_buyuk": _puan(_alan(p, r"büyük")),
                             "yerlesen": _alan(p, r"yerleşen"), "bos": _alan(p, r"boş")}
                    seviye_puanlari[("kod", kod)] = kayit
                    if len(parca) >= 2:
                        seviye_puanlari[("ad", parca[0], A.tr_upper(parca[1]), A.tr_upper(_alan(p, r"ünvan")))] = kayit
            except Exception:
                pass
        puanlar[seviye] = seviye_puanlari

        nit_url = next((h for h, t in linkler if re.search(ayar["nitelik"], t, re.I)), None)
        nit_sozluk = {}
        if nit_url:
            try:
                nit_sozluk = _nitelikler(nit_url, onbellek)
            except Exception:
                nit_sozluk = {}
        nit_sozluk = {**ozel_sozluk, **nit_sozluk}

        ayni_donem = puan_donemi == d
        for s in satirlar:
            kod = _alan(s, r"ÖSYM KODU|^KOD")
            if not re.fullmatch(r"\d{9}", kod or ""):
                continue
            adet = A.sayi(_alan(s, r"ADET"))
            kurum = _alan(s, r"KURUM")
            unvan = _alan(s, r"ÜNVAN")
            il = A.tr_upper(_alan(s, r"(^|\s)İL$"))
            ilce = _alan(s, r"İLÇE")
            nitelikler = [v for k, v in s.items() if re.search(r"Nit\d", k) and re.fullmatch(r"\d{3,5}", v or "")]
            if ayni_donem:
                yp = seviye_puanlari.get(("kod", kod))
            else:
                yp = seviye_puanlari.get(("ad", kurum, il, A.tr_upper(unvan)))
            sonuc["kadrolar"].append({
                "kod": kod, "seviye": seviye, "puan_turu": ayar["puan"],
                "kurum": kurum, "unvan": unvan, "il": il or None, "ilce": ilce,
                "istihdam": _alan(s, r"İSTİHDAM"), "adet": adet,
                "nitelikler": nitelikler,
                "nitelik_metinleri": [f"{n}: {nit_sozluk[n]}" if n in nit_sozluk else f"{n}: (açıklama için ÖSYM kılavuzuna bakın)"
                                      for n in nitelikler],
                # ÖSYM'de "herhangi bir alan/bölümden mezun olmak" kodları: 2001 (lise), 3001 (önlisans), 4001 (lisans)
                "herhangi_bolum": any(n in ("2001", "3001", "4001") for n in nitelikler),
                "taban": yp["en_kucuk"] if yp else None,
                "tavan": yp["en_buyuk"] if yp else None,
                "bos_kaldi": (yp or {}).get("bos") not in (None, "", "0"),
                "taban_ayni_donem": bool(yp) and ayni_donem,
            })

    if puan_donemi:
        sonuc["puan_donemi"] = f"KPSS-{puan_donemi[0]}/{puan_donemi[1]}"
    # aynı kod iki kez gelirse (sayfa sonu tekrarı) tek say
    gorulen, tekil = set(), []
    for k in sonuc["kadrolar"]:
        if k["kod"] in gorulen:
            continue
        gorulen.add(k["kod"])
        tekil.append(k)
    sonuc["kadrolar"] = tekil
    return sonuc
