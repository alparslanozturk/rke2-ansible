#!/usr/bin/env python3
"""antrea_surum.py — hangi Antrea sürümü hangi Kubernetes (RKE2) sürümünü destekler (KURUM).

Antrea'nın kuralı (docs/versioning.md "Supported K8s versions"): her Antrea ana sürümü, ÇIKTIĞI GÜN desteklenen
son 4 Kubernetes sürümünü destekler. Resmi tablo yok; bu betik Antrea ve Kubernetes'in çıkış tarihlerinden
tabloyu hesaplar (github.com'dan; internet gerekir).

Kullanım:  araclar/antrea_surum.py            → tablo
           araclar/antrea_surum.py 1.34       → tablo + 1.34 için önerilen Antrea
"""
import re
import subprocess
import sys
import urllib.request


def etiketler(depo: str, desen: str) -> list[str]:
    cikti = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", f"https://github.com/{depo}.git", desen],
        capture_output=True, text=True, timeout=60, check=True,
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


def sayilar(s: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", s)]


def main() -> None:
    hedef = sys.argv[1].lstrip("v") if len(sys.argv) > 1 else ""

    # Kubernetes ana sürümlerinin çıkış tarihleri (1.N.0)
    k8s = sorted({e for e in etiketler("kubernetes/kubernetes", "refs/tags/v1.*.0") if re.fullmatch(r"v1\.\d+\.0", e)}, key=sayilar)
    k8s = [e for e in k8s if sayilar(e)[1] >= 26]
    k8s_tarih = {sayilar(e)[1]: cikis_tarihi("kubernetes/kubernetes", e) for e in k8s}

    # Antrea v2.x ana sürümleri: X.Y.0 tarihi + en son yama
    antrea = [e for e in etiketler("antrea-io/antrea", "refs/tags/v2.*") if re.fullmatch(r"v2\.\d+\.\d+", e)]
    anasurum: dict[str, list[str]] = {}
    for e in antrea:
        anasurum.setdefault(".".join(e.split(".")[:2]), []).append(e)

    satirlar = []
    for ana in sorted(anasurum, key=sayilar):
        tarih = cikis_tarihi("antrea-io/antrea", ana + ".0")
        if not tarih:
            continue
        cikmis = [m for m, t in k8s_tarih.items() if t and t <= tarih]
        if not cikmis:
            continue
        ust = max(cikmis)
        son_yama = max(anasurum[ana], key=sayilar)
        satirlar.append((ana, son_yama, tarih, ust - 3, ust))

    print("Antrea → desteklenen Kubernetes (kural: çıktığı gün desteklenen son 4 sürüm)")
    print(f"  {'ANTREA':<8}{'EN SON YAMA':<13}{'ÇIKIŞ':<12}KUBERNETES")
    for ana, yama, tarih, alt, ust in satirlar:
        print(f"  {ana:<8}{yama:<13}{tarih:<12}1.{alt} – 1.{ust}")

    if hedef:
        m = int(hedef.split(".")[1])
        uygun = [s for s in satirlar if s[3] <= m <= s[4]]
        if uygun:
            en = uygun[-1]
            print(f"\n  Kubernetes {hedef} için: {', '.join(s[0] for s in uygun)} → önerilen {en[1]}")
            print(f"  İndirmek için:  airgap/indir.sh --antrea {en[1]} ...")
        else:
            print(f"\n  !! Kubernetes {hedef} için garanti edilen Antrea sürümü yok (daha yeni Antrea bekleniyor olabilir).")
    print("\n  Kümede kullanılan sürüm:  grep 'image:' antrea.yaml   ya da")
    print("  kubectl -n kube-system get ds antrea-agent -o jsonpath='{.spec.template.spec.containers[0].image}'")


if __name__ == "__main__":
    main()
