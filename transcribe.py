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

        # --- Advanced settings toggle ---
        self.show_advanced = tk.BooleanVar(value=False)
        tk.Checkbutton(root, text="Advanced model settings", variable=self.show_advanced, command=self.toggle_advanced).grid(row=3, column=0, columnspan=3, sticky="w", padx=10)

        # --- Advanced frame ---
        self.adv_frame = tk.LabelFrame(root, text="Model parameters", padx=8, pady=5)

        def row(label, widget_fn, r, hint=""):
            tk.Label(self.adv_frame, text=label).grid(row=r, column=0, sticky="w", pady=2)
            widget_fn(r)
            if hint:
                tk.Label(self.adv_frame, text=hint, fg="gray", font=("", 8)).grid(row=r, column=2, sticky="w", padx=5)

        # no_speech_threshold
        self.no_speech_var = tk.DoubleVar(value=0.3)
        def make_no_speech(r):
            tk.Scale(self.adv_frame, variable=self.no_speech_var, from_=0.0, to=1.0, resolution=0.05,
                     orient="horizontal", length=200).grid(row=r, column=1)
        row("No speech threshold:", make_no_speech, 0, "Lower = include more quiet parts")

        # logprob_threshold
        self.logprob_var = tk.DoubleVar(value=-1.5)
        def make_logprob(r):
            tk.Scale(self.adv_frame, variable=self.logprob_var, from_=-3.0, to=0.0, resolution=0.1,
                     orient="horizontal", length=200).grid(row=r, column=1)
        row("Logprob threshold:", make_logprob, 1, "Lower = accept low-confidence text")

        # compression_ratio_threshold
        self.compression_var = tk.DoubleVar(value=3.0)
        def make_compression(r):
            tk.Scale(self.adv_frame, variable=self.compression_var, from_=1.0, to=5.0, resolution=0.1,
                     orient="horizontal", length=200).grid(row=r, column=1)
        row("Compression ratio:", make_compression, 2, "Higher = allow mixed/varied content")

        # condition_on_previous_text
        self.condition_var = tk.BooleanVar(value=True)
        def make_condition(r):
            tk.Checkbutton(self.adv_frame, variable=self.condition_var).grid(row=r, column=1, sticky="w")
        row("Use previous context:", make_condition, 3, "Helps coherence between segments")

        # word_timestamps
        self.word_ts_var = tk.BooleanVar(value=True)
        def make_word_ts(r):
            tk.Checkbutton(self.adv_frame, variable=self.word_ts_var).grid(row=r, column=1, sticky="w")
        row("Word timestamps:", make_word_ts, 4, "Precise timing per word")

        # fp16
        self.fp16_var = tk.BooleanVar(value=False)
        def make_fp16(r):
            tk.Checkbutton(self.adv_frame, variable=self.fp16_var).grid(row=r, column=1, sticky="w")
        row("FP16 (GPU only):", make_fp16, 5, "Faster on GPU, disable for CPU")

        # --- Start button ---
        self.btn = tk.Button(root, text="Start Transcription", command=self.start, bg="#4CAF50", fg="white", width=20)
        self.btn.grid(row=5, column=0, columnspan=3, pady=10)

        # --- Status ---
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(root, textvariable=self.status_var, fg="gray").grid(row=6, column=0, columnspan=3, **pad)

        # --- Progress bar ---
        self.progress = ttk.Progressbar(root, mode="indeterminate", length=400)
        self.progress.grid(row=7, column=0, columnspan=3, **pad)

    def toggle_advanced(self):
        if self.show_advanced.get():
            self.adv_frame.grid(row=4, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        else:
            self.adv_frame.grid_remove()

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
                no_speech_threshold=self.no_speech_var.get(),
                logprob_threshold=self.logprob_var.get(),
                compression_ratio_threshold=self.compression_var.get(),
                condition_on_previous_text=self.condition_var.get(),
                word_timestamps=self.word_ts_var.get(),
                fp16=self.fp16_var.get(),
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
