# rke2-ansible — kurum fork'u

Kurumun RKE2 kümelerini (RHEL 9 · CIS · air-gap · Antrea) kuran/genişleten playbook. Temel:
**rancherfederal/rke2-ansible 2.x** (`upstream/main`). İlke: **upstream'e az dokun** — her değişiklik küçük, `KURUM`
ile işaretli ve bu dosyada listeli; böylece upstream güncellemesi `git merge upstream/main` ile alınır.

| Remote | Adres | Rol |
|---|---|---|
| `upstream` | rancherfederal/rke2-ansible | temel (push kapalı) |
| `hepapi` | hepapi/rke2-ansible | danışman fork'u — `hepapi` dalı **eski 1.x** (2023-11), yalnız referans (push kapalı) |
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
| Rancher matrisi okuyucu | `araclar/rancher_matris.py` | Rancher sürümü → desteklenen RKE2 hatları + RHEL sürümleri (suse.com matrisinden) |
| Kurum örnek envanteri | `docs/kurum_ornek_envanter/` | sahadaki `inventory/<küme>/` yapısı: Antrea, CIS, PSA, audit, kayıt aynası |

Yeni değişkenler (`roles/rke2/defaults/main.yml`, hepsi kapatılabilir): `rke2_require_pinned_version: true`,
`rke2_tmp_remount_exec: true`, `rke2_tmp_restore_noexec: true`, `rke2_selinux_rpm_local_path: ""`.

## Kullanım

**0) Hangi RKE2 sürümü?** Kurumda RKE2 sürümü **Rancher sürümüne** göre seçilir (SUSE Rancher destek matrisi,
`https://www.suse.com/suse-rancher/support-matrix/all-supported-versions/rancher-v2-15-2/` biçiminde).
OS yalnız RHEL 8 / 9 / 10.
```bash
araclar/rancher_matris.py v2.15.2 rhel9     # yalnız tablo
```

Matristen okunan örnekler (2026-09-29; güncel değer için her zaman betiği çalıştır):

| Rancher | Rancher'ın kendi kümesi (RKE2) | Downstream RKE2 hatları → en son kararlı | RKE2 için RHEL |
|---|---|---|---|
| v2.15.2 | v1.34 … v1.36 | 1.36 → v1.36.4+rke2r1 · 1.35 → v1.35.8+rke2r1 · 1.34 → v1.34.11+rke2r1 | 10.2, 10.0, 9.8, 9.6, 8.10 |
| v2.12.3 | v1.31 … v1.33 | 1.33 → v1.33.13+rke2r2 · 1.32 → v1.32.13+rke2r2 · 1.31 → v1.31.14+rke2r2 | 8.10, 8.8 (RHEL 9 süzgeciyle boş) |
| v2.11.3 | v1.30 … v1.32 | 1.32 → v1.32.13+rke2r2 · 1.31 → v1.31.14+rke2r2 · 1.30 → v1.30.14+rke2r4 | 9.3–9.5, 8.8–8.10 |

- **Matris dışı hat kurulmaz/yükseltilmez.** Rancher v2.15.2'de **1.33 destek dışı** (en düşük 1.34) — 1.33
  kümeler için önce 1.34'e yükseltme planı, ya da Rancher'ın o sürümü desteklemesi gerekir.
- "Rancher-provisioned / imported" sütunu: kümeyi Rancher mi kurdu, biz mi kurup içe aldık (bu playbook = imported).
- Kaynaklar: RKE2 dosyaları `github.com/rancher/rke2/releases/download/<sürüm>/`, en son sürüm aynı deponun git
  etiketlerinden (update.rke2.io kanal servisi güvenilir değil — denemede 404 verdi), SELinux
  `github.com/rancher/rke2-selinux/releases`.

**1) Air-gap dosyaları** (repo içinden, internete çıkabilen kurum sunucusunda):
```bash
airgap/indir.sh --rancher v2.15.2 --os rhel9     # Rancher'ın desteklediği tüm RKE2 hatları
airgap/indir.sh --rancher v2.15.2 v1.35          # yalnız bir hat
airgap/indir.sh --kuru --rancher v2.15.2         # indirmeden: ne inecek + tablo
airgap/indir.sh v1.34.11+rke2r1                  # Rancher'sız, tam sürüm
```
Sonda iki tablo basar: **Özet** (sürüm · dosya · boyut · sha256 OK/HATALI) ve verilmişse **Rancher uyum tablosu**.
Bozuk/yarım eski indirme sha256'da yakalanıp bir kez yeniden indirilir. Çıktı `airgap/<sürüm>/` +
`airgap/selinux/` (git dışı). Antrea kullandığımız için (`cni: none`) yalnız **core** imajlar iner; Antrea imajları
kayıt aynasından gelir (`RKE2_IMAJ=tum` tüm CNI imajlarını indirir).

**2) Envanter:** `cp -r docs/kurum_ornek_envanter inventory/<küme>` → `host.yml`, `group_vars/all.yml`
(`rke2_install_version`, `rke2_kubernetes_api_server_host`), `files/registries.yaml`, `pre_deploy_manifests/antrea.yaml`.
`inventory/` git dışıdır (upstream `.gitignore`) — gerçek envanterler sahada kalır.
Not: `site.yml` ile koşunca `playbook_dir` = `<repo>/playbooks` olur; bu yüzden örnekte yollar
`{{ playbook_dir }}/../airgap/...` ve `{{ inventory_dir }}/files/...` biçiminde (upstream örneklerindeki
`{{ playbook_dir }}/docs/...` yolları bu nedenle yanlış yere bakar).

**3) Yeni küme:**
```bash
ansible-playbook -i inventory/<küme>/host.yml site.yml --check --diff    # kuru
ansible-playbook -i inventory/<küme>/host.yml site.yml
```

**4) Mevcut kümeye node ekleme:** yeni makineleri `rke2_agents` altına (sunucuysa `rke2_servers`'ın **sonuna**) ekle,
sonra yalnız onlarla koş — mevcut node'lara dokunulmaz, token ilk sunucudan `delegate_to` ile okunur:
```bash
ansible-playbook -i inventory/<küme>/host.yml site.yml --limit '<yeni1>,<yeni2>' --check --diff
ansible-playbook -i inventory/<küme>/host.yml site.yml --limit '<yeni1>,<yeni2>'
```
Şartlar (preflight denetler): `rke2_install_version` ve tarball kümenin **mevcut** sürümü;
`rke2_kubernetes_api_server_host` mevcut node'lardaki `grep ^server: /etc/rancher/rke2/config.yaml` ile aynı.

**5) Sürüm yükseltme (1.33 → 1.34):** `airgap/indir.sh v1.34` → `all.yml`'de `rke2_install_version` →
`ansible-playbook -i … playbooks/upgrade.yml`. Upstream'in bu playbook'u node'ları **drain etmez** ve başta onay
sorar; sunucular tek tek, sonra agent'lar tek tek yükselir. Kritik iş yükü varsa önce elle `kubectl drain`.

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

## Sıradaki adaylar

Antrea imajlarını manifestten okuyup aynaya/arşive alan betik · drain'li yükseltme · node ekleme için sahadaki
kümede ilk `--check --diff` koşusunun sonucuna göre ince ayar.
