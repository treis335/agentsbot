with open('agents/executor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if 'GlobalMemory' in line or 'global_memory' in line.lower() or 'LessonExtractor' in line:
        print(f'Line {i}: {line.rstrip()}')
