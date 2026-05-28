#!/usr/bin/env python3
"""
Скрипт собирает содержимое всех текстовых файлов проекта в один output.txt.
Файлы разделяются заголовками с их относительными путями.
"""

import os

def collect_project_files(
    root_dir: str = ".",
    output_file: str = "project_contents.txt",
    exclude_dirs: set = None,
    exclude_exts: set = None
):
    # Настройки по умолчанию: какие папки и расширения игнорировать
    if exclude_dirs is None:
        exclude_dirs = {
            ".git", "__pycache__", "node_modules", "venv", ".venv",
            "env", ".idea", ".vscode", "dist", "build", "target"
        }
    if exclude_exts is None:
        exclude_exts = {
            ".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".png",
            ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".zip", ".tar",
            ".gz", ".rar", ".pdf", ".mp4", ".mp3", ".wav", ".lock"
        }

    output_path = os.path.abspath(os.path.join(root_dir, output_file))
    results = []
    file_count = 0
    total_size = 0

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Исключаем ненужные папки из обхода (модификация списка на месте)
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            filepath_abs = os.path.abspath(filepath)

            # Не включаем сам выходной файл
            if filepath_abs == output_path:
                continue

            ext = os.path.splitext(filename)[1].lower()
            if ext in exclude_exts:
                continue

            rel_path = os.path.relpath(filepath, root_dir)

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(filepath, "r", encoding="latin-1") as f:
                        content = f.read()
                    rel_path += " (latin-1)"
                except Exception as e:
                    content = f"[⚠️ Бинарный или нечитаемый файл: {e}]"
            except Exception as e:
                content = f"[⚠️ Ошибка чтения: {e}]"

            total_size += len(content)
            file_count += 1
            results.append(f"\n{'='*60}\n📄 {rel_path}\n{'='*60}\n{content}\n")

    with open(output_path, "w", encoding="utf-8") as out:
        out.writelines(results)

    print(f"✅ Готово!")
    print(f"📁 Обработано файлов: {file_count}")
    print(f"📄 Результат сохранён в: {output_file}")
    print(f"⚖️ Примерный размер содержимого: {total_size / 1024:.1f} КБ")


if __name__ == "__main__":
    collect_project_files()