#!/usr/bin/env python3
"""rancher_matris.py — Rancher sürümüne göre desteklenen RKE2 hatlarını ve RHEL sürümlerini gösterir (KURUM).

Kaynak: SUSE Rancher destek matrisi
  https://www.suse.com/suse-rancher/support-matrix/all-supported-versions/rancher-v2-15-2/

Kullanım:  araclar/rancher_matris.py <rancher-sürümü> [rhel8|rhel9|rhel10]
  ör.      araclar/rancher_matris.py v2.15.2 rhel9
           araclar/rancher_matris.py --hatlar v2.15.2   → yalnız "v1.36 v1.35 v1.34" (indir.sh kullanır)
           araclar/rancher_matris.py --liste            → repodaki (çevrimdışı) matris dosyaları
           araclar/rancher_matris.py --kaydet v2.14.3 v2.15.2   → sayfayı indirip araclar/matris/'e yaz (internet)

Çevrimdışı: kurum sunucusu suse.com'a erişemiyor → matris sayfaları araclar/matris/rancher-v2-X-Y.txt olarak
repoda durur; araç ÖNCE bu dosyayı okur, yoksa internete çıkar. "En son kararlı" RKE2 sürümü için git
(github.com) gerekir; erişilemezse "?" yazılır, gerisi çalışır. Bağımlılık yok (yalnız Python 3 + git).

Çıktı: Rancher'ın kendi kümesi için RKE2 aralığı, downstream kümeler için RKE2 hatları ve RKE2 için RHEL desteği.
"""
import datetime
import html
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

URL = "https://www.suse.com/suse-rancher/support-matrix/all-supported-versions/rancher-v{}/"
MATRIS_DIZIN = Path(__file__).resolve().parent / "matris"
SURUM = re.compile(r"^\d+\.\d+$")
OS_SURUM = re.compile(r"^\d+(\.\d+)?$")


def dosya_adi(rancher: str) -> Path:
    return MATRIS_DIZIN / f"rancher-v{rancher.lstrip('v').replace('.', '-')}.txt"


def indir(rancher: str) -> list[str]:
    url = URL.format(rancher.lstrip("v").replace(".", "-"))
    istek = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ham = urllib.request.urlopen(istek, timeout=30).read().decode("utf-8", "ignore")
    ham = re.sub(r"<script.*?</script>|<style.*?</style>", "", ham, flags=re.S)
    metin = html.unescape(re.sub(r"<[^>]+>", "\n", ham))
    return [s.strip() for s in metin.split("\n") if s.strip()]


def satirlar(rancher: str) -> list[str]:
    yol = dosya_adi(rancher)
    if yol.exists():
        return [s for s in yol.read_text(encoding="utf-8").splitlines() if s and not s.startswith("#")]
    try:
        return indir(rancher)
    except Exception as e:  # noqa: BLE001
        var = ", ".join(sorted_surumler()) or "yok"
        sys.exit(f"!! {rancher} için çevrimdışı matris yok ({yol.name}) ve internetten alınamadı: {e}\n"
                 f"   Repodaki sürümler: {var}\n"
                 f"   İnternetli makinede: araclar/rancher_matris.py --kaydet {rancher}  → commit/push → git pull")


def sorted_surumler() -> list[str]:
    ad = [p.stem.replace("rancher-v", "v").replace("-", ".") for p in MATRIS_DIZIN.glob("rancher-v*.txt")]
    return sorted(ad, key=lambda v: [int(x) for x in re.findall(r"\d+", v)])


def kaydet(surumler: list[str]) -> None:
    MATRIS_DIZIN.mkdir(exist_ok=True)
    for r in surumler:
        r = r if r.startswith("v") else "v" + r
        s = indir(r)
        bul(s, "RKE2 Versions")  # beklenen bölüm yoksa (ör. yanlış sürüm/404 sayfası) burada durur
        url = URL.format(r.lstrip("v").replace(".", "-"))
        bas = f"# kaynak: {url}\n# indirildi: {datetime.date.today().isoformat()} (araclar/rancher_matris.py --kaydet)\n"
        dosya_adi(r).write_text(bas + "\n".join(s) + "\n", encoding="utf-8")
        print(f"kaydedildi: {dosya_adi(r).relative_to(MATRIS_DIZIN.parent.parent)} ({len(s)} satır)")


def bul(s: list[str], deger: str, bas: int = 0) -> int:
    for i in range(bas, len(s)):
        if s[i] == deger:
            return i
    sys.exit(f"!! sayfa yapısı beklenenden farklı: '{deger}' bulunamadı")


def yerel_kume(s: list[str]) -> tuple[str, str]:
    i = bul(s, "Supported Kubernetes Platforms for Rancher Manager")
    j = bul(s, "RKE2", i)
    return s[j + 1], s[j + 2]


def downstream(s: list[str]) -> list[tuple[str, str, str]]:
    i = bul(s, "RKE2 Versions", bul(s, "Downstream Cluster Support"))
    son = bul(s, "RKE2 Provisioned Through Rancher", i)
    out = []
    k = i
    while k < son:
        if SURUM.match(s[k]):
            ileri = s[k + 1 : son]
            # "Yes (x86 / arm64 / mixed", "15", ")", "Yes" → Rancher-provisioned ve imported
            evet = [x for x in ileri[:6] if x.startswith(("Yes", "No"))]
            out.append((s[k], evet[0].split(" ")[0] if evet else "?", evet[1] if len(evet) > 1 else "?"))
        k += 1
    return out


def rhel(s: list[str]) -> list[tuple[str, str]]:
    i = bul(s, "RKE2 Provisioned Through Rancher")
    out = []
    k = i
    while k < len(s):
        if s[k] in ("K3S Provisioned Through Rancher", "k3s Provisioned Through Rancher") or (
            k > i + 5 and s[k].endswith("Provisioned Through Rancher")
        ):
            break
        if s[k] == "RHEL":
            m = k + 1
            while m < len(s) and not OS_SURUM.match(s[m]):
                m += 1
            if m < len(s):
                out.append((s[m], s[m + 1]))  # (sürüm, Custom sütunu)
            k = m
        k += 1
    return out


def son_yama(hat: str) -> str:
    try:
        cikti = subprocess.run(
            ["git", "ls-remote", "--tags", "--refs", "https://github.com/rancher/rke2.git", f"refs/tags/v{hat}.*"],
            capture_output=True, text=True, timeout=20, check=True,
        ).stdout
    except Exception:  # noqa: BLE001
        return "?"
    etiketler = [l.rsplit("/", 1)[-1] for l in cikti.splitlines()]
    kararli = [e for e in etiketler if re.fullmatch(rf"v{re.escape(hat)}\.\d+\+rke2r\d+", e)]
    anahtar = lambda e: [int(x) for x in re.findall(r"\d+", e)]  # noqa: E731
    return max(kararli, key=anahtar) if kararli else "?"


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--liste":
        print("Çevrimdışı matris dosyaları (araclar/matris/):", " ".join(sorted_surumler()) or "yok")
        return
    if len(sys.argv) >= 3 and sys.argv[1] == "--kaydet":
        kaydet(sys.argv[2:])
        return
    if len(sys.argv) >= 3 and sys.argv[1] == "--hatlar":
        r = sys.argv[2] if sys.argv[2].startswith("v") else "v" + sys.argv[2]
        print(" ".join("v" + h for h, _, _ in downstream(satirlar(r))))
        return
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    rancher = sys.argv[1] if sys.argv[1].startswith("v") else "v" + sys.argv[1]
    os_filtre = sys.argv[2].lower().replace("rhel", "") if len(sys.argv) > 2 else ""
    s = satirlar(rancher)

    alt, ust = yerel_kume(s)
    kaynak = f"çevrimdışı: araclar/matris/{dosya_adi(rancher).name}" if dosya_adi(rancher).exists() else "internet"
    print(f"Rancher {rancher} — destek matrisi ({kaynak})")
    print(f"  Rancher'ın kendi kümesi (local) RKE2: {alt} … {ust}")
    print("  Downstream RKE2 hatları (Rancher-provisioned / imported) → en son kararlı sürüm:")
    hatlar = downstream(s)
    for hat, prov, imp in hatlar:
        print(f"    v{hat:<6} {prov:>3} / {imp:<3} → {son_yama(hat)}")
    satir = rhel(s)
    if os_filtre:
        satir = [r for r in satir if r[0].split(".")[0] == os_filtre]
    print("  RKE2 için RHEL (custom küme sütunu):", ", ".join(f"{v} ({c})" for v, c in satir) or "YOK")
    if os_filtre and not satir:
        print(f"  !! RHEL {os_filtre} bu Rancher sürümünde RKE2 için listelenmiyor.")
    if hatlar:
        os_arg = f" --os rhel{os_filtre}" if os_filtre else ""
        print(f"\n  İndirmek için:  airgap/indir.sh --rancher {rancher}{os_arg}   (ya da tek hat: ... {'v' + hatlar[0][0]})")


if __name__ == "__main__":
    main()
