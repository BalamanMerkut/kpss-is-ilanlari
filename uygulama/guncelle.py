"""GitHub'daki son sürümü kontrol edip exe'yi kendiliğinden günceller.

Güvenlik:
  - Yalnızca bu reponun GitHub "Releases" sayfasındaki exe indirilir.
  - İndirilen dosyanın SHA-256 parmak izi GitHub'ın bildirdiği değerle karşılaştırılır;
    tutmazsa dosya silinir, güncelleme yapılmaz.
  - Exe açılışta yeni sürüm bulursa kullanıcıya sormadan kurar ve kendini yeniden başlatır.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

SURUM = "1.5"
REPO = "BalamanMerkut/kpss-is-ilanlari"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
SAYFA = f"https://github.com/{REPO}/releases/latest"
EXE_ADI = "KPSS-Is-Ilanlari.exe"
UA = f"KPSS-Ilan-Takip/{SURUM}"
IZINLI_ADRES = re.compile(r"^https://github\.com/" + re.escape(REPO) + r"/releases/download/[^/]+/" + re.escape(EXE_ADI) + r"$")

EXE_MI = getattr(sys, "frozen", False)


def surum_sayi(s):
    return tuple(int(x) for x in re.findall(r"\d+", s or "")[:3]) or (0,)


def kontrol(zaman=15):
    """Yeni sürüm varsa bilgisini, yoksa None döndürür."""
    req = urllib.request.Request(API, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=zaman) as r:
        d = json.loads(r.read().decode("utf-8"))
    if d.get("draft") or d.get("prerelease"):
        return None
    yeni = (d.get("tag_name") or "").lstrip("vV")
    if surum_sayi(yeni) <= surum_sayi(SURUM):
        return None
    varlik = next((a for a in d.get("assets") or [] if a.get("name") == EXE_ADI), None)
    bilgi = {"surum": yeni, "sayfa": d.get("html_url") or SAYFA, "notlar": (d.get("body") or "")[:3000]}
    if varlik and IZINLI_ADRES.match(varlik.get("browser_download_url") or ""):
        ozet = (varlik.get("digest") or "")
        bilgi.update(url=varlik["browser_download_url"], boyut=varlik.get("size"),
                     sha256=ozet.split(":", 1)[1].lower() if ozet.startswith("sha256:") else None)
    return bilgi


def otomatik_kurulabilir_mi(bilgi):
    # Yalnızca Windows exe'si kendini günceller. Mac'te program yeni sürümü haber verir,
    # kullanıcı indirme sayfasından yeni sürümü indirir (Windows exe'si asla Mac'e kurulmaz).
    return bool(EXE_MI and sys.platform == "win32" and bilgi and bilgi.get("url") and bilgi.get("sha256"))


def eski_dosyayi_temizle():
    """Bir önceki güncellemeden kalan .old dosyasını siler."""
    if not EXE_MI:
        return
    eski = sys.executable + ".old"
    for _ in range(10):
        if not os.path.exists(eski):
            return
        try:
            os.remove(eski)
            return
        except OSError:
            time.sleep(1)


def uygula(bilgi, ilerleme=lambda s: None):
    """Yeni exe'yi indirir, doğrular, eskisinin yerine koyar ve yeni sürümü başlatır.

    Başarılı olursa True döner; çağıran taraf ardından kendini kapatmalıdır.
    """
    if not otomatik_kurulabilir_mi(bilgi):
        raise RuntimeError("Bu sürüm otomatik güncellenemiyor.")
    mevcut = sys.executable
    klasor = os.path.dirname(mevcut)
    gecici = os.path.join(klasor, EXE_ADI + ".indiriliyor")
    yeni = os.path.join(klasor, EXE_ADI + ".yeni")

    ilerleme("Yeni sürüm indiriliyor...")
    req = urllib.request.Request(bilgi["url"], headers={"User-Agent": UA})
    h = hashlib.sha256()
    toplam = 0
    try:
        with urllib.request.urlopen(req, timeout=60) as r, open(gecici, "wb") as f:
            while True:
                parca = r.read(1 << 16)
                if not parca:
                    break
                f.write(parca)
                h.update(parca)
                toplam += len(parca)
                if bilgi.get("boyut"):
                    ilerleme(f"Yeni sürüm indiriliyor... %{min(100, toplam * 100 // bilgi['boyut'])}")
        if h.hexdigest() != bilgi["sha256"] or (bilgi.get("boyut") and toplam != bilgi["boyut"]):
            raise RuntimeError("İndirilen dosya doğrulanamadı (parmak izi tutmuyor). Güncelleme iptal edildi.")
        with open(gecici, "rb") as f:
            if f.read(2) != b"MZ":
                raise RuntimeError("İndirilen dosya geçerli bir program değil. Güncelleme iptal edildi.")
        os.replace(gecici, yeni)
    except Exception:
        for p in (gecici, yeni):
            try:
                os.remove(p)
            except OSError:
                pass
        raise

    ilerleme("Yeni sürüm kuruluyor...")
    eski = mevcut + ".old"
    try:
        if os.path.exists(eski):
            os.remove(eski)
    except OSError:
        pass
    # Windows çalışan exe'nin üzerine yazmaya izin vermez ama adını değiştirmeye izin verir
    os.replace(mevcut, eski)
    try:
        os.replace(yeni, mevcut)
    except OSError:
        os.replace(eski, mevcut)  # geri al
        raise

    ilerleme("Program yeniden başlatılıyor...")
    ortam = dict(os.environ)
    ortam["PYINSTALLER_RESET_ENVIRONMENT"] = "1"  # yeni exe kendi geçici klasörünü kullansın
    bayrak = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen([mevcut, "--guncelleme-sonrasi"], cwd=klasor, env=ortam, close_fds=True, creationflags=bayrak)
    return True
