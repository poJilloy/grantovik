# grantovik
A GUI wrapper for a TF2 promotional [distribution script](https://gist.github.com/BenjaminSchaaf/e65c9dbccf32d49c23d97d94b61b95da), originally made by Benjamin Schaaf.

## Installation

1. Install requests module:
   ```bash
   pip install requests
   ```
   
2. Install tkinter module via package manager:

   Ubuntu / Debian:
   ```bash
   sudo apt install python3-tk
   ```

   Fedora:
   ```bash
   sudo dnf install python3-tkinter
   ```

   Arch:
   ```bash
   sudo pacman -S tk
   ```

   openSUSE:
   ```bash
   sudo zypper install python3-tk
   ```

## Running

Download the [latest release](https://github.com/poJilloy/grantovik/releases), put it anywhere on your disk. Open up a terminal in the directory you have this program in, and use `python3 grantovik.py` to run the program.

## Usage

On startup, you'll see a window prompting your Steam API key and a promo ID that represents the item you are giving away.

The program works with a file formatted in the following way: 1 steamID64 per line.
steamID64 is a 17-symbol digit string.

This is an example of how your input file can look like:

`file.txt`:
```
76561198030620256
76561197960265749
```

Invalid lines (anything that is not a 17-digit SteamID64) and empty lines are skipped, and repeated SteamIDs are de-duplicated automatically, so you don't have to clean your file beforehand.

Fill in your API key and a Promo ID, press the "Load file" button and select the file you need. The path to the file will appear at the bottom of the window, and the number of detected SteamIDs will be shown in the status line.

Once the file was loaded, you'll be able to press the "Grant" button. The window stays responsive while the distribution runs: press "Stop" any time to abort. The status line shows the current progress, and the full log is also printed to the terminal.

Take a look at the terminal, it will show you the progress of the distribution process:

```
Granting [promo id] to:
  76561198030620256 [SUCCESS!]
  76561197960265749 [FAIL: already granted]
--------------------------
Finished file processing
Summary: 1 granted, 1 failed
```

The final `Summary` line also stays in the window's status bar after the distribution ends, so you don't have to look at the terminal for the result.

After a run, the Promo ID field is cleared, but your Steam API key is kept in the window for the next run (so processing several files one after another doesn't require re-entering it).

Requests are sent at a modest pace (0.2 s between them by default) to avoid hammering the Steam API. If you need to go faster or slower, tune the `REQUEST_DELAY` constant near the top of the file.

If you close the window while a distribution is still running, you'll be asked to confirm; the worker is then stopped and given a moment to finish its in-flight request before the program exits.

If the distribution fails, you'll see `[FAIL (reason)]` instead of the usual success message. Usually it will be either an invalid token or a network problem.

To see the "About" window, press `F1`.

## Logging

The `log.txt` file is created in the directory the program runs from only when there is something to log - a launch without any activity leaves no file behind. New entries are appended to the existing log, so the history of previous runs is preserved.
This file is basically an echo of what you'll see in the terminal, with timestamps.

If you had some of your requests failed, be sure to save your log / SteamIDs that failed into another place and try granting again later.
