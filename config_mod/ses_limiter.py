# --- Ses: render öncesi koşullu true-peak limiter (2026-09-13) ---------------
# `suno_kalite_onerileri.md` §1 #8 ve §5. Suno çıktıları zaten -12,9 … -14,8
# LUFS; genel loudnorm/normalizasyon BİLEREK YOK. Tek risk true peak: AAC 192k
# kodlaması tepeyi taşırabiliyor. render.render_project() sesi ffmpeg
# `ebur128=peak=true` ile ölçüp `state.json` -> `ses_olcum`a yazıyor (aynı md5
# için tekrar ölçmüyor); TP bu eşiği AŞARSA render zincirine YALNIZ limiter
# giriyor. Ölçüm başarısızsa render durmuyor, limitersiz sürüyor, log'a UYARI.
SES_LIMITER_ACIK = True
SES_TP_ESIK_DBTP = -1.0          # ölçülen TP bunu AŞARSA (> , eşit değil) limiter
# NEDEN 4x aşırı örneklemeli alimiter ve NEDEN -2,0 dBFS (-1,5 değil): katalogun
# sınırdaki gerçek dosyalarında, AAC 192k SONRASI TP ölçüldü (2026-09-13):
#   Küllerimden Geç (kaynak -0,5): limitersiz -0,7 | düz alimiter -1,5 -> -0,3 (!)
#                                  | 4x alimiter -1,5 -> -1,0 | 4x alimiter -2,0 -> -1,6
#   Sokaklar Beni Tanır (-0,7):    limitersiz -0,9 | düz -1,5 -> -1,3 | 4x -2,0 -> -1,3
# Düz (48 kHz) alimiter yalnız ÖRNEK tepesini görüyor; örnekler arası tepe ve
# kırpmanın eklediği üst frekans AAC'den sonra TP'yi KÖTÜLEŞTİRDİ. 192 kHz'de
# sınırlamak örnekler arası tepeyi de yakalıyor. I ve LRA üç dosyada da 0,0
# değişti. İki geçişli loudnorm (linear, TP=-1,5) da eşdeğer olurdu ama ikinci
# bir ölçüm geçişi + `measured_*` parametre taşıma demek; bu daha basit.
SES_LIMITER_TAVAN_DBFS = -2.0
SES_LIMITER_ASIRI_ORNEKLEME = 192000
SES_LIMITER_CIKIS_HZ = 48000
