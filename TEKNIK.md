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
| CIS `/tmp noexec` | `tarball_tmp.yml` | tarball geçici dizinde açılıp oradan `rke2 -v` çalıştırılıyor; noexec'te düşüyordu. Upstream'in belgelenmemiş `tarball_tmp_dir`'i (`tarball_install.yml:6`) data-dir'in üstüne (`/var/lib/rancher`) yönlendirilir; orası noexec ise dur. (2026-10-18'e kadar `/tmp` remount ediliyordu — `tmp_exec/tmp_restore.yml` silindi) |
| `--check` düzeltmeleri | `check_node_ready.yml`, `main.yml` | upstream PR #350 (`node_metrics.status is defined`; `uri` check modunda atlanır). `tempfile` check modunda atlanır → tarball kurulumu `--check`'te atlanır; kurulu olmayan node'da `config.yaml` farkı gösterilip `end_host` (servis/token/API yok) |
| SELinux enforcing ön kontrolü | `preflight.yml` | kurumda SELinux kapalı; enforcing node + `rke2_selinux_rpm_local_path` boş → dur (`rke2_require_selinux_policy`) |
| İşletim sistemi uyarısı | `preflight.yml` | RHEL ailesi 8/9/10 değilse uyar |
| Satellite CIS L1 tailoring | `docs/satellite/` | OpenSCAP düzeltmesi forwarding'i anında 0 yapar; RKE2 node politikasından 6 kural çıkarılır (autotailor ile üretildi, oscap ile doğrulandı) |
| rke2-selinux RPM (isteğe bağlı) | `selinux_rpm.yml` | SELinux enforcing + tarball kurulumu politikasız çalışmaz; upstream yalnız dokümanda uyarıyor |
| Kurulu sürüm `/opt/rke2`'de de aranır | `previous_install.yml` | `/usr/local` bağlama noktasıysa kurulum `/opt/rke2`'ye gider; upstream sürümü bilemiyor → gereksiz yeniden açma/restart |
| `in groups[..][0]` → `==` | `main.yml`, `roles/testing` | alt-dize eşleşmesi (`k8s1` ⊂ `k8s10`) ilk-sunucu görevlerini yanlış makinede koşturabilirdi |
| authn-webhook yolunda eksik `/` | `configure_rke2.yml` | dosya `/var/lib/rancher/rke2kube-api-...` gibi yanlış yere yazılıyordu |
| Air-gap indirici | `airgap/indir.sh` | tarball + core imajlar + rke2-selinux, sha256 doğrulamalı |
| Küme sürümü = envanter sürümü | `preflight.yml` | SUC kümeyi yükseltince envanter geride kalır; ilk sunucudan node sürümleri okunur, `rke2_upgrade: false` iken fark varsa dur, değilse uyar |
| Antrea uyum tablosu | `araclar/antrea_surum.py` + `araclar/matris/antrea-uyum.txt` (çevrimdışı; `--yenile` internetten yeniden hesaplar; `--antrea` kümedeki sürümü kontrol eder) | Antrea kuralı (docs/versioning.md): her minor, çıktığı gün desteklenen son 4 K8s'i destekler; resmi tablo yok → Antrea X.Y.0 ve K8s 1.N.0 çıkış tarihlerinden (GitHub release sayfaları) hesaplanır |
| `indir.sh --antrea` | `airgap/indir.sh` | `releases/download/<v>/antrea.yml` + `imajlar.txt` (agent/controller); `v2.7` → en son yama (git etiketleri) |
| Kalıcı IP yönlendirme | `sysctl_forward.yml` | CIS L1: RHEL 9 `ip_forward=0` (3.3.1), RHEL 10 `conf.all/default.forwarding=0` (3.3.1.2/3); SSG bunları `/etc/sysctl.d/net_ipv4_*.conf` drop-in'lerine yazar (`sysctl_remediate_drop_in_file: true`). Dosya `zz-rke2.conf` (eski `99-zz-` "net_" drop-in'lerinden ÖNCE okunuyordu → reboot'ta 0). İki eşdeğer satır (`ip_forward=1`, `conf.all.forwarding=1`): SSG düzeltmesi yalnız kendi anahtarının satırını yorumlar. Koşu anında üç değer denetlenir, forwarding=0 yazan dosya varsa uyarı. `rke2_ip_forward: true` |
| `install.sh` repoda | `airgap/install.sh` | Saha yalnız GitHub'a erişir; get.rke2.io = github.com/rancher/rke2 `install.sh` (2026-09-30 birebir aynı, sha256 36826294…). Güncelleme: `RKE2_INSTALL_GUNCELLE=1 airgap/indir.sh …` (raw.githubusercontent.com) |
| Çevrimdışı Rancher matrisi | `araclar/matris/rancher-v2-X-Y.txt` | Kurum suse.com'a erişemiyor; sayfalar ayıklanmış düz metin olarak repoda (v2.11.3, v2.14.3–v2.14.6, v2.15.1–v2.15.2). Araç önce dosyayı okur, yoksa internete çıkar; `--kaydet`/`--liste` |
| Rancher matrisi okuyucu | `araclar/rancher_matris.py` | Rancher sürümü → desteklenen RKE2 hatları + RHEL sürümleri (suse.com matrisinden) |
| Kurum örnek envanteri | `docs/kurum_ornek_envanter/` | sahadaki `inventory/<küme>/` yapısı: Antrea, CIS, PSA, audit, kayıt aynası |

Yeni değişkenler (`roles/rke2/defaults/main.yml`, hepsi kapatılabilir): `rke2_require_pinned_version: true`,
`rke2_tarball_tmp_dir: ""` (boş → data-dir'in üstü), `rke2_ip_forward: true`, `rke2_require_selinux_policy: true`,
`rke2_selinux_rpm_local_path: ""`. Kaldırılan: `rke2_tmp_remount_exec`, `rke2_tmp_restore_noexec` (envanterde kalırsa
etkisiz).

Önemli yollar: `site.yml` ile koşunca `playbook_dir` = `<repo>/playbooks` → örnek envanterde
`{{ playbook_dir }}/../airgap/...` ve `{{ inventory_dir }}/files/...` (upstream örneklerindeki
`{{ playbook_dir }}/docs/...` bu yüzden yanlış yere bakar). PSA dosyası rol tarafından
`/etc/rancher/rke2/rke2-pss.yaml`'a yazılır; `pod-security-admission-config-file` bu yol olmalı.

Kaynaklar: RKE2 dosyaları `github.com/rancher/rke2/releases/download/<sürüm>/`; en son sürüm aynı deponun git
etiketlerinden (update.rke2.io kanal servisi denemede 404 verdi); SELinux `github.com/rancher/rke2-selinux/releases`;
Rancher matrisi `suse.com/suse-rancher/support-matrix/all-supported-versions/rancher-v2-X-Y/`.

## RHEL 9 / CIS notları

- `/tmp noexec`: `/tmp`'ye dokunulmaz (`tarball_tmp.yml`). CIS L1 `/var` için yalnız nodev/nosuid ister.
- Neden RPM (Satellite custom repo) değil de tarball: RKE2 el8/el9/el10 RPM'leri GitHub'da var
  (`rancher/rke2-packaging` sürüm ekleri), ama SUC yükseltmesi ikiliyi `cp` ile değiştirir
  (`rancher/rke2-upgrade` `scripts/upgrade.sh` `replace_binary`) → RPM veritabanı eski sürümde kalır, `rpm -V`
  bozulur, sonraki `dnf update` geri alabilir. Yükseltme SUC'ta kaldıkça tarball doğru yöntem.
- RHEL 10 / Satellite / CIS L1 ayrıntıları (kural kimlikleri, kaynaklar, AIDE/SCTP/umask/rp_filter notları):
  `docs/satellite/README.md`.
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

Gerçek koşu denemeleri (2026-10-18, bu sunucu, AlmaLinux 10): `site.yml --check --diff` tam koşu — `/etc /usr
/var /opt /boot` salt-okunur bağlı ayrı mount namespace'inde (önce: `temp_dir.path` hatası; sonra rc 0) ·
tarball kurulumu noexec tmpfs `/tmp` ile (`/usr/local/*`, `/opt`, `/var/lib/rancher`, `/etc/systemd/system`
tmpfs; ikinci koşu hatasız) · `/var/lib/rancher` noexec → dur · `sysctl_forward.yml` `unshare -m -n` içinde CIS
drop-in'lerine karşı (1 1 1, ikinci koşu changed=0, `systemd-sysctl` reboot taklidi 1 1 1) · SSG'nin gerçek
`sysctl_net_ipv4_conf_{all,default}_forwarding` (RHEL 10 L1) ve `sysctl_net_ipv4_ip_forward` (RHEL 9 L1) bash
düzeltmeleri `zz-rke2.conf`'a karşı: anlık 0 0 0, reboot taklidi 1 1 1 · preflight `--limit` API kontrolü
(`ansible_facts`). Gerçek RKE2 kümesinde hâlâ koşulmadı.

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
- **2026-09-29** — Antrea: `araclar/antrea_surum.py` (v2.0–v2.7 tablosu hesaplandı), `indir.sh --antrea` (v2.7.0 indirildi, 2 imaj; sonra silindi).
- **2026-09-29** — Kurum kararları: SELinux kapalı, K8s CIS profili yok, firewalld kapalı → örnek envanter sadeleşti; `sysctl_forward.yml` (unshare -m -n ile CIS 0 dosyasına karşı gerçek koşu: 1, `sysctl --system` sonrası 1, ikinci koşu changed=0); indir.sh SELinux paketi artık isteğe bağlı (`RKE2_SELINUX=1`).
- **2026-09-29** — `docs/MANUEL-WORKER.md` (GPU/H200 gibi özel worker'ı elle ekleme); `indir.sh` `install.sh`'i de indirir. Not: resmi install.sh air-gap'te yalnız tam imaj paketini (`rke2-images.*`) tanır, core paketi elle `agent/images/`'a kopyalanır (install.sh kaynağından teyit). Rehber gerçek RKE2 üzerinde henüz denenmedi.
- **2026-09-30** — T29: matris sayfaları repoya (7 sürüm, 116 KB); `rancher_matris.py` çevrimdışı öncelikli. Test: `unshare -n` (ağsız) ile v2.14.3/--hatlar çalışıyor; dosya canlı sayfayla birebir aynı (diff); repoda olmayan sürümde yol gösteren hata.
- **2026-09-30** — T29 ek (saha ekran7, splsonatype01 offline): `indir.sh --kuru` artık ağsız çalışır — matris yerelden, github.com'a erişilemezse sürüm satırı "en son sürüm bulunamadı" notuyla gösterilir (rc 0); gerçek indirmede anlaşılır hata. `unshare -n` ile v2.14.3 ve v2.11.3 denendi.
- **2026-09-30** — İlke (Alp): saha yalnız GitHub'a erişir → dış bağımlılık repoya peşin. `install.sh` repoya alındı (get.rke2.io yerine); KURUM.md'ye kaynak/erişim tablosu.
- **2026-09-30** — T31: `rancher_matris.py --upstream/--downstream` (mevcut küme sürümleri matrise uygun mu). Ağsız test: v2.14.3'te upstream/downstream v1.33.13 ✅; v2.15.2'de ❌ (önce RKE2 ≥1.34).
- **2026-09-30** — T32 (saha ekran10: kubernetes/kubernetes ls-remote exit 128, model v2.3.0+1.33'ü yanlışlıkla uyumlu saydı): Antrea tablosu repoda, araç önce yerel dosyayı okur; `--antrea`. Veri Şef'in bağımsız hesabıyla birebir aynı. Ağsız test: v2.3.0+1.33 ❌ KURAL DIŞI, v2.7.0 ✅.
- **2026-10-18** — RHEL 10 + Satellite + CIS L1 (kaynak: ComplianceAsCode `cis_rhel10.yml` v1.0.1, `cis_rhel9.yml`
  v2.0.0): `/tmp` remount yerine `tarball_tmp_dir`; `zz-rke2.conf` (eski ad reboot'ta 0'a düşüyordu, denendi);
  `docs/satellite/` tailoring; SELinux enforcing ön kontrolü; `--check` düzeltmeleri (PR #350 + tempfile/end_host);
  preflight `ansible_facts` (ansible-core 2.24'te `INJECT_FACTS_AS_VARS` kalkıyor, upstream #370 — upstream'in kendi
  3 satırına dokunulmadı).
