import shutil
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
from pillow_heif import register_heif_opener

register_heif_opener()

PROCESSED_LOG = "processed.txt"

def load_processed():
    if not Path(PROCESSED_LOG).exists():
        return set()
    with open(PROCESSED_LOG, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def save_processed(file_path, processed_set):
    with open(PROCESSED_LOG, "a", encoding="utf-8") as f:
        f.write(str(file_path) + "\n")
    processed_set.add(str(file_path))

def get_image_model(image_path):
    try:
        with Image.open(image_path) as img:
            exifdata = img.getexif()
            for tag_id, value in exifdata.items():
                if TAGS.get(tag_id) == 'Model':
                    return str(value).strip()
    except:
        pass
    return None

def main():
    source = Path(input("Исходная папка: ").strip())

    print("\nВведите модель устройства (например, iPhone 14 Plus, iPhone 13 Pro, SM-G991B).")
    print("Как узнать модель?")
    print("  - На iPhone: «Настройки» → «Основные» → «Об этом устройстве» → «Название модели».")
    print("  - На Android: «Настройки» → «О телефоне» → «Модель».")
    print("  - Для фото, уже скопированных на компьютер: откройте свойства файла -> вкладка «Подробно» -> «Модель камеры».")
    print("Можно указать часть названия, например 'iPhone 14' или 'SM-G991'.\n")
    target_model = input("Модель устройства (или её часть): ").strip()
    if not target_model:
        print("Модель не указана. Скрипт завершён.")
        return

    target_photos_input = input("\nПапка для фото (оставьте пустым, чтобы пропустить): ").strip()
    target_live_videos_input = input("Папка для видео Live Photo (оставьте пустым, чтобы пропустить): ").strip()
    target_other_videos_input = input("Папка для остальных видео (оставьте пустым, чтобы пропустить): ").strip()
    target_other_files_input = input("Папка для прочих файлов (всё остальное, оставьте пустым, чтобы пропустить): ").strip()
    action = input("\nmove/copy? ").strip().lower()

    if not source.exists():
        print("Исходная папка не найдена")
        return

    target_photos = Path(target_photos_input) if target_photos_input else None
    target_live_videos = Path(target_live_videos_input) if target_live_videos_input else None
    target_other_videos = Path(target_other_videos_input) if target_other_videos_input else None
    target_other_files = Path(target_other_files_input) if target_other_files_input else None

    if target_photos:
        target_photos.mkdir(parents=True, exist_ok=True)
    if target_live_videos:
        target_live_videos.mkdir(parents=True, exist_ok=True)
    if target_other_videos:
        target_other_videos.mkdir(parents=True, exist_ok=True)
    if target_other_files:
        target_other_files.mkdir(parents=True, exist_ok=True)

    if not target_photos:
        print("Папка для фото не указана. Фото и Live-видео обрабатываться не будут.")
        target_live_videos = None

    source_abs = source.resolve()
    target_paths = set()
    if target_photos:
        target_paths.add(target_photos.resolve())
    if target_live_videos:
        target_paths.add(target_live_videos.resolve())
    if target_other_videos:
        target_paths.add(target_other_videos.resolve())
    if target_other_files:
        target_paths.add(target_other_files.resolve())

    def is_inside_targets(path):
        path_abs = path.resolve()
        for tp in target_paths:
            if path_abs == tp or tp in path_abs.parents:
                return True
        return False

    processed = load_processed()
    all_files = {}
    for file in source_abs.rglob("*"):
        if not file.is_file():
            continue
        if is_inside_targets(file):
            continue
        all_files[file.name] = file

    # --- Фото с указанной моделью ---
    selected_photos = []
    if target_photos:
        for file in all_files.values():
            if str(file) in processed:
                continue
            if file.suffix.lower() in ('.jpg', '.jpeg', '.png', '.heic', '.heif'):
                model = get_image_model(file)
                if model and target_model.lower() in model.lower():
                    selected_photos.append(file)

    # --- Live-видео ---
    live_video_names = set()
    if target_live_videos and selected_photos:
        for photo in selected_photos:
            base = photo.stem
            for ext in ['.mov', '.MOV', '.mp4']:
                vid_name = base + ext
                if vid_name in all_files:
                    live_video_names.add(vid_name)

    # --- Перемещение фото ---
    count_photos = 0
    if target_photos:
        for photo in selected_photos:
            dest = target_photos / photo.name
            try:
                if action == 'move':
                    shutil.move(str(photo), str(dest))
                else:
                    shutil.copy2(str(photo), str(dest))
                print(f"Фото: {photo.name} -> {target_photos.name}")
                count_photos += 1
                save_processed(photo, processed)
            except Exception as e:
                print(f"Ошибка фото {photo.name}: {e}")

    # --- Перемещение Live-видео ---
    count_live = 0
    if target_live_videos:
        for vid_name in live_video_names:
            vid_path = all_files[vid_name]
            if str(vid_path) in processed:
                continue
            dest = target_live_videos / vid_name
            try:
                if action == 'move':
                    shutil.move(str(vid_path), str(dest))
                else:
                    shutil.copy2(str(vid_path), str(dest))
                print(f"  📹 Live-видео: {vid_name} -> {target_live_videos.name}")
                count_live += 1
                save_processed(vid_path, processed)
            except Exception as e:
                print(f"Ошибка Live-видео {vid_name}: {e}")

    # --- Остальные видео (не Live) ---
    count_other_videos = 0
    if target_other_videos:
        for file in all_files.values():
            if str(file) in processed:
                continue
            if file.suffix.lower() in ('.mov', '.mp4', '.avi', '.mkv'):
                if file.name not in live_video_names:
                    dest = target_other_videos / file.name
                    try:
                        if action == 'move':
                            shutil.move(str(file), str(dest))
                        else:
                            shutil.copy2(str(file), str(dest))
                        print(f"Видео (обычное): {file.name} -> {target_other_videos.name}")
                        count_other_videos += 1
                        save_processed(file, processed)
                    except Exception as e:
                        print(f"Ошибка видео {file.name}: {e}")

    # --- Прочие файлы (все, что не было обработано выше) ---
    count_other_files = 0
    if target_other_files:
        for file in all_files.values():
            if str(file) in processed:
                continue
            if not file.exists():
                continue  # файл уже перемещён и не существует
            dest = target_other_files / file.name
            try:
                if action == 'move':
                    shutil.move(str(file), str(dest))
                else:
                    shutil.copy2(str(file), str(dest))
                print(f"Прочий файл: {file.name} -> {target_other_files.name}")
                count_other_files += 1
                save_processed(file, processed)
            except Exception as e:
                print(f"Ошибка прочего файла {file.name}: {e}")

    # --- Вывод итогов ---
    print(f"\n✅ Готово!")
    if target_photos:
        print(f"Фото (модель '{target_model}'): {count_photos}")
    if target_live_videos:
        print(f"Видео Live Photo: {count_live}")
    if target_other_videos:
        print(f"Остальные видео: {count_other_videos}")
    if target_other_files:
        print(f"Прочие файлы (всё остальное): {count_other_files}")

    # Если ни один файл не был обработан ни в одной категории
    if (count_photos == 0 and count_live == 0 and
        count_other_videos == 0 and count_other_files == 0):
        print("\n⚠️ Не найдено новых необработанных файлов.")
        print("Все файлы в исходной папке уже были обработаны ранее.")
        print("Если вы хотите обработать их заново (например, сменив модель или целевые папки),")
        print(f"удалите файл '{PROCESSED_LOG}' и запустите скрипт снова.")

if __name__ == "__main__":
    main()