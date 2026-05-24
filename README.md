# Управляющая программа для экспериментальной установки очистки воздуха

## Локальный запуск

```powershell
uv sync
uv run -m co2_control_app
```

Резервный вариант без сокращения:

```powershell
uv run python -m co2_control_app
```

Локальные скрипты сборки отсутствуют намеренно. Исполняемые файлы собираются через GitHub Actions при push в ветку `main`.

## Автоматическая сборка

Workflow `.github/workflows/build-desktop.yml` запускается при push в ветку `main` и публикует артефакты для Windows, Linux и macOS.
