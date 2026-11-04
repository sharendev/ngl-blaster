import argparse
import threading
import itertools
import random
import signal
import sys
import time
import uuid
import urllib.parse
import requests

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

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
]

stop_event = threading.Event()

def extract_username(url_or_user: str) -> str:
    cleaned = url_or_user.strip()
    if not cleaned:
        return ""
    if not cleaned.startswith("http://") and not cleaned.startswith("https://"):
        if "/" in cleaned:
            cleaned = "https://" + cleaned
        else:
            return cleaned.lstrip("@")
    parsed = urllib.parse.urlparse(cleaned)
    path = parsed.path.strip("/")
    parts = path.split("/")
    return parts[-1].lstrip("@") if parts and parts[-1] else ""


def send_ngl_messages(username, count, delay_ms=100, thread_id=1):
    session = requests.Session()
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Origin": "https://ngl.link",
        "Referer": f"https://ngl.link/{username}",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    counter = itertools.count(1) if count == -1 else range(1, count + 1)
    for i in counter:
        if stop_event.is_set():
            print(f"[Thread-{thread_id}] Stopped.")
            break

        label = f"{i}/∞" if count == -1 else f"{i}/{count}"
        print(f"[Thread-{thread_id}] [{label}] Sending...")

        msg = random.choice(MESSAGES)
        payload = {
            "username": username,
            "question": msg,
            "deviceId": str(uuid.uuid4()),
            "gameSlug": "",
            "referrer": "",
        }

        sent = False
        for attempt in range(3):
            if stop_event.is_set():
                break
            try:
                resp = session.post(
                    "https://ngl.link/api/submit",
                    data=payload,
                    headers=headers,
                    timeout=12
                )
                if resp.status_code == 200:
                    print(f"[Thread-{thread_id}] [{label}] ✓ Sent: \"{msg}\"")
                    sent = True
                    break
                elif resp.status_code == 429:
                    print(f"[Thread-{thread_id}] [{label}] Rate limit (429) hit, cooling down 2s...")
                    for _ in range(20):
                        if stop_event.is_set():
                            break
                        time.sleep(0.1)
                else:
                    print(f"[Thread-{thread_id}] [{label}] ✗ HTTP {resp.status_code}: {resp.text[:80]}")
                    break
            except requests.exceptions.RequestException as e:
                if attempt < 2 and not stop_event.is_set():
                    time.sleep(0.5)
                    continue
                print(f"[Thread-{thread_id}] [{label}] ✗ Connection error: {e}")
                break

        if delay_ms > 0 and not stop_event.is_set():
            sleep_steps = max(1, int(delay_ms / 50))
            for _ in range(sleep_steps):
                if stop_event.is_set():
                    break
                time.sleep(delay_ms / (1000.0 * sleep_steps))

    print(f"[Thread-{thread_id}] Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fast, ultra-lightweight NGL message sender (zero browser).")
    parser.add_argument("--url",       type=str, help="NGL link or username (e.g., https://ngl.link/username or username)")
    parser.add_argument("--count",     type=int, default=10, help="Number of messages to send")
    parser.add_argument("--threads",   type=int, default=1,  help="Number of parallel worker threads")
    parser.add_argument("--delay",     type=int, default=100, help="Delay between requests in ms")
    parser.add_argument("--unlimited", action="store_true",  help="Send unlimited messages until Ctrl+C")

    args = parser.parse_args()

    target = args.url
    if not target:
        target = input("Enter the NGL link or username: ")

    username = extract_username(target)
    if not username:
        print("[!] Invalid username or URL.")
        sys.exit(1)

    total         = -1 if args.unlimited else args.count
    threads_count = args.threads
    label_count   = "∞" if args.unlimited else str(total)

    def handle_sigint(sig, frame):
        print("\n[!] Ctrl+C — stopping all threads...")
        stop_event.set()
    signal.signal(signal.SIGINT, handle_sigint)

    print(f"Starting {threads_count} thread(s), sending {label_count} messages to @{username} (Direct HTTP • Low CPU)...")
    if args.unlimited:
        print("[!] Unlimited mode — press Ctrl+C to stop.\n")

    threads = []
    for t in range(threads_count):
        if args.unlimited:
            n = -1
        else:
            per_thread = total // threads_count
            remainder  = total % threads_count
            n = per_thread + (1 if t < remainder else 0)

        thread = threading.Thread(target=send_ngl_messages, args=(username, n, args.delay, t + 1))
        threads.append(thread)

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    print("All done!")
