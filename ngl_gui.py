import customtkinter as ctk
import threading
import random
import queue
import itertools
from datetime import datetime

# ── Try importing playwright; show error in UI if missing ──────────────────────
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False

# ── Theme ──────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT   = "#7C3AED"   # purple
ACCENT2  = "#06B6D4"   # cyan
SUCCESS  = "#10B981"   # green
ERROR    = "#EF4444"   # red
WARN     = "#F59E0B"   # amber
BG       = "#0F0F1A"
CARD     = "#161627"
CARD2    = "#1E1E35"
TEXT     = "#E2E8F0"
MUTED    = "#64748B"

MESSAGES = [
    "You're absolutely amazing 🌟",
    "Keep being you, always!",
    "You're one of a kind 💫",
    "Sending good vibes your way!",
    "You're genuinely cool 😎",
    "Never change, seriously.",
    "Big fan of everything you do ✨",
    "You make the world better 🌍",
    "Stay awesome, always!",
    "You inspire people around you 💪",
    "You're a vibe 🔥",
    "Honestly? You're great.",
    "The world needs more people like you 🙌",
    "You radiate good energy ⚡",
    "Rooting for you every single day 🎯",
]


# ── Worker ─────────────────────────────────────────────────────────────────────
def worker(url, count, thread_id, log_q, stop_event, done_q):
    if not PLAYWRIGHT_OK:
        log_q.put(("error", "playwright not installed. Run: pip install playwright && python -m playwright install"))
        done_q.put(thread_id)
        return

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()

            def block_resources(route):
                if route.request.resource_type in ("image", "media", "font"):
                    route.abort()
                else:
                    route.continue_()

            page = context.new_page()
            page.route("**/*", block_resources)

            # count=-1 means unlimited — loop until stop_event is set
            counter = itertools.count(1) if count == -1 else range(1, count + 1)
            for i in counter:
                if stop_event.is_set():
                    log_q.put(("warn", f"[T{thread_id}] Stopped by user."))
                    break

                label = f"{i}/∞" if count == -1 else f"{i}/{count}"
                log_q.put(("info", f"[T{thread_id}] [{label}] Sending..."))
                sent = False

                for attempt in range(3):  # retry up to 3x on transient errors
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        page.wait_for_selector('textarea', timeout=8000)

                        msg = random.choice(MESSAGES)
                        page.fill('textarea', '')
                        page.type('textarea', msg, delay=20)

                        page.wait_for_selector('button.submit:visible', timeout=8000)
                        page.click('button.submit')

                        # Wait for post-submit redirect to fully settle before next goto
                        # This prevents ERR_ABORTED on the next navigation
                        try:
                            page.wait_for_load_state("networkidle", timeout=3000)
                        except Exception:
                            page.wait_for_timeout(900)  # fallback if networkidle times out

                        log_q.put(("success", f"[T{thread_id}] [{label}] ✓ Sent: \"{msg}\""))
                        log_q.put(("progress", None))
                        sent = True
                        break  # success — no retry needed

                    except Exception as e:
                        err = str(e)
                        if "ERR_ABORTED" in err and attempt < 2:
                            log_q.put(("warn", f"[T{thread_id}] [{label}] Retrying (aborted)..."))
                            page.wait_for_timeout(700)
                            continue
                        log_q.put(("error", f"[T{thread_id}] [{label}] ✗ {err.splitlines()[0]}"))
                        log_q.put(("progress", None))
                        break

            browser.close()
    except Exception as e:
        log_q.put(("error", f"[T{thread_id}] Browser error: {e}"))

    done_q.put(thread_id)


# ── Main App ───────────────────────────────────────────────────────────────────
class NGLApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NGL Blaster")
        self.geometry("860x680")
        self.minsize(760, 600)
        self.configure(fg_color=BG)

        self.log_q    = queue.Queue()
        self.done_q   = queue.Queue()
        self.stop_evt = threading.Event()
        self.total    = 0
        self.sent     = 0
        self.active_threads = 0
        self.unlimited_mode = False

        self._build_ui()
        self._poll()

    # ── UI Construction ────────────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Header ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=70)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        dot_frame = ctk.CTkFrame(header, fg_color="transparent")
        dot_frame.grid(row=0, column=0, padx=20, pady=20)
        for color in ["#EF4444", "#F59E0B", "#10B981"]:
            ctk.CTkLabel(dot_frame, text="●", text_color=color, font=("Segoe UI", 12)).pack(side="left", padx=2)

        ctk.CTkLabel(
            header, text="NGL  Blaster",
            font=("Segoe UI", 22, "bold"), text_color=TEXT
        ).grid(row=0, column=1, pady=20)

        ctk.CTkLabel(
            header, text="v2.0  •  anonymous messages",
            font=("Segoe UI", 11), text_color=MUTED
        ).grid(row=0, column=2, padx=20, pady=20)

        # ── Controls Card ───────────────────────────────────────────────────
        ctrl = ctk.CTkFrame(self, fg_color=CARD, corner_radius=16)
        ctrl.grid(row=1, column=0, padx=20, pady=(16, 8), sticky="ew")
        ctrl.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # URL
        url_frame = ctk.CTkFrame(ctrl, fg_color=CARD2, corner_radius=10)
        url_frame.grid(row=0, column=0, columnspan=4, padx=16, pady=(16, 8), sticky="ew")
        url_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(url_frame, text="🔗", font=("Segoe UI", 16), text_color=ACCENT2).grid(row=0, column=0, padx=(12, 6), pady=10)
        self.url_entry = ctk.CTkEntry(
            url_frame, placeholder_text="https://ngl.link/username",
            font=("Segoe UI", 13), fg_color="transparent",
            border_width=0, text_color=TEXT, height=40
        )
        self.url_entry.grid(row=0, column=1, sticky="ew", pady=10, padx=(0, 12))

        # Count / Threads / Delay sliders
        self.count_slider_frame = self._labeled_slider(ctrl, "Messages", 1, 200, 10, row=1, col=0, attr="count_var")
        self._labeled_slider(ctrl, "Threads",  1,  10,  1, row=1, col=1, attr="threads_var")
        self._labeled_slider(ctrl, "Delay (ms)", 100, 2000, 400, row=1, col=2, attr="delay_var")

        # Unlimited toggle
        unlimited_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        unlimited_frame.grid(row=2, column=0, padx=16, pady=(0, 4), sticky="w")
        self.unlimited_var = ctk.BooleanVar(value=False)
        ctk.CTkLabel(unlimited_frame, text="∞  Unlimited Mode", font=("Segoe UI", 12), text_color=MUTED).pack(side="left", padx=(0, 10))
        self.unlimited_switch = ctk.CTkSwitch(
            unlimited_frame, text="", variable=self.unlimited_var,
            onvalue=True, offvalue=False,
            fg_color=CARD2, progress_color=WARN,
            button_color=ACCENT2, button_hover_color=ACCENT,
            width=44, command=self._toggle_unlimited
        )
        self.unlimited_switch.pack(side="left")

        # Buttons
        btn_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        btn_frame.grid(row=1, column=3, padx=12, pady=12, sticky="nsew")
        btn_frame.grid_rowconfigure((0, 1), weight=1)

        self.start_btn = ctk.CTkButton(
            btn_frame, text="▶  START",
            font=("Segoe UI", 13, "bold"),
            fg_color=ACCENT, hover_color="#6D28D9",
            corner_radius=10, height=42,
            command=self._start
        )
        self.start_btn.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        self.stop_btn = ctk.CTkButton(
            btn_frame, text="■  STOP",
            font=("Segoe UI", 13, "bold"),
            fg_color="#1E1E35", hover_color="#2D1B69",
            border_width=1, border_color=ERROR,
            text_color=ERROR, corner_radius=10, height=42,
            command=self._stop, state="disabled"
        )
        self.stop_btn.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        # Progress bar
        prog_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        prog_frame.grid(row=2, column=0, columnspan=4, padx=16, pady=(4, 14), sticky="ew")
        prog_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(prog_frame, height=6, fg_color=CARD2, progress_color=ACCENT)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.progress_bar.set(0)

        self.prog_label = ctk.CTkLabel(prog_frame, text="0 / 0", font=("Segoe UI", 11), text_color=MUTED, width=60)
        self.prog_label.grid(row=0, column=1)

        # ── Log Area ────────────────────────────────────────────────────────
        log_frame = ctk.CTkFrame(self, fg_color=CARD, corner_radius=16)
        log_frame.grid(row=2, column=0, padx=20, pady=(0, 8), sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        log_header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(log_header, text="  Console Output", font=("Segoe UI", 12, "bold"), text_color=MUTED).grid(row=0, column=0, sticky="w")

        self.clear_btn = ctk.CTkButton(
            log_header, text="Clear", width=60, height=26,
            font=("Segoe UI", 11), fg_color=CARD2, hover_color="#2D2D4E",
            text_color=MUTED, corner_radius=6, command=self._clear_log
        )
        self.clear_btn.grid(row=0, column=1, sticky="e")

        self.log_box = ctk.CTkTextbox(
            log_frame, fg_color=CARD2, text_color=TEXT,
            font=("Courier", 11), corner_radius=10,
            wrap="word", state="disabled"
        )
        self.log_box.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")

        # colour tags
        self.log_box._textbox.tag_config("success", foreground=SUCCESS)
        self.log_box._textbox.tag_config("error",   foreground=ERROR)
        self.log_box._textbox.tag_config("warn",    foreground=WARN)
        self.log_box._textbox.tag_config("info",    foreground=ACCENT2)
        self.log_box._textbox.tag_config("time",    foreground=MUTED)

        # ── Status Bar ──────────────────────────────────────────────────────
        status = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=32)
        status.grid(row=3, column=0, sticky="ew")
        status.grid_propagate(False)
        status.grid_columnconfigure(1, weight=1)

        self.status_dot = ctk.CTkLabel(status, text="●", text_color=MUTED, font=("Segoe UI", 12))
        self.status_dot.grid(row=0, column=0, padx=(14, 4), pady=6)
        self.status_lbl = ctk.CTkLabel(status, text="Ready", font=("Segoe UI", 11), text_color=MUTED, anchor="w")
        self.status_lbl.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            status, text="⚡ Powered by Ajith",
            font=("Segoe UI", 11, "bold"), text_color=ACCENT2
        ).grid(row=0, column=2, padx=(0, 16), sticky="e")

        if not PLAYWRIGHT_OK:
            self._log("error", "⚠ playwright not found. Run: pip install playwright && python -m playwright install")

    def _labeled_slider(self, parent, label, from_, to, default, row, col, attr):
        frame = ctk.CTkFrame(parent, fg_color=CARD2, corner_radius=10)
        frame.grid(row=row, column=col, padx=(12 if col == 0 else 6, 6 if col < 2 else 0), pady=8, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        var = ctk.IntVar(value=default)
        setattr(self, attr, var)

        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 0))
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text=label, font=("Segoe UI", 11), text_color=MUTED).grid(row=0, column=0, sticky="w")
        val_lbl = ctk.CTkLabel(top, text=str(default), font=("Segoe UI", 11, "bold"), text_color=TEXT)
        val_lbl.grid(row=0, column=1, sticky="e")

        def on_change(v):
            val_lbl.configure(text=str(int(float(v))))

        ctk.CTkSlider(
            frame, from_=from_, to=to, variable=var,
            fg_color=BG, progress_color=ACCENT, button_color=ACCENT2,
            button_hover_color=ACCENT, command=on_change, height=16
        ).grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 10))
        return frame

    # ── Actions ────────────────────────────────────────────────────────────────
    def _toggle_unlimited(self):
        self.unlimited_mode = self.unlimited_var.get()
        state = "disabled" if self.unlimited_mode else "normal"
        for child in self.count_slider_frame.winfo_children():
            try:
                child.configure(state=state)
            except Exception:
                pass
            for sub in child.winfo_children():
                try:
                    sub.configure(state=state)
                except Exception:
                    pass

    def _start(self):
        url = self.url_entry.get().strip()
        if not url:
            self._log("error", "⚠ Please enter an NGL URL first.")
            return
        if not url.startswith("http"):
            url = "https://" + url

        unlimited  = self.unlimited_var.get()
        total      = -1 if unlimited else self.count_var.get()
        threads_n  = self.threads_var.get()
        self.total = total
        self.sent  = 0
        self.progress_bar.set(0)
        self.prog_label.configure(text="0 / ∞" if unlimited else f"0 / {total}")

        self.stop_evt.clear()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        label_count = "∞" if unlimited else str(total)
        self._set_status("running", f"Sending {label_count} messages via {threads_n} thread(s)...")
        self._log("info", f"━━ Starting  ▸  {url}  |  {label_count} msgs  |  {threads_n} thread(s) ━━")

        self.active_threads = threads_n
        for t in range(threads_n):
            threading.Thread(
                target=worker,
                args=(url, total, t + 1, self.log_q, self.stop_evt, self.done_q),
                daemon=True
            ).start()

    def _stop(self):
        self.stop_evt.set()
        self._set_status("warn", "Stopping…")
        self._log("warn", "■ Stop requested — waiting for threads to finish...")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ── Polling loop ───────────────────────────────────────────────────────────
    def _poll(self):
        try:
            while True:
                kind, msg = self.log_q.get_nowait()
                if kind == "progress":
                    self.sent += 1
                    if self.total == -1:
                        # Unlimited: pulse bar back and forth, show sent count only
                        self.progress_bar.set((self.sent % 20) / 20)
                        self.prog_label.configure(text=f"{self.sent} / ∞")
                    else:
                        ratio = self.sent / self.total if self.total else 0
                        self.progress_bar.set(ratio)
                        self.prog_label.configure(text=f"{self.sent} / {self.total}")
                else:
                    self._log(kind, msg)
        except queue.Empty:
            pass

        try:
            while True:
                self.done_q.get_nowait()
                self.active_threads -= 1
                if self.active_threads <= 0:
                    self._on_all_done()
        except queue.Empty:
            pass

        self.after(80, self._poll)

    def _on_all_done(self):
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        if self.stop_evt.is_set():
            self._set_status("warn", f"Stopped — {self.sent}/{self.total} sent")
            self._log("warn", f"━━ Stopped  |  {self.sent}/{self.total} sent ━━")
        else:
            self._set_status("success", f"Done — {self.sent}/{self.total} messages sent!")
            self._log("success", f"━━ Finished  |  {self.sent}/{self.total} sent ✓ ━━")
        self.progress_bar.set(self.sent / self.total if self.total else 1)

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _log(self, kind, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box._textbox.insert("end", f"[{ts}] ", ("time",))
        self.log_box._textbox.insert("end", msg + "\n", (kind,))
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_status(self, kind, text):
        colors = {"running": ACCENT2, "success": SUCCESS, "error": ERROR, "warn": WARN, "idle": MUTED}
        self.status_dot.configure(text_color=colors.get(kind, MUTED))
        self.status_lbl.configure(text=text)


if __name__ == "__main__":
    app = NGLApp()
    app.mainloop()
