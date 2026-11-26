"""KPSS İlan Takip – yerel sunucu.

Çift tıklayınca: verileri resmî kaynaklardan günceller, tarayıcıda ekranı açar.
Yalnızca bu bilgisayardan erişilebilir (127.0.0.1).
"""
import json
import os
import socket
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

EXE_MI = getattr(sys, "frozen", False)  # tek dosyalık .exe olarak mı çalışıyor?
# Ekran dosyası: exe içinde paketlenmiş halde (sys._MEIPASS) ya da bu klasörde
KLASOR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KLASOR)
import kaynaklar  # noqa: E402
import osym  # noqa: E402,F401  (exe paketine dahil edilmesi için)
import guncelle  # noqa: E402

if EXE_MI and sys.platform == "darwin":
    # Mac uygulaması: veriler kullanıcının Library/Application Support klasörüne
    VERI_KLASORU = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "KPSS-Ilanlari")
elif EXE_MI:
    # Arkadaşların bilgisayarında: veriler kullanıcının kendi klasörüne
    VERI_KLASORU = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "KPSS-Ilanlari")
else:
    VERI_KLASORU = os.path.join(os.path.dirname(KLASOR), "veri")
VERI_DOSYASI = os.path.join(VERI_KLASORU, "ilanlar.json")
GUNLUK = os.path.join(VERI_KLASORU, "hata_gunlugu.txt")
PORT = int(os.environ.get("KPSS_PORT") or 8765)  # test için başka port verilebilir
ESKI_SAYILIR_SANIYE = 3 * 3600  # 3 saatten eski veri açılışta otomatik yenilenir
BOSTA_KAPANMA_SANIYE = 15 * 60  # ekran kapatıldıktan 15 dk sonra program kendiliğinden kapanır

os.makedirs(VERI_KLASORU, exist_ok=True)

durum = {"calisiyor": False, "mesaj": "", "hata": None}
kilit = threading.Lock()
son_nabiz = [time.time()]
veri_onbellek = {"zaman": 0, "liste": None, "metinler": {}}
surum_durumu = {"yeni": None, "guncelleniyor": False, "mesaj": "", "hata": None}
sunucu_ref = [None]


def surumu_kontrol_et():
    try:
        surum_durumu["yeni"] = guncelle.kontrol()
    except Exception as e:  # internet yoksa sessizce geç
        gunluge_yaz(f"Sürüm kontrolü yapılamadı: {e}")
        return
    # Yeni sürüm varsa sormadan kur (parmak izi doğrulaması guncelle.uygula içinde yapılır)
    if guncelle.otomatik_kurulabilir_mi(surum_durumu["yeni"]):
        guncellemeyi_baslat()


def guncellemeyi_baslat():
    if surum_durumu["guncelleniyor"] or not guncelle.otomatik_kurulabilir_mi(surum_durumu["yeni"]):
        return
    surum_durumu.update(guncelleniyor=True, hata=None, mesaj="Başlatılıyor...")

    def is_parcacigi():
        try:
            guncelle.uygula(surum_durumu["yeni"], lambda s: surum_durumu.__setitem__("mesaj", s))
            time.sleep(1.0)  # son yanıtların gitmesi için
            if sunucu_ref[0]:
                sunucu_ref[0].shutdown()  # yeni sürüm bu portu devralacak
        except Exception as e:
            gunluge_yaz(traceback.format_exc())
            surum_durumu.update(guncelleniyor=False, hata=f"Güncelleme yapılamadı: {e}")

    threading.Thread(target=is_parcacigi, daemon=True).start()


def gunluge_yaz(s):
    try:
        with open(GUNLUK, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + s + "\n")
    except OSError:
        pass


def veriyi_yukle():
    try:
        mt = os.path.getmtime(VERI_DOSYASI)
    except OSError:
        return None
    if veri_onbellek["zaman"] != mt:
        with open(VERI_DOSYASI, encoding="utf-8") as f:
            v = json.load(f)
        metinler = {}
        for ilan in v.get("ilanlar", []):
            metinler[ilan["id"]] = ilan.pop("metin", "")
        veri_onbellek.update(zaman=mt, liste=v, metinler=metinler)
    return veri_onbellek["liste"]


def yenile():
    with kilit:
        if durum["calisiyor"]:
            return
        durum.update(calisiyor=True, mesaj="Başlatılıyor...", hata=None)

    def is_parcacigi():
        try:
            v = kaynaklar.topla(VERI_KLASORU, lambda s: durum.__setitem__("mesaj", s))
            if not v["ilanlar"] and v["hatalar"]:
                raise RuntimeError("; ".join(v["hatalar"]))
            gecici = VERI_DOSYASI + ".tmp"
            with open(gecici, "w", encoding="utf-8") as f:
                json.dump(v, f, ensure_ascii=False)
            os.replace(gecici, VERI_DOSYASI)
            for h in v["hatalar"]:
                gunluge_yaz(h)
            durum["mesaj"] = "Tamamlandı"
        except Exception as e:
            gunluge_yaz(traceback.format_exc())
            durum["hata"] = ("İlanlar güncellenemedi. İnternet bağlantınızı kontrol edip "
                             "'İlanları Yenile' düğmesine tekrar basın. (Ayrıntı: %s)" % e)
        finally:
            durum["calisiyor"] = False

    threading.Thread(target=is_parcacigi, daemon=True).start()


class Isleyici(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _gonder(self, kod, govde, tur="application/json; charset=utf-8"):
        if isinstance(govde, (dict, list)):
            govde = json.dumps(govde, ensure_ascii=False).encode("utf-8")
        elif isinstance(govde, str):
            govde = govde.encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def _yerel_mi(self):
        # Başka sitelerin bu yerel sunucuya istek atmasını engelle
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self._yerel_mi():
            return self._gonder(403, {"hata": "yasak"})
        u = urlparse(self.path)
        son_nabiz[0] = time.time()
        if u.path in ("/", "/index.html"):
            with open(os.path.join(KLASOR, "arayuz.html"), encoding="utf-8") as f:
                return self._gonder(200, f.read(), "text/html; charset=utf-8")
        if u.path == "/api/veri":
            v = veriyi_yukle()
            return self._gonder(200, v or {"ilanlar": [], "guncelleme": None})
        if u.path == "/api/metin":
            veriyi_yukle()
            i = parse_qs(u.query).get("id", [""])[0]
            return self._gonder(200, {"metin": veri_onbellek["metinler"].get(i, "")})
        if u.path == "/api/durum":
            return self._gonder(200, durum)
        if u.path == "/api/nabiz":
            return self._gonder(200, {"ok": True})
        if u.path == "/api/surum":
            return self._gonder(200, dict(surum_durumu, surum=guncelle.SURUM, exe_mi=guncelle.EXE_MI,
                                          otomatik=guncelle.otomatik_kurulabilir_mi(surum_durumu["yeni"]),
                                          sayfa=guncelle.SAYFA))
        return self._gonder(404, {"hata": "bulunamadı"})

    def do_POST(self):
        if not self._yerel_mi():
            return self._gonder(403, {"hata": "yasak"})
        # Başka bir web sitesinin bu düğmelere basmasını engelle
        koken = self.headers.get("Origin")
        if koken and koken not in (f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"):
            return self._gonder(403, {"hata": "yasak"})
        yol = urlparse(self.path).path
        if yol == "/api/yenile":
            yenile()
            return self._gonder(200, durum)
        if yol == "/api/guncelle":
            guncellemeyi_baslat()
            return self._gonder(200, surum_durumu)
        return self._gonder(404, {"hata": "bulunamadı"})


def port_dolu_mu(p):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", p)) == 0


def main():
    adres = f"http://127.0.0.1:{PORT}/"
    guncelleme_sonrasi = "--guncelleme-sonrasi" in sys.argv
    if guncelleme_sonrasi:
        # eski sürümün kapanıp portu bırakmasını bekle; açık olan sayfa kendini yenileyecek
        for _ in range(60):
            if not port_dolu_mu(PORT):
                break
            time.sleep(0.5)
    elif port_dolu_mu(PORT):  # program zaten açık: sadece ekranı aç
        if "--tarayici-acma" not in sys.argv:
            webbrowser.open(adres)
        return
    sunucu = ThreadingHTTPServer(("127.0.0.1", PORT), Isleyici)
    sunucu_ref[0] = sunucu
    threading.Thread(target=guncelle.eski_dosyayi_temizle, daemon=True).start()
    threading.Thread(target=surumu_kontrol_et, daemon=True).start()

    try:
        eski = time.time() - os.path.getmtime(VERI_DOSYASI) > ESKI_SAYILIR_SANIYE
    except OSError:
        eski = True
    if eski:
        yenile()

    def bekci():
        while True:
            time.sleep(30)
            if time.time() - son_nabiz[0] > BOSTA_KAPANMA_SANIYE and not durum["calisiyor"]:
                sunucu.shutdown()
                return

    threading.Thread(target=bekci, daemon=True).start()
    if "--tarayici-acma" not in sys.argv and not guncelleme_sonrasi:
        threading.Timer(0.8, lambda: webbrowser.open(adres)).start()
    sunucu.serve_forever()


if __name__ == "__main__":
    main()
