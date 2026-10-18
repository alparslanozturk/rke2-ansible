# Satellite + OpenSCAP: RKE2 node'ları için CIS Level 1 istisnaları

Kurumda RHEL 9/10 sunuculara CIS Level 1 Satellite üzerinden (OpenSCAP, ComplianceAsCode içeriği =
`scap-security-guide`) uygulanıyor. Bazı CIS kuralları RKE2'nin çalışması için gerekenlerle çelişir.
Bu klasördeki **tailoring dosyası** o kuralları yalnız RKE2 node'larının politikasında kapatır; geri kalan
CIS Level 1 aynen uygulanır.

Dosya: `rke2-cis-l1-tailoring.xml` — temel profil `xccdf_org.ssgproject.content_profile_cis_server_l1`,
yeni profil `xccdf_org.ssgproject.content_profile_cis_server_l1_rke2`.

## Neden gerekli (kanıt)

| Kural (SSG id) | CIS madde | Neden kapatılıyor |
|---|---|---|
| `sysctl_net_ipv4_conf_all_forwarding` | RHEL 10 L1 3.3.1.2 | Pod ağı IP yönlendirme ister |
| `sysctl_net_ipv4_conf_default_forwarding` | RHEL 10 L1 3.3.1.3 | Yeni arayüzler (pod veth, antrea-gw0) yönlendirmesiz açılır |
| `sysctl_net_ipv4_ip_forward` | RHEL 9 L1 3.3.1 (RHEL 10'da L2) | Aynı ayar, RHEL 9 içeriğindeki adı |
| `service_firewalld_enabled` | RHEL 10 L1 4.1.3 / RHEL 9 4.1.2 | Kurum kararı: firewalld kapalı (RKE2/CNI önerisi) |
| `firewalld_loopback_traffic_trusted` | RHEL 10 L1 4.1.5 / RHEL 9 4.2.2 | firewalld kapalı |
| `grub2_enable_selinux`, `selinux_not_disabled` | L1 1.3.1.2 / 1.3.1.4 | Kurum kararı: SELinux kapalı |

Kaynak: ComplianceAsCode `products/rhel10/controls/cis_rhel10.yml` (CIS RHEL 10 v1.0.1) ve
`products/rhel9/controls/cis_rhel9.yml` (v2.0.0), 2026-10-18.

**Asıl tehlike:** OpenSCAP'in sysctl düzeltmesi (`shared/templates/sysctl/bash.template`) değeri **anında**
`sysctl -w ...=0` yapar ve `/etc/sysctl.d/net_ipv4_conf_all_forwarding.conf` gibi bir dosyaya yazar. Çalışan
bir RKE2 node'unda düzeltme yeniden koşarsa pod ağı o an kesilir. Playbook'un `zz-rke2.conf` dosyası reboot'ta
değeri geri getirir (denendi: SSG'nin RHEL 9 ve RHEL 10 düzeltme kodu gerçekten çalıştırıldı, reboot taklidinde
`ip_forward=1`), ama aradaki kesintiyi yalnız bu tailoring önler.

## Satellite'ta kullanım

Satellite'ta **denenmedi** — adımlar Satellite/foreman_openscap arayüzüne göre; kurumda doğrulanacak.

1. **Hosts → Compliance → Tailoring Files → New Tailoring File**: `rke2-cis-l1-tailoring.xml` dosyasını yükle.
2. **Hosts → Compliance → Policies**: RKE2 node'ları için ayrı politika (ya da mevcut CIS politikasının kopyası):
   SCAP içeriği `ssg-rhel10-ds.xml` (RHEL 9 için `ssg-rhel9-ds.xml`), profil **CIS Level 1 Server**,
   tailoring dosyası bu dosya, tailored profil **CIS Level 1 Server - RKE2 node (kurum)**.
3. Politikayı yalnız RKE2 host group'una ata. Düzeltme (remediation) bu profil ile koşulursa yukarıdaki kurallara
   dokunmaz.

Komut satırından: `hammer tailoring-file --help` ve `hammer policy --help` ile seçenekleri kontrol et.

Yerelde kontrol (Satellite'a yüklemeden önce):

```bash
oscap info rke2-cis-l1-tailoring.xml
oscap xccdf generate fix --tailoring-file rke2-cis-l1-tailoring.xml \
  --profile xccdf_org.ssgproject.content_profile_cis_server_l1_rke2 --fix-type bash \
  /usr/share/xml/scap/ssg/content/ssg-rhel10-ds.xml | grep -c '^# BEGIN fix'
```

Burada (AlmaLinux 10 SSG 0.1.82 içeriğiyle) sonuç: CIS L1 324 kural → tailored 318 kural (6 kural düştü;
`ip_forward` RHEL 10 L1'de zaten yok).

## Yeniden üretme

```bash
autotailor --title "CIS Level 1 Server - RKE2 node (kurum)" \
  -p xccdf_org.ssgproject.content_profile_cis_server_l1_rke2 \
  -u sysctl_net_ipv4_ip_forward -u sysctl_net_ipv4_conf_all_forwarding -u sysctl_net_ipv4_conf_default_forwarding \
  -u service_firewalld_enabled -u firewalld_loopback_traffic_trusted \
  -u grub2_enable_selinux -u selinux_not_disabled \
  -o rke2-cis-l1-tailoring.xml /usr/share/xml/scap/ssg/content/ssg-rhel10-ds.xml cis_server_l1
```

`autotailor` `openscap-utils` paketindedir. Kurumda IPv6 yok (Alp, 2026-10-18) → IPv6 yönlendirme kuralları
(`sysctl_net_ipv6_conf_*_forwarding`) CIS'te kalır, istisna gerekmez.

## Kapsam (Alp, 2026-10-18)

Kesin kararlar: **SELinux kapalı, firewalld kapalı, IPv6 yok.** Kurumda yalnız işletim sistemi **CIS Level 1**
uygulanıyor; PCI-DSS, CIS Level 2, STIG ve Kubernetes CIS profili şimdilik kapsam dışı — zamanı gelince
değerlendirilecek. (Not: SSG'nin PCI-DSS v4.0.1 profili SELinux enforcing + firewalld açık ister; CIS L2 overlay
modülünü kapatır — o gün bu klasördeki istisnalar yeniden ele alınmalı.)

Bilinen ve kabul edilen sapmaların tam listesi (SELinux, firewalld, `/var/lib/rancher` ayrı bölüm değil, `hostPath`):
`KURUM.md` §4 "Bilinen ve kabul edilen sapmalar".

## İstisna gerektirmeyen ama bilinmesi gerekenler (RHEL 10 L1)

| CIS kuralı | RKE2'ye etkisi |
|---|---|
| `/tmp`, `/var/tmp`, `/dev/shm` noexec | Playbook tarball'ı `/var/lib/rancher` altında açar (`rke2_tarball_tmp_dir`); `/tmp`'ye dokunmaz |
| `/var` nodev + nosuid | Konteyner içinde setuid programlar yetki yükseltemez (ör. imaj içindeki `sudo`). Çoğu iş yükü etkilenmez |
| `/var/lib/rancher` | CIS L1 noexec istemez; noexec ise playbook baştan durur |
| `sctp` modülü kapalı (3.2.6) | Kubernetes SCTP servisleri çalışmaz; gerekiyorsa `kernel_module_sctp_disabled` da tailoring'e eklenir |
| `rp_filter = 1` (3.3.1.12) | Antrea Egress gerektiğinde kendi arayüzünde `rp_filter=2` yapar (antrea `route_linux.go`) — işlem gerekmez |
| AIDE (6.1.1/6.1.2) | Varsayılan `aide.conf` `/usr`'ü tarar, `/var/lib`'i taramaz → SUC her yükseltmede `/usr/local/bin/rke2` değişikliği raporlar; beklenen durum, yükseltmeden sonra `aide --update` |
| umask 027 (5.4.2.6, 5.4.3.3) | Playbook dosya izinlerini açıkça verir; etkisi beklenmez |
| CIS **L2** `kernel_module_overlayfs_disabled` | containerd overlayfs kullanır — L2 uygulanırsa RKE2 çalışmaz (kurumda L1) |
