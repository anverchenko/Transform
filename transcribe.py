import whisper
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

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

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Transform — Audio Transcription")
        self.root.resizable(False, False)

        pad = {"padx": 10, "pady": 5}

        # --- File selection ---
        tk.Label(root, text="Audio file:").grid(row=0, column=0, sticky="w", **pad)
        self.file_var = tk.StringVar()
        tk.Entry(root, textvariable=self.file_var, width=45).grid(row=0, column=1, **pad)
        tk.Button(root, text="Browse...", command=self.browse).grid(row=0, column=2, **pad)

        # --- Language ---
        tk.Label(root, text="Language:").grid(row=1, column=0, sticky="w", **pad)
        self.lang_var = tk.StringVar(value="uk")
        lang_options = [f"{code} — {name}" for code, name in LANGUAGES.items()]
        self.lang_combo = ttk.Combobox(root, values=lang_options, textvariable=self.lang_var, width=20, state="readonly")
        self.lang_combo.current(0)
        self.lang_combo.grid(row=1, column=1, sticky="w", **pad)

        # --- Model ---
        tk.Label(root, text="Model:").grid(row=2, column=0, sticky="w", **pad)
        self.model_var = tk.StringVar(value="large")
        ttk.Combobox(root, values=MODELS, textvariable=self.model_var, width=10, state="readonly").grid(row=2, column=1, sticky="w", **pad)

        # --- Start button ---
        self.btn = tk.Button(root, text="Start Transcription", command=self.start, bg="#4CAF50", fg="white", width=20)
        self.btn.grid(row=3, column=0, columnspan=3, pady=10)

        # --- Status ---
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(root, textvariable=self.status_var, fg="gray").grid(row=4, column=0, columnspan=3, **pad)

        # --- Progress bar ---
        self.progress = ttk.Progressbar(root, mode="indeterminate", length=400)
        self.progress.grid(row=5, column=0, columnspan=3, **pad)

    def browse(self):
        path = filedialog.askopenfilename(
            title="Select audio file",
            filetypes=[("Audio files", "*.mp3 *.mp4 *.m4a *.wav *.ogg *.flac *.webm"), ("All files", "*.*")]
        )
        if path:
            self.file_var.set(path)

    def start(self):
        audio_path = self.file_var.get().strip()
        if not audio_path:
            messagebox.showerror("Error", "Please select an audio file first.")
            return
        if not os.path.exists(audio_path):
            messagebox.showerror("Error", f"File not found:\n{audio_path}")
            return

        # Run in background thread so UI doesn't freeze
        self.btn.config(state="disabled")
        self.progress.start(10)
        self.status_var.set("Working...")
        thread = threading.Thread(target=self.run, args=(audio_path,), daemon=True)
        thread.start()

    def run(self, audio_path):
        try:
            lang_raw = self.lang_var.get().split(" — ")[0]  # extract code like "uk"
            model_name = self.model_var.get()

            self.status_var.set("Loading model...")
            model = whisper.load_model(model_name)

            self.status_var.set("Transcribing...")
            result = model.transcribe(
                audio_path,
                language=lang_raw,
                task="transcribe",
                suppress_tokens=[],
                no_speech_threshold=0.3,
                logprob_threshold=-1.5,
                compression_ratio_threshold=3.0,
                condition_on_previous_text=True,
                word_timestamps=True,
                fp16=False,
                verbose=False,
            )

            segments = result["segments"]
            lines = []
            for seg in segments:
                start = format_time(seg["start"])
                end   = format_time(seg["end"])
                text  = seg["text"].strip()
                if text:
                    lines.append(f"[{start} → {end}]  {text}")

            output_path = os.path.splitext(audio_path)[0] + "_transcription.txt"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            self.root.after(0, self.on_success, output_path, len(segments))

        except Exception as e:
            self.root.after(0, self.on_error, str(e))

    def on_success(self, output_path, count):
        self.progress.stop()
        self.btn.config(state="normal")
        self.status_var.set(f"Done! {count} segments saved.")
        messagebox.showinfo("Done!", f"Transcription complete!\n\nSaved to:\n{output_path}")

    def on_error(self, error_msg):
        self.progress.stop()
        self.btn.config(state="normal")
        self.status_var.set("Error.")
        messagebox.showerror("Error", f"Something went wrong:\n\n{error_msg}")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
