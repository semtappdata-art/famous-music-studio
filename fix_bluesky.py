import re

with open('C:/Users/ACER/Desktop/ilk-projem/upload/bluesky_upload.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the return post.uri section
old_return = '''    print(f"  tamam: uri={post.uri}")
    _save_state(project_dir, {
        "bluesky_post_uri": post.uri,
        "bluesky_post_cid": post.cid,
        "bluesky_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    return post.uri


# --------------------------------------------------------------------------'''

new_return = '''    print(f"  tamam: uri={post.uri}")
    _save_state(project_dir, {
        "bluesky_post_uri": post.uri,
        "bluesky_post_cid": post.cid,
        "bluesky_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    
    # Bluesky thread oluştur (track-by-track breakdown)
    _create_bluesky_thread(project_dir, post.uri, post.cid)
    
    return post.uri


def _create_bluesky_thread(project_dir: str, parent_uri: str, parent_cid: str) -> None:
    """Bluesky thread oluştur (track-by-track breakdown).
    Her track için bir reply gönderir, parent gönderi thread halinde oluşur."""
    try:
        meta = _load_meta(project_dir)
        tracklist = meta.get("tracklist", [])
        if not tracklist:
            return
        
        from atproto_client import models
        from atproto_client import Client
        
        creds = _load_credentials()
        
        client = Client(base_url=_load_credentials()["service"])
        creds = _load_credentials()
        client.login(creds["handle"], creds["app_password"])
        
        # Parent gönderi referansı
        from atproto_client.models import models as at_models
        parent_ref = at_models.ComAtprotoRepoStrongRef.Main(uri=parent_uri, cid=parent_cid)
        
        # Tracklist'ten her parça için reply oluştur
        for i, track in enumerate(meta.get("tracklist", [])):
            ts = track.get("timestamp", "00:00")
            title = track.get("title", f"Track {i+1}")
            artist = track.get("artist", "DJ Famous")
            bpm = track.get("bpm", "")
            key = track.get("key", "")
            
            # Thread içeriği
            thread_text = f"{i+1}. {title} - {artist}"
            if bpm:
                thread_text += f" [{bpm} BPM" + (f", {key}" if key else "") + "]"
            thread_text += f" ({ts})"
            
            # Reply gönder
            client.send_post(
                text=thread_text,
                reply=models.AppBskyFeedPost.ReplyRef(
                    root=at_models.ComAtprotoRepoStrongRef.Main(uri=parent_uri, cid=parent_cid),
                    parent=at_models.ComAtprotoRepoStrongRef.Main(uri=parent_uri, cid=parent_cid),
                ),
            )
            time.sleep(0.5)  # Rate limiting
        
        print(f"  Bluesky thread oluşturuldu: {len(meta.get('tracklist', []))} parçalı")
    except Exception as e:
        print(f"  Bluesky thread oluşturma HATA: {e}")


def main():'''

if old_return in content:
    content = content.replace(old_return, new_return)
    with open('C:/Users/ACER/Desktop/ilk-projem/upload/bluesky_upload.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Replacement successful')
else:
    print('Old return text not found')
    # Debug: find similar text
    idx = content.find('return post.uri')
    if idx != -1:
        print(f'Found at {idx}: {content[idx:idx+200]}')
    else:
        print('Not found at all')

# Also replace the end marker
old_end = '''    return post.uri


# --------------------------------------------------------------------------'''

new_end = '''    return post.uri


def _create_bluesky_thread(project_dir: str, parent_uri: str, parent_cid: str) -> None:
    """Bluesky thread oluştur (track-by-track breakdown).
    Her track için bir reply gönderir, parent gönderi thread halinde oluşur."""
    try:
        meta = _load_meta(project_dir)
        tracklist = meta.get("tracklist", [])
        if not tracklist:
            return
        
        from atproto_client import models
        from atproto_client import Client
        
        creds = _load_credentials()
        
        client = Client(base_url=_load_credentials()["service"])
        creds = _load_credentials()
        client.login(creds["handle"], creds["app_password"])
        
        # Parent gönderi referansı
        from atproto_client.models import models as at_models
        parent_ref = at_models.ComAtprotoRepoStrongRef.Main(uri=parent_uri, cid=parent_cid)
        
        # Tracklist'ten her parça için reply oluştur
        for i, track in enumerate(meta.get("tracklist", [])):
            ts = track.get("timestamp", "00:00")
            title = track.get("title", f"Track {i+1}")
            artist = track.get("artist", "DJ Famous")
            bpm = track.get("bpm", "")
            key = track.get("key", "")
            
            # Thread içeriği
            thread_text = f"{i+1}. {title} - {artist}"
            if bpm:
                thread_text += f" [{bpm} BPM" + (f", {key}" if key else "") + "]"
            thread_text += f" ({ts})"
            
            # Reply gönder
            client.send_post(
                text=thread_text,
                reply=models.AppBskyFeedPost.ReplyRef(
                    root=at_models.ComAtprotoRepoStrongRef.Main(uri=parent_uri, cid=parent_cid),
                    parent=at_models.ComAtprotoRepoStrongRef.Main(uri=parent_uri, cid=parent_cid),
                ),
            )
            time.sleep(0.5)  # Rate limiting
        
        print(f"  Bluesky thread oluşturuldu: {len(meta.get('tracklist', []))} parçalı")
    except Exception as e:
        print(f"  Bluesky thread oluşturma HATA: {e}")


def main():'''

if old_end in content:
    content = content.replace(old_end, new_end)
    with open('C:/Users/ACER/Desktop/ilk-projem/upload/bluesky_upload.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('End replacement successful')
else:
    print('End text not found')
    idx = content.find('def main():')
    if idx != -1:
        print(f'Found main at {idx}: {content[idx:idx+100]}')
    else:
        print('main not found')