"""ÖSYM tercih kılavuzu PDF tablolarını (çizgili tablolar) satır/sütun olarak okur.

PyMuPDF (pymupdf / fitz) gerektirir. Kurulu değilse ÖSYM kadroları yalnızca bağlantı olarak gösterilir.
"""
import re

try:
    import pymupdf
except ImportError:  # eski sürümler
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None


def kullanilabilir():
    return pymupdf is not None


def _cizgiler(sayfa):
    yatay, dikey = [], []
    for d in sayfa.get_drawings():
        for it in d["items"]:
            if it[0] == "re":
                r = it[1]
                if r.width > 150 and r.height < 2.5:
                    yatay.append((r.y0 + r.y1) / 2)
                elif r.height > 150 and r.width < 2.5:
                    dikey.append((r.x0 + r.x1) / 2)
            elif it[0] == "l":
                a, b = it[1], it[2]
                if abs(a.y - b.y) < 1 and abs(a.x - b.x) > 150:
                    yatay.append(a.y)
                elif abs(a.x - b.x) < 1 and abs(a.y - b.y) > 150:
                    dikey.append(a.x)

    def tekil(v, tol=2.0):
        v = sorted(v)
        out = []
        for x in v:
            if not out or x - out[-1] > tol:
                out.append(x)
        return out

    return tekil(yatay), tekil(dikey)


def _sutun_no(x, sinirlar):
    for i in range(len(sinirlar) - 1):
        if sinirlar[i] <= x < sinirlar[i + 1]:
            return i
    return None


def sayfa_satirlari(sayfa, kod_re=re.compile(r"^\d{9}$")):
    """Bir sayfadaki tabloyu (başlıklar, satırlar) olarak döndürür."""
    yatay, dikey = _cizgiler(sayfa)
    kelimeler = sayfa.get_text("words")
    if len(dikey) < 3:
        return None, []
    sol, sag = dikey[0], dikey[-1]
    sinirlar = dikey

    # veri satırları: 9 haneli kodla başlayan satırlar; başlık bunların üstünde
    kod_y = sorted((w[1] + w[3]) / 2 for w in kelimeler if kod_re.match(w[4]) and w[0] < sinirlar[1] + 1)
    if not kod_y:
        return None, []
    ilk_kod = kod_y[0]

    # satır bantları: yatay çizgiler arası
    bantlar = [(yatay[i], yatay[i + 1]) for i in range(len(yatay) - 1) if yatay[i + 1] - yatay[i] > 4]
    if not bantlar:
        return None, []

    # başlık: ilk kod satırından önceki, tablo genişliğindeki kelimeler
    baslik_bant_alt = max((b for b in yatay if b < ilk_kod), default=None)
    basliklar = [[] for _ in range(len(sinirlar) - 1)]
    for w in kelimeler:
        yc = (w[1] + w[3]) / 2
        if baslik_bant_alt and baslik_bant_alt - 45 < yc < baslik_bant_alt:
            j = _sutun_no((w[0] + w[2]) / 2, sinirlar)
            if j is not None:
                basliklar[j].append((w[1], w[0], w[4]))
    basliklar = [" ".join(t for _, _, t in sorted(h)) for h in basliklar]

    satirlar = []
    for ust, alt in bantlar:
        if alt <= ilk_kod - 3:
            continue
        hucreler = [[] for _ in range(len(sinirlar) - 1)]
        for w in kelimeler:
            yc = (w[1] + w[3]) / 2
            if ust <= yc < alt and sol - 1 <= w[0] <= sag:
                j = _sutun_no((w[0] + w[2]) / 2, sinirlar)
                if j is not None:
                    hucreler[j].append((round(w[1], 0), w[0], w[4]))
        metinler = [" ".join(t for _, _, t in sorted(h)) for h in hucreler]
        if any(metinler):
            satirlar.append(metinler)
    return basliklar, satirlar


def nitelik_kodlari(pdf_bayt):
    """ÖSYM nitelik kodları PDF'i → {kod: açıklama}. Her kodun ilk açıklaması alınır."""
    if pymupdf is None:
        raise RuntimeError("PyMuPDF kurulu değil")
    belge = pymupdf.open(stream=pdf_bayt, filetype="pdf")
    satirlar = []
    for sayfa in belge:
        satirlar += [s.strip() for s in sayfa.get_text().splitlines()]
    sozluk = {}
    i = 0
    while i < len(satirlar):
        s = satirlar[i]
        if re.fullmatch(r"\d{4}", s) and i + 1 < len(satirlar):
            ilk = satirlar[i + 1]
            # açıklama cümlesi: küçük harf içerir (alan adları tamamen büyük harf)
            if ilk and not re.fullmatch(r"[\d*]+", ilk) and re.search(r"[a-zçğıöşü]", ilk):
                parca, j = [], i + 1
                while j < len(satirlar) and len(parca) < 12:
                    parca.append(satirlar[j])
                    if satirlar[j].endswith("."):
                        break
                    if j + 1 < len(satirlar) and re.fullmatch(r"\d{1,4}|Kodu|\*", satirlar[j + 1]):
                        break  # sonraki kod / sayfa başlığı başlıyor
                    j += 1
                if s not in sozluk:
                    sozluk[s] = re.sub(r"\s+", " ", " ".join(parca)).strip()
                i = j
        i += 1
    return sozluk


def tablo_oku(pdf_bayt):
    """Tüm sayfaları okur; başlığı ilk sayfadan alır. [{başlık: değer}] döner."""
    if pymupdf is None:
        raise RuntimeError("PyMuPDF kurulu değil")
    belge = pymupdf.open(stream=pdf_bayt, filetype="pdf")
    sonuc = []
    basliklar = None
    for sayfa in belge:
        b, satirlar = sayfa_satirlari(sayfa)
        if b and any(b) and (basliklar is None or len(b) == len(basliklar)):
            basliklar = basliklar or b
        if not basliklar:
            continue
        for s in satirlar:
            if len(s) != len(basliklar):
                continue
            sonuc.append(dict(zip(basliklar, s)))
    return basliklar or [], sonuc
