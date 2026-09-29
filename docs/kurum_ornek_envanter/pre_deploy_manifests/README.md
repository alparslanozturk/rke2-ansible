Antrea manifestini (`antrea.yaml`) buraya koy. Yalnız ilk sunucuya kopyalanır, RKE2 otomatik uygular.

- Sürüm seçimi: `araclar/antrea_surum.py <k8s-sürümü>` (ör. 1.34 → v2.5/v2.6/v2.7, önerilen en yenisi).
- İndirme: `airgap/indir.sh --antrea v2.7` → `airgap/antrea/<sürüm>/antrea.yml` (buraya kopyala) ve
  `imajlar.txt` (bu imajlar kurum kayıt aynasında olmalı; RKE2 imaj paketinde yoklar).
