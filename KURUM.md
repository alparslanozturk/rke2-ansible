# RKE2 Kurulum Rehberi (Kurum)

Bu depo, kurumdaki RKE2 (Kubernetes) kümelerini **kurmak** ve kümeye **yeni sunucu eklemek** için kullandığımız
Ansible playbook'udur. Rancher'ın resmi playbook'unu (rancherfederal/rke2-ansible) temel alır; kurumumuza göre
küçük eklemeler yaptık.

Ortamımız: RHEL 8 / 9 / 10 · CIS güvenlik ayarları · internetsiz (air-gap) kurulum · ağ eklentisi Antrea ·
yükseltmeleri system-upgrade-controller (SUC) yapıyor.

> Teknik ayrıntılar (neyi değiştirdik, nasıl test ettik): `TEKNIK.md`

**Önemli — kurum sunucusu yalnız GitHub'a erişir.** Sahanın ihtiyaç duyduğu dış dosya/bilgi GitHub'da değilse
**repoya peşin konur**, araçlar önce repodakini kullanır:

| Gerekli şey | Nereden | Sahada |
|---|---|---|
| Rancher destek matrisi | suse.com (erişilemez) | **repoda**: `araclar/matris/` (v2.11.3, v2.14.3–v2.14.6, v2.15.x) |
| RKE2 kurulum betiği (`install.sh`) | get.rke2.io (erişilemez) | **repoda**: `airgap/install.sh` |
| RKE2 tarball + imajlar, rke2-selinux, Antrea | github.com | `airgap/indir.sh` indirir |
| En son sürüm bilgisi | github.com (git etiketleri) | `indir.sh` / araçlar sorgular |

---

## 1. Hangi RKE2 sürümünü kuracağım?

RKE2 sürümünü **Rancher sürümüne göre** seçiyoruz. Rancher sürümünü yaz, desteklenen RKE2 sürümlerini göster.
Kurum sunucusu suse.com'a erişemediği için matris sayfaları **repoda** duruyor (`araclar/matris/`) — araç
internetsiz çalışır. Repoda olmayan bir sürüm için internetli makinede `araclar/rancher_matris.py --kaydet v2.x.y`
çalıştırıp commit/push et. Repodaki sürümler: `araclar/rancher_matris.py --liste`.

```bash
araclar/rancher_matris.py v2.15.2 rhel9
```

Örnek sonuçlar (2026-09-29):

| Rancher | Kurulabilecek RKE2 sürümleri | Desteklenen RHEL |
|---|---|---|
| v2.15.2 | 1.34 · 1.35 · 1.36 | 8.10, 9.6, 9.8, 10.0, 10.2 |
| **v2.14.3 (kurumda kullanılan)** | **1.33 · 1.34 · 1.35** | 9.6, 9.7, 9.8 (RHEL 9) |
| v2.12.3 | 1.31 · 1.32 · 1.33 | 8.8, 8.10 |
| v2.11.3 | 1.30 · 1.31 · 1.32 | 8.8–8.10, 9.3–9.5 |

Mevcut kümeler uygun mu? (Rancher'ın kendi kümesi = **upstream**, Rancher'ın yönettikleri = **downstream**):

```bash
araclar/rancher_matris.py v2.14.3 rhel9 --upstream v1.33.13+rke2r1 --downstream v1.33.13+rke2r1
# → her biri için ✅ UYGUN / ❌ DESTEK DIŞI
```

**Dikkat:** Listede olmayan sürüm kurulmaz. Örneğin Rancher v2.15.2 artık **1.33'ü desteklemiyor**.

### Antrea (ağ eklentisi) hangi sürüm?

Antrea, RKE2 ile gelmez; `antrea.yaml` dosyasını biz koyarız, RKE2 kurar. Her Antrea sürümü belirli
Kubernetes sürümlerini destekler:

```bash
araclar/antrea_surum.py 1.34        # 1.34 için hangi Antrea? → tablo + öneri
```

| Antrea | Desteklediği Kubernetes |
|---|---|
| v2.4 | 1.30 – 1.33 |
| v2.5 | 1.31 – 1.34 |
| v2.6 | 1.32 – 1.35 |
| v2.7 | 1.33 – 1.36 |

Kümede şu an hangi Antrea var? `grep image: antrea.yaml` ya da
`kubectl -n kube-system get ds antrea-agent -o jsonpath='{.spec.template.spec.containers[0].image}'`.
Kubernetes'i yükseltmeden önce Antrea'nın yeni sürümü desteklediğine bak; desteklemiyorsa önce Antrea'yı yükselt.

---

## 2. Kurulum

### Adım 1 — Dosyaları indir (internete çıkabilen kurum sunucusunda)

```bash
airgap/indir.sh --rancher v2.15.2 --os rhel9
```

Rancher'ın desteklediği RKE2 sürümlerini indirir, bozuk olup olmadığını kontrol eder ve sonunda bir tablo
gösterir. Neyin ineceğini önceden görmek için başına `--kuru` ekle. Tek sürüm için: `airgap/indir.sh v1.35`.

Antrea'yı da birlikte almak için `--antrea v2.7` ekle: `antrea.yml` iner ve kurum imaj deposuna konması gereken
imajların listesi tabloda görünür (`airgap/antrea/<sürüm>/imajlar.txt`).

### Adım 2 — Küme dosyalarını hazırla

```bash
cp -r docs/kurum_ornek_envanter inventory/<küme-adı>
```

Sonra şunları düzenle:

- `host.yml` → sunucuların IP'leri (ilk 3'ü yönetici sunucular, gerisi işçi sunucular)
- `group_vars/all.yml` → kurulacak **RKE2 sürümü** ve kümenin **API adresi** (sanal IP ya da ilk sunucunun IP'si)
- `files/registries.yaml` → kurum imaj deposu adresi
- `pre_deploy_manifests/` → `antrea.yaml` dosyasını buraya koy (`airgap/antrea/<sürüm>/antrea.yml`'den kopyala)

### Adım 3 — Önce dene (hiçbir şey değiştirmez)

```bash
ansible-playbook -i inventory/<küme-adı>/host.yml site.yml --check --diff
```

### Adım 4 — Kur

```bash
ansible-playbook -i inventory/<küme-adı>/host.yml site.yml
```

### Var olan kümeye yeni sunucu ekleme

1. Yeni sunucuları `host.yml`'de işçi listesinin (`rke2_agents`) **sonuna** ekle.
   Yönetici sunucu ekliyorsan yönetici listesinin sonuna ekle; yönetici sayısı tek olmalı (3, 5).
2. `all.yml`'deki RKE2 sürümü **kümenin şu anki sürümüyle aynı** olmalı (`kubectl get nodes` ile bak).
3. Yalnız yeni sunucularda çalıştır; mevcut sunuculara dokunulmaz:

```bash
ansible-playbook -i inventory/<küme-adı>/host.yml site.yml --limit '<yeni1>,<yeni2>' --check --diff
ansible-playbook -i inventory/<küme-adı>/host.yml site.yml --limit '<yeni1>,<yeni2>'
```

**Farklı donanımlı sunucu (ör. fiziksel GPU H200):** playbook yerine **elle** eklenir — adım adım:
`docs/MANUEL-WORKER.md` (aynı sürümü kur, kümenin adresi + token'ı yaz, `rke2-agent`'ı başlat).

Bir şey eksik ya da yanlışsa playbook **başlamadan durur** ve nedenini Türkçe söyler (sürüm yazılmamış, dosya
indirilmemiş, API adresi boş, sürüm kümeyle uyuşmuyor…).

---

## 3. Yükseltme

Kümeleri bu playbook **yükseltmez**. Yükseltmeyi **system-upgrade-controller (SUC)** yapıyor. SUC sunucuları
sırayla boşaltıp yeni sürüme geçirir.

Yükseltmeden sonra yapılacak tek şey:

1. `all.yml`'de RKE2 sürümünü kümenin yeni sürümüne güncelle.
2. O sürümü `airgap/indir.sh` ile indir.

Bunu unutursan, bir sonraki sunucu eklemede playbook farkı görür ve durur. Böylece yeni sunucu yanlış sürümle
kurulmaz.

_Kurumdaki SUC ayarları, sürüm geçmişi ve deneyimler buraya eklenecek._

---

## 4. Bilinmesi gerekenler

- **/tmp:** CIS ayarlarında `/tmp` üzerinde program çalıştırılamaz (`noexec`). Playbook kurulum sırasında
  `/tmp`'yi geçici olarak açar, bitince geri kapatır. Kurulum yarıda kesilirse elle kapat:
  `mount -o remount,noexec /tmp`.
- **IP yönlendirme:** Kubernetes için `net.ipv4.ip_forward = 1` olmalı. İşletim sisteminin CIS ayarı bunu 0 yapıyor;
  playbook 1'i kalıcı yazar (`/etc/sysctl.d/99-zz-rke2.conf`, CIS dosyalarından sonra okunur), yeniden başlatmada bozulmaz.
- **SELinux:** kurumda kapalı. (Açılırsa: `RKE2_SELINUX=1 airgap/indir.sh …` paketi indirir, playbook kurar.)
- **Kubernetes CIS profili kullanılmıyor.** Sunucuların CIS Level 1'i Satellite'ta ayrıca uygulanıyor.
- **Güvenlik duvarı:** `firewalld` kapatılır (kurum imajlarında zaten kapalı).
- **Antrea imajları** RKE2 paketinde gelmez; kurum imaj deposunda olmalıdır.

### CIS Level 1 (Satellite / OpenSCAP) ile çakışabilecekler — kurumda SCAP raporuyla kontrol edilecek

Kurumda RHEL sunuculara CIS Level 1 Satellite üzerinden (OpenSCAP) uygulanıyor. Aşağıdaki kurallar RKE2'nin
çalışması için gerekenlerle çelişebilir; SCAP raporunda karşılığına bakıp **istisna** mı, **ayar** mı karar verilecek:

| CIS kuralı | RKE2'ye etkisi | Karar (Alp, 2026-09-29) |
|---|---|---|
| `/tmp` noexec | Kurulum `/tmp`'den program çalıştırır | Kurulum sırasında geçici açılır, sonra kapanır ✅ |
| firewalld açık olmalı | RKE2 ile çakışır | **Kapalı** (kurum imajlarında zaten kapalı) ✅ |
| `net.ipv4.ip_forward = 0` | Pod ağı bozulur | **1 yapılır**, kalıcı (`99-zz-rke2.conf`) ✅ |
| SELinux | — | **Kapalı** ✅ |
| Kubernetes CIS profili | — | **Kullanılmıyor** ✅ |
| `/var/lib/rancher` noexec | RKE2 programları çalışmaz | noexec olmamalı (kontrol edilecek) |

_Kurumdaki SCAP raporu, uygulanmayan kurallar ve alınan istisnalar buraya eklenecek._

---

## 5. Geliştirme önerileri

### Kurulum
1. **Sunucu ekleme için ayrı, kısa bir komut** (`playbooks/sunucu-ekle.yml`): yalnız yeni sunucular çalışır,
   sürüm kontrolü zorunludur, sonunda yeni sunucuların "Ready" olduğunu bekleyip tablo gösterir.
2. **Kurulum sonrası kontrol raporu:** tüm sunucular hazır mı, Antrea çalışıyor mu, sürümler aynı mı —
   tek ekranda.
3. **Antrea imaj kontrolü:** `antrea.yaml` içindeki imajlar kurum deposunda var mı, kurulumdan **önce**
   kontrol edilsin. Eksikse yeni sunucu "NotReady" kalıyor.
4. **Yeni sunucu ön kontrolü:** swap kapalı mı, `/var` diski yeterli mi, saat doğru mu, sunucu adı tekil mi,
   yönetici sunuculara (9345/6443) erişebiliyor mu.
5. **Küme dosyası üretici:** küme adı + IP listesi verince `inventory/<küme>` klasörünü hazırlayan küçük bir
   betik (elle yazım hatalarını önler).

### Yükseltme (SUC)
1. **Hazır SUC plan dosyaları:** yönetici ve işçi sunucular için örnek planlar ve internetsiz ortam için
   gereken imaj listesi (SUC imajı + `rke2-upgrade:<sürüm>`).
2. **Yükseltme öncesi kontrol:** hedef sürüm Rancher'ın desteklediği listede mi, tüm sunucular hazır mı,
   atlanan ara sürüm var mı (1.33'ten doğrudan 1.35'e geçilmez).
3. **Yükseltme öncesi etcd yedeği:** tek komutla `rke2 etcd-snapshot save`.

### Genel
- Rancher sürümü `all.yml`'e tek satır olarak yazılsın; seçilen RKE2 sürümü desteklenmiyorsa playbook uyarsın.
  Matris bilgisi `indir.sh` sırasında kaydedilir, internetsiz ortamda da kullanılabilir.

---

## Değişiklik geçmişi

- **2026-09-29** — Depo kuruldu. Eklenenler: kurulum öncesi kontroller, `/tmp` görevi, SELinux paketi,
  internetsiz dosya indirici (sonda tablo), Rancher sürüm tablosu, SUC uyumu (sürüm farkı kontrolü),
  kurum örnek küme dosyaları. Elle worker ekleme rehberi (`docs/MANUEL-WORKER.md`). Antrea sürüm tablosu (`araclar/antrea_surum.py`) ve `indir.sh --antrea`.
