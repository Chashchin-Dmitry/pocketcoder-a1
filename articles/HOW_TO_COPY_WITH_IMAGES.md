# Как скопировать Markdown-статью с картинками в буфер обмена (macOS)

## Проблема

`pbcopy` копирует только текст. Картинки из Markdown (`![alt](file.png)`) не попадают в буфер.

## Решение

Два шага:
1. **pandoc** конвертирует `.md` в HTML, вшивая картинки как base64 (`--self-contained`)
2. **Swift + NSPasteboard** кладёт HTML в буфер как rich content (не plain text)

## Требования

- macOS (Swift и NSPasteboard встроены)
- pandoc (`brew install pandoc`)

## Одна команда

```bash
cd /путь/к/папке/со/статьёй && \
pandoc article.md \
  --self-contained \
  --resource-path=".:diagrams:screenshots" \
  --metadata title="Title" \
  -t html -o /tmp/_md2clip.html && \
swift -e '
import Cocoa
let data = try! Data(contentsOf: URL(fileURLWithPath: "/tmp/_md2clip.html"))
let html = String(data: data, encoding: .utf8)!
let pb = NSPasteboard.general
pb.clearContents()
pb.setString(html, forType: .html)
print("OK: \(data.count / 1024)KB in clipboard")
'
```

Затем Cmd+V в Notion / Google Docs / любой редактор.

## Разбор по шагам

### Шаг 1: pandoc конвертирует Markdown в HTML

```bash
pandoc article.md --self-contained --resource-path=".:diagrams:screenshots" -t html -o /tmp/_md2clip.html
```

| Флаг | Зачем |
|------|-------|
| `--self-contained` | Вшивает картинки как base64 прямо в HTML |
| `--resource-path=".:diagrams:screenshots"` | Где искать картинки (текущая папка + подпапки) |
| `-t html` | Формат вывода — HTML |
| `-o /tmp/_md2clip.html` | Временный файл |

Если картинки лежат в других папках — добавь их через `:` в `--resource-path`.

### Шаг 2: Swift кладёт HTML в буфер как rich content

```swift
import Cocoa
let data = try! Data(contentsOf: URL(fileURLWithPath: "/tmp/_md2clip.html"))
let html = String(data: data, encoding: .utf8)!
let pb = NSPasteboard.general
pb.clearContents()
pb.setString(html, forType: .html)
```

Ключевой момент: `.html` тип в NSPasteboard. Без этого буфер содержит plain text и картинки не вставляются.

## Скрипт md2clip

Положить в `~/bin/md2clip` (или `/usr/local/bin/md2clip`) и сделать `chmod +x`:

```bash
#!/bin/bash
# md2clip — копирует Markdown с картинками в буфер обмена
# Использование: md2clip article.md [папка1:папка2:...]

set -e

FILE="$1"
RESOURCE_DIRS="${2:-.:diagrams:screenshots:images:assets}"

if [ -z "$FILE" ]; then
  echo "Использование: md2clip <file.md> [resource_dirs]"
  echo "Пример: md2clip article_ru.md .:diagrams:screenshots"
  exit 1
fi

if [ ! -f "$FILE" ]; then
  echo "Файл не найден: $FILE"
  exit 1
fi

DIR=$(dirname "$FILE")
BASENAME=$(basename "$FILE" .md)
TMPFILE="/tmp/_md2clip_${BASENAME}.html"

cd "$DIR"

pandoc "$(basename "$FILE")" \
  --self-contained \
  --resource-path="$RESOURCE_DIRS" \
  --metadata title="$BASENAME" \
  -t html \
  -o "$TMPFILE"

swift -e "
import Cocoa
let data = try! Data(contentsOf: URL(fileURLWithPath: \"$TMPFILE\"))
let html = String(data: data, encoding: .utf8)!
let pb = NSPasteboard.general
pb.clearContents()
pb.setString(html, forType: .html)
print(\"OK: \(data.count / 1024)KB copied to clipboard with images\")
"
```

После этого:

```bash
md2clip article_ru.md                          # стандартные папки
md2clip article_ru.md .:diagrams:screenshots   # указать папки вручную
```

## Где работает вставка

| Редактор | Картинки вставляются |
|----------|---------------------|
| Google Docs | Да |
| Notion | Да |
| Apple Pages | Да |
| Telegram | Да |
| Habr | Нет (нужен их загрузчик картинок) |
| GitHub | Нет (нужен upload) |

## Почему это работает

1. `pbcopy` пишет в буфер как `public.utf8-plain-text` — просто текст
2. `NSPasteboard.setString(forType: .html)` пишет как `public.html` — rich content
3. Приложения видят HTML-тип, парсят `<img src="data:image/png;base64,...">` и рендерят картинки
