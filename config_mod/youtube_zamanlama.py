# --- YouTube yayın zamanlaması (Türkiye yerel saati — Türkiye DST kullanmıyor,
# yıl boyunca sabit UTC+3) ---
# trend_hashtag_notlari.md'ye göre en iyi paylaşım saatleri: 12:00-14:00 ve
# 18:00-22:00. Eskiden Görev Zamanlayıcı sadece 13:00/19:00'da çalıştığı için
# her yükleme zaten bu aralıklara denk geliyordu; artık otomatik kademeleme
# saatte bir SIK çalıştığı için (bkz. auto_process.py) yükleme anı günün her
# saatine denk gelebilir. YouTube'un status.publishAt özelliği (video
# privacyStatus="private" + gelecek bir publishAt zamanıyla yüklenir, YouTube
# o ana gelince otomatik public'e çeviriyor) sayesinde render/upload ANI ile
# videonun CANLIYA ÇIKTIĞI an birbirinden ayrılabiliyor — auto_process.py
# kendi kademeleme mantığına göre istediği saatte render+upload yapmaya devam
# eder, YouTube tarafı ise bir sonraki golden-hour penceresine kadar bekletir.
