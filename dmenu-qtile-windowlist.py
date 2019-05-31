#!/usr/bin/env python3

from libqtile.command import Client
import subprocess
import re

# connect to Qtile
c = Client()

# get info of windows
wins = []
id_map = {}
id = 0
for win in c.windows():
    if win["group"]:
        wins.append(bytes("%i: %s (%s)" % (id, win["name"], win["group"]),
            'utf-8'))
        id_map[id] = {
                'id' : win['id'],
                'group' : win['group']
                }
        id = id +1

# call dmenu
DMENU='dmenu -i -p "window >>>" -fn "Ubuntu-10" -l 20 -nb "#252525" -nf "#CCCCCC" -sb "#AA2A2A" -sf "#C3C300"'
#DMENU="dmenu -i -p >>> -fn 'Ubuntu-10' -l 20 -nb #252525 -nf #CCCCCC -sb #AA2A2A -sf #C3C300"
#dmenu_run -i -p ">>" -fn "Ubuntu-14" -nb "#252525" -nf "#CCCCCC" -sb "#AA2A2A" -sf "#C3C300"
p = subprocess.Popen(DMENU, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
out = p.communicate(b"\n".join(wins))[0]

# get selected window info
id = int(re.match(b"^\d+", out).group())
win = id_map[id]

# focusing selected window
g = c.group[win["group"]]
g.toscreen()
w = g.window[win["id"]]
for i in range(len(g.info()["windows"])):
    insp = w.inspect()
    if insp['attributes']['map_state']:
        break
    g.next_window()
