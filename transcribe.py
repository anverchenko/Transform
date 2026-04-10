import whisper
import sys
import os
import argparse

# Available languages with friendly names
LANGUAGES = {
    "uk": "Українська",
    "en": "English",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "pl": "Polski",
    "ru": "Русский",
    "it": "Italiano",
    "pt": "Português",
    "ja": "日本語",
    "zh": "中文",
    "ar": "العربية",
}

MODELS = ["tiny", "base", "small", "medium", "large"]

def list_languages():
    print("Available languages:")
    for code, name in LANGUAGES.items():
        marker = " (default)" if code == "uk" else ""
        print(f"  {code}  —  {name}{marker}")

def format_time(seconds):
    """Convert seconds to HH:MM:SS format"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def transcribe(audio_path, lang, model_name):
    # Check if file exists
    if not os.path.exists(audio_path):
        print(f"Error: file '{audio_path}' not found")
        sys.exit(1)

    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
    print(f"File: {audio_path} ({file_size_mb:.1f} MB)")
    print(f"Language: {LANGUAGES.get(lang, lang)}")
    print(f"Model: {model_name}")
    print(f"Loading model (first run downloads it)...")

    model = whisper.load_model(model_name)

    print(f"Transcribing... (large files may take a few minutes)")

    result = model.transcribe(
        audio_path,
        language=lang,
        task="transcribe",

        # --- FULL transcription settings ---
        suppress_tokens=[],          # do NOT suppress any tokens (filler words, "е", "м", "хм")
        no_speech_threshold=0.3,     # low threshold — don't skip quiet/uncertain parts
        logprob_threshold=-1.5,      # accept even low-confidence segments
        compression_ratio_threshold=3.0,  # allow varied/mixed-language content

        # --- Quality settings ---
        condition_on_previous_text=True,  # use context from previous segments
        word_timestamps=True,             # enable word-level timestamps
        fp16=False,                       # CPU-safe mode
        verbose=False,
    )

    segments = result["segments"]

    # Build output lines with timecodes
    lines = []
    for seg in segments:
        start = format_time(seg["start"])
        end   = format_time(seg["end"])
        text  = seg["text"].strip()
        if text:
            lines.append(f"[{start} → {end}]  {text}")

    output_text = "\n".join(lines)

    # Print to terminal
    print("\n--- Transcription ---\n")
    print(output_text)

    # Save to .txt file
    output_path = os.path.splitext(audio_path)[0] + "_transcription.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_text)

    print(f"\n--- Done ---")
    print(f"Segments: {len(segments)}")
    print(f"Saved to: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Full audio transcription with timecodes (Whisper)",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("audio", nargs="?", help="Path to audio file")
    parser.add_argument(
        "--lang", default="uk", choices=LANGUAGES.keys(), metavar="LANG",
        help="Language code (default: uk)\nUse --list-langs to see all options"
    )
    parser.add_argument(
        "--model", default="large", choices=MODELS, metavar="MODEL",
        help="Whisper model (default: large)\nOptions: tiny, base, small, medium, large\nLarger = more accurate but slower"
    )
    parser.add_argument("--list-langs", action="store_true", help="Show available languages and exit")

    args = parser.parse_args()

    if args.list_langs:
        list_languages()
        sys.exit(0)

    if not args.audio:
        parser.print_help()
        print()
        list_languages()
        sys.exit(1)

    transcribe(args.audio, args.lang, args.model)
