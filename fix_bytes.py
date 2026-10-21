with open('ffmpeg_utils.py', 'rb') as f:
    content = f.read()

# Replace the bytes
content = content.replace(b'\\U0001fac1', b'\xf0\x9f\xab\x81')

with open('ffmpeg_utils.py', 'wb') as f:
    f.write(content)

print('Fixed')