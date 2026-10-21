import re

with open('.env', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix SUNO_API_KEY duplicates (keep first real one, remove placeholder duplicates)
content = re.sub(r'(^SUNO_API_KEY=your-real-suno-api-key-here\n)+', 'SUNO_API_KEY=your-real-suno-api-key-here\n', content, flags=re.MULTILINE)

# Fix SUNO_MCP_TOKEN - ensure only one exists after SUNO_MCP_URL
content = re.sub(r'^SUNO_MCP_TOKEN=.*\n', '', content, flags=re.MULTILINE)
content = content.replace(
    'SUNO_MCP_URL=https://suno.mcp.acedata.cloud/mcp',
    'SUNO_MCP_URL=https://suno.mcp.acedata.cloud/mcp\nSUNO_MCP_TOKEN=5d8ef282-9c99-474d-b9ed-2bfea64a598c'
)

# Fix duplicate SUNO_API_KEY lines (keep first non-placeholder)
lines = []
seen_suno_api = False
for line in content.split('\n'):
    if line.strip().startswith('SUNO_API_KEY='):
        if 'your-real-suno-api-key-here' in line:
            if not hasattr(fix_suno, 'seen'):
                # First placeholder - keep it for now (will be replaced later)
                pass
            else:
                continue  # skip duplicates
    lines.append(line)

# Actually, let's do this more carefully
with open('.env', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
seen_suno_api = False
for line in lines:
    if line.strip().startswith('SUNO_API_KEY='):
        if 'your-real-suno-api-key-here' in line:
            if not hasattr(seen_suno_api, 'seen'):
                pass  # keep first
            else:
                continue  # skip duplicate placeholder
        elif 'your-real-suno-api-key-here' not in line:
            # This is a real key, keep it
            pass
    new_lines.append(line)

# Simpler approach: just use the file we already fixed
with open('.env', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')