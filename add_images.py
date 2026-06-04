# -*- coding: utf-8 -*-
"""Вставляет фото Unsplash в статьи (articles/*.json -> bodyMarkdown)."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ART = Path(__file__).resolve().parent / "articles"

UNS = "https://unsplash.com/"

# slug -> (anchor_before, image_markdown)  : картинку вставляем ПЕРЕД anchor
INSERTS = {
    "zachem-rossiyaninu-zarubezhnaya-karta-2026": (
        "## Зачем вообще нужна зарубежная карта",
        '![Оплата банковской картой](../assets/img/credit-card.jpg '
        '"Зарубежная карта пригодится для подписок, онлайн-покупок и поездок. '
        f'Фото: [Unsplash]({UNS})")',
    ),
    "top-stran-dlya-karty-rossiyanam-2026": (
        "## Краткий разбор по странам",
        '![Загранпаспорт и посадочный талон](../assets/img/passport-travel.jpg '
        '"Загранпаспорт — ключевой документ для открытия счёта за рубежом. '
        f'Фото: [Unsplash]({UNS})")',
    ),
    "zarubezhnaya-karta-bez-problem-nalogi-otchetnost-limity": (
        "## Главное: счёт за рубежом — это отчётность",
        '![Онлайн-банкинг на ноутбуке](../assets/img/online-banking.jpg '
        '"Управление зарубежным счётом и отчётность — часть финансовой рутины. '
        f'Фото: [Unsplash]({UNS})")',
    ),
}

errors = []
for slug, (anchor, img) in INSERTS.items():
    path = ART / f"{slug}.json"
    data = json.load(open(path, encoding="utf-8"))
    body = data["bodyMarkdown"]
    if img.split("(", 1)[1][:25] in body:
        print(f"skip (уже есть): {slug}")
        continue
    if body.count(anchor) != 1:
        errors.append(f"{slug}: якорь найден {body.count(anchor)} раз: {anchor}")
        continue
    body = body.replace(anchor, img + "\n\n" + anchor, 1)
    data["bodyMarkdown"] = body
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"ok: {slug}")

if errors:
    print("\nОШИБКИ:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("\nГотово.")
