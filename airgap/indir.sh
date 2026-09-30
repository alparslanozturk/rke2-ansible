#!/usr/bin/env bash
# airgap/indir.sh — RKE2 air-gap kurulum dosyalarını indirir, sha256 ile doğrular, sonda tablo gösterir (KURUM).
#
# Kullanım:
#   airgap/indir.sh --rancher v2.15.2 --os rhel9      Rancher'ın desteklediği TÜM RKE2 hatlarını indir
#   airgap/indir.sh --rancher v2.15.2 v1.35           yalnız v1.35 (sonda yine Rancher uyum tablosu)
#   airgap/indir.sh v1.34 v1.33.13+rke2r2             Rancher'sız: ana hat (en son kararlı) ya da tam sürüm
#   airgap/indir.sh --kuru --rancher v2.15.2          hiçbir şey indirmeden neyin indirileceğini + tabloyu göster
#
# Seçenekler:
#   -r, --rancher <v2.x.y>   RKE2 hatlarını ve uyum tablosunu SUSE Rancher destek matrisinden al
#                            (araclar/rancher_matris.py). Sürüm verilmezse matristeki hatların hepsi indirilir.
#   -o, --os <rhel8|rhel9|rhel10>   tabloyu o RHEL'e süz (+ RKE2_SELINUX=1 ise rke2-selinux elN) (varsayılan rhel9)
#   -n, --kuru               indirme yok; yalnız çözülen sürümler ve tablo
#   -a, --antrea <v2.7|v2.7.0>   antrea.yml'yi indir + kayıt aynasına konacak imaj listesini çıkar
#                            (hangi sürüm? araclar/antrea_surum.py <k8s-sürümü>). Yalnız bu da verilebilir.
# Ortam:
#   RKE2_IMAJ=core (varsayılan; Antrea gibi CNI'yi kendin kuruyorsan) · tum (tüm CNI imajları, büyük)
#   RKE2_ARCH=amd64 (varsayılan) · arm64
#   RKE2_SELINUX=1 → rke2-selinux RPM'ini de indir (kurumda SELinux kapalı → varsayılan indirmez)
#
# Çıktı: airgap/<tam-sürüm>/{rke2.linux-<arch>.tar.gz, rke2-images-*.tar.zst, sha256sum-<arch>.txt},
#        airgap/install.sh (elle worker ekleme — docs/MANUEL-WORKER.md), airgap/antrea/<sürüm>/{antrea.yml, imajlar.txt},
#        (RKE2_SELINUX=1 ise) airgap/selinux/rke2-selinux-*.elN.noarch.rpm.
#        İndirilenler git dışı (.gitignore).
# group_vars/all.yml (playbook_dir = <repo>/playbooks → ../airgap):
#   rke2_install_version: v1.34.11+rke2r1
#   rke2_install_local_tarball_path: "{{ playbook_dir }}/../airgap/{{ rke2_install_version }}/rke2.linux-amd64.tar.gz"
#   rke2_images_local_tarball_path:
#     - "{{ playbook_dir }}/../airgap/{{ rke2_install_version }}/rke2-images-core.linux-amd64.tar.zst"
# İnternete çıkabilen kurum sunucusunda, repo içinden çalıştır.
set -euo pipefail

DIZIN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MATRIS="$DIZIN/../araclar/rancher_matris.py"
ARCH="${RKE2_ARCH:-amd64}"
case "${RKE2_IMAJ:-core}" in
  core) IMAJ="rke2-images-core.linux-${ARCH}.tar.zst" ;;
  tum) IMAJ="rke2-images.linux-${ARCH}.tar.zst" ;;
  *) echo "RKE2_IMAJ core ya da tum olmalı" >&2; exit 2 ;;
esac

RANCHER=""
OS="rhel9"
KURU=0
ANTREA=""
ISTEKLER=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    -r | --rancher) RANCHER="${2:?--rancher sürüm ister}"; shift 2 ;;
    -o | --os) OS="${2:?--os rhel8|rhel9|rhel10 ister}"; shift 2 ;;
    -n | --kuru) KURU=1; shift ;;
    -a | --antrea) ANTREA="${2:?--antrea sürüm ister}"; shift 2 ;;
    -h | --help) sed -n '2,28p' "$0"; exit 0 ;;
    -*) echo "bilinmeyen seçenek: $1" >&2; exit 2 ;;
    *) ISTEKLER+=("$1"); shift ;;
  esac
done
case "$OS" in rhel8 | rhel9 | rhel10) ;; *) echo "--os rhel8, rhel9 ya da rhel10 olmalı" >&2; exit 2 ;; esac
[ -z "$RANCHER" ] || [[ "$RANCHER" == v* ]] || RANCHER="v$RANCHER"

if [ "${#ISTEKLER[@]}" -eq 0 ] && [ -n "$RANCHER" ]; then
  read -r -a ISTEKLER <<< "$(python3 "$MATRIS" --hatlar "$RANCHER")"
  [ "${#ISTEKLER[@]}" -gt 0 ] || { echo "!! Rancher $RANCHER için RKE2 hattı bulunamadı" >&2; exit 1; }
fi
[ "${#ISTEKLER[@]}" -gt 0 ] || [ -n "$ANTREA" ] || { sed -n '2,32p' "$0"; exit 2; }

tam_surum() { # v1.33 → o hattın en son kararlı sürümü (rancher/rke2 git etiketleri; rc'ler hariç)
  case "$1" in
    v*+rke2r*) printf '%s\n' "$1" ;;
    v[0-9]*.[0-9]*)
      git ls-remote --tags --refs https://github.com/rancher/rke2.git "refs/tags/$1.*" \
        | sed 's|.*refs/tags/||' | grep -E "^${1//./\\.}\.[0-9]+\+rke2r[0-9]+$" | sort -V | tail -1 ;;
    *) echo "anlaşılmayan sürüm: $1" >&2; return 1 ;;
  esac
}

dogrula() { # <dizin> <dosya> — sha256sum-<arch>.txt'e göre
  (cd "$1" && grep -E " ${2//./\\.}$" "sha256sum-${ARCH}.txt" | sha256sum -c --quiet - >/dev/null 2>&1)
}

OZET=()
for istek in ${ISTEKLER[@]+"${ISTEKLER[@]}"}; do
  surum="$(tam_surum "$istek" 2>/dev/null || true)"
  if [[ "$surum" != v*+rke2r* ]]; then
    # "v1.35" gibi ana hattın en son sürümü github.com'dan (git etiketleri) bulunur. İnternetsiz makinede --kuru
    # yine de tabloyu gösterir; gerçek indirme zaten internet ister.
    if [ "$KURU" = 1 ]; then
      OZET+=("$istek.x|en son sürüm bulunamadı (github.com erişimi yok)|-|indirilmedi (--kuru)")
      continue
    fi
    echo "!! $istek için sürüm çözülemedi — github.com'a erişim gerekir (ya da tam sürüm ver: v1.35.8+rke2r1)" >&2
    exit 1
  fi
  hedef="$DIZIN/$surum"
  if [ "$KURU" = 1 ]; then
    OZET+=("$surum|tarball + ${IMAJ%%.linux*} imajları|-|indirilmedi (--kuru)")
    continue
  fi
  mkdir -p "$hedef"
  taban="https://github.com/rancher/rke2/releases/download/${surum/+/%2B}"
  echo "== $surum → $hedef"
  for dosya in "sha256sum-${ARCH}.txt" "rke2.linux-${ARCH}.tar.gz" "$IMAJ"; do
    if [ -s "$hedef/$dosya" ] && [ "$dosya" != "sha256sum-${ARCH}.txt" ]; then
      echo "   var: $dosya"
      continue
    fi
    echo "   indir: $dosya"
    curl -fsSL --retry 3 -o "$hedef/$dosya.part" "$taban/$dosya"
    mv "$hedef/$dosya.part" "$hedef/$dosya"
  done
  for dosya in "rke2.linux-${ARCH}.tar.gz" "$IMAJ"; do
    if ! dogrula "$hedef" "$dosya"; then
      echo "   sha256 uyuşmadı, yeniden indir: $dosya"   # yarım/bozuk eski indirme
      curl -fsSL --retry 3 -o "$hedef/$dosya.part" "$taban/$dosya"
      mv "$hedef/$dosya.part" "$hedef/$dosya"
    fi
    if dogrula "$hedef" "$dosya"; then durum="OK"; else durum="HATALI"; fi
    OZET+=("$surum|$dosya|$(du -h "$hedef/$dosya" | cut -f1)|$durum")
    [ "$durum" = OK ] || { echo "!! sha256 uyuşmadı: $hedef/$dosya" >&2; exit 1; }
  done
done

# Resmi kurulum betiği (sürümden bağımsız) — elle worker eklerken kullanılır (docs/MANUEL-WORKER.md).
if [ "${#ISTEKLER[@]}" -gt 0 ]; then
  if [ "$KURU" = 1 ]; then
    OZET+=("install.sh|get.rke2.io → airgap/install.sh|-|indirilmedi (--kuru)")
  else
    curl -fsSL --retry 3 -o "$DIZIN/install.sh.part" https://get.rke2.io && mv "$DIZIN/install.sh.part" "$DIZIN/install.sh"
    OZET+=("install.sh|install.sh (elle worker için)|$(du -h "$DIZIN/install.sh" | cut -f1)|indirildi")
  fi
fi

# Antrea (kurumda CNI): RKE2 paketinde gelmez. antrea.yml manifesti ilk sunucuya konur (pre_deploy_manifests/),
# içindeki imajlar kurum kayıt aynasında olmalı → imajlar.txt.
if [ -n "$ANTREA" ]; then
  case "$ANTREA" in
    v2.[0-9]*.[0-9]*) av="$ANTREA" ;;
    v[0-9]*.[0-9]*)
      av="$(git ls-remote --tags --refs https://github.com/antrea-io/antrea.git "refs/tags/$ANTREA.*" 2>/dev/null \
        | sed 's|.*refs/tags/||' | grep -E "^${ANTREA//./\\.}\.[0-9]+$" | sort -V | tail -1 || true)" ;;
    *) echo "--antrea v2.7 ya da v2.7.0 biçiminde olmalı" >&2; exit 2 ;;
  esac
  if [ -z "$av" ] && [ "$KURU" = 1 ]; then
    OZET+=("antrea $ANTREA.x|en son sürüm bulunamadı (github.com erişimi yok)|-|indirilmedi (--kuru)")
  elif [ -z "$av" ]; then
    echo "!! Antrea $ANTREA bulunamadı — github.com'a erişim gerekir (ya da tam sürüm ver: v2.7.0)" >&2
    exit 1
  elif [ "$KURU" = 1 ]; then
    OZET+=("antrea $av|antrea.yml + imaj listesi|-|indirilmedi (--kuru)")
  else
    ad="$DIZIN/antrea/$av"
    mkdir -p "$ad"
    echo "== antrea $av → $ad"
    curl -fsSL --retry 3 -o "$ad/antrea.yml.part" "https://github.com/antrea-io/antrea/releases/download/$av/antrea.yml"
    mv "$ad/antrea.yml.part" "$ad/antrea.yml"
    grep -E '^\s+image:' "$ad/antrea.yml" | sed 's/.*image: *//; s/"//g' | sort -u > "$ad/imajlar.txt"
    OZET+=("antrea $av|antrea.yml|$(du -h "$ad/antrea.yml" | cut -f1)|indirildi (GitHub sürüm dosyası)")
    while read -r imaj; do OZET+=("  imaj|$imaj|-|kayıt aynasına koy"); done < "$ad/imajlar.txt"
  fi
fi

# SELinux enforcing RHEL'de tarball kurulumu rke2-selinux ister (bağımlılığı container-selinux RHEL
# AppStream/Satellite'tan gelir). Sürümden bağımsız, tek dosya → airgap/selinux/.
if [ "${RKE2_SELINUX:-0}" = "1" ]; then
  EL="el${OS#rhel}"
  etiket="$(curl -fsSL -o /dev/null -w '%{url_effective}' https://github.com/rancher/rke2-selinux/releases/latest)"
  etiket="${etiket##*/}"
  yol="$(curl -fsSL "https://github.com/rancher/rke2-selinux/releases/expanded_assets/$etiket" \
    | grep -oE "/rancher/rke2-selinux/releases/download/[^\"]*\.${EL}\.noarch\.rpm" | head -1 || true)"
  if [ -z "$yol" ]; then
    OZET+=("selinux|rke2-selinux ${EL} ($etiket)|-|YOK — bu RHEL için yayınlanmamış")
  elif [ "$KURU" = 1 ]; then
    OZET+=("selinux|${yol##*/}|-|indirilmedi (--kuru)")
  else
    mkdir -p "$DIZIN/selinux"
    rpm_ad="${yol##*/}"
    if [ ! -s "$DIZIN/selinux/$rpm_ad" ]; then
      echo "== selinux: indir: $rpm_ad"
      curl -fsSL --retry 3 -o "$DIZIN/selinux/$rpm_ad.part" "https://github.com$yol"
      mv "$DIZIN/selinux/$rpm_ad.part" "$DIZIN/selinux/$rpm_ad"
    fi
    OZET+=("selinux|$rpm_ad|$(du -h "$DIZIN/selinux/$rpm_ad" | cut -f1)|OK (imzasız, resmi sürüm)")
  fi
fi

echo
echo "== Özet ($DIZIN)"
# başlık elle hizalı: printf %-Ns bayt sayar, Ü/Ö iki bayt
echo "  SÜRÜM              DOSYA                                        BOYUT  SHA256"
for satir in "${OZET[@]}"; do
  IFS='|' read -r s d b h <<< "$satir"
  printf '  %-18s %-44s %-6s %s\n' "$s" "$d" "$b" "$h"
done

if [ -n "$RANCHER" ]; then
  echo
  python3 "$MATRIS" "$RANCHER" "$OS"
else
  echo
  echo "  (Rancher uyumu için: airgap/indir.sh --rancher <v2.x.y> --os $OS ...  ya da araclar/rancher_matris.py <v2.x.y> $OS)"
fi
