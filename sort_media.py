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

def get_media_model(file_path):
    """Извлекает модель камеры из EXIF для изображений."""
    try:
        with Image.open(file_path) as img:
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
    target_other_cameras_input = input("Папка для медиа с других камер (будут созданы подпапки по модели) – оставьте пустым, чтобы пропустить: ").strip()
    action = input("\nmove/copy? ").strip().lower()

    if not source.exists():
        print("Исходная папка не найдена")
        return

    target_photos = Path(target_photos_input) if target_photos_input else None
    target_live_videos = Path(target_live_videos_input) if target_live_videos_input else None
    target_other_videos = Path(target_other_videos_input) if target_other_videos_input else None
    target_other_files = Path(target_other_files_input) if target_other_files_input else None
    target_other_cameras = Path(target_other_cameras_input) if target_other_cameras_input else None

    # Создаём папки
    if target_photos:
        target_photos.mkdir(parents=True, exist_ok=True)
    if target_live_videos:
        target_live_videos.mkdir(parents=True, exist_ok=True)
    if target_other_videos:
        target_other_videos.mkdir(parents=True, exist_ok=True)
    if target_other_files:
        target_other_files.mkdir(parents=True, exist_ok=True)
    if target_other_cameras:
        target_other_cameras.mkdir(parents=True, exist_ok=True)

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
    if target_other_cameras:
        target_paths.add(target_other_cameras.resolve())

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

    # --- Ограничение количества обрабатываемых файлов ---
    all_files_list = list(all_files.values())
    total_found = len(all_files_list)
    print(f"\n📁 Найдено файлов: {total_found}")

    limit_input = input("Сколько файлов обработать (0 — все): ").strip()
    try:
        limit = int(limit_input)
        if limit <= 0:
            limit = total_found
    except:
        limit = total_found

    if limit < total_found:
        print(f"⚠️ Будет обработано только {limit} из {total_found} файлов (первые в порядке обхода).")
        all_files_list = all_files_list[:limit]
    else:
        print(f"✅ Будут обработаны все {total_found} файлов.")

    # --- Фото с целевой моделью ---
    selected_photos = []
    if target_photos:
        for file in all_files_list:
            if str(file) in processed:
                continue
            if file.suffix.lower() in ('.jpg', '.jpeg', '.png', '.heic', '.heif'):
                model = get_media_model(file)
                if model and target_model.lower() in model.lower():
                    selected_photos.append(file)

    # --- Live-видео (по найденным фото) ---
    live_video_names = set()
    if target_live_videos and selected_photos:
        for photo in selected_photos:
            base = photo.stem
            for ext in ['.mov', '.MOV', '.mp4']:
                vid_name = base + ext
                if vid_name in all_files:
                    live_video_names.add(vid_name)

    # --- Перемещение целевых фото ---
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
        for file in all_files_list:
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

    # --- Медиа с других камер (имеют модель, не целевую, и не Live) ---
    count_other_cameras = 0
    if target_other_cameras:
        for file in all_files_list:
            if str(file) in processed:
                continue
            is_photo = file.suffix.lower() in ('.jpg', '.jpeg', '.png', '.heic', '.heif')
            is_video = file.suffix.lower() in ('.mov', '.mp4', '.avi', '.mkv')
            if not (is_photo or is_video):
                continue
            if is_video and file.name in live_video_names:
                continue
            model = get_media_model(file) if is_photo else None
            if model and target_model.lower() not in model.lower():
                safe_model = "".join(c for c in model if c.isalnum() or c in " ._-").strip()
                if not safe_model:
                    safe_model = "unknown_model"
                dest_folder = target_other_cameras / safe_model
                dest_folder.mkdir(parents=True, exist_ok=True)
                dest = dest_folder / file.name
                try:
                    if action == 'move':
                        shutil.move(str(file), str(dest))
                    else:
                        shutil.copy2(str(file), str(dest))
                    print(f"Медиа (другая модель): {file.name} -> {target_other_cameras.name}/{safe_model}")
                    count_other_cameras += 1
                    save_processed(file, processed)
                except Exception as e:
                    print(f"Ошибка перемещения {file.name} в другую модель: {e}")

    # --- Прочие файлы (все, что не было обработано выше) ---
    count_other_files = 0
    if target_other_files:
        for file in all_files_list:
            if str(file) in processed:
                continue
            if not file.exists():
                continue
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
    total_processed = (count_photos + count_live + count_other_videos +
                       count_other_cameras + count_other_files)
    print(f"\n✅ Готово!")
    print(f"📊 Всего обработано файлов за этот запуск: {total_processed}")

    # Определяем, сколько файлов осталось необработанными
    # total_found - общее количество файлов, найденных при сканировании
    # limit - количество файлов, выбранных для обработки (если был лимит)
    if limit < total_found:
        # Если был ограничен лимит, то необработанными остались (total_found - limit) файлов
        not_processed = total_found - limit
        print(f"📁 Осталось необработанных файлов (не попали в лимит): {not_processed}")
    else:
        # Если обрабатывались все файлы, то необработанными остались те, которые не подошли ни под одну категорию
        not_processed = total_found - total_processed
        if not_processed > 0:
            print(f"📁 Осталось необработанных файлов (не подошли ни под одну категорию): {not_processed}")
        else:
            print(f"📁 Все найденные файлы обработаны.")

    if target_photos:
        print(f"  - Фото (модель '{target_model}'): {count_photos}")
    if target_live_videos:
        print(f"  - Видео Live Photo: {count_live}")
    if target_other_videos:
        print(f"  - Остальные видео: {count_other_videos}")
    if target_other_cameras:
        print(f"  - Медиа с других камер (отсортированы по моделям): {count_other_cameras}")
    if target_other_files:
        print(f"  - Прочие файлы (всё остальное): {count_other_files}")

    if total_processed == 0 and not_processed == total_found:
        print("\n⚠️ Не найдено новых необработанных файлов.")
        print("Все файлы в исходной папке уже были обработаны ранее.")
        print(f"Чтобы обработать заново, удалите файл '{PROCESSED_LOG}'.")

if __name__ == "__main__":
    main()