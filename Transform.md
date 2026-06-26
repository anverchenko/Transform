# Transform — Audio Transcription

Десктопний застосунок для транскрипції аудіо в текст за допомогою AI (OpenAI Whisper).

## Можливості

- Підтримка форматів: mp3, mp4, m4a, wav, ogg, flac, webm
- 12 мов (українська, англійська, німецька та інші)
- Моделі Whisper: tiny, base, small, medium, large
- Обрізка аудіо по секундах
- Результат зберігається у .txt файл поряд з аудіо

## Запуск

```bash
pip install -r requirements.txt
python transcribe.py
```

## Вимоги

- Python 3.8+
- ffmpeg (додати в PATH)
- Залежності з requirements.txt
