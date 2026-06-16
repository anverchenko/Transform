import sys
import os
import io
import time
import datetime
import traceback
import whisper

# PyInstaller sets stdout/stderr to None in windowed mode; tqdm crashes on it
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()
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

def format_elapsed(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}м {s}с" if m else f"{s}с"


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

        # --- Model --- (default: tiny = fastest)
        tk.Label(root, text="Model:").grid(row=2, column=0, sticky="w", **pad)
        self.model_var = tk.StringVar(value="tiny")
        ttk.Combobox(root, values=MODELS, textvariable=self.model_var, width=10, state="readonly").grid(row=2, column=1, sticky="w", **pad)

        # --- Clip range: from / to ---
        clip_frame = tk.Frame(root)
        clip_frame.grid(row=3, column=0, columnspan=3, sticky="w", padx=10, pady=5)
        tk.Label(clip_frame, text="Від секунди:").pack(side="left")
        self.clip_start_var = tk.StringVar(value="")
        tk.Entry(clip_frame, textvariable=self.clip_start_var, width=8).pack(side="left", padx=(4, 12))
        tk.Label(clip_frame, text="По секунду:").pack(side="left")
        self.clip_end_var = tk.StringVar(value="")
        tk.Entry(clip_frame, textvariable=self.clip_end_var, width=8).pack(side="left", padx=(4, 12))
        tk.Label(clip_frame, text="(порожньо = весь файл)", fg="gray", font=("", 8)).pack(side="left")

        # --- Advanced settings toggle ---
        self.show_advanced = tk.BooleanVar(value=False)
        tk.Checkbutton(root, text="Advanced model settings", variable=self.show_advanced, command=self.toggle_advanced).grid(row=4, column=0, columnspan=3, sticky="w", padx=10)

        # --- Advanced frame ---
        self.adv_frame = tk.LabelFrame(root, text="Model parameters", padx=8, pady=5)

        def adv_row(label, widget_fn, r, hint=""):
            tk.Label(self.adv_frame, text=label).grid(row=r, column=0, sticky="w", pady=2)
            widget_fn(r)
            if hint:
                tk.Label(self.adv_frame, text=hint, fg="gray", font=("", 8)).grid(row=r, column=2, sticky="w", padx=5)

        # no_speech_threshold
        self.no_speech_var = tk.DoubleVar(value=1.0)
        def make_no_speech(r):
            tk.Scale(self.adv_frame, variable=self.no_speech_var, from_=0.0, to=1.0, resolution=0.05,
                     orient="horizontal", length=200).grid(row=r, column=1)
        adv_row("No speech threshold:", make_no_speech, 0, "Higher = keep more silent parts (1.0 = keep all)")

        # logprob_threshold
        self.logprob_var = tk.DoubleVar(value=-3.0)
        def make_logprob(r):
            tk.Scale(self.adv_frame, variable=self.logprob_var, from_=-3.0, to=0.0, resolution=0.1,
                     orient="horizontal", length=200).grid(row=r, column=1)
        adv_row("Logprob threshold:", make_logprob, 1, "Lower = accept low-confidence text")

        # compression_ratio_threshold
        self.compression_var = tk.DoubleVar(value=3.0)
        def make_compression(r):
            tk.Scale(self.adv_frame, variable=self.compression_var, from_=1.0, to=5.0, resolution=0.1,
                     orient="horizontal", length=200).grid(row=r, column=1)
        adv_row("Compression ratio:", make_compression, 2, "Higher = allow mixed/varied content")

        # condition_on_previous_text (off by default = faster)
        self.condition_var = tk.BooleanVar(value=False)
        def make_condition(r):
            tk.Checkbutton(self.adv_frame, variable=self.condition_var).grid(row=r, column=1, sticky="w")
        adv_row("Use previous context:", make_condition, 3, "Helps coherence but slower")

        # word_timestamps (off by default = faster)
        self.word_ts_var = tk.BooleanVar(value=False)
        def make_word_ts(r):
            tk.Checkbutton(self.adv_frame, variable=self.word_ts_var).grid(row=r, column=1, sticky="w")
        adv_row("Word timestamps:", make_word_ts, 4, "Precise timing per word (slower)")

        # fp16
        self.fp16_var = tk.BooleanVar(value=False)
        def make_fp16(r):
            tk.Checkbutton(self.adv_frame, variable=self.fp16_var).grid(row=r, column=1, sticky="w")
        adv_row("FP16 (GPU only):", make_fp16, 5, "Faster on GPU, disable for CPU")

        # --- Start button ---
        self.btn = tk.Button(root, text="Start Transcription", command=self.start, bg="#4CAF50", fg="white", width=20)
        self.btn.grid(row=6, column=0, columnspan=3, pady=10)

        # --- Status ---
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(root, textvariable=self.status_var, fg="gray").grid(row=7, column=0, columnspan=3, **pad)

        # --- Progress bar ---
        self.progress = ttk.Progressbar(root, mode="indeterminate", length=400)
        self.progress.grid(row=8, column=0, columnspan=3, **pad)

    def toggle_advanced(self):
        if self.show_advanced.get():
            self.adv_frame.grid(row=5, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
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

        self.btn.config(state="disabled")
        self.progress.start(10)
        self.status_var.set("Working...")
        thread = threading.Thread(target=self.run, args=(audio_path,), daemon=True)
        thread.start()

    def run(self, audio_path):
        try:
            t_start = time.time()  # total time including model load

            lang_raw = self.lang_var.get().split(" — ")[0]
            model_name = self.model_var.get()

            # Parse clip range
            clip_start_raw = self.clip_start_var.get().strip()
            clip_end_raw = self.clip_end_var.get().strip()
            clip_start = float(clip_start_raw) if clip_start_raw else None
            clip_end = float(clip_end_raw) if clip_end_raw else None

            # Parse advanced params
            no_speech = self.no_speech_var.get()
            logprob = self.logprob_var.get()

            self.status_var.set("Loading model...")
            model = whisper.load_model(model_name)

            self.status_var.set("Transcribing...")

            PROMPTS = {
                "uk": "ну, ось, так, е, ем, а, і, й, от, це, воно, типу, короче",
                "ru": "ну, вот, так, э, эм, а, и, это, типа, короче, значит",
                "en": "um, uh, well, so, like, you know, I mean, actually",
            }
            initial_prompt = PROMPTS.get(lang_raw, "")

            transcribe_kwargs = dict(
                language=lang_raw,
                task="transcribe",
                initial_prompt=initial_prompt,
                suppress_tokens=[],
                no_speech_threshold=float("inf") if no_speech >= 1.0 else no_speech,
                logprob_threshold=float("-inf") if logprob <= -3.0 else logprob,
                compression_ratio_threshold=self.compression_var.get(),
                condition_on_previous_text=self.condition_var.get(),
                word_timestamps=self.word_ts_var.get(),
                fp16=self.fp16_var.get(),
                verbose=False,
            )

            # Build clip_timestamps: [start, end] in seconds
            if clip_start is not None or clip_end is not None:
                cs = clip_start if clip_start is not None else 0.0
                # end=None means transcribe to file end — omit upper bound
                if clip_end is not None:
                    transcribe_kwargs["clip_timestamps"] = [cs, clip_end]
                else:
                    transcribe_kwargs["clip_timestamps"] = [cs]

            result = model.transcribe(audio_path, **transcribe_kwargs)
            elapsed = time.time() - t_start

            segments = result["segments"]
            lines = []
            for seg in segments:
                s = format_time(seg["start"])
                e = format_time(seg["end"])
                text = seg["text"].strip()
                if text:
                    lines.append(f"[{s} → {e}]  {text}")

            # Build log header
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            filename = os.path.basename(audio_path)
            if clip_start is not None or clip_end is not None:
                cs_str = format_time(clip_start or 0)
                ce_str = format_time(clip_end) if clip_end else "кінець"
                fragment_str = f"{cs_str} → {ce_str}"
            else:
                fragment_str = "весь файл"

            header = (
                f"Файл:              {filename}\n"
                f"Дата:              {now_str}\n"
                f"Модель:            {model_name} | Мова: {lang_raw}\n"
                f"Фрагмент:          {fragment_str}\n"
                f"Час обробки:       {format_elapsed(elapsed)}\n"
                f"Сегментів:         {len(segments)}\n"
                f"{'─' * 60}\n"
            )

            output_path = os.path.splitext(audio_path)[0] + "_transcription.txt"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(header + "\n".join(lines))

            self.root.after(0, self.on_success, output_path, len(segments), elapsed)

        except Exception:
            self.root.after(0, self.on_error, traceback.format_exc())

    def on_success(self, output_path, count, elapsed):
        self.progress.stop()
        self.btn.config(state="normal")
        time_str = format_elapsed(elapsed)
        self.status_var.set(f"Done! {count} segments — {time_str}")
        messagebox.showinfo("Done!", f"Transcription complete!\n\n{count} segments\nTotal time: {time_str}\n\nSaved to:\n{output_path}")

    def on_error(self, error_msg):
        self.progress.stop()
        self.btn.config(state="normal")
        self.status_var.set("Error.")

        win = tk.Toplevel(self.root)
        win.title("Error")
        win.grab_set()
        tk.Label(win, text="Something went wrong:", fg="red").pack(padx=10, pady=(10, 0))
        txt = tk.Text(win, wrap="word", width=70, height=15)
        txt.insert("1.0", error_msg)
        txt.config(state="disabled")
        txt.pack(padx=10, pady=5)
        tk.Button(win, text="Close", command=win.destroy).pack(pady=(0, 10))


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
