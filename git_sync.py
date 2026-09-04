"""auto_process.py/dj_famous_process.py için paylaşılan, opsiyonel otomatik
`git pull` yardımcısı.

NEDEN VAR: kullanıcı geliştirmeyi ayrı bir dalda (Claude Code ile) yapıp PR'la
`main`'e birleştiriyor; üretimdeki makine ise değişikliği ancak elle
`git pull` yapılırsa görüyordu — her ufak kod düzeltmesi için bunu elle
yapmak unutulmaya/gecikmeye açık. Bu modül, her otomasyon çalıştırmasının
başında sessizce `main`'i güncel tutmaya çalışıyor.

NEDEN SADECE FAST-FORWARD (`--ff-only`): `projects/*/state.json` gibi bazı
runtime dosyaları git'e commit'li (bkz. CLAUDE.md) ve otomasyon her
yükleme sonrası bunları YEREL olarak değiştiriyor — commit'lenmemiş bu
değişiklikler sürekli var olabilir. `git pull --ff-only`, uzak taraf o
dosyalara dokunmadığı sürece (ki commit'ler sadece kod/config değiştiriyor)
yereldeki commit'lenmemiş değişiklikleri OLDUĞU GİBİ bırakıp sadece dalı
ileri sarar — sert bir reset/merge gibi bunların üzerine yazmaz. Fast-forward
mümkün değilse (ör. gerçekten çakışan bir durum) sessizce vazgeçer, ASLA
otomatik merge/reset denemez.

NEDEN SADECE `main` DALINDA: kullanıcı yerel makinede elle farklı bir dalı
(ör. bir PR'ı test etmek için) checkout etmişse, otomasyon bunun altını
sessizce değiştirmemeli.

Herhangi bir adım (git yok, ağ yok, ff-only başarısız) otomasyonu ASLA
durdurmuyor — en kötü ihtimalle log'a bir satır düşüp eski koduyla devam
ediyor."""

import os
import subprocess


def auto_pull(repo_dir: str, log) -> None:
    if not os.path.isdir(os.path.join(repo_dir, ".git")):
        return
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_dir, capture_output=True, text=True, timeout=15,
        )
        if branch.returncode != 0 or branch.stdout.strip() != "main":
            return

        result = subprocess.run(
            ["git", "pull", "--ff-only", "origin", "main"],
            cwd=repo_dir, capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            last_line = output.splitlines()[-1] if output else ""
            if last_line and "Already up to date" not in last_line:
                log(f"git: otomatik güncellendi — {last_line}")
        else:
            detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "bilinmeyen hata"
            log(f"git: otomatik pull atlandı (fast-forward yapılamadı) — {detail}")
    except (subprocess.TimeoutExpired, OSError) as e:
        log(f"git: otomatik pull atlandı — {e}")
