#! Python 3.4

import logging
import requests
from datetime import datetime
from tkinter import *
from tkinter import ttk
from tkinter.filedialog import askopenfilename


# Logging to file so we can track down failed distributions
logging.basicConfig(filename="log.txt", level=logging.INFO, filemode='w', format='%(message)s')
logging.info("PGrant log file") # Logging everything into info level because formatting is disabled anyway
logging.info(datetime.now())

# Defining core components

GRANT_ITEM_URL = 'https://api.steampowered.com/ITFPromos_440/GrantItem/v0001/'

def grant_medals(idarray, promo_id, api_key):
    steam_ids = idarray 
    
    print("Granting {} to:".format(promo_id))
    logging.info("Granting {} to:".format(promo_id))
    for steam_id in steam_ids:
        print("  {} ".format(steam_id), end='')
        logging.info("  {} ".format(steam_id))
        grant_item(steam_id, promo_id, api_key)
        
    Reset()  
    logging.info("--------------------------")
    print("--------------------------")
    logging.info("Finished file processing")
    print("Finished file processing")
    
def grant_item(steam_id, promo_id, api_key):
    data = {
        'SteamID': steam_id,
        'PromoID': promo_id,
        'Key': api_key,
    }
    response = requests.post(GRANT_ITEM_URL, data = data)
    try:
        json = response.json()
    except ValueError:
        print('[FAIL: request error/not authorized]')
        logging.info('[FAIL: request error/not authorized]')
        return

    if 'result' not in json:
        print('[FAIL: response error/invalid promo id]')
        logging.info('[FAIL: response error/invalid promo id]')
        return

    result = json['result']
    if int(result['status']) != 1:
        print("[FAIL: {}]".format(result['statusDetail']))
        logging.info("[FAIL: {}]".format(result['statusDetail']))
    else:
        print("[SUCCESS!]")
        logging.info("[SUCCESS!]")


# Defining GUI components

root = Tk()
fileopened = False

def OpenFile():
    name = askopenfilename(filetypes =(("Text File", "*.txt"),("All Files","*.*")),
                           title = "Choose a list of SteamIDs"
                           )
    try:
        with open(name,'r') as UseFile:
            global steamids
            steamids = UseFile.read().splitlines()
            print(name)
            print("Found " + str(len(steamids)) + " potential SteamIDs")
            logging.info("--------------------------")
            logging.info("Loaded file: " + name)            
            logging.info("Found " + str(len(steamids)) + " potential SteamIDs")
            
            global fileopened
            fileopened = True
            BtnCheck(fileopened)
            
            global filelabel
            filelabel['text'] = name
            filelabel['foreground'] = "black"
            
    except:
        print("Invalid file")  
    
    
def About():
    window = Toplevel(root)  
    window.title( "About PGrant")
    window.geometry( "400x250")
    version = Label(window, text ="v. 0.4", foreground="grey", font=(4))
    version.pack(padx=6, pady = 2, side=TOP)
    aboutt = Label(window, text ="This tool is designed to distribute promotional TF2 items, parsing multiple SteamID64s from a file, one per line. Be sure to keep your console output visible so you can keep track of the progress.", wraplength=180, font=(6))
    aboutt.pack(padx=6, pady = 2, side=LEFT)
    aboutp = Label(window, text ="The software  is licensed under the Apache License 2.0. A major part of the original code was generously provided by Benjamin Schaaf.", wraplength=180, font=(6))
    aboutp.pack(padx=6, pady = 6, side=LEFT)

def BtnCheck(event):
    if (len(apitoken.get()) != 0)&(len(promoid.get()) != 0)&fileopened:
        global runbutton
        runbutton['state'] = 'normal'
        runbutton['text'] = 'Grant'
    else:
        runbutton['state'] = 'disabled'        
        runbutton['text'] = 'Grant'        

def Reset():
    global fileopened
    fileopened = False
    BtnCheck(fileopened)
    
    global apitoken
    apitoken.delete(0, END)
    
    global promoid
    promoid.delete(0, END)
    
    global filelabel
    filelabel['text'] = "No file loaded."
    filelabel['foreground'] = "grey"



# Window properties    
    
root.title( "PGrant 0.4")
root.geometry( "350x400")


# Packing GUI elements

apilabel = Label(root, text ="Steam API key:", font=(14))
apilabel.pack(padx=6, pady = 2)
apitoken = Entry(root, width = 37)
apitoken.bind("<KeyRelease>", BtnCheck)
apitoken.pack(padx=6, pady = 2)
apitoken.focus_set()

promolabel = Label(root, text ="Promo ID:",font=(14))
promolabel.pack(padx=6, pady = 2)
promoid = Entry(root, width = 37)
promoid.bind("<KeyRelease>", BtnCheck)
promoid.pack(padx=6, pady = 2)

runbutton = Button(root, text="Grant", width=14, state=DISABLED, command=lambda: grant_medals(steamids, promoid.get(), apitoken.get()))
runbutton.pack(padx=6, pady = 10)

filelabel = Label(root, text ="No file loaded.", wraplength=300, foreground="grey",font=(12))
filelabel.pack(side = BOTTOM, padx=6, pady = 14)


# Menu Bar

menu = Menu(root)
root.config(menu=menu)
menu.add_command(label = 'Load a file', command = OpenFile)
menu.add_command(label = 'About', command = About)

root.mainloop()
