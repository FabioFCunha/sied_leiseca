import os
import re

def grep_r(pattern, directory):
    for root, dirs, files in os.walk(directory):
        if '__pycache__' in root or '.git' in root or 'migrations' in root:
            continue
        for file in files:
            if not file.endswith('.py'): continue
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                for i, line in enumerate(lines, 1):
                    if pattern in line:
                        print(f"{path.replace(chr(92), '/')}:{i}:{line.rstrip(chr(10))}")
            except Exception:
                pass

def sed_n(start_pattern, end_pattern, file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        in_block = False
        for line in lines:
            if re.search(start_pattern, line):
                in_block = True
            if in_block:
                print(line, end='')
                # The logic in the original bash command:
                # /def foo/,/^def /p
                # it prints from /def foo/ until /^def / (inclusive of the line that matches end pattern)
                # but we need to avoid matching the start pattern line with the end pattern.
                if line != lines[-1] and re.search(end_pattern, line) and not re.search(start_pattern, line):
                    break
    except Exception as e:
        print(e)

print('# 1) Mostrar a função invalidate_statistics completa')
sed_n(r'def invalidate_statistics', r'^def ', 'E:/agenda_eventos_ols/backend/apps/statistics/services.py')

print('\n# 2) Mostrar generate_statistics_for_report')
sed_n(r'def generate_statistics_for_report', r'^def ', 'E:/agenda_eventos_ols/backend/apps/statistics/services.py')

print('\n# 3) Mostrar update_statistics_for_report')
sed_n(r'def update_statistics_for_report', r'^def ', 'E:/agenda_eventos_ols/backend/apps/statistics/services.py')

print('\n# 4) Mostrar remove_statistics_for_report')
sed_n(r'def remove_statistics_for_report', r'^def ', 'E:/agenda_eventos_ols/backend/apps/statistics/services.py')

print('\n# 5) Procurar onde invalidate_statistics é utilizada')
grep_r('invalidate_statistics(', 'E:/agenda_eventos_ols/backend/apps')

print('\n# 6) Procurar onde generate_statistics_for_report é utilizada')
grep_r('generate_statistics_for_report(', 'E:/agenda_eventos_ols/backend/apps')

print('\n# 7) Procurar onde update_statistics_for_report é utilizada')
grep_r('update_statistics_for_report(', 'E:/agenda_eventos_ols/backend/apps')

print('\n# 8) Procurar onde remove_statistics_for_report é utilizada')
grep_r('remove_statistics_for_report(', 'E:/agenda_eventos_ols/backend/apps')

print('\n# 9) Mostrar o endpoint process_statistics')
# Original command: sed -n '/def process_statistics/,/^    @/p' backend/apps/schedules/views.py
sed_n(r'def process_statistics', r'^    @', 'E:/agenda_eventos_ols/backend/apps/schedules/views.py')

print('\n# 10) Mostrar perform_update')
# Original command: sed -n '/def perform_update/,/^    def /p' backend/apps/schedules/views.py
sed_n(r'def perform_update', r'^    def ', 'E:/agenda_eventos_ols/backend/apps/schedules/views.py')

print('\n# 11) Mostrar return_for_correction')
# Original command: sed -n '/def return_for_correction/,/^    @/p' backend/apps/schedules/views.py
sed_n(r'def return_for_correction', r'^    @', 'E:/agenda_eventos_ols/backend/apps/schedules/views.py')

print('\n# 12) Procurar qualquer chamada ao módulo statistics dentro do fluxo operacional')
with open('E:/agenda_eventos_ols/backend/apps/schedules/views.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f.readlines(), 1):
        if 'statistics' in line:
            print(f"{i}:{line.rstrip(chr(10))}")
