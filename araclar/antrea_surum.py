#!/usr/bin/env python3
"""antrea_surum.py — hangi Antrea sürümü hangi Kubernetes (RKE2) sürümünü destekler (KURUM).

Antrea'nın kuralı (docs/versioning.md "Supported K8s versions"): her Antrea ana sürümü, ÇIKTIĞI GÜN desteklenen
son 4 Kubernetes sürümünü destekler. Resmi tablo yok; tablo Antrea ve Kubernetes'in çıkış tarihlerinden hesaplanır.

ÇEVRİMDIŞI: kurum sunucusu bu hesap için gereken GitHub sorgularını yapamıyor (kubernetes/kubernetes etiketleri
sahada exit 128) → hesaplanmış tablo repoda: araclar/matris/antrea-uyum.txt. Araç ÖNCE bu dosyayı okur;
internete yalnız dosya yoksa ya da --yenile ile çıkar.

Kullanım:  araclar/antrea_surum.py                        → tablo
           araclar/antrea_surum.py 1.33                   → tablo + 1.33 için uygun/önerilen Antrea
           araclar/antrea_surum.py 1.33 --antrea v2.3.0   → kümedeki Antrea bu K8s ile uyumlu mu (✅/❌)
           araclar/antrea_surum.py --yenile               → internetten yeniden hesapla, dosyaya yaz (commit/push et)
"""
import datetime
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

VERI = Path(__file__).resolve().parent / "matris" / "antrea-uyum.txt"


def sayilar(s: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", s)]


# --- internetten hesap (yalnız --yenile ya da dosya yoksa) ---------------------------------------------------

def etiketler(depo: str, desen: str) -> list[str]:
    cikti = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", f"https://github.com/{depo}.git", desen],
        capture_output=True, text=True, timeout=120, check=True,
    ).stdout
    return [s.rsplit("/", 1)[-1] for s in cikti.splitlines()]


def cikis_tarihi(depo: str, etiket: str) -> str:
    istek = urllib.request.Request(f"https://github.com/{depo}/releases/tag/{etiket}", headers={"User-Agent": "Mozilla/5.0"})
    try:
        sayfa = urllib.request.urlopen(istek, timeout=30).read().decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return ""
    m = re.search(r'datetime="(\d{4}-\d{2}-\d{2})', sayfa)
    return m.group(1) if m else ""


def hesapla() -> list[tuple[str, str, str, int, int]]:
    k8s = sorted({e for e in etiketler("kubernetes/kubernetes", "refs/tags/v1.*.0") if re.fullmatch(r"v1\.\d+\.0", e)}, key=sayilar)
    k8s = [e for e in k8s if sayilar(e)[1] >= 26]
    k8s_tarih = {sayilar(e)[1]: cikis_tarihi("kubernetes/kubernetes", e) for e in k8s}
    antrea = [e for e in etiketler("antrea-io/antrea", "refs/tags/v2.*") if re.fullmatch(r"v2\.\d+\.\d+", e)]
    anasurum: dict[str, list[str]] = {}
    for e in antrea:
        anasurum.setdefault(".".join(e.split(".")[:2]), []).append(e)
    satirlar = []
    for ana in sorted(anasurum, key=sayilar):
        tarih = cikis_tarihi("antrea-io/antrea", ana + ".0")
        cikmis = [m for m, t in k8s_tarih.items() if t and tarih and t <= tarih]
        if not tarih or not cikmis:
            continue
        ust = max(cikmis)
        satirlar.append((ana, max(anasurum[ana], key=sayilar), tarih, ust - 3, ust))
    return satirlar


def kaydet(satirlar: list[tuple[str, str, str, int, int]]) -> None:
    VERI.parent.mkdir(exist_ok=True)
    bas = [
        "# Antrea → desteklenen Kubernetes — ÇEVRİMDIŞI VERİ (araclar/antrea_surum.py okur)",
        f"# Üretim: {datetime.date.today().isoformat()} · araclar/antrea_surum.py --yenile (internetli makinede)",
        "# Kural (antrea.io docs/versioning, 'Supported K8s versions'): her Antrea minor sürümü ÇIKTIĞI GÜN bakımda",
        "#   olan son 4 Kubernetes minor'ını destekler. Resmi tablo yok; Antrea X.Y.0 ve Kubernetes 1.N.0 çıkış",
        "#   tarihlerinden (github.com release sayfaları + git etiketleri) hesaplanır. Yama sürümü aralığı değiştirmez.",
        "# Kubernetes minor = RKE2 hattı (v1.33.13+rke2r1 → 1.33).",
        "#",
        "# ANTREA  EN_SON_YAMA  CIKIS       K8S_ALT  K8S_UST",
    ]
    govde = [f"{a:<9}{y:<13}{t:<12}1.{alt:<7}1.{ust}" for a, y, t, alt, ust in satirlar]
    VERI.write_text("\n".join(bas + govde) + "\n", encoding="utf-8")
    print(f"kaydedildi: araclar/matris/{VERI.name} ({len(govde)} satır)")


# --- çevrimdışı okuma -------------------------------------------------------------------------------------------

def oku() -> list[tuple[str, str, str, int, int]]:
    out = []
    for s in VERI.read_text(encoding="utf-8").splitlines():
        if not s.strip() or s.startswith("#"):
            continue
        a, y, t, alt, ust = s.split()
        out.append((a, y, t, sayilar(alt)[1], sayilar(ust)[1]))
    return out


def main() -> None:
    args = sys.argv[1:]
    yenile = "--yenile" in args
    antrea_kume = ""
    if "--antrea" in args:
        i = args.index("--antrea")
        antrea_kume = args[i + 1] if i + 1 < len(args) else ""
        del args[i : i + 2]
    args = [a for a in args if a != "--yenile"]
    hedef = args[0].lstrip("v") if args else ""

    if yenile or not VERI.exists():
        try:
            satirlar = hesapla()
        except Exception as e:  # noqa: BLE001
            if VERI.exists():
                sys.exit(f"!! internetten hesaplanamadı ({e}) — mevcut araclar/matris/{VERI.name} korunuyor, değişmedi.")
            sys.exit(f"!! internetten hesaplanamadı ({e}) ve {VERI.name} yok — repoyu güncelle (git pull).")
        kaydet(satirlar)
        kaynak = "internet (dosyaya yazıldı — commit/push et)"
    else:
        satirlar = oku()
        uretim = next((s for s in VERI.read_text(encoding="utf-8").splitlines() if s.startswith("# Üretim:")), "")
        kaynak = f"çevrimdışı: araclar/matris/{VERI.name}{' — ' + uretim[2:].split(' · ')[0] if uretim else ''}"

    print(f"Antrea → desteklenen Kubernetes ({kaynak})")
    print("  Kural: her Antrea sürümü, çıktığı gün desteklenen son 4 Kubernetes sürümünü destekler.")
    print(f"  {'ANTREA':<8}{'EN SON YAMA':<13}{'ÇIKIŞ':<12}KUBERNETES")
    for ana, yama, tarih, alt, ust in satirlar:
        print(f"  {ana:<8}{yama:<13}{tarih:<12}1.{alt} – 1.{ust}")

    if hedef:
        try:
            m = int(hedef.split(".")[1])
        except (IndexError, ValueError):
            sys.exit(f"!! Kubernetes sürümü anlaşılmadı: {hedef} (ör. 1.33 ya da v1.33.13+rke2r1)")
        uygun = [s for s in satirlar if s[3] <= m <= s[4]]
        if uygun:
            en = uygun[-1]
            print(f"\n  Kubernetes 1.{m} için: {', '.join(s[0] for s in uygun)} → önerilen {en[1]}")
            print(f"  İndirmek için:  airgap/indir.sh --antrea {en[1]} ...")
        else:
            print(f"\n  !! Kubernetes 1.{m} için tabloda uyumlu Antrea yok (daha yeni Antrea gerekebilir: --yenile).")
        if antrea_kume:
            ana = "v" + ".".join(str(x) for x in sayilar(antrea_kume)[:2])
            satir = next((s for s in satirlar if s[0] == ana), None)
            if not satir:
                print(f"  Kümedeki Antrea {antrea_kume}: tabloda yok — sonuç bilinmiyor (tahmin etme; --yenile)")
            elif satir[3] <= m <= satir[4]:
                print(f"  Kümedeki Antrea {antrea_kume} + Kubernetes 1.{m}: ✅ UYUMLU ({ana} → 1.{satir[3]} – 1.{satir[4]})")
            else:
                print(f"  Kümedeki Antrea {antrea_kume} + Kubernetes 1.{m}: ❌ KURAL DIŞI ({ana} → 1.{satir[3]} – 1.{satir[4]})."
                      f" Antrea'yı {uygun[-1][1] if uygun else 'daha yeni bir sürüme'} yükselt — K8s yükseltmesinden ÖNCE.")
    print("\n  Kümede kullanılan sürüm:  grep 'image:' antrea.yaml   ya da")
    print("  kubectl -n kube-system get ds antrea-agent -o jsonpath='{.spec.template.spec.containers[0].image}'")


if __name__ == "__main__":
    main()
