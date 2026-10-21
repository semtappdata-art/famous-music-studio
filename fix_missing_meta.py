import json, os

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
            {'timestamp': '20:00', 'title': 'Dawn Approach', 'artist': 'DJ Famous', 'start_sec': 1200, 'end_sec': 1500, 'bpm': 126, 'key': 'G'},
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
        'location': {'city': 'Los Angeles', 'country': 'USA', 'route': 'Mulholland Drive', 'gps': '34.1033,-118.3275', 'story': 'City lights below, stars above, midnight cruise', 'story_tr': 'Şehir ışıkları aşağıda, yıldızlar yukarısında, gece yarısı kruvazı. Mulholland Drive\'in virajlarında melodi kaybolur, ritim kalır.'},
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
    }
}

for dir_name, data in projects.items():
    proj_path = f'projects/{dir_name}'
    os.makedirs(f'projects/{dir_name}', exist_ok=True)
    
    # sozler.md
    sozler_content = f'# {data["title"]}\n\n# {data.get("set_style", "").replace("_", " ").title()}\n\n{data.get("hikaye", data.get("story_tr", ""))}\n\n# Bölümler:\n'
    for track in data['tracklist']:
        sozler_content = f'\n## {track["timestamp"]} - {track["title"]}\n{track.get("lyrics", "[Enstrümental - Söz yok]")}\n'
    
    sozler_content += '\n\n# Etiketler: ' + data.get('marquee_text', '')
    
    with open(f'projects/{dir_name}/sozler.md', 'w', encoding='utf-8') as f:
        f.write(sozler_content)
    
    # structure.txt
    structure_lines = ['# Structure for ' + data['title'], '']
    for track in data['tracklist']:
        structure_lines.append(f"{track['timestamp']} - {track['title']} | {track['bpm']} BPM | {track['key']}")
    with open(f'projects/{dir_name}/structure.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(structure_lines))
    
    # segments.json
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
    
    print(f'Fixed {dir_name}')

print('Night Drive concepts fixed!')