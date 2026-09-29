# RKE2 Kurulum Rehberi (Kurum)

Bu depo, kurumdaki RKE2 (Kubernetes) kümelerini **kurmak** ve kümeye **yeni sunucu eklemek** için kullandığımız
Ansible playbook'udur. Rancher'ın resmi playbook'unu (rancherfederal/rke2-ansible) temel alır; kurumumuza göre
küçük eklemeler yaptık.

Ortamımız: RHEL 8 / 9 / 10 · CIS güvenlik ayarları · internetsiz (air-gap) kurulum · ağ eklentisi Antrea ·
yükseltmeleri system-upgrade-controller (SUC) yapıyor.

> Teknik ayrıntılar (neyi değiştirdik, nasıl test ettik): `TEKNIK.md`

---

## 1. Hangi RKE2 sürümünü kuracağım?

RKE2 sürümünü **Rancher sürümüne göre** seçiyoruz. Rancher sürümünü yaz, desteklenen RKE2 sürümlerini göster:

```bash
araclar/rancher_matris.py v2.15.2 rhel9
```

Örnek sonuçlar (2026-09-29):

| Rancher | Kurulabilecek RKE2 sürümleri | Desteklenen RHEL |
|---|---|---|
| v2.15.2 | 1.34 · 1.35 · 1.36 | 8.10, 9.6, 9.8, 10.0, 10.2 |
| v2.12.3 | 1.31 · 1.32 · 1.33 | 8.8, 8.10 |
| v2.11.3 | 1.30 · 1.31 · 1.32 | 8.8–8.10, 9.3–9.5 |

**Dikkat:** Listede olmayan sürüm kurulmaz. Örneğin Rancher v2.15.2 artık **1.33'ü desteklemiyor**.

---

## 2. Kurulum

### Adım 1 — Dosyaları indir (internete çıkabilen kurum sunucusunda)

```bash
airgap/indir.sh --rancher v2.15.2 --os rhel9
```

Rancher'ın desteklediği RKE2 sürümlerini indirir, bozuk olup olmadığını kontrol eder ve sonunda bir tablo
gösterir. Neyin ineceğini önceden görmek için başına `--kuru` ekle. Tek sürüm için: `airgap/indir.sh v1.35`.

### Adım 2 — Küme dosyalarını hazırla

```bash
cp -r docs/kurum_ornek_envanter inventory/<küme-adı>
```

Sonra şunları düzenle:

- `host.yml` → sunucuların IP'leri (ilk 3'ü yönetici sunucular, gerisi işçi sunucular)
- `group_vars/all.yml` → kurulacak **RKE2 sürümü** ve kümenin **API adresi** (sanal IP ya da ilk sunucunun IP'si)
- `files/registries.yaml` → kurum imaj deposu adresi
- `pre_deploy_manifests/` → `antrea.yaml` dosyasını buraya koy

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
- **SELinux:** RHEL'de SELinux açıksa `rke2-selinux` paketi gerekir. `indir.sh` bu paketi de indirir, playbook
  kurar.
- **CIS profili:** RKE2 çalışan bir sunucuda CIS çekirdek ayarları değişirse sunucu **yeniden başlatılır**.
- **Güvenlik duvarı:** `firewalld` kapatılır (Kubernetes böyle istiyor).
- **Antrea imajları** RKE2 paketinde gelmez; kurum imaj deposunda olmalıdır.

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
  kurum örnek küme dosyaları.
