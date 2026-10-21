import json, os


def _bitis_karti_metni(theme: str = '', dil: str = 'en') -> str:
    """Bitiş kartı metni (son 15sn) — ABONE + SONRAKİ İÇERİK çağrısı.

    NEDEN ayrı fonksiyon: hem uzun format hem Shorts aynı metni kullanır
    (tek kaynak) ve tema bazlı değişir (DJ setleri vs. şarkılar).

    NEDEN 'abone' vurgusu: bitiş kartı videonun EN SON görülen karesi —
    izleyici burada en çok aksiyon alır. Cercle/Boiler Room referanslarında
    da set sonunda kanal + abone çağrısı vardır.
    """
    if dil == 'tr':
        if theme == 'dj':
            return "Yeni setler için abone ol  •  @Famous_musics_studio"
        return "Abone ol, her hafta yeni şarkı  •  @Famous_musics_studio"
    if theme == 'dj':
        return "Subscribe for new sets  •  @Famous_musics_studio"
    return "Subscribe — new track every week  •  @Famous_musics_studio"


projects = {
    'Night_Drive_Concept_1': {
        'title': 'Night Drive – Melodic Techno (Concept 1: The Poster)',
        'theme': 'elektronik',
        'set_style': 'techno_chill',
        'marquee_text': 'DJ Famous  •  Night Drive – Melodic Techno (Concept 1: The Poster)',
        'art_query': 'POV car dashboard night highway rain neon lights',
        'location': {'city': 'Berlin', 'country': 'Germany', 'landmark': 'TV Tower', 'gps': '52.5200,13.4050', 'story': 'Techno capital, concrete and neon, history in every beat', 'story_tr': 'Tekno başkenti, beton ve neon, her vuruşta tarih hiss edilir.'},
        'tracklist': [
            {'timestamp': '00:00', 'title': 'Midnight Departure', 'artist': 'DJ Famous', 'start_sec': 0, 'end_sec': 300, 'bpm': 122, 'key': 'Am'},
            {'timestamp': '05:00', 'title': 'City Lights Descent', 'artist': 'DJ Famous', 'start_sec': 300, 'end_sec': 600, 'bpm': 124, 'key': 'F'},
            {'timestamp': '10:00', 'title': 'Neon Visions', 'artist': 'DJ Famous', 'start_sec': 600, 'end_sec': 900, 'bpm': 126, 'key': 'C'},
            {'timestamp': '15:00', 'title': 'Starlit Corridor', 'artist': 'DJ Famous', 'start_sec': 900, 'end_sec': 1200, 'bpm': 125, 'key': 'G'},
            {'timestamp': '20:00', 'title': 'Dawn Approach', 'artist': 'DJ Famous', 'start_sec': 1200, 'end_sec': 1500, 'bpm': 124, 'key': 'Dm'},
            {'timestamp': '25:00', 'title': 'Homeward Bound', 'artist': 'DJ Famous', 'start_sec': 1500, 'end_sec': 1800, 'bpm': 122, 'key': 'Am'}
        ],
        'hikaye': 'Gece yarısı, sadece sen ve yol. Farların ışığı tünelin içinde dans ediyor, ritim kalbinle senkronize oluyor. Bu gece sadece sürmek için sürüyorsun, varış noktası önemli değil.',
        'neden_bu_sarki': 'Gece sürüşlerinin o eşsiz huzurunu ve özgürlük hissini paylaşmak için.'
    },
    'Night_Drive_Concept_2': {
        'title': 'Night Drive – Melodic Techno (Concept 2: The Aspirational Billboard)',
        'theme': 'elektronik',
        'set_style': 'techno_chill',
        'marquee_text': 'DJ Famous  •  Night Drive – Melodic Techno (Concept 2: The Aspirational Billboard)',
        'art_query': 'illuminated tunnel night highway light trails symmetrical',
        'location': {'city': 'Los Angeles', 'country': 'USA', 'route': 'Mulholland Drive', 'gps': '34.1033,-118.3275', 'story': 'City lights below, stars above, midnight cruise', 'story_tr': 'Şehir ışıkları aşağıda, yıldızlar yukarısında, gece yarısı kruvazı. Mulholland Drive\'ın virajlarında melodi kaybolur, ritim kalır.'},
        'tracklist': [
            {'timestamp': '00:00', 'title': 'Midnight Departure', 'artist': 'DJ Famous', 'start_sec': 0, 'end_sec': 300, 'bpm': 122, 'key': 'Am'},
            {'timestamp': '05:00', 'title': 'City Lights Descent', 'artist': 'DJ Famous', 'start_sec': 300, 'end_sec': 600, 'bpm': 124, 'key': 'F'},
            {'timestamp': '10:00', 'title': 'Neon Visions', 'artist': 'DJ Famous', 'start_sec': 600, 'end_sec': 900, 'bpm': 126, 'key': 'C'},
            {'timestamp': '15:00', 'title': 'Starlit Corridor', 'artist': 'DJ Famous', 'start_sec': 900, 'end_sec': 1200, 'bpm': 125, 'key': 'G'},
            {'timestamp': '20:00', 'title': 'Dawn Approach', 'artist': 'DJ Famous', 'start_sec': 1200, 'end_sec': 1500, 'bpm': 124, 'key': 'Dm'},
            {'timestamp': '25:00', 'title': 'Homeward Bound', 'artist': 'DJ Famous', 'start_sec': 1500, 'end_sec': 1800, 'bpm': 122, 'key': 'Am'}
        ],
        'hikaye': 'Tünelin ucundaki ışık, hayallerin kapısı. Her virajda yeni bir hayal, her çıkışta yeni bir umut. Billboard\'un ışıkları sana fısıldıyor: "Devam et, ulaşıyorsun."',
        'neden_bu_sarki': 'Hedeflere ulaşırken yolculuğun kendisinin ne kadar değerli olduğunu hatırlatmak için.'
    },
    'Night_Drive_Concept_3': {
        'title': 'Night Drive – Melodic Techno (Concept 3: Negative Space)',
        'theme': 'elektronik',
        'set_style': 'techno_chill',
        'marquee_text': 'DJ Famous  •  Night Drive – Melodic Techno (Concept 3: Negative Space)',
        'art_query': 'futuristic car dashboard turquoise pink speedometer glow',
        'location': {'city': 'Tokyo', 'country': 'Japan', 'landmark': 'Tokyo Tower', 'gps': '35.6762,139.6503', 'story': 'Neon dreams, Shibuya crossing, future sound', 'story_tr': 'Neon rüyalar, Shibuya kavşağı, gelecek sesi.'},
        'tracklist': [
            {'timestamp': '00:00', 'title': 'Neon Entry', 'artist': 'DJ Famous', 'start_sec': 0, 'end_sec': 320, 'bpm': 124, 'key': 'Cm'},
            {'timestamp': '05:20', 'title': 'Shibuya Crossing', 'artist': 'DJ Famous', 'start_sec': 320, 'end_sec': 640, 'bpm': 126, 'key': 'Gm'},
            {'timestamp': '10:40', 'title': 'Neon Dreams', 'artist': 'DJ Famous', 'start_sec': 640, 'end_sec': 960, 'bpm': 128, 'key': 'Dm'},
            {'timestamp': '16:00', 'title': 'Tokyo Drift', 'artist': 'DJ Famous', 'start_sec': 960, 'end_sec': 1280, 'bpm': 127, 'key': 'Bb'},
            {'timestamp': '21:20', 'title': 'Mount Fuji Sunrise', 'artist': 'DJ Famous', 'start_sec': 1280, 'end_sec': 1600, 'bpm': 125, 'key': 'F'},
            {'timestamp': '26:40', 'title': 'Sayonara Tokyo', 'artist': 'DJ Famous', 'start_sec': 1600, 'end_sec': 1800, 'bpm': 123, 'key': 'Cm'}
        ],
        'hikaye': 'Bazen en güçlü ses, sessizliktir. Ara aralıktaki boşluklar, notalar kadar önemli. Gece sessizliğinde, ritim kendi kendini bulur.',
        'neden_bu_sarki': 'Negatif boşluğun gücünü ve boşluklarda doğan melodiyi keşfetmek için.'
    },
    'Night_Drive_Concept_4': {
        'title': 'Night Drive – Melodic Techno (Concept 4: Title Subtitle)',
        'theme': 'elektronik',
        'set_style': 'techno_chill',
        'marquee_text': 'DJ Famous  •  Night Drive – Melodic Techno (Concept 4: Title Subtitle)',
        'art_query': 'rainy city street car taillights reflection night',
        'location': {'city': 'London', 'country': 'UK', 'route': 'M25 Orbital', 'gps': '51.5074,-0.1278', 'story': 'Rain on windshield, city lights blur, midnight thoughts', 'story_tr': 'Yağmurlu camdan şehir ışıkları dans ediyor. Her durakta yeni bir hikaye, her ışıkta yeni bir umut.'},
        'tracklist': [
            {'timestamp': '00:00', 'title': 'Rainy Departure', 'artist': 'DJ Famous', 'start_sec': 0, 'end_sec': 300, 'bpm': 120, 'key': 'Gm'},
            {'timestamp': '05:00', 'title': 'London Fog', 'artist': 'DJ Famous', 'start_sec': 300, 'end_sec': 600, 'bpm': 122, 'key': 'Dm'},
            {'timestamp': '10:00', 'title': 'Thames Reflection', 'artist': 'DJ Famous', 'start_sec': 600, 'end_sec': 900, 'bpm': 124, 'key': 'Bb'},
            {'timestamp': '15:00', 'title': 'Big Ben Chimes', 'artist': 'DJ Famous', 'start_sec': 900, 'end_sec': 1200, 'bpm': 123, 'key': 'F'},
            {'timestamp': '20:00', 'title': 'Dawn Approach', 'artist': 'DJ Famous', 'start_sec': 1200, 'end_sec': 1500, 'bpm': 123, 'key': 'F'},
            {'timestamp': '25:00', 'title': 'Foggy Arrival', 'artist': 'DJ Famous', 'start_sec': 1500, 'end_sec': 1800, 'bpm': 121, 'key': 'Gm'}
        ],
        'hikaye': 'Yağmurlu camdan şehir ışıkları dans ediyor. Her durakta yeni bir hikaye, her ışıkta yeni bir umut. Gece bitmiyor, sadece dönüşüyor.',
        'neden_bu_sarki': 'Gece sürüşünün o sihirli anını, sonsuza dek kilitlemek için.'
    },
    'TR01_ArabeskTrap': {
        'title': 'Gece Sürüşünde Hasret',
        'theme': 'arabesk',
        'set_style': 'arabesk_trap',
        'marquee_text': 'Gece Sürüşünde Hasret • Arabesk Trap • #DJFamous',
        'art_query': 'rainy istanbul street night neon reflections car interior',
        'tracklist': [
            {'timestamp': '00:00', 'title': 'Istanbul Nights', 'artist': 'DJ Famous', 'start_sec': 0, 'end_sec': 180, 'bpm': 140, 'key': 'Fm'},
            {'timestamp': '03:00', 'title': 'Bosphorus Breeze', 'artist': 'DJ Famous', 'start_sec': 180, 'end_sec': 360, 'bpm': 142, 'key': 'Cm'},
            {'timestamp': '06:00', 'title': 'Minaret Dreams', 'artist': 'DJ Famous', 'start_sec': 360, 'end_sec': 540, 'bpm': 138, 'key': 'Gm'},
            {'timestamp': '09:00', 'title': 'Golden Horn', 'artist': 'DJ Famous', 'start_sec': 540, 'end_sec': 720, 'bpm': 144, 'key': 'Ebm'},
            {'timestamp': '12:00', 'title': 'Istanbul Dawn', 'artist': 'DJ Famous', 'start_sec': 720, 'end_sec': 900, 'bpm': 138, 'key': 'Bbm'}
        ],
        'hikaye': 'Gece sürüşünde şehrin ışıklarıyla dans eden gölgeler, hasretin ritmiyle dans ediyor. Beton elleri içinde, kalbin o eski sokaklarda hala yürüyor.',
        'neden_bu_sarki': 'Gece sürüşlerinin o eşsiz huzurunu ve özgürlük hissini, arabesk trap\'in derinliğiyle anlatmak için.'
    },
    'TR02_90larNostalji': {
        'title': '90\'lar Nostalji Rooftop',
        'theme': 'pop',
        'set_style': 'nineties_nostalji',
        'marquee_text': '90\'lar Nostalji Rooftop • Pop • #DJFamous',
        'art_query': 'vintage tv static retro living room cassette tape',
        'tracklist': [
            {'timestamp': '00:00', 'title': 'Kaset Başlangıcı', 'artist': 'DJ Famous', 'start_sec': 0, 'end_sec': 180, 'bpm': 118, 'key': 'Am'},
            {'timestamp': '03:00', 'title': 'Kaset Kaydı', 'artist': 'DJ Famous', 'start_sec': 180, 'end_sec': 360, 'bpm': 120, 'key': 'C'},
            {'timestamp': '06:00', 'title': 'Rooftop Party', 'artist': 'DJ Famous', 'start_sec': 360, 'end_sec': 540, 'bpm': 122, 'key': 'F'},
            {'timestamp': '09:00', 'title': 'Kaset Finali', 'artist': 'DJ Famous', 'start_sec': 540, 'end_sec': 720, 'bpm': 118, 'key': 'Am'}
        ],
        'hikaye': 'Kasetlerin sarı sayfaları arasında kaybolan çocukluk anıları, çatı katında dans eden gölgeler. 90\'ların o samimi sıcaklığı, bugün de kalbimizde yaşıyor.',
        'neden_bu_sarki': '90\'ların o unutulmaz enerjisini ve samimiyetini, genç nesille paylaşmak için.'
    },
    'TR03_MelodicTechnoBridge': {
        'title': 'Gece Sürüşü Bridge',
        'theme': 'elektronik',
        'set_style': 'melodic_techno',
        'marquee_text': 'Gece Sürüşü Bridge • Elektronik • #DJFamous',
        'art_query': 'night highway lights motion blur tunnel lights driving',
        'tracklist': [
            {'timestamp': '00:00', 'title': 'Midnight Departure', 'artist': 'DJ Famous', 'start_sec': 0, 'end_sec': 300, 'bpm': 122, 'key': 'Am'},
            {'timestamp': '05:00', 'title': 'City Lights Descent', 'artist': 'DJ Famous', 'start_sec': 300, 'end_sec': 600, 'bpm': 124, 'key': 'F'},
            {'timestamp': '10:00', 'title': 'Neon Visions', 'artist': 'DJ Famous', 'start_sec': 600, 'end_sec': 900, 'bpm': 126, 'key': 'C'},
            {'timestamp': '15:00', 'title': 'Starlit Corridor', 'artist': 'DJ Famous', 'start_sec': 900, 'end_sec': 1200, 'bpm': 125, 'key': 'G'},
            {'timestamp': '20:00', 'title': 'Dawn Approach', 'artist': 'DJ Famous', 'start_sec': 1200, 'end_sec': 1500, 'bpm': 124, 'key': 'Dm'},
            {'timestamp': '25:00', 'title': 'Homeward Bound', 'artist': 'DJ Famous', 'start_sec': 1500, 'end_sec': 1800, 'bpm': 122, 'key': 'Am'}
        ],
        'hikaye': 'Tünelin ucundaki ışık, hayatın en karanlık anlarında bile umut olduğunu fısıldıyor. Her viraj bir dönüşüm, her düz yol bir meditasyon.',
        'neden_bu_sarki': 'Gece sürüşlerinin o meditatif halini, melodik tekno\'nun derinliğiyle yakalamak için.'
    },
    'TR04_OrganicHouse': {
        'title': 'Gün Doğumu Umudu',
        'theme': 'akustik',
        'set_style': 'organic_house',
        'marquee_text': 'Gün Doğumu Umudu • Akustik • #DJFamous',
        'art_query': 'sunrise terrace warm light nature awakening golden hour',
        'tracklist': [
            {'timestamp': '00:00', 'title': 'Dawn Awakening', 'artist': 'DJ Famous', 'start_sec': 0, 'end_sec': 280, 'bpm': 116, 'key': 'G'},
            {'timestamp': '04:40', 'title': 'Morning Mist', 'artist': 'DJ Famous', 'start_sec': 280, 'end_sec': 560, 'bpm': 117, 'key': 'D'},
            {'timestamp': '09:20', 'title': 'Gamelan Whispers', 'artist': 'DJ Famous', 'start_sec': 560, 'end_sec': 840, 'bpm': 118, 'key': 'Am'},
            {'timestamp': '14:00', 'title': 'Terrace Dreams', 'artist': 'DJ Famous', 'start_sec': 840, 'end_sec': 1120, 'bpm': 119, 'key': 'Em'},
            {'timestamp': '18:40', 'title': 'Rice Field Breeze', 'artist': 'DJ Famous', 'start_sec': 1120, 'end_sec': 1400, 'bpm': 118, 'key': 'C'},
            {'timestamp': '23:20', 'title': 'Eternal Calm', 'artist': 'DJ Famous', 'start_sec': 1400, 'end_sec': 1680, 'bpm': 116, 'key': 'G'}
        ],
        'hikaye': 'İlk ışığın dokunmasıyla doğa uyanıyor, her yaprak yeni bir nota. Umut, en küçük çiçekten bile büyür.',
        'neden_bu_sarki': 'Yeni başlangıçların o müjdelesi hissi, organik house\'ın doğallığıyla paylaşmak için.'
    }
}

for dir_name, data in projects.items():
    proj_path = f'projects/{dir_name}'
    os.makedirs(f'projects/{dir_name}', exist_ok=True)
    
    # 1. meta.json
    # NEDEN .get() ile: TR01-TR04 gibi projelerde 'location' anahtarı YOK —
    # data['location'] ile erişim KeyError veriyor ve script 4 projeyi
    # ürettikten sonra tüm hattan düşüyordu. Eksik alanlar boş doldurulur
    # (validate_project zorunlu alanları ayrıca kontrol ediyor).
    meta = {
        'title': data['title'],
        'theme': data['theme'],
        'set_style': data.get('set_style', ''),
        'marquee_text': data.get('marquee_text', 'DJ Famous'),
        'art_query': data.get('art_query', ''),
        'location': data.get('location', {}),
        'playlist_id': f'PL_{dir_name.replace("_", "").upper()}',
        'tags_base': data.get('tags_base', []),
        'hashtags': data.get('hashtags', ''),
        'seo': data.get('seo', {}),
        'cross_promo': data.get('cross_promo', {}),
        'yayin_tarihi': data.get('yayin_tarihi', ''),
        'end_card_text': data.get('end_card_text', ''),
        'end_card_text_tr': data.get('end_card_text_tr', ''),
        'tracklist': data.get('tracklist', []),
        'tur_ozel': data.get('tur_ozel', '')
    }
    
    if 'hikaye' in data:
        meta['hikaye'] = data['hikaye']
    if 'neden_bu_sarki' in data:
        meta['neden_bu_sarki'] = data['neden_bu_sarki']
    if 'story_tr' in data.get('location', {}):
        meta['story_tr'] = data['location']['story_tr']

    # BİTİŞ KARTI (abone kaldıracı) — meta'da yoksa ÜRET.
    # NEDEN burada: CLAUDE.md §16 "Bitiş kartı: meta.json'da end_card_text
    # varsa son 15sn'de — yoksa çizilmez" diyor. Kuralı BOZMADAN otomatik
    # dolduruyoruz: render.py aynen calismaya devam ediyor, sadece meta artik
    # end_card_text iceriyor. Böylece bitis kartindaki "Abone ol" cagrisi
    # video içinde de görünür olur.
    if not meta.get('end_card_text'):
        meta['end_card_text'] = _bitis_karti_metni(data.get('theme', ''))
    if not meta.get('end_card_text_tr'):
        meta['end_card_text_tr'] = _bitis_karti_metni(
            data.get('theme', ''), dil='tr')

    with open(f'projects/{dir_name}/meta.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    # 2. structure.txt
    structure_lines = ['# Structure for ' + data['title'], '']
    for track in data['tracklist']:
        structure_lines.append(f"{track['timestamp']} - {track['title']} | {track['bpm']} BPM | {track['key']}")
    with open(f'projects/{dir_name}/structure.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(structure_lines))
    
    # 3. segments.json (for all tracks)
    segments = []
    for track in data['tracklist']:
        segments.append({
            'start': track['start_sec'],
            'end': track['end_sec'],
            'title': track['title'],
            'artist': track['artist'],
            'bpm': track['bpm'],
            'key': track['key'],
            'section': 'verse' if track['start_sec'] % 2 == 0 else 'chorus'
        })
    with open(f'projects/{dir_name}/segments.json', 'w', encoding='utf-8') as f:
        json.dump({'segments': segments}, f, ensure_ascii=False, indent=2)
    
    # 4. sozler.md
    sozler_content = f"# {data['title']}\n\n# {data.get('set_style', '').replace('_', ' ').title()}\n\n{data.get('hikaye', data.get('story_tr', ''))}\n\n# Bölümler:\n"
    for track in data['tracklist']:
        sozler_content += f"\n## {track['timestamp']} - {track['title']}\n{track.get('lyrics', '[Enstrümental - Söz yok]')}\n"
    sozler_content += "\n\n# Etiketler: " + data.get('marquee_text', '')
    
    with open(f'projects/{dir_name}/sozler.md', 'w', encoding='utf-8') as f:
        f.write(sozler_content)
    
    # segments.json (already created above for all)
    segments = []
    for track in data['tracklist']:
        segments.append({
            'start': track['start_sec'],
            'end': track['end_sec'],
            'title': track['title'],
            'artist': track['artist'],
            'bpm': track['bpm'],
            'key': track['key']
        })
    with open(f'projects/{dir_name}/segments.json', 'w', encoding='utf-8') as f:
        json.dump({'segments': segments}, f, ensure_ascii=False, indent=2)
    
    # structure.txt (already created above)
    structure_lines = ['# Structure for ' + data['title'], '']
    for track in data['tracklist']:
        structure_lines.append(f"{track['timestamp']} - {track['title']} | {track['bpm']} BPM | {track['key']}")
    with open(f'projects/{dir_name}/structure.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(structure_lines))
    
    print(f'Created meta files for {dir_name}')

print('All meta files created!')