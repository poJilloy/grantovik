
# grantovik
A GUI wrapper for a TF2 promotional [distribution script](https://gist.github.com/BenjaminSchaaf/e65c9dbccf32d49c23d97d94b61b95da), originally made by Benjamin Schaaf.

## Installation

Install requests module with pip:

`pip install requests`

## Running 

Download the [latest release](https://https://github.com/poJilloy/grantovik/releases), put it anywhere on your disk. Open up a terminal in the directory you have this program in, and use `python3 grant.py` to run the program.

## Usage

On startup, you'll see 2 windows: console and a window prompting your Steam API key and a promo ID that represents the item you are giving away.

The program works with a file formatted in the following way: 1 steamID64 per line.
steamID64 is a 17-symbol digit string.

This is an example of how your input file can look like:

`file.txt`:
```
76561198030620256
76561198030620256
76561198030620256
76561198030620256
76561198030620256
76561198030620256
```

Fill in your API key and a Promo ID, press "Load a file" button and select the file you need. The path to the file will appear at the bottom of the window. 
The console window will show how many SteamIDs it detected in the file.

Once the file was loaded, you'll be able to press the "Grant" button. Once pressed, the window may become non-responsive, this is normal. 

Take a look at the console window, it will show you the progress of the distrubution process.
You'll see something that looks like this:

```
Granting [promo id] to:
76561198030620256 [SUCCESS!]
76561198030620256 [SUCCESS!]
76561198030620256 [SUCCESS!]
76561198030620256 [SUCCESS!]
76561198030620256 [SUCCESS!]
76561198030620256 [SUCCESS!]
--------------------------
Finished file processing
```

If the distribution fails, you'll see `[FAIL (reason)]`  instead of the usual success message. Usually it will be either invalid token or internet connection problems.

## Logging

On every program launch, it will generate/overwrite `log.txt` file, at the same directory the program is running.
This file is basically an echo of what you'll see in the console window.

If you had some of your requests failed, be sure to save your log / SteamIDs that failed into another place and try granting again later.
