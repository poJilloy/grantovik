#!/usr/bin/env python3
"""grantovik - a GUI tool for distributing TF2 promotional items.

Reads a file with one SteamID64 per line and grants a promo item to each ID
via the Steam store API. Progress is printed to the terminal and logged to
log.txt.
"""

import logging
import queue
import re
import threading
import time

import requests
from tkinter import (
    BOTTOM,
    DISABLED,
    END,
    NORMAL,
    TOP,
    Button,
    Entry,
    Label,
    Tk,
    Toplevel,
    messagebox,
)
from tkinter.filedialog import askopenfilename

# --- Logging -----------------------------------------------------------
# Log to file so failed distributions can be tracked down later.
# The file is created only when there is actually something to log (a
# launch with no activity must not leave an empty log.txt behind), and
# new entries are appended, so the history of previous runs is kept.
class LazyFileHandler(logging.Handler):
    """A file handler that opens the log lazily on the first log entry."""

    def __init__(self, filename="log.txt"):
        super().__init__()
        self._filename = filename
        self._fh = None
        self.setFormatter(
            logging.Formatter(fmt="%(asctime)s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )

    def _file(self):
        if self._fh is None:
            self._fh = open(self._filename, "a", encoding="utf-8")
        return self._fh

    def emit(self, record):
        try:
            fh = self._file()
            fh.write(self.format(record) + "\n")
            fh.flush()
        except OSError:
            pass  # a logging failure must not take the app down

    def close(self):
        if self._fh is not None:
            self._fh.close()
            self._fh = None
        super().close()


_root = logging.getLogger()
_root.setLevel(logging.INFO)
_root.addHandler(LazyFileHandler())

# --- Constants ---------------------------------------------------------
GRANT_ITEM_URL = "https://api.steampowered.com/ITFPromos_440/GrantItem/v0001/"
REQUEST_TIMEOUT = 15  # seconds; a request should never hang forever
STEAMID_RE = re.compile(r"^\d{17}$")
MAX_MESSAGES_PER_POLL = 200  # keep the main thread responsive for huge ID lists
REQUEST_DELAY = 0.2  # seconds between grants to avoid potential error 429
VERSION = "0.5"

# --- Global state (populated by main()) --------------------------------
root = None
apitoken = None
promoid = None
loadbutton = None
runbutton = None
stopbutton = None
filelabel = None
statuslabel = None
steam_ids = []
fileloaded = False
running = False
stop_event = threading.Event()
ui_queue = queue.Queue()
worker = None
about_window = None

# --- Input parsing -----------------------------------------------------

def parse_steam_ids(path):
    """Read SteamID64s from *path*, one per line.

    Returns (steam_ids, invalid_count, duplicate_count). Empty lines are
    ignored, malformed lines are counted as invalid, and repeated IDs are
    counted as duplicates (only the first occurrence is kept).
    """
    # utf-8-sig: transparently drops a BOM if present, harmless otherwise
    with open(path, encoding="utf-8-sig") as fh:
        lines = fh.read().splitlines()

    steam_ids = []
    seen = set()
    invalid = 0
    duplicates = 0
    for line in lines:
        steam_id = line.strip()
        if not steam_id:
            continue
        if not STEAMID_RE.match(steam_id):
            invalid += 1
            continue
        if steam_id in seen:
            duplicates += 1
            continue
        seen.add(steam_id)
        steam_ids.append(steam_id)

    return steam_ids, invalid, duplicates

# --- Distribution logic -------------------------------------------------

def grant_item(steam_id, promo_id, api_key):
    try:
        response = requests.post(
            GRANT_ITEM_URL,
            data={
                "SteamID": steam_id,
                "PromoID": promo_id,
                "Key": api_key,
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        return f"[FAIL: network error ({type(exc).__name__})]"

    try:
        payload = response.json()
    except ValueError:
        return "[FAIL: request error/not authorized]"

    if not isinstance(payload, dict):
        return "[FAIL: request error/not authorized]"

    result = payload.get("result")
    if not isinstance(result, dict):
        return "[FAIL: response error/invalid promo id]"

    try:
        status = int(result["status"])
    except (KeyError, TypeError, ValueError):
        return "[FAIL: response error/invalid promo id]"

    if status != 1:
        return f"[FAIL: {result.get('statusDetail', 'unknown error')}]"
    return "[SUCCESS!]"


def distribution_worker(ids, promo_id, api_key, stop_event):
    def report(message):
        print(message)
        logging.info(message)
        ui_queue.put(message)

    granted = 0
    failed = 0
    try:
        report(f"Granting {promo_id} to:")
        for steam_id in ids:
            if stop_event.is_set():
                break
            outcome = grant_item(steam_id, promo_id, api_key)
            if outcome == "[SUCCESS!]":
                granted += 1
            else:
                failed += 1
            report(f"  {steam_id} {outcome}")
            # pace ourselves so we don't hammer the API back-to-back; skip
            # the pause if the user already asked to stop
            if not stop_event.is_set():
                time.sleep(REQUEST_DELAY)
        report("--------------------------")
        if stop_event.is_set():
            report(f"Stopped by user after {granted + failed} of {len(ids)}")
        else:
            report("Finished file processing")
        report(f"Summary: {granted} granted, {failed} failed")
    except Exception as exc:  # last-resort guard: the GUI must never hang
        report(f"ERROR: unexpected error ({type(exc).__name__}: {exc})")
        logging.exception("Distribution worker crashed")
    finally:
        ui_queue.put(None)  # sentinel: always delivered, even if the worker crashed

# --- GUI ----------------------------------------------------------------

def update_grant_state():
    can_run = (
        bool(apitoken.get().strip())
        and bool(promoid.get().strip())
        and fileloaded
        and not running
    )
    loadbutton.config(state=NORMAL if not running else DISABLED)
    runbutton.config(state=NORMAL if can_run else DISABLED)
    stopbutton.config(state=NORMAL if running else DISABLED)


def on_entry_edit(_event):
    if not running:
        update_grant_state()


def reject_file(message):
    """Report a failed load and drop the previously loaded file state.

    Without this, a bad second file would silently keep the first file's
    IDs loaded, and "Grant" would run against the stale list.
    """
    global fileloaded, steam_ids
    print(message)
    logging.info(message)
    fileloaded = False
    steam_ids = []
    filelabel.config(text="No file loaded.", foreground="grey")
    statuslabel.config(text=message)
    update_grant_state()


def load_file():
    global fileloaded, steam_ids
    path = askopenfilename(
        filetypes=(("Text files", "*.txt"), ("All files", "*")),
        title="Choose a list of SteamIDs",
    )
    if not path:
        return

    try:
        ids, invalid, duplicates = parse_steam_ids(path)
    except (OSError, UnicodeDecodeError) as exc:
        reject_file(f"Invalid file: {exc}")
        return

    if not ids:
        reject_file("No valid SteamID64s found in the file")
        return

    steam_ids = ids
    print(f"Loaded file: {path}")
    print(f"Found {len(ids)} valid SteamID64(s)")
    if invalid:
        print(f"{invalid} invalid line(s) skipped (expected 17 digits)")
        logging.info(f"{invalid} invalid line(s) skipped (expected 17 digits)")
    if duplicates:
        print(f"{duplicates} duplicate SteamID64(s) skipped")
        logging.info(f"{duplicates} duplicate SteamID64(s) skipped")
    logging.info(f"Loaded file: {path}")
    logging.info(f"Found {len(ids)} valid SteamID64(s)")

    fileloaded = True
    filelabel.config(text=path)
    statuslabel.config(text=f"Ready: {len(ids)} SteamID64(s) loaded")
    update_grant_state()


def start_distribution():
    global running, worker
    running = True
    statuslabel.config(text="Starting...")
    update_grant_state()
    worker = threading.Thread(
        target=distribution_worker,
        args=(steam_ids, promoid.get().strip(), apitoken.get().strip(), stop_event),
        daemon=True,
    )
    worker.start()


def request_stop():
    stop_event.set()


def reset_form():
    global fileloaded
    fileloaded = False
    # Intentionally keep the API key until the program is closed, so
    # consecutive runs don't require re-entering it; the PromoID is cleared
    # after every run.
    promoid.delete(0, END)
    filelabel.config(text="No file loaded.", foreground="grey")
    # Intentionally leave statuslabel as-is: after a finished distribution it
    # holds the final summary line, which should stay visible to the user.
    update_grant_state()


def on_close():
    """Graceful shutdown: if a distribution is running, confirm with the user,
    stop the worker and wait for it to finish before destroying the window."""
    if running:
        if not messagebox.askyesno(
            "grantovik", "Distribution is still running. Close anyway?"
        ):
            return
        stop_event.set()
        # Give the in-flight request time to finish (REQUEST_TIMEOUT is the
        # worst case) while keeping the window responsive.
        deadline = time.time() + REQUEST_TIMEOUT + 5
        while running and time.time() < deadline:
            root.update()
            time.sleep(0.05)
    root.destroy()


def finish_distribution():
    global running
    running = False
    stop_event.clear()
    reset_form()


def poll_queue():
    finished = False
    processed = 0
    try:
        while processed < MAX_MESSAGES_PER_POLL:
            message = ui_queue.get_nowait()
            processed += 1
            if message is None:
                finished = True
                break
            statuslabel.config(text=message)
    except queue.Empty:
        pass
    if finished:
        finish_distribution()
    root.after(100, poll_queue)


def show_about():
    global about_window
    if about_window is not None and about_window.winfo_exists():
        about_window.lift()
        about_window.focus()
        return

    about_window = Toplevel(root)
    about_window.title("About grantovik")
    about_window.geometry("400x250")
    Label(about_window, text=f"grantovik v.{VERSION}", foreground="grey", font=10).pack(
        padx=6, pady=2, side=TOP
    )
    Label(
        about_window,
        text=(
            "This tool is designed to distribute promotional TF2 items. "
            "It parses SteamID64s (17 digits, one per line) from a file and "
            "grants a promo item to each of them. Progress is printed to the "
            "terminal and logged to log.txt."
        ),
        wraplength=360,
        font=10,
    ).pack(padx=6, pady=2, side=TOP)
    Label(
        about_window,
        text=(
            "The software is licensed under the Apache License 2.0. "
            "A major part of the original code was generously provided by "
            "Benjamin Schaaf."
        ),
        wraplength=360,
        font=10,
    ).pack(padx=6, pady=6, side=TOP)


def main():
    global root, apitoken, promoid, loadbutton, runbutton, stopbutton, filelabel, statuslabel

    root = Tk()
    root.title(f"grantovik {VERSION}")
    root.geometry("350x420")

    # Form fields
    Label(root, text="Steam API key:", font=14).pack(padx=6, pady=2)
    apitoken = Entry(root, width=37, show="*")
    apitoken.bind("<KeyRelease>", on_entry_edit)
    apitoken.pack(padx=6, pady=2)
    apitoken.focus_set()

    Label(root, text="Promo ID:", font=14).pack(padx=6, pady=2)
    promoid = Entry(root, width=37)
    promoid.bind("<KeyRelease>", on_entry_edit)
    promoid.pack(padx=6, pady=2)

    # Buttons
    loadbutton = Button(root, text="Load file", width=14, command=load_file)
    loadbutton.pack(side=TOP, padx=6, pady=2)
    runbutton = Button(root, text="Grant", width=14, state=DISABLED, command=start_distribution)
    runbutton.pack(side=TOP, padx=6, pady=2)
    stopbutton = Button(root, text="Stop", width=8, state=DISABLED, command=request_stop)
    stopbutton.pack(side=TOP, padx=6, pady=2)

    # Status / file info
    statuslabel = Label(root, text="Ready", foreground="grey", font=10)
    statuslabel.pack(side=BOTTOM, padx=6, pady=4)
    filelabel = Label(root, text="No file loaded.", wraplength=300, foreground="grey", font=12)
    filelabel.pack(side=BOTTOM, padx=6, pady=2)
    Label(root, text="F1 — About", foreground="grey", font=8).pack(side=BOTTOM, padx=6, pady=2)

    root.bind("<F1>", lambda _event: show_about())
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.after(100, poll_queue)
    root.mainloop()


if __name__ == "__main__":
    main()
