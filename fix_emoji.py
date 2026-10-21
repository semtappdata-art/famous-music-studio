with open('ffmpeg_utils.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all occurrences of the problematic unicode escape
content = content.replace('\U0001fac1', '🫁')

with open('ffmpeg_utils.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed all occurrences')