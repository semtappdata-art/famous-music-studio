with open('ffmpeg_utils.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix zoom filter name
content = content.replace(
    'filter_complex += f";[{pre_label}]zoom={zoom_expr}[zoom]" ',
    'filter_complex += f";[{pre_label}]zoompan={zoom_expr}[zoom]" '
)

with open('ffmpeg_utils.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed zoom filter name')