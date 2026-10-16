from playwright.sync_api import sync_playwright
import argparse
import threading
import itertools
import random
import signal
import sys

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

stop_event = threading.Event()

def send_ngl_messages(url, count, thread_id=0):
    """count=-1 means unlimited."""
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

        counter = itertools.count(1) if count == -1 else range(1, count + 1)
        for i in counter:
            if stop_event.is_set():
                print(f"[Thread-{thread_id}] Stopped.")
                break

            label = f"{i}/∞" if count == -1 else f"{i}/{count}"
            print(f"[Thread-{thread_id}] [{label}] Sending...")

            for attempt in range(3):
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_selector('textarea', timeout=8000)

                    msg = random.choice(MESSAGES)
                    page.fill('textarea', '')
                    page.type('textarea', msg, delay=20)

                    page.wait_for_selector('button.submit:visible', timeout=8000)
                    page.click('button.submit')

                    try:
                        page.wait_for_load_state("networkidle", timeout=3000)
                    except Exception:
                        page.wait_for_timeout(900)

                    print(f"[Thread-{thread_id}] [{label}] ✓ Sent: \"{msg}\"")
                    break

                except Exception as e:
                    err = str(e)
                    if "ERR_ABORTED" in err and attempt < 2:
                        print(f"[Thread-{thread_id}] [{label}] Retrying...")
                        page.wait_for_timeout(700)
                        continue
                    print(f"[Thread-{thread_id}] [{label}] ✗ {err.splitlines()[0]}")
                    break

        browser.close()
        print(f"[Thread-{thread_id}] Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fast NGL message sender.")
    parser.add_argument("--url",       type=str, help="NGL link (e.g., https://ngl.link/username)")
    parser.add_argument("--count",     type=int, default=10, help="Number of messages to send")
    parser.add_argument("--threads",   type=int, default=1,  help="Number of parallel browser threads")
    parser.add_argument("--unlimited", action="store_true",  help="Send unlimited messages until Ctrl+C")

    args = parser.parse_args()

    url = args.url
    if not url:
        url = input("Enter the NGL link (e.g., https://ngl.link/username): ")

    total         = -1 if args.unlimited else args.count
    threads_count = args.threads
    label_count   = "∞" if args.unlimited else str(total)

    # Graceful Ctrl+C handler
    def handle_sigint(sig, frame):
        print("\n[!] Ctrl+C — stopping all threads...")
        stop_event.set()
    signal.signal(signal.SIGINT, handle_sigint)

    print(f"Starting {threads_count} thread(s), sending {label_count} messages total...")
    if args.unlimited:
        print("[!] Unlimited mode — press Ctrl+C to stop.\n")

    threads = []
    for t in range(threads_count):
        n = total  # each thread runs unlimited independently
        if not args.unlimited:
            per_thread = total // threads_count
            remainder  = total % threads_count
            n = per_thread + (1 if t < remainder else 0)

        thread = threading.Thread(target=send_ngl_messages, args=(url, n, t + 1))
        threads.append(thread)

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    print("All done!")

