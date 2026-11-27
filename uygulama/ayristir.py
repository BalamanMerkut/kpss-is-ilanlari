"""İlan metinlerinden pozisyon / kişi sayısı / puan türü / son başvuru tarihi çıkarma."""
import html
import re
from datetime import date, datetime, timedelta
from html.parser import HTMLParser

ILLER = [
    "ADANA", "ADIYAMAN", "AFYONKARAHİSAR", "AĞRI", "AKSARAY", "AMASYA", "ANKARA", "ANTALYA",
    "ARDAHAN", "ARTVİN", "AYDIN", "BALIKESİR", "BARTIN", "BATMAN", "BAYBURT", "BİLECİK", "BİNGÖL",
    "BİTLİS", "BOLU", "BURDUR", "BURSA", "ÇANAKKALE", "ÇANKIRI", "ÇORUM", "DENİZLİ", "DİYARBAKIR",
    "DÜZCE", "EDİRNE", "ELAZIĞ", "ERZİNCAN", "ERZURUM", "ESKİŞEHİR", "GAZİANTEP", "GİRESUN",
    "GÜMÜŞHANE", "HAKKARİ", "HATAY", "IĞDIR", "ISPARTA", "İSTANBUL", "İZMİR", "KAHRAMANMARAŞ",
    "KARABÜK", "KARAMAN", "KARS", "KASTAMONU", "KAYSERİ", "KIRIKKALE", "KIRKLARELİ", "KIRŞEHİR",
    "KİLİS", "KOCAELİ", "KONYA", "KÜTAHYA", "MALATYA", "MANİSA", "MARDİN", "MERSİN", "MUĞLA", "MUŞ",
    "NEVŞEHİR", "NİĞDE", "ORDU", "OSMANİYE", "RİZE", "SAKARYA", "SAMSUN", "SİİRT", "SİNOP", "SİVAS",
    "ŞANLIURFA", "ŞIRNAK", "TEKİRDAĞ", "TOKAT", "TRABZON", "TUNCELİ", "UŞAK", "VAN", "YALOVA",
    "YOZGAT", "ZONGULDAK",
]

AYLAR = {"ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6, "temmuz": 7,
         "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12}


def tr_upper(s):
    return (s or "").replace("i", "İ").replace("ı", "I").upper()


def tr_lower(s):
    return (s or "").replace("İ", "i").replace("I", "ı").lower()


def bosluk(s):
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


# ---------------------------------------------------------------- HTML -> tablo + düz metin
class _Ayristirici(HTMLParser):
    BLOK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "table"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tablolar = []
        self._yigin = []  # her tablo: {"satirlar": [...], "bekleyen": {sutun: [kalan, metin]}}
        self._hucre = None
        self._hucre_ozellik = None
        self.metin = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self._yigin.append({"satirlar": []})
        elif tag == "tr" and self._yigin:
            self._yigin[-1]["satirlar"].append([])
        elif tag in ("td", "th") and self._yigin:
            if not self._yigin[-1]["satirlar"]:
                self._yigin[-1]["satirlar"].append([])
            self._hucre = []
            try:
                rs = int(a.get("rowspan") or 1)
            except ValueError:
                rs = 1
            try:
                cs = int(a.get("colspan") or 1)
            except ValueError:
                cs = 1
            self._hucre_ozellik = (max(1, min(rs, 200)), max(1, min(cs, 30)))
        if tag in self.BLOK:
            if self._hucre is not None:
                self._hucre.append(" ")
            self.metin.append("\n")
        if tag in ("td", "th"):
            self.metin.append(" | ")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._hucre is not None and self._yigin:
            satir = self._yigin[-1]["satirlar"][-1]
            satir.append((bosluk("".join(self._hucre)), *self._hucre_ozellik))
            self._hucre = None
        elif tag == "table" and self._yigin:
            t = self._yigin.pop()
            self.tablolar.append(_izgara(t["satirlar"]))
        if tag in self.BLOK:
            self.metin.append("\n")

    def handle_data(self, data):
        if self._hucre is not None:
            self._hucre.append(data)
        self.metin.append(data)


def _izgara(satirlar):
    """rowspan / colspan'ı açarak düz bir ızgara üretir."""
    izgara = []
    bekleyen = {}  # sütun -> [kalan_satir, metin]
    for satir in satirlar:
        cikti = []
        sutun = 0
        hucreler = list(satir)
        while hucreler or any(k >= sutun for k in bekleyen):
            if sutun in bekleyen:
                kalan, metin = bekleyen[sutun]
                cikti.append(metin)
                if kalan <= 1:
                    del bekleyen[sutun]
                else:
                    bekleyen[sutun][0] = kalan - 1
                sutun += 1
                continue
            if not hucreler:
                if not any(k > sutun for k in bekleyen):
                    break
                cikti.append("")
                sutun += 1
                continue
            metin, rs, cs = hucreler.pop(0)
            for _ in range(cs):
                cikti.append(metin)
                if rs > 1:
                    bekleyen[sutun] = [rs - 1, metin]
                sutun += 1
        if any(c for c in cikti):
            izgara.append(cikti)
    return izgara


def html_coz(icerik):
    p = _Ayristirici()
    try:
        p.feed(icerik or "")
        p.close()
    except Exception:
        pass
    metin = "".join(p.metin)
    metin = re.sub(r"[ \t\xa0]+", " ", metin)
    metin = re.sub(r"\n\s*\n+", "\n\n", metin).strip()
    return p.tablolar, metin


def bbcode_temizle(s):
    s = re.sub(r"\[/?[a-zA-Z]+(=[^\]]*)?\]", "", s or "")
    return html.unescape(s).strip()


# ---------------------------------------------------------------- puan türü / seviye
PT_RE = re.compile(r"(?<![A-Za-z0-9])(?:KPSS\s*[-(]?\s*)?P\s?0?(\d{1,2})(?![0-9])", re.I)


def puan_turleri(metin):
    """Metinde geçen KPSS puan türleri (P3, P93, P94, P1..P48)."""
    bulunan = []
    for m in PT_RE.finditer(metin or ""):
        n = int(m.group(1))
        onceki = (metin[max(0, m.start() - 12):m.start()]).upper()
        # 'P' tek başına geçen başka şeyleri ayıkla: yalnızca KPSS bağlamında ya da P3/P93/P94
        if n in (3, 93, 94) or "KPSS" in m.group(0).upper() or "PUAN" in onceki or "KPSS" in onceki:
            k = f"P{n}"
            if k not in bulunan:
                bulunan.append(k)
    return bulunan


def seviye_puanturunden(pt):
    if pt == "P94":
        return "lise"
    if pt == "P93":
        return "onlisans"
    if pt and pt.startswith("P"):
        return "lisans"
    return None


def seviye_metinden(metin):
    t = tr_lower(metin)
    s = []
    if re.search(r"orta\s?öğretim|ortaöğretim|\blise\b|liseden|lise mezun|meslek lisesi", t):
        s.append("lise")
    if re.search(r"ön\s?lisans|önlisans|onlisans", t):
        s.append("onlisans")
    if re.search(r"(?<!ön)(?<!ön )(?<!on)\blisans\b|fakülte|yüksekokul|mühendis", t) and not re.search(r"yüksek lisans", t):
        s.append("lisans")
    elif re.search(r"(?<!ön)(?<!ön )\blisans (programından|mezun)", t):
        s.append("lisans")
    return s


def asgari_puan(metin):
    t = tr_lower(metin)
    m = re.search(r"(?:en az|asgari|taban|en düşük)[^0-9]{0,40}?(\d{2}(?:[.,]\d+)?)\s*(?:\(|puan|ve)", t)
    if not m:
        m = re.search(r"(\d{2}(?:[.,]\d+)?)\s*(?:\([a-zçğıöşü\s-]+\)\s*)?puan(?:dan)?\s*(?:ve üzeri|veya üzeri|almış|alan)", t)
    if m:
        v = float(m.group(1).replace(",", "."))
        if 40 <= v <= 100:
            return v
    return None


def sayi(s):
    s = bosluk(s)
    m = re.match(r"^\(?\s*(\d{1,5})\s*\)?(?:\s*\(?[a-zçğıöşüA-ZÇĞİÖŞÜ ]*\)?)?\s*(?:adet|kişi|kisi)?\.?$", s, re.I)
    if m:
        v = int(m.group(1))
        return v if 0 < v < 100000 else None
    return None


def il_bul(metin):
    u = tr_upper(metin)
    for il in sorted(ILLER, key=len, reverse=True):
        if re.search(r"(?<![A-ZÇĞİÖŞÜ])" + re.escape(il) + r"(?![A-ZÇĞİÖŞÜ])", u):
            return il
    return None


# ---------------------------------------------------------------- tablodan pozisyon çıkarma
BASLIK_UNVAN = re.compile(r"unvan|ünvan|pozisyon(?!.*sayı)|kadro\s*(adı|unvanı|ünvanı)|talep edilen|meslek|branş|görev\s*(unvanı|adı)|kadro$|^kadro\b", re.I)
BASLIK_SAYI = re.compile(r"sayı|sayısı|adet|adedi|kontenjan|kişi", re.I)
BASLIK_SAYI_HARIC = re.compile(r"çağrıl|cagril|aday sayısı|sıra|telefon|derece", re.I)
BASLIK_PT = re.compile(r"puan\s*tür|kpss\s*puan|puan türü|puan turu", re.I)
BASLIK_TABAN = re.compile(r"(asgari|taban|en az|en düşük|minimum).*puan|puan.*(asgari|taban|en az)", re.I)
BASLIK_OGRENIM = re.compile(r"öğrenim|mezuniyet|eğitim|nitelik|şart|tahsil", re.I)
BASLIK_YER = re.compile(r"görev\s*yeri|il\s*/\s*ilçe|^il$|ilçe|birim|çalışacağı|istihdam yeri|atama yeri|yer", re.I)


def _baslik_bul(tablo):
    en_iyi = None
    for i, satir in enumerate(tablo[:5]):
        unvan = sayi_s = pt = taban = ogr = yer = None
        for j, h in enumerate(satir):
            hl = tr_lower(h)
            if len(hl) > 90:
                continue
            if BASLIK_TABAN.search(hl) and taban is None:
                taban = j
            elif BASLIK_PT.search(hl) and pt is None:
                pt = j
            elif BASLIK_SAYI.search(hl) and not BASLIK_SAYI_HARIC.search(hl) and sayi_s is None:
                sayi_s = j
            elif BASLIK_UNVAN.search(hl) and unvan is None:
                unvan = j
            elif BASLIK_YER.search(hl) and yer is None and not BASLIK_OGRENIM.search(hl):
                yer = j
            elif BASLIK_OGRENIM.search(hl) and ogr is None:
                ogr = j
        if unvan is not None and sayi_s is not None and unvan != sayi_s:
            puan = 2 + (pt is not None) + (taban is not None)
            if not en_iyi or puan > en_iyi[0]:
                en_iyi = (puan, i, dict(unvan=unvan, sayi=sayi_s, pt=pt, taban=taban, ogr=ogr, yer=yer))
    return en_iyi


def tablolardan_pozisyonlar(tablolar):
    sonuc = []
    for tablo in tablolar:
        b = _baslik_bul(tablo)
        if not b:
            continue
        _, bi, s = b
        kullanilan = {v for k, v in s.items() if v is not None and k != "ogr"}
        sart_sutunlari = [j for j, h in enumerate(tablo[bi])
                          if j not in kullanilan and len(h) < 90
                          and re.search(r"öğrenim|mezuniyet|niteli[kğ]|şart|tahsil|aranan|açıklama|özel|cinsiyet", tr_lower(h))]
        for satir in tablo[bi + 1:]:
            def h(k):
                j = s.get(k)
                return satir[j] if j is not None and j < len(satir) else ""
            unvan = bosluk(h("unvan"))
            adet = sayi(h("sayi"))
            if not unvan or adet is None:
                continue
            if re.match(r"^(genel\s*)?toplam", tr_lower(unvan)):
                continue
            satir_metni = " ".join(satir)
            pts = puan_turleri(h("pt")) or puan_turleri(satir_metni)
            taban = None
            if s.get("taban") is not None:
                m = re.search(r"(\d{2}(?:[.,]\d+)?)", h("taban"))
                if m:
                    taban = float(m.group(1).replace(",", "."))
            if taban is None:
                taban = asgari_puan(satir_metni)
            yer = bosluk(h("yer"))
            nitelik_parca = []
            for j in sart_sutunlari:
                hucre = bosluk(satir[j]) if j < len(satir) else ""
                if hucre and hucre not in nitelik_parca and hucre not in ("-", "—"):
                    nitelik_parca.append(hucre)
            sonuc.append({
                "nitelik": " - ".join(nitelik_parca)[:800],
                "unvan": unvan[:160],
                "adet": adet,
                "puan_turleri": pts,
                "seviye": [x for x in (seviye_puanturunden(p) for p in pts) if x] or seviye_metinden(h("ogr") or satir_metni),
                "asgari_puan": taban,
                "yer": yer[:120] if yer and not sayi(yer) else "",
                "il": il_bul(yer) if yer else None,
            })
    return sonuc


# ---------------------------------------------------------------- şartlar (kısa liste)
def _kisalt(s, n=160):
    s = bosluk(re.sub(r"^[\s\-–•*|)(a-zçğıöşü0-9]{0,4}[)\-.]\s*", "", bosluk(s)))
    s = s.strip(" ,;:|")
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def _cumleler(metin):
    for c in re.split(r"(?<=[.;])\s+|\n|(?<=,)\s+(?=[a-zçğıöşü]\)\s)", metin or ""):
        c = bosluk(c)
        if 8 < len(c) < 400:
            yield c


# belge listesi, sınava giriş evrakı gibi "şart olmayan" cümleler
_SART_DEGIL = re.compile(r"fotokopi|suret|onaylı örne|yanlarında|ibraz|yükle|aslı|tasdik|fotoğraf", re.I)


def ilan_sartlari(metin):
    """İlan metninden öne çıkan şartları kısa, okunur bir liste olarak çıkarır.

    Yorum yapmaz: bulunan ifadeyi kısaltıp gösterir. Bulamadığını göstermez.
    """
    t = metin or ""
    tl = tr_lower(t)
    liste = []

    # Yaş üst sınırı (alt sınır "18 yaşını tamamlamış" genel şarttır, gösterilmez)
    yaslar = []
    for c in _cumleler(t):
        cl = tr_lower(c)
        if _SART_DEGIL.search(cl):
            continue
        m = re.search(r"(\d{2})\s*(?:\([^)]{0,20}\)\s*)?yaş(?:ını|ından)\s*(doldurmamış|gün almamış|büyük olmamak)", cl)
        if m and 18 < int(m.group(1)) < 70:
            ifade = f"{m.group(1)} yaşını doldurmamış olmak" if m.group(2) == "doldurmamış" else f"{m.group(1)} yaşından gün almamış olmak"
            if ifade not in yaslar:
                yaslar.append(ifade)
    if yaslar:
        liste.append("Yaş: " + " / ".join(yaslar[:2]))

    # Ehliyet
    siniflar = []
    for c in _cumleler(t):
        cl = tr_lower(c)
        if _SART_DEGIL.search(cl) or "sürücü belge" not in cl:
            continue
        for m in re.finditer(r"\(?\b([a-e]\d?e?)\)?\s*sınıfı\s*sürücü belge", cl):
            s = m.group(1).upper()
            if s not in siniflar:
                siniflar.append(s)
    if siniflar:
        liste.append("Ehliyet: " + ", ".join(siniflar[:4]) + " sınıfı sürücü belgesi")

    # Boy / kilo: sayılar net okunabiliyorsa kısaca yaz, okunamıyorsa sadece "şart var" de
    for c in _cumleler(t):
        cl = tr_lower(c)
        if not (re.search(r"\bboy(u|unda|da|uzunluğu)?\b", cl) and re.search(r"kilo|\bkg\b", cl)):
            continue
        m = re.search(r"erkeklerde en az ([\d.,]+)\s*(metre|m\b|cm)[^,;]*?[,;]?\s*kadınlarda en az ([\d.,]+)\s*(metre|m\b|cm)", cl)
        if m:
            b1 = m.group(1).replace(".", ",") + (" m" if m.group(2) != "cm" else " cm")
            b2 = m.group(3).replace(".", ",") + (" m" if m.group(4) != "cm" else " cm")
            liste.append(f"Boy: erkek en az {b1}, kadın en az {b2} (kilo şartı da var)")
        else:
            m = re.search(r"en az (\d{3})\s*cm", cl)
            liste.append(f"Boy: en az {m.group(1)} cm (kilo şartı da var)" if m else "Boy-kilo şartı var (ayrıntı ilanda)")
        break

    # Askerlik (erkek adaylar)
    if re.search(r"askerlik", tl) and re.search(r"muaf|yapmış|tecil|ertelen", tl):
        liste.append("Erkekler için: askerliğini yapmış, muaf ya da ertelenmiş olmak")

    # Güvenlik görevlisi kimlik kartı vb. özel belge
    for c in _cumleler(t):
        cl = tr_lower(c)
        if _SART_DEGIL.search(cl):
            continue
        if re.search(r"özel güvenlik görevlisi kimlik kart|silahlı .*kimlik kart", cl) and re.search(r"sahip olmak|olmak", cl):
            liste.append("Belge: " + _kisalt(c, 150))
            break

    # Seçim şekli
    secim = []
    for anahtar, ad in ((r"noter (huzurunda )?kura", "noter kurası"), (r"yazılı sınav", "yazılı sınav"),
                        (r"sözlü sınav", "sözlü sınav"), (r"uygulamalı sınav|uygulama sınavı", "uygulamalı sınav")):
        if re.search(anahtar, tl):
            secim.append(ad)
    if secim:
        liste.append("Seçim: " + ", ".join(secim))
    elif re.search(r"kpss[^.]{0,60}(puan|sıra)[^.]{0,60}(esas|göre|sırala)", tl):
        liste.append("Seçim: KPSS puan sırasına göre")

    # Başvuru şekli: yalnızca "başvuru" geçen ve olumsuz olmayan cümlelerden
    # ("e-Devlet'ten alınan belge" ya da "şahsen başvuru kabul edilmez" gibi cümleler sayılmaz)
    # İtiraz dilekçesi, e-Devlet şifre zarfı, tebligat gibi başvuru dışı cümleler ve olumsuz ifadeler sayılmaz.
    haric = r"kabul edilme|yapılamaz|alınmay|geçersiz|sorumlu|itiraz|tebligat|tebliğ|şifre|zarf|sonuç|faks|e-?mail|e-posta"
    internet = cikti_teslim = False
    elden = posta = False
    for c in _cumleler(t):
        cl = tr_lower(c)
        if not re.search(r"başvuru|müracaat", cl):
            continue
        if re.search(r"çıktı", cl) and re.search(r"şahsen|elden|posta|teslim", cl) and not re.search(haric, cl):
            cikti_teslim = True
        if re.search(haric, cl):
            continue
        if (re.search(r"e-devlet|e‑devlet|kariyer kapısı|turkiye\.gov\.tr|isealim|elektronik ortam|internet|web sitesi|online", cl)
                and re.search(r"üzerinden|aracılığıyla|yapıl|yapabil|bulunabil|alınacak", cl)):
            internet = True
        if re.search(r"\bşahsen|\belden\b|bizzat", cl):
            elden = True
        if re.search(r"posta (yoluyla|ile)|iadeli taahhütlü|kargo", cl):
            posta = True
    if internet:
        yazi = "internetten"  # hangi site olduğu tahmin edilmez; adres "Başvuru sayfası" düğmesinde / ilanda
        if cikti_teslim:
            yazi += " — başvuru çıktısı ayrıca elden ya da posta ile teslim edilecek"
        liste.append("Başvuru: " + yazi)
    elif elden or posta:
        liste.append("Başvuru: " + " veya ".join(x for x, var in (("şahsen kuruma giderek", elden), ("posta ile", posta)) if var))
    return liste


def kadro_nitelikleri(metin):
    """Bir kadronun tablo/özel şart metnini kısa maddelere böler (bölüm, cinsiyet vb.)."""
    if not metin:
        return []
    parcalar = re.split(r"\s*(?:\n|(?<=[.;])\s+|\s-\s|^-|•)\s*", metin)
    out = []
    for p in parcalar:
        p = _kisalt(p, 170)
        pl = tr_lower(p)
        if len(p) < 6 or _SART_DEGIL.search(pl) or p in out:
            continue
        if re.fullmatch(r"[\d\s/.,-]+", p):
            continue
        # tek başına anlamsız kalan kısa değerlere etiket ekle
        if re.fullmatch(r"(erkek|kadın)(\s*/\s*(erkek|kadın))?", pl.strip(" .")):
            p = "Cinsiyet: " + p
        elif re.fullmatch(r"(ön ?lisans|lisans|ortaöğretim|lise|yüksek lisans|ilköğretim|ortaokul)( \(.*\))?", pl.strip(" .")):
            p = "Mezuniyet: " + (p[:1] + tr_lower(p[1:]) if p.isupper() else p)
        if p in out:
            continue
        out.append(p)
    return out[:6]


# ---------------------------------------------------------------- son başvuru tarihi
TARIH_RE = re.compile(
    r"(\d{1,2})\s*[./]\s*(\d{1,2})\s*[./]\s*(20\d{2})|(\d{1,2})\s+(ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık)\s+(20\d{2})",
    re.I)


def _tarihler(s):
    out = []
    for m in TARIH_RE.finditer(tr_lower(s)):
        try:
            if m.group(1):
                out.append(date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
            else:
                out.append(date(int(m.group(6)), AYLAR[m.group(5)], int(m.group(4))))
        except ValueError:
            pass
    return out


def son_basvuru(metin, yayim):
    """Metinden son başvuru tarihini tahmin eder. (tarih, kesin_mi) döner."""
    t = tr_lower(metin)
    cumleler = re.split(r"(?<=[.!?:;])\s+|\n", t)
    adaylar = []
    for c in cumleler:
        if "başvuru" in c or "müracaat" in c:
            for d in _tarihler(c):
                if yayim is None or d >= yayim - timedelta(days=2):
                    adaylar.append(d)
    if adaylar:
        return max(adaylar), True
    if yayim:
        m = re.search(r"(?:yayım|yayın)\w*\s+(?:tarihi|günü)\w*\s*(?:den|ten)?\s*(?:itibaren|başlayarak|sonra)[^.]{0,40}?(\d{1,2})\s*(?:\([a-zçğıöşü\s]+\)\s*)?(iş\s+)?gün", t)
        if m:
            n = int(m.group(1))
            if m.group(2):  # iş günü: hafta sonlarını atla
                d, kalan = yayim, n
                while kalan > 0:
                    d += timedelta(days=1)
                    if d.weekday() < 5:
                        kalan -= 1
                return d, False
            return yayim + timedelta(days=n - 1), False
    return None, False


def iso_tarih(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None
