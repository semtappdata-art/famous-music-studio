with open('ffmpeg_utils.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 542 (index 541)
line = lines[541]
print('Before:', repr(lines[541]))

# Replace the problematic unicode escape
lines[541] = lines[541].replace('\\U0001fac1', '🫁')

print('After:', repr(lines[541]))

with open('ffmpeg_utils.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed')