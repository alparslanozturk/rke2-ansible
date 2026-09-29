# Teknik notlar (geliştirici için)

Kullanım rehberi: `KURUM.md`. Bu dosya: upstream'den farklar, test yöntemi, upstream güncellemesi.

Temel: **rancherfederal/rke2-ansible 2.x** (`upstream/main`). İlke: upstream'e az dokun — her değişiklik küçük,
`KURUM` yorumuyla işaretli ve aşağıdaki tabloda; upstream güncellemesi `git merge upstream/main` ile alınır.

| Remote | Adres | Rol |
|---|---|---|
| `upstream` | rancherfederal/rke2-ansible | temel (push kapalı) |
| `hepapi` | hepapi/rke2-ansible | danışman fork'u — `hepapi` dalı eski 1.x (2023-11), yalnız referans (push kapalı) |
| `origin` | alparslanozturk/rke2-ansible | bu fork |

## Upstream'e göre farklar

| Değişiklik | Dosya | Neden |
|---|---|---|
| Ön kontrol (değişiklik yapmaz) | `roles/rke2/tasks/preflight.yml` | sürüm verilmemişse dur (internetten "stable" çekmesin) · yerel tarball/imaj dosyası yoksa dur · `--limit`'li koşuda `rke2_kubernetes_api_server_host` boşsa dur · `node_name` (1.x kalıntısı) için uyar |
| RHEL 9 CIS `/tmp noexec` | `tmp_exec.yml`, `tmp_restore.yml` | tarball `/tmp`'de açılıp oradan `rke2 -v` çalıştırılıyor; noexec'te düşüyordu. Başta `mount -o remount,exec /tmp`, sonda geri `noexec` (yalnız başta noexec idiyse) |
| rke2-selinux RPM (isteğe bağlı) | `selinux_rpm.yml` | SELinux enforcing + tarball kurulumu politikasız çalışmaz; upstream yalnız dokümanda uyarıyor |
| Kurulu sürüm `/opt/rke2`'de de aranır | `previous_install.yml` | `/usr/local` bağlama noktasıysa kurulum `/opt/rke2`'ye gider; upstream sürümü bilemiyor → gereksiz yeniden açma/restart |
| `in groups[..][0]` → `==` | `main.yml`, `roles/testing` | alt-dize eşleşmesi (`k8s1` ⊂ `k8s10`) ilk-sunucu görevlerini yanlış makinede koşturabilirdi |
| authn-webhook yolunda eksik `/` | `configure_rke2.yml` | dosya `/var/lib/rancher/rke2kube-api-...` gibi yanlış yere yazılıyordu |
| Air-gap indirici | `airgap/indir.sh` | tarball + core imajlar + rke2-selinux, sha256 doğrulamalı |
| Küme sürümü = envanter sürümü | `preflight.yml` | SUC kümeyi yükseltince envanter geride kalır; ilk sunucudan node sürümleri okunur, `rke2_upgrade: false` iken fark varsa dur, değilse uyar |
| Rancher matrisi okuyucu | `araclar/rancher_matris.py` | Rancher sürümü → desteklenen RKE2 hatları + RHEL sürümleri (suse.com matrisinden) |
| Kurum örnek envanteri | `docs/kurum_ornek_envanter/` | sahadaki `inventory/<küme>/` yapısı: Antrea, CIS, PSA, audit, kayıt aynası |

Yeni değişkenler (`roles/rke2/defaults/main.yml`, hepsi kapatılabilir): `rke2_require_pinned_version: true`,
`rke2_tmp_remount_exec: true`, `rke2_tmp_restore_noexec: true`, `rke2_selinux_rpm_local_path: ""`.

Önemli yollar: `site.yml` ile koşunca `playbook_dir` = `<repo>/playbooks` → örnek envanterde
`{{ playbook_dir }}/../airgap/...` ve `{{ inventory_dir }}/files/...` (upstream örneklerindeki
`{{ playbook_dir }}/docs/...` bu yüzden yanlış yere bakar). PSA dosyası rol tarafından
`/etc/rancher/rke2/rke2-pss.yaml`'a yazılır; `pod-security-admission-config-file` bu yol olmalı.

Kaynaklar: RKE2 dosyaları `github.com/rancher/rke2/releases/download/<sürüm>/`; en son sürüm aynı deponun git
etiketlerinden (update.rke2.io kanal servisi denemede 404 verdi); SELinux `github.com/rancher/rke2-selinux/releases`;
Rancher matrisi `suse.com/suse-rancher/support-matrix/all-supported-versions/rancher-v2-X-Y/`.

## RHEL 9 / CIS notları

- `/tmp noexec`: yukarıdaki görev çözer. Koşu yarıda kalırsa `/tmp` exec kalır → `mount -o remount,noexec /tmp`
  (reboot da fstab'dan geri getirir).
- `profile: cis`: etcd kullanıcısı + `60-rke2-cis.conf` sysctl; RKE2 zaten çalışan node'da sysctl değişirse node
  **reboot** edilir (upstream davranışı).
- SELinux: `selinux: true` + `rke2_selinux_rpm_local_path`; `container-selinux` RHEL deposundan (Satellite) gelmeli.
- firewalld durdurulur (`rke2_ignore_firewalld: true` ile dokunulmaz); fapolicyd çalışıyorsa kural eklenir.
- PSA: rol dosyayı `/etc/rancher/rke2/rke2-pss.yaml`'a yazar — `pod-security-admission-config-file` bu yol olmalı
  (upstream örneği farklı yol veriyor).

## Test

```bash
ansible-playbook -i <envanter> site.yml --syntax-check
ansible-playbook -i <envanter> site.yml --check --tags always      # yalnız preflight + /tmp kontrolü
.venv/bin/ansible-lint roles && .venv/bin/yamllint -c .yamllint roles docs/kurum_ornek_envanter
```
Bu fork'ta doğrulananlar (2026-09-29): syntax-check (site/upgrade) · preflight olumlu + 4 olumsuz durum ·
`/tmp` noexec→exec→noexec (yalıtılmış mount namespace'inde gerçek koşu) · `/opt/rke2` sürüm algısı ·
ansible-lint: upstream ile aynı (0 hata, 59 upstream uyarısı) · yamllint temiz. Gerçek bir RKE2 kümesinde
**henüz koşulmadı** — ilk saha koşusu `--check --diff` ile.

## Upstream güncellemesi

```bash
git fetch upstream && git merge upstream/main     # çakışma çoğunlukla KURUM satırlarında
```
Sonra "Test" bölümü. `ansible-core >= 2.17` gerekir (`meta/runtime.yml`).

## Değişiklik günlüğü

- **2026-09-29** — fork kuruldu (upstream `49f09d5`, v2.1.0+2). Yukarıdaki tablo. `indir.sh` burada denendi
  (1.33.13+rke2r2, 1.34.11+rke2r1 sha256 OK) sonra dosyalar silindi — air-gap dosyaları kurum sunucusunda indirilir.

- **2026-09-29** — `araclar/rancher_matris.py` (v2.15.2, v2.12.3, v2.11.3 ile denendi); `indir.sh --rancher/--os/--kuru`,
  sonda özet + uyum tablosu, bozuk indirmeyi yeniden indirme (sha256 bozma testiyle denendi).
- **2026-09-29** — SUC: preflight küme sürümü karşılaştırması (4 senaryo denendi), örnek envanterde `rke2_upgrade: false`.
