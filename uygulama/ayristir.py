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
                "nitelik": " - ".join(nitelik_parca)[:4000],
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


def _uzunsa_kisalt(s, n=230):
    """Uzun maddeyi kelime ortasından değil, virgül/noktalı virgül gibi doğal bir yerden kısaltır."""
    s = bosluk(s).strip(" ,;:|")
    if len(s) <= n:
        return s
    kes = max(s.rfind(", ", 0, n), s.rfind("; ", 0, n))
    if kes < n * 0.5:
        kes = s.rfind(" ", 0, n)
    return s[:kes].rstrip(" ,;:") + "… (tamamı ilanda)"


def _maddele(metin):
    """Hücre metnini maddelere ayırır: a) b) c) / 1) 2) / - • işaretleri, satır sonları ve cümleler."""
    t = (metin or "").replace("\r", "")
    # örnek ve "sisteme yükleyin" türü açıklama parantezleri şart değildir
    t = re.sub(r"\((?:\s*örne[ğk]|\s*ör\.)[^()]*\)", " ", t, flags=re.I)
    t = re.sub(r"\([^()]*(?:yüklen|ibraz|beyan form)[^()]*\)", " ", t, flags=re.I)
    t = re.sub(r"\s-\s+(?=[-•A-ZÇĞİÖŞÜ])", "\n", t)  # tablo sütunlarını birleştiren " - " ayıracı
    # noktası unutulmuş şartlar: "...mezun olmak En az iki..." → ayrı madde
    # ("olmak, En az..." gibi virgülle bitişik iki şart da ayrılır; bölüm listeleri fiil ile bitmediği için bölünmez)
    for fiil in ("olmak", "olmamak", "belgelemek", "bulunmamak"):
        t = re.sub(r"(?<=\b" + fiil + r")[,]?\s+(?=[A-ZÇĞİÖŞÜ][a-zçğıöşü])", "\n", t)
    parcalar = re.split(r"\n+|(?:^|(?<=[\s.;,:]))(?:[a-zçğıöşü]|\d{1,2})\)\s*|(?:^|(?<=[.;:]))\s*[-•]\s*(?=\S)", t)
    maddeler = []
    for p in parcalar:
        if not p or not p.strip():
            continue
        # cümleye böl: yalnızca noktadan sonra BÜYÜK harf/rakam geliyorsa ("cm. 'den" bölünmez)
        for c in re.split(r"(?<=[.;])\s+(?=[A-ZÇĞİÖŞÜ0-9(])", p):
            c = bosluk(c).lstrip("-–•* ").strip()
            if not c:
                continue
            # küçük harf ya da noktalama ile başlayan parça önceki maddenin devamıdır
            if maddeler and re.match(r"^[a-zçğıöşü'’\",)]", c):
                maddeler[-1] += " " + c
            else:
                maddeler.append(c)
    return maddeler


def _ozetle(m):
    """Çok sık geçen uzun kalıpları kısa ve aslına sadık bir cümleye çevirir; tanımazsa None."""
    ml = tr_lower(m)
    if re.search(r"yaşını|yaşından", ml):
        p_ = r"\s*(?:\([^)]{0,25}\)\s*)?"  # "35 (otuz beş) yaşından" gibi yazıyla tekrar
        alt = re.search(r"(\d{2})" + p_ + r"yaşını (doldurmuş|tamamlamış)", ml)
        ust = re.search(r"(\d{2})" + p_ + r"yaşını (bitirmemiş|doldurmamış)|(\d{2})" + p_ + r"yaşından gün almamış", ml)
        if ust:
            parca = []
            if alt:
                parca.append(f"{alt.group(1)} yaşını {alt.group(2)}")
            parca.append(f"{ust.group(1)} yaşını {ust.group(2)}" if ust.group(1) else f"{ust.group(3)} yaşından gün almamış")
            dogum = re.search(r"(\d{1,2} \w+ \d{4}) ve sonrası doğumlu", m)
            return "Yaş: " + ", ".join(parca) + " olmak" + (f" ({dogum.group(1)} ve sonrası doğumlular)" if dogum else "")
    if re.search(r"\byds|e-yds|yökdil|yabancı dil", ml) and re.search(r"seviye|puan", ml) and not re.search(r"aranmaz\.?$", ml.strip()):
        diller = [ad for ad in ("İngilizce", "Almanca", "Fransızca", "Arapça", "Rusça") if tr_lower(ad) in ml]
        sev = re.search(r"en az \(?([a-e])\)?\s*seviye", ml)
        pn = re.search(r"en az (\d{2,3})\s*(?:\([^)]{0,15}\)\s*)?puan", ml)
        if sev or pn:
            esik = f"en az ({sev.group(1).upper()}) seviyesi" if sev else f"en az {pn.group(1)} puan"
            return ("Yabancı dil: YDS/e-YDS'den " + esik
                    + (f" ({', '.join(diller)})" if diller else "")
                    + (" ya da ÖSYM'nin denk saydığı belge" if "denk" in ml else ""))
    if re.search(r"\bboy", ml) and re.search(r"kilo", ml) and re.search(r"fark", ml):
        return "Boy-kilo oranı şartı var (ayrıntı ilanda)"
    m_boy = re.search(r"(\d{3})\s*cm[.\s'’]*(?:den|dan)?[^;]{0,15}kısa boylu olmamak", ml)
    if m_boy:
        return f"Boy: en az {m_boy.group(1)} cm"
    if re.search(r"sağlık kurulu raporu|akıl hastalığı|bedensel özür|engel olabilecek[^.]{0,40}hastalı", ml):
        return ("Sağlık: görevine engel bir hastalığı ya da engeli olmamak"
                + (" (sağlık kurulu raporuyla belgelenecek)" if "sağlık kurulu raporu" in ml else ""))
    if re.search(r"vardiya|hafta ?son|mesai saatleri dışında|gece", ml) and re.search(r"engel|çalışabil", ml):
        turler = [ad for desen, ad in _CALISMA_TURLERI if re.search(desen, ml)]
        return "Çalışma düzeni: " + ", ".join(turler) + " çalışmaya engeli olmamak"
    return None


_CALISMA_TURLERI = ((r"vardiya", "vardiyalı"), (r"mesai saatleri dışında", "mesai dışı"),
                    (r"gece", "gece"), (r"hafta ?son", "hafta sonu"))


def kadro_nitelikleri(metin):
    """Bir kadronun tablo/özel şart metnini kısa maddelere böler (bölüm, cinsiyet vb.)."""
    if not metin:
        return []
    out = []
    for p in _maddele(metin):
        if _SART_DEGIL.search(tr_lower(p)):
            continue
        # önceki maddenin açıklaması olan cümleler ("Ancak…", "Bu şekilde…", tamamı parantez içi bilgi) ayrı şart değildir
        if re.match(r"^(ancak|bu şekilde|bu durumda|örneğin)\b", tr_lower(p)) or re.fullmatch(r"\(.*\)\.?", p.strip()):
            continue
        p = _ozetle(p) or _uzunsa_kisalt(p)
        pl = tr_lower(p)
        if len(p) < 6 or p in out:
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
        # aynı türden çalışma düzeni maddelerini tek satırda birleştir
        onceki = next((i for i, x in enumerate(out) if x.startswith("Çalışma düzeni: ")), None)
        if p.startswith("Çalışma düzeni: ") and onceki is not None:
            birlesik = " ".join([out[onceki], p])
            turler = [ad for _, ad in _CALISMA_TURLERI if ad in birlesik]
            out[onceki] = "Çalışma düzeni: " + ", ".join(turler) + " çalışmaya engeli olmamak"
            continue
        out.append(p)
    return out[:10]


_OZEL_BASLANGIC = re.compile(
    r"aşağı(?:daki|da belirtilen) özel (?:şartlar|nitelikler|koşullar)[^:\n]{0,40}:"      # "...aşağıdaki özel şartlar aranır:"
    r"|^[ \t]*(?:[ıivx\d]+[.)-]|[a-zçğıöşü][.)])?[ \t]*(?:başvuru(?:ya ilişkin)? )?özel (?:şartlar|koşullar)\w*[ \t]*:?[ \t]*$",  # "ÖZEL ŞARTLAR" başlığı
    re.M)
_BOLUM_SONU = re.compile(
    r"^[ \t]*(?:[A-ZÇĞİÖŞÜ]|\d{1,2}|[IVX]{1,4})[.)-][ \t]*[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ \t/,]{5,}$"   # "B. BAŞVURU TARİHİ VE ŞEKLİ"
    r"|^[ \t]*[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ \t/,]{7,}:?[ \t]*$"                                   # "İSTENEN BELGELER"
    r"|^[ \t]*(?:\d{1,2}[.)-]\s*)?(?i:başvuru (?:tarihi|şekli|yeri|süresi)|istenen belgeler|sınav(?:ın)? (?:şekli|yeri|tarihi|konuları)|değerlendirme)",
    re.M)  # büyük harf başlık kontrolleri harf duyarlı kalmalı; yalnızca anahtar kelimeler duyarsız


def ozel_sartlar(metin):
    """İlan metnindeki "özel şartlar" bölümünü bulup kısa maddelere çevirir (bulamazsa boş liste).

    Kadro tablosu ilanın içinde olmayan (ayrı ek dosyada yayımlanan) ilanlar için kullanılır.
    Genel şartlar (vatandaşlık, kamu hakları vb.) bu bölümde olmadığı için alınmaz.
    """
    t = metin or ""
    m = _OZEL_BASLANGIC.search(tr_lower(t))
    if not m:
        return []
    bolum = t[m.end(): m.end() + 5000]
    son = _BOLUM_SONU.search(bolum)
    if son:
        bolum = bolum[: son.start()]
    # Bölüm pozisyon pozisyon ayrılmışsa ("1-ARŞİV UZMANI", "2-AVUKAT"…) bu şartlar tek bir satıra
    # yapıştırılmaz: başka pozisyonun şartı yanlışlıkla bu işe aitmiş gibi görünürdü.
    basliklar = set()
    for no, ad in re.findall(r"(?<!\w)(\d{1,2})[ \t]*[-.)][ \t]*([A-ZÇĞİÖŞÜ]{3,}(?:[ \t]+[A-ZÇĞİÖŞÜ()/]{2,})*)(?![a-zçğıöşü])", bolum):
        if ad.split()[0] not in ("KPSS", "YDS", "ÖSYM", "KPSSP3", "ALES"):
            basliklar.add(no)
    if len(basliklar) >= 2:
        return []
    maddeler = []
    for x in kadro_nitelikleri(bolum):
        xl = tr_lower(x)
        # "…de genel şartlara ilave olarak … özel şartlar aranır" gibi açıklama cümleleri madde değildir
        if re.search(r"özel şartlar aranır|şartlara ilave olarak|aşağıdaki (?:özel )?şartlar", xl):
            continue
        # herkes için geçerli genel şartlar (657/48) özel şart değildir
        if re.search(r"türkiye cumhuriyeti vatandaşı|kamu haklarından mahrum|657 sayılı|türk ceza kanunu|kazai rüşt", xl):
            continue
        # başvuru talimatları şart değildir ("…beyan etmesi gerekmektedir", "…tercihte bulunabilecek")
        if "başvur" in xl and not re.search(r"olmak|olmamak|sahip|mezun", xl):
            continue
        # kadro başlıkları: "1 (Bir) Mühendis (…)", "1.SİSTEM YÖNETİCİSİ (3 Katı)"
        if re.match(r"^\d+\s*\([a-zçğıöşü ]+\)\s", xl) or (re.match(r"^\d+[.)]", x) and sum(ch.isupper() for ch in x) > 0.5 * sum(ch.isalpha() for ch in x)):
            continue
        maddeler.append(x)
    return maddeler


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
