# Kümeye elle worker ekleme (özel sunucular: fiziksel GPU, H200 vb.)

Sanal sunucular hep aynı olduğu için playbook ile eklenir (`KURUM.md`). Farklı donanımlı / farklı kurulumlu
sunucuları (ör. fiziksel **GPU H200**) elle ekliyoruz. Bu sunucu playbook'un `host.yml`'ine **yazılmaz**
(yazılırsa playbook onu da yönetmeye çalışır); takip için `host.yml`'e yorum satırı olarak not düşülebilir.

Kısaca: aynı RKE2 sürümünü kur → kümenin adresi ve anahtarını (token) yaz → `rke2-agent`'ı başlat.

---

## 0. Gerekenler

- Kümenin **şu anki RKE2 sürümü**: `kubectl get nodes` → VERSION (ör. `v1.34.11+rke2r1`). Yeni sunucu **aynı**
  sürümle kurulur.
- Bu sürümün dosyaları (internete çıkabilen sunucuda, repo içinden):
  ```bash
  airgap/indir.sh v1.34.11+rke2r1
  ```
  → `airgap/v1.34.11+rke2r1/` içinde `rke2.linux-amd64.tar.gz`, `rke2-images-core.linux-amd64.tar.zst`,
  `sha256sum-amd64.txt` ve `airgap/install.sh`. Hepsini yeni sunucuya, ör. `/root/rke2-dosyalar/` altına kopyala.
- Kümenin **API adresi** (VIP ya da bir yönetici sunucunun IP'si) — mevcut bir worker'da:
  `grep ^server: /etc/rancher/rke2/config.yaml`
- Kümenin **token**'ı — bir yönetici sunucuda: `cat /var/lib/rancher/rke2/server/node-token`
- Kurum imaj deposu ayarı: kümedeki `files/registries.yaml` (ya da mevcut bir worker'daki
  `/etc/rancher/rke2/registries.yaml`).

## 1. Sunucuyu hazırla

```bash
# IP yönlendirme (CIS 0 yazıyor; Kubernetes için 1 olmalı) — kalıcı
echo 'net.ipv4.ip_forward = 1' > /etc/sysctl.d/99-zz-rke2.conf
sysctl -w net.ipv4.ip_forward=1

systemctl disable --now firewalld 2>/dev/null   # kurum imajlarında zaten kapalı
swapoff -a                                       # ve /etc/fstab'daki swap satırını kapat
hostnamectl                                      # sunucu adı kümede TEKİL olmalı (node adı buradan gelir)
```

## 2. RKE2'yi kur (internetsiz)

```bash
cd /root/rke2-dosyalar
INSTALL_RKE2_TYPE=agent INSTALL_RKE2_ARTIFACT_PATH=/root/rke2-dosyalar sh install.sh

# install.sh yalnız "tam" imaj paketini tanır; biz "core" kullanıyoruz → elle kopyala
mkdir -p /var/lib/rancher/rke2/agent/images
cp rke2-images-core.linux-amd64.tar.zst /var/lib/rancher/rke2/agent/images/
```

`install.sh` programları `/usr/local` altına kurar (`/usr/local` ayrı bir bağlama noktasıysa `/opt/rke2`).
`/tmp` noexec olsa da sorun olmaz — bu yöntem `/tmp`'den program çalıştırmaz.

## 3. Ayar dosyalarını yaz

```bash
mkdir -p /etc/rancher/rke2
cp registries.yaml /etc/rancher/rke2/registries.yaml

cat > /etc/rancher/rke2/config.yaml <<'EOF'
server: https://<API-ADRESİ>:9345
token: <NODE-TOKEN>
# İsteğe bağlı — bu sunucuya özel:
node-label:
  - "kurum/donanim=gpu-h200"
# GPU'yu yalnız GPU iş yükleri kullansın istiyorsan:
# node-taint:
#   - "nvidia.com/gpu=present:NoSchedule"
EOF
chmod 600 /etc/rancher/rke2/config.yaml
```

## 4. Başlat ve izle

```bash
systemctl enable --now rke2-agent
journalctl -u rke2-agent -f          # "Waiting to retrieve agent configuration" → bağlanınca akar
```

Yönetici sunucuda:
```bash
kubectl get nodes -o wide            # yeni sunucu Ready, VERSION kümeyle aynı
kubectl get pods -A -o wide --field-selector spec.nodeName=<yeni-sunucu>   # antrea-agent Running
```

Downstream (Rancher'a bağlı) kümede yeni sunucu Rancher arayüzünde kendiliğinden görünür.

## Sorun olursa

| Belirti | Bakılacak yer |
|---|---|
| `journalctl`'da bağlanamıyor | API adresi / 9345 portu erişimi, token doğru mu |
| Node NotReady | `sysctl net.ipv4.ip_forward` 1 mi · `antrea-agent` pod'u imaj çekebiliyor mu (kayıt deposu) |
| Sürüm farklı görünüyor | Yanlış sürümün dosyaları kopyalanmış — `rke2 -v` |

Kaldırmak için: `rke2-agent-uninstall.sh` (ya da `/usr/local/bin/rke2-uninstall.sh`), sonra yönetici sunucuda
`kubectl delete node <ad>`.

## GPU (H200) notu

GPU sürücüsü ve NVIDIA container toolkit / GPU Operator bu belgenin dışında (ayrı kurulum). RKE2, sunucuda NVIDIA
container runtime kuruluysa bunu containerd'ye kendiliğinden ekler. GPU Operator kullanılıyorsa RKE2'ye özgü
ayarlar gerekir: containerd yapılandırması `/var/lib/rancher/rke2/agent/etc/containerd/config.toml.tmpl`, soket
`/run/k3s/containerd/containerd.sock`. Kurumdaki GPU kurulum adımları buraya eklenecek.

## Yükseltme

Elle eklenen sunucu da kümenin parçasıdır; **system-upgrade-controller** planları node seçicisine uyuyorsa onu da
yükseltir. GPU sunucusunu yükseltmeden hariç tutmak ya da ayrı yükseltmek istiyorsan SUC planlarının
`nodeSelector`'ına bak (ör. `kurum/donanim` etiketine göre).
