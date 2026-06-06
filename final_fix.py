import sys

with open('bot.py', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Add Path import if missing
if 'from pathlib import Path' not in c:
    c = c.replace('import urllib.parse', 'import urllib.parse\nfrom pathlib import Path')
    print('Added: from pathlib import Path')

# 2. Remove Markdown formatting from captions (parse_mode=None)
c = c.replace("*{cat['title']}*", "{cat['title']}")
c = c.replace("*{cat['name']}*", "{cat['name']}")
c = c.replace("_{cat['description']}_", "{cat['description']}")
c = c.replace("{cat['element']}*", "{cat['element']}")
c = c.replace("*Хочешь узнать свой тотем?*", "Хочешь узнать свой тотем?")
print('Removed Markdown markers from captions')

with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(c)

# Verify
with open('bot.py', 'r', encoding='utf-8') as f:
    v = f.read()
try:
    compile(v, 'bot.py', 'exec')
    print('Syntax: OK')
except SyntaxError as e:
    print(f'Syntax ERROR: {e}')

# Show final captions
with open('_captions.txt', 'w', encoding='utf-8') as out:
    for i, l in enumerate(v.split('\n'), 1):
        if 'caption=f' in l:
            out.write(f'L{i}: {l.strip()[:300]}\n')

print('Done')