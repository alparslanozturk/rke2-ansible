#!/usr/bin/env bash
# airgap/indir.sh — RKE2 air-gap kurulum dosyalarını indirir ve sha256 ile doğrular (KURUM).
#
# Kullanım:  airgap/indir.sh <sürüm> [<sürüm> ...]
#   <sürüm>  tam sürüm (v1.33.5+rke2r1) ya da ana hat (v1.33 → o hattın en son kararlı sürümü, git etiketlerinden)
#
# Ortam:
#   RKE2_IMAJ=core   (varsayılan) rke2-images-core — CNI'yi kendin kuruyorsan (Antrea, cni: none)
#   RKE2_IMAJ=tum    rke2-images (tüm CNI'ler dahil, büyük)
#   RKE2_ARCH=amd64  (varsayılan) ya da arm64
#   RKE2_SELINUX=el9 (varsayılan) rke2-selinux RPM'i de airgap/selinux/'a indir · el8 · yok
#
# Çıktı: airgap/<tam-sürüm>/{rke2.linux-<arch>.tar.gz, rke2-images-*.tar.zst, sha256sum-<arch>.txt}
# group_vars/all.yml'de:
#   rke2_install_version: v1.33.5+rke2r1
#   rke2_install_local_tarball_path: "{{ playbook_dir }}/airgap/{{ rke2_install_version }}/rke2.linux-amd64.tar.gz"
#   rke2_images_local_tarball_path:
#     - "{{ playbook_dir }}/airgap/{{ rke2_install_version }}/rke2-images-core.linux-amd64.tar.zst"
# Bu dizin git'e girmez (.gitignore); offline sahaya diziniyle birlikte kopyalanır.
set -euo pipefail

DIZIN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCH="${RKE2_ARCH:-amd64}"
case "${RKE2_IMAJ:-core}" in
  core) IMAJ="rke2-images-core.linux-${ARCH}.tar.zst" ;;
  tum) IMAJ="rke2-images.linux-${ARCH}.tar.zst" ;;
  *) echo "RKE2_IMAJ core ya da tum olmalı" >&2; exit 2 ;;
esac

[ "$#" -ge 1 ] || { sed -n '2,10p' "$0"; exit 2; }

tam_surum() { # v1.33 → o hattın en son kararlı sürümü (rancher/rke2 git etiketleri; rc'ler hariç)
  case "$1" in
    v*+rke2r*) printf '%s\n' "$1" ;;
    v[0-9]*.[0-9]*)
      git ls-remote --tags --refs https://github.com/rancher/rke2.git "refs/tags/$1.*" \
        | sed 's|.*refs/tags/||' | grep -E "^${1//./\\.}\.[0-9]+\+rke2r[0-9]+$" | sort -V | tail -1 ;;
    *) echo "anlaşılmayan sürüm: $1" >&2; return 1 ;;
  esac
}

for istek in "$@"; do
  surum="$(tam_surum "$istek")"
  [[ "$surum" == v*+rke2r* ]] || { echo "!! $istek için sürüm çözülemedi ($surum)" >&2; exit 1; }
  hedef="$DIZIN/$surum"
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
  ( cd "$hedef" && grep -E " (rke2\.linux-${ARCH}\.tar\.gz|${IMAJ//./\\.})$" "sha256sum-${ARCH}.txt" | sha256sum -c - )
  echo "   doğrulandı: $surum"
done

# SELinux enforcing RHEL'de tarball kurulumu rke2-selinux ister (bağımlılığı container-selinux RHEL
# AppStream/Satellite'tan gelir). Sürümden bağımsız, tek dosya → airgap/selinux/.
SEL="${RKE2_SELINUX:-el9}"
if [ "$SEL" != "yok" ]; then
  etiket="$(curl -fsSL -o /dev/null -w '%{url_effective}' https://github.com/rancher/rke2-selinux/releases/latest)"
  etiket="${etiket##*/}"
  yol="$(curl -fsSL "https://github.com/rancher/rke2-selinux/releases/expanded_assets/$etiket" \
    | grep -oE "/rancher/rke2-selinux/releases/download/[^\"]*\.${SEL}\.noarch\.rpm" | head -1)"
  [ -n "$yol" ] || { echo "!! rke2-selinux ${SEL} RPM'i bulunamadı ($etiket)" >&2; exit 1; }
  mkdir -p "$DIZIN/selinux"
  rpm_ad="${yol##*/}"
  if [ -s "$DIZIN/selinux/$rpm_ad" ]; then
    echo "== selinux: var: $rpm_ad"
  else
    echo "== selinux: indir: $rpm_ad"
    curl -fsSL --retry 3 -o "$DIZIN/selinux/$rpm_ad.part" "https://github.com$yol"
    mv "$DIZIN/selinux/$rpm_ad.part" "$DIZIN/selinux/$rpm_ad"
  fi
fi
