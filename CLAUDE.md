# rke2-ansible (kurum fork'u) — çalışma notları

- Ne: rancherfederal/rke2-ansible 2.x fork'u; kurumun RKE2 kümeleri (RHEL 9, CIS, air-gap, Antrea, 1.33/1.34+).
  Ayrıntı ve farklar: `KURUM.md` (tek kaynak — her değişiklik oraya tek satır).
- İlke: upstream'e AZ dokun. Değişiklikler küçük, `KURUM` yorumlu; yeni iş mümkünse ayrı görev dosyası.
- Remote: `upstream` (rancherfederal, push kapalı), `hepapi` (eski 1.x, yalnız referans, push kapalı), `origin` (fork).
- Test: `--syntax-check`, `--check --tags always`, `.venv/bin/ansible-lint roles` (upstream ile aynı sayı kalmalı:
  0 hata), `.venv/bin/yamllint -c .yamllint roles docs/kurum_ornek_envanter`. Riskli görevleri
  `unshare -m` namespace'inde gerçek koşu ile dene (bu sunucunun /tmp, /opt'una dokunma).
- `inventory/` ve `airgap/*/` git dışı. Commit yazarı alpozturklive, AI atıf satırı yok.
