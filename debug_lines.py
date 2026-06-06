with open('bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(219, 250):  # 0-indexed, lines 220-250
    print(f'{i+1:3}: {repr(lines[i])}')