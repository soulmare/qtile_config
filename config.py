# Copyright (c) 2010 Aldo Cortesiscreen:
# Copyright (c) 2010, 2014 dequis
# Copyright (c) 2012 Randall Ma
# Copyright (c) 2012-2014 Tycho Andersen
# Copyright (c) 2012 Craig Barnes
# Copyright (c) 2013 horsik
# Copyright (c) 2013 Tao Sauvage
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import socket
import subprocess
import re
from subprocess import check_output, call
from libqtile.config import Key, Screen, Group, Drag, Click, Match
from libqtile.command import lazy
from libqtile import layout, bar, widget, hook
from libqtile.dgroups import simple_key_binder

from typing import List

mod = "mod4"
alt = "mod1"
terminal = "gnome-terminal --hide-menubar"
browser = "chromium-browser --profile-directory=Default"
browser_wm_class = "chromium-browser"
file_manager = "nautilus"
home = os.path.expanduser('~')
# Switch selected group when moving window to another group
switch_group_when_moving_window = True
# Switch focused screen when moving window to another screen
switch_screen_when_moving_window = True

### COLORS ###

color_hl = "#C3C300"
#color_hl = "#44DD44"
#color_hl = "#DD4444"
colors = [
         ["#707070", "#303030"], # panel background
         ["#000000", "#000000"], # background for current screen tab
         ["#AAAAAA", "#EEEEEE"], # foreground for group names (inactive/active)
         ["#333333", "#333333"], # group on this screen when unfocused
         ["#AA2A2A", "#AA2A2A"], # group on this screen when focused
         ["#4A4A4A", "#4A4A4A"], # group on other screen when unfocused
         ["#4A4A4A", "#4A4A4A"], # group on other screen when focused
         ["#707070", "#303030"], # background color for layout widget
         [color_hl, color_hl], # foreground color for layout widget
         ["#000000", "#000000"], # background color for clock widget
         ["#CCCCCC", "#CCCCCC"], # foreground color for clock widget
         ["#CCCCCC", "#CCCCCC"], # foreground color for network widget
         ["#FF0000", "#FF0000"], # background color for updates widget (has updates)

         #[color_hl, "#FFFFFF"], # foreground color for prompt widget (normal/selected)
         #["#252525", "#AA2A2A"], # background color for prompt widget (normal/selected)

         ["#CCCCCC", color_hl], # foreground color for prompt widget (normal/selected)
         ["#252525", "#AA2A2A"], # background color for prompt widget (normal/selected)

         ["#303030", "#303030"], # separator color
         [color_hl, color_hl], # foreground color for keyboardLayout widget
         ["#444444", "#444444"], # background color for systray widget
]
flat_theme = {
          "bg_dark": ["#606060", "#000000"],
         "bg_light": ["#707070", "#303030"],
         "font_color": ["#ffffff", "#cacaca"],
         # groupbox
         "gb_selected": ["#7BA1BA", "#215578"],
         "gb_urgent": ["#ff0000", "#820202"]
}
theme = flat_theme
#bars_background = ["#101010", "#202020"]

layout_theme = {"border_width": 2,
            "margin": 0,
            "border_focus": "DD0000",
            "border_normal": "1D2330"
           }


##### WINDOW UTIL FUNCTIONS #####

@lazy.function
def window_to_prev_group(qtile):
    if qtile.currentWindow is not None:
        i = qtile.groups.index(qtile.currentGroup)
        target_group = qtile.groups[i - 1]
        qtile.currentWindow.togroup(target_group.name)
        if switch_group_when_moving_window: 
            qtile.currentScreen.setGroup(target_group)



@lazy.function
def window_to_next_group(qtile):
    if qtile.currentWindow is not None:
        i = qtile.groups.index(qtile.currentGroup)
        target_group = qtile.groups[i + 1]
        qtile.currentWindow.togroup(target_group.name)
        if switch_group_when_moving_window: 
            qtile.currentScreen.setGroup(target_group)


def window_to_prev_screen():
    @lazy.function
    def __inner(qtile):
        if qtile.currentWindow is not None:
            index = qtile.screens.index(qtile.currentScreen)
            if index > 0:
                index_target_screen = index - 1
            else:
                index_target_screen = len(qtile.screens) - 1
            qtile.currentWindow.togroup(qtile.screens[index_target_screen].group.name)
            if switch_screen_when_moving_window: 
                qtile.cmd_to_screen(index_target_screen)

    return __inner


def window_to_next_screen():
    @lazy.function
    def __inner(qtile):
        if qtile.currentWindow is not None:
            index = qtile.screens.index(qtile.currentScreen)
            if index < len(qtile.screens) - 1:
                index_target_screen = index + 1
            else:
                index_target_screen = 0
            qtile.currentWindow.togroup(qtile.screens[index_target_screen].group.name)
            if switch_screen_when_moving_window: 
                qtile.cmd_to_screen(index_target_screen)

    return __inner


def to_urgent(qtile):
    cg = qtile.currentGroup
    for group in qtile.groupMap.values():
        if group == cg:
            continue
        if len([w for w in group.windows if w.urgent]) > 0:
            qtile.currentScreen.setGroup(group)
            return


class swap_group(object):
    def __init__(self, group):
        self.group = group
        self.last_group = None

    def group_by_name(self, groups, name):
        for group in groups:
            if group.name == name:
                return group

    def __call__(self, qtile):
        group = self.group_by_name(qtile.groups, self.group)
        cg = qtile.currentGroup
        if cg != group:
            qtile.currentScreen.setGroup(group)
            self.last_group = cg
        elif self.last_group:
            qtile.currentScreen.setGroup(self.last_group)


'''
  Find application if it is already launched and focus it on the current screen.
  If multiple windows are found - prefer focusing those belonging to the specified group.
  If not found, launch new instance. If group is given, first go to that group
  and then launch app.

  Original source: https://github.com/qtile/qtile-examples/blob/master/mort65/config.py
  Modified by Soulmare:
    * Compatibility with Ubuntu (different location of ps util)
    * Go to group
    * Prefer window if group specified
'''
def find_or_run(app, classes=(), group="", processes=()):
    if not processes:
        processes = [regex(app.split('/')[-1])]
    if not classes:
        # If no class specified, try to use app name as class
        classes = (app[0], ) if isinstance(app, list) else (app, )

    def __inner(qtile):
        window_found = None
        for window in qtile.windowMap.values():
            for c in classes:
                if window.group and window.match(wmclass=c):
                    window_found = window
            if group and window_found and group == window_found.group.name:
                # If window was found on it's preferred group, stop search.
                # Otherwise, continue search to the end.
                # Doing so, we can select which window to focus
                # if multiple windows were matched.
                break
        if window_found:
            qtile.currentScreen.setGroup(window_found.group)
            window_found.group.focus(window_found, False)
            return

        if group:
            if os.path.isfile('/usr/bin/ps'):
                ps = '/usr/bin/ps'
            elif os.path.isfile('/bin/ps'):
                ps = '/bin/ps'
            else:
                # ps not found. maybe, should be better to raise an exception here..
                return
            lines = subprocess.check_output([ps, "axw"]).decode("utf-8").splitlines()
            ls = [line.split()[4:] for line in lines][1:]
            ps = [' '.join(l) for l in ls]
            for p in ps:
                for process in processes:
                    if re.match(process, p):
                        qtile.groupMap[group].cmd_toscreen()
                        return
            for check_group in qtile.groups:
                if check_group.name == group:
                    qtile.currentScreen.setGroup(check_group)
        subprocess.Popen(app.split())

    return __inner


def group_to_screen_by_index(index, screen_index=None):
    def __inner(qtile):
        if index >= 0 and index < len(qtile.groups):
            qtile.groups[index].cmd_toscreen(screen_index)

    return __inner


def window_to_group_by_index(index, screen_index=None):
    def __inner(qtile):
        if index >= 0 and index < len(qtile.groups):
            if qtile.currentWindow is not None:
                qtile.currentWindow.togroup(qtile.groups[index].name)
                if switch_group_when_moving_window: 
                    #qtile.currentScreen.setGroup(qtile.groups[index])
                    qtile.groups[index].cmd_toscreen(screen_index)
                    current_screen_index = qtile.screens.index(qtile.currentScreen)
                    if switch_screen_when_moving_window and screen_index and current_screen_index != screen_index:
                        qtile.cmd_to_screen(screen_index)

    return __inner


#### OTHER FUNCTIONS ####

def my_log(s):
    with open('/home/alx/qtile2.log', 'a') as file:
        file.write(s)
        file.write("\n")


def is_running(process):
    s = subprocess.Popen(["ps", "axuw"], stdout=subprocess.PIPE)
    for x in s.stdout:
        if re.search(process, x.decode("utf-8")):
            return True
    return False


def execute_once(process):
    if not is_running(process):
        return subprocess.Popen(process.split())


def regex(name):
    return r'.*(^|\s|\t|\/)' + name + r'(\s|\t|$).*'


#### MAIN ####

# Init monitors
def xrandr_set_screens():
    xrandr_state = check_output(['xrandr'])

    if b'HDMI-3 connected' in xrandr_state:
        xrandr_setting = [
            'xrandr',
            '--output', 'VGA-1','--off',
            '--output', 'LVDS-1','--mode','1366x768','--pos','1920x0','--rotate','normal',
            '--output', 'HDMI-3', '--primary','--mode','1920x1080','--pos','0x0','--rotate','normal',
            '--output', 'HDMI-2','--off',
            '--output', 'HDMI-1','--off',
            '--output', 'DP-3', '--off',
            '--output', 'DP-2', '--off',
            '--output', 'DP-1', '--off',
            ]
    else:
        xrandr_setting = [
            'xrandr',
            '--output', 'VGA-1','--off',
            '--output', 'LVDS-1','--mode','1366x768','--pos','0x0','--rotate','normal',
            '--output', 'HDMI-3','--off',
            '--output', 'HDMI-2','--off',
            '--output', 'HDMI-1','--off',
            '--output', 'DP-3', '--off',
            '--output', 'DP-2', '--off',
            '--output', 'DP-1', '--off',
        ]

    call(xrandr_setting)
 
xrandr_set_screens()

group_names = [
        "1:term",
        "2:www",
        "3:dev",
        "4:msg",
        ]

prompt = "{0}@{1}: ".format(os.environ["USER"], socket.gethostname())
dmenu = 'dmenu_run -i -p ' + prompt + ' -fn "Ubuntu-14" -nb "' + colors[14][0] + '" -nf "' + colors[13][0] + '" -sb "' + colors[14][1] + '" -sf "' + colors[13][1] + '"'
my_log(dmenu)
dmenu_windows = home + '/.config/qtile/dmenu-qtile-windowlist.py'

# Key bindings

keys = [
    # Window controls

    # Kill window
    Key([mod, "shift"], "c", lazy.window.kill()),

    # Switch between windows in current stack pane
    Key([mod], "j", lazy.layout.down()),
    Key([mod], "k", lazy.layout.up()),
    Key([mod], "l", lazy.layout.right()),
    Key([mod], "h", lazy.layout.left()),

    # Switch between monitors
    Key([mod], "Left", lazy.to_screen(0)),
    Key([mod], "Right", lazy.to_screen(1)),

    # Move windows up or down in current stack
    Key([mod, "shift"], "j", lazy.layout.shuffle_down()),
    Key([mod, "shift"], "k", lazy.layout.shuffle_up()),

    # Move through groups
    #Key([alt], "Tab", lazy.screen.nextgroup()),
    #Key([mod, "control"], "Tab", lazy.screen.nextgroup(skip_managed=True)),
    #Key([alt, "shift"], "Tab", lazy.screen.prevgroup(skip_managed=True)),

    Key(
        [mod, "shift"], "l",
        lazy.layout.grow_up(),
        lazy.layout.grow(),
        lazy.layout.decrease_nmaster(),
        ),
    Key(
        [mod, "shift"], "h",
        lazy.layout.grow_down(),
        lazy.layout.shrink(),
        lazy.layout.increase_nmaster(),
        ),
    Key(
        [mod, "shift"], "Left",                 # Move window to workspace to the left
        window_to_prev_group
        ),
    Key(
        [mod, "shift"], "Right",                # Move window to workspace to the right
        window_to_next_group
        ),
    Key(
        [mod, "control"], "Left",                 # Move window to screen to the left
        window_to_prev_screen()
        ),
    Key(
        [mod, "control"], "Right",                # Move window to screen to the right
        window_to_next_screen()
        ),
    Key(
        [mod], "n",
        lazy.layout.normalize()                 # Restore all windows to default size ratios 
        ),
    Key(
        [mod], "m",
        lazy.layout.maximize()                  # Toggle a window between minimum and maximum sizes
        ),
    Key(
        [mod, "shift"], "f",
        lazy.window.toggle_floating()           # Toggle floating
        ),
    Key(
        [mod, "shift"], "space",
        lazy.layout.rotate(),                   # Swap panes of split stack (Stack)
        lazy.layout.flip()                      # Switch which side main pane occupies (XmonadTall)
        ),
 
    # Stack controls

    # Switch window focus to other pane(s) of stack
    Key([mod], "space", lazy.layout.next()),

    # Toggle between split and unsplit sides of stack.
    # Split = all windows displayed
    # Unsplit = 1 window displayed, like Max layout, but still with
    # multiple stack panes
    Key([mod, "shift"], "Return", lazy.layout.toggle_split()),

    # Toggle between different layouts as defined below
    Key([mod], "Tab", lazy.next_layout()),
    Key([mod, "shift"], "Tab", lazy.prev_layout()),

    # Swap groups
    Key([alt], "1", lazy.function(swap_group(group_names[0]))),
    Key([alt], "2", lazy.function(swap_group(group_names[1]))),
    Key([alt], "3", lazy.function(swap_group(group_names[2]))),
    Key([alt], "4", lazy.function(swap_group(group_names[3]))),

    # Switch groups on 2nd monitor
    Key([mod], "F5", lazy.function(group_to_screen_by_index(5))),

    #Key([], "F12", lazy.function(to_urgent)),

    # Keyboard layouts
    Key([mod, "shift"], "e", lazy.spawn("dbus-send --dest=ru.gentoo.KbddService /ru/gentoo/KbddService ru.gentoo.kbdd.set_layout uint32:0")),
    Key([mod, "shift"], "r", lazy.spawn("dbus-send --dest=ru.gentoo.KbddService /ru/gentoo/KbddService ru.gentoo.kbdd.set_layout uint32:1")),
    Key([mod, "shift"], "u", lazy.spawn("dbus-send --dest=ru.gentoo.KbddService /ru/gentoo/KbddService ru.gentoo.kbdd.set_layout uint32:2")),

    # Sound
    Key([], "XF86AudioRaiseVolume", lazy.spawn("amixer sset Master 5%+")),
    Key([mod], "KP_Add", lazy.spawn("amixer sset Master 5%+")),
    Key([], "XF86AudioLowerVolume", lazy.spawn("amixer sset Master 5%-")),
    Key([mod], "KP_Subtract", lazy.spawn("amixer sset Master 5%-")),
    # BUG: Unmute in Ubuntu works not so much good. Workaround: mute master, but unmute other channels also.
    Key([], "XF86AudioMute", lazy.spawn("amixer sset Master toggle"), lazy.spawn("amixer sset Speaker+LO toggle")),
    Key([mod], "KP_Multiply", lazy.spawn("amixer sset Master toggle"), lazy.spawn("amixer sset Speaker+LO toggle")),

    # Launch applications
    Key([mod], "Return", lazy.spawn(terminal)),
    Key([mod], "w", lazy.function(find_or_run(browser, (browser_wm_class,), group=group_names[1]))),
    #Key([mod], "q", lazy.function(find_or_run("chromium-browser --profile-directory=ProfileDev", ("chromium-browser",), group=group_names[2]))),
    Key([mod], "q", lazy.spawn("chromium-browser --profile-directory=ProfileDev")),
    Key([mod], "f", lazy.spawn(file_manager)),
    Key([mod], "v", lazy.function(find_or_run("viber"))),
    Key([mod], "s", lazy.function(find_or_run("skypeforlinux"))),
    Key([mod], "d", lazy.spawn("goldendict")),
    Key([mod], "e", lazy.spawn("gedit")),
    Key([mod], "c", lazy.function(find_or_run("gnome-calculator"))),
    Key([mod], "o", lazy.function(find_or_run("gnome-control-center"))),
    Key([mod], "i", lazy.spawn("libreoffice --writer")),
    Key([mod, "control"], "F1", lazy.spawn("qtile-autostart-dev")),

    # Screenshots
    Key(["shift"], "Print", lazy.spawn("gnome-screenshot -ia")),
    #Key(["shift"], "Print", lazy.spawn("gnome-screenshot -a -f " + home + "/Pictures/screenshot.png --display=:0")),
    Key([], "Print", lazy.spawn("scrot " + home + "/Pictures/screenshot_%Y_%m_%d_%H_%M_%S.png")),
    Key(["control"], "Print", lazy.spawn("scrot -u " + home + "/Pictures/screenshot_%Y_%m_%d_%H_%M_%S.png")),

    Key([mod, "control"], "r", lazy.restart()),
    Key([mod, "control"], "q", lazy.shutdown()),
    #Key([mod], "t", lazy.findwindow()),
    #Key([mod], "r", lazy.spawncmd()),
    Key([mod], "r", lazy.spawn(dmenu)),
    Key([mod], "a", lazy.spawn(dmenu_windows)),
    
    # suspend
    Key([mod, "control"], "z", lazy.spawn("systemctl suspend")),
    # power off
    Key([mod, "control"], "x", lazy.spawn("shutdown -h now")),
]

groups = [
        Group(group_names[0],
            position=1,
            layout='monadtall',
            #layouts=['monadtall', 'max', 'ratiotile', 'treetab'],
            ),
        Group(group_names[1],
            position=2,
            layout='max',
            #layouts=['monadtall', 'max', 'floating'],
            matches=[Match(wm_class=['Chrome', 'Firefox', 'Tor Browser', 'Opera'])]
            ),
        Group(group_names[2],
            position=3,
            layout='monadtall',
            matches=[Match(wm_class=['Apache NetBeans IDE 11.0'])]
            ),
        Group(group_names[3],
            position=4,
            layout='monadtall',
            matches=[Match(wm_class=['ViberPC', 'GoldenDict'])]
            ),
        Group('gimp',
            init=False,
            persist=False,
            layout='gimp',
            matches=[Match(wm_class=['Gimp'])]
            ),
        Group('vbox',
            init=False,
            persist=False,
            layout='max',
            matches=[Match(wm_class=['VirtualBox Manager'])],
            ),
        Group('skype',
            init=False,
            persist=False,
            layout='max',
            matches=[Match(wm_class=['Skype'])],
            ),
]

# auto bind keys to dgroups mod+1 to 9
#dgroups_key_binder = simple_key_binder(mod)

for i in range(0, 10):
    key_name = str(i + 1) if i < 9 else "0"
    fkey_name = "F" + str(i + 1)
    keys.extend([
        # switch to group on current screen
        Key([mod], key_name, lazy.function(group_to_screen_by_index(i))),

        # switch to group on 2nd screen
        Key([mod], fkey_name, lazy.function(group_to_screen_by_index(i, 1))),

        # switch to & move focused window to group on current screen
        #Key([mod, "shift"], i.name, lazy.window.togroup(i.name)),
        Key([mod, "shift"], key_name, lazy.function(window_to_group_by_index(i))),

        # switch to & move focused window to group on 2nd screen
        #Key([mod, "shift"], i.name, lazy.window.togroup(i.name)),
        Key([mod, "shift"], fkey_name, lazy.function(window_to_group_by_index(i, 1))),
    ])

layouts = [
    layout.MonadTall(ratio=0.7, **layout_theme),
    layout.Max(**layout_theme),
    layout.RatioTile(**layout_theme),
    #layout.Tile(ratio=0.50, masterWindows=2),
    layout.TreeTab(
        #font = "Ubuntu",
        #fontsize = 13,
        #sections = ["FIRST", "SECOND"],
        #section_fontsize = 11,
        bg_color = colors[0][1],
        active_bg = colors[4],
        active_fg = colors[2][1],
        inactive_bg = colors[0][0],
        inactive_fg = colors[2][1],
        padding_y = 3,
        #section_top = 10,
        panel_width = 320,
        **layout_theme
        ),
    #layout.MonadWide(**layout_theme),
    #layout.Tile(**layout_theme),
    #layout.Matrix(**layout_theme),
    #layout.Stack(num_stacks=2, **layout_theme),
    layout.Slice(side="left", width=200, name="gimp", role="gimp-toolbox",
                fallback=layout.Slice(side="right", width=250, role="gimp-dock",
                fallback=layout.Stack(num_stacks=1, border_args={"border_width": 2}))),
    layout.Floating(**layout_theme)
]

widget_defaults = dict(
    font='Ubuntu',
    fontsize=13,
    foreground=colors[11],
)
widgets_default_update_interval = 0.7
extension_defaults = widget_defaults.copy()

group_box_options = dict(font="Ubuntu",
                    fontsize = 15,
                    margin_y = 0,
                    margin_x = 0,
                    padding_y = 4,
                    padding_x = 10,
                    borderwidth = 1,
                    active = colors[2][1],
                    inactive = colors[2][0],
                    rounded = False,
                    highlight_method = "block",
                    this_current_screen_border = colors[4],
                    this_screen_border = colors[3],
                    other_current_screen_border = colors[6],
                    other_screen_border = colors[5],
                    foreground = colors[2][1],
                    background = colors[0],
                    disable_drag=True,
)

widget_kb_layout_options = dict(
                        font="Ubuntu Bold",
                        fontsize=16,
                        foreground = colors[16],
                        padding = 6,
                        update_interval = widgets_default_update_interval,
                        configured_keyboards=['us', 'ru', 'ua']
                        )
widget_kbdd_options = dict(
                        font="Ubuntu Bold",
                        fontsize=18,
                        foreground = colors[16],
                        padding = 6,
                        update_interval = widgets_default_update_interval,
                        configured_keyboards=['us', 'ru', 'ua']
                        )
sep_options = dict(
                        linewidth = 1,
                        padding = 10,
                        foreground = colors[15],
                        background = colors[0]
)
sep_inv_options = dict(
                        padding = 5,
                        linewidth = 0,
)
wn_prefix_options = dict(
                        font="Ubuntu Mono",
                        text="::",
                        foreground = "DDDDDD",
                        padding = 0,
                        fontsize=14,
)
wn_options = dict(
                        font="Ubuntu Italic",
                        foreground = "DDDDDD",
                        fontsize=14,
                        #padding=5,
) 
cur_scr_options = dict(
        active_text = "▶",
        inactive_text = "▶",
        #active_text = "◼",
        #inactive_text = "◼",
        active_color = "FF0000",
        inactive_color = "AAAAAA",
        padding=4,
)
cur_scr2_options = dict(
        font="Ubuntu Mono",
        active_text = "::",
        inactive_text = "::",
        active_color = "DDDDDD",
        inactive_color = "AAAAAA",
        padding = 0,
        fontsize=14,
)
 
screens = [
    Screen(
        top=bar.Bar(
            [
                #widget.CurrentScreen(**cur_scr_options),
                #widget.TextBox(text=u"◥", fontsize=30, padding=-1,
                #        font="Arial",
                #        foreground=theme["bg_dark"]),

                widget.GroupBox(**group_box_options),
                widget.Prompt(
                        prompt=prompt,
                        font="Ubuntu Mono Bold",
                        fontsize=16,
                        padding=12,
                        foreground = colors[13],
                        background = colors[14]
                ),
                widget.Sep(**sep_options),
                widget.Sep(**sep_inv_options),
                widget.CurrentLayout(
                        foreground = colors[8],
                        background = colors[7],
                        padding = 5
                        ),

                widget.Sep(**sep_inv_options),
                #widget.CurrentScreen(**cur_scr2_options),
                widget.TextBox(**wn_prefix_options),
                widget.WindowName(**wn_options),
                widget.Notify(
                    background = colors[16],
                    background_urgent = "FF0000",
                    foreground = "000000",
                    ),
#                widget.Net(
#                        interface = "eno1",
#                        foreground = colors[11],
#                        update_interval = 2,
#                        padding = 5
#                        ),
                #widget.TaskList(),
                #widget.WindowTabs(),
                widget.Sep(**sep_inv_options),
                widget.TextBox(
                    text="CPU:",
                    padding=1,
                    **widget_defaults
                    ),
                widget.ThermalSensor(
                    foreground=colors[11],
                    padding=1,
                    #show_tag=True,
                    ),
                widget.Sep(**sep_inv_options),
                widget.CPUGraph(
                    frequency=3,
                    border_color="333333",
                    border_width=1,
                    fill_color="333333",
                    graph_color=colors[7][0],
                    ),
#                widget.Memory(
#                    foreground=colors[11],
#                    update_interval=5,
#                    fmt='RAM: {MemUsed}/{MemTotal}M',
#                    ),
               widget.Sep(**sep_inv_options),
               widget.DF(
                        foreground=colors[11],
                        visible_on_warn=False,
                        partition='/',
                        format='{p}:{uf}{m}',
                        padding=3,
                        ),
                widget.DF(
                        foreground=colors[11],
                        visible_on_warn=False,
                        partition='/home',
                        format='{p}:{uf}{m}',
                        padding=3,
                        ),
                #widget.Sep(**sep_options),
                widget.Sep(**sep_inv_options),
                widget.Systray(
                        background=colors[17],
                        #padding=10,
                        ),
#                widget.CheckUpdates(
#                        colour_have_updates=colors[12],
#                        distro='Ubuntu',
#                        execute='update-manager'
#                        ),
                widget.TextBox(
                        font="Ubuntu Bold",
                        text=" ♫",
                        #text="🔉",
                        #text="🔊",
                        padding = 0,
                        fontsize=14,
                        foreground=colors[11],
                        background=colors[17],
                        ),
                widget.Volume(
                        update_interval=widgets_default_update_interval,
                        foreground=colors[11],
                        background=colors[17],
                        ),
                #widget.KeyboardLayout(**widget_kb_layout_options),
                widget.KeyboardKbdd(
                        background=colors[17],
                        **widget_kbdd_options
                        ),
                widget.CapsNumLockIndicator(
                        update_interval=widgets_default_update_interval,
                        foreground=colors[16],
                        background=colors[17],
                        padding=0,
                        ),
                widget.Clock(
                        update_interval=2,
                        font="Ubuntu",
                        padding=5,
                        fontsize=16,
                        foreground=colors[10],
                        background=colors[17],
                        format='%d %a %H:%M',
                        ),
            ],
            24,
            background = colors[0]

        ),
    ),
    Screen(
        top=bar.Bar(
            [
                #widget.CurrentScreen(**cur_scr_options),
                widget.GroupBox(**group_box_options),
                widget.Sep(**sep_inv_options),
                widget.CurrentLayout(
                        foreground = colors[8],
                        background = colors[7],
                        padding = 5
                        ),
                widget.TextBox(**wn_prefix_options),
                #widget.CurrentScreen(**cur_scr2_options),
                widget.WindowName(**wn_options),
                #widget.KeyboardLayout(**widget_kb_layout_options),
                widget.KeyboardKbdd(**widget_kbdd_options),
            ],
            24,
            background = colors[0]
        ),
    ),
]

# Drag floating layouts.
mouse = [
    Drag([mod], "Button1", lazy.window.set_position_floating(),
         start=lazy.window.get_position()),
    Drag([mod], "Button3", lazy.window.set_size_floating(),
         start=lazy.window.get_size()),
    Click([mod], "Button2", lazy.window.bring_to_front())
]

#dgroups_key_binder = None
dgroups_app_rules: List = []
main = None
follow_mouse_focus = False
bring_front_click = False
cursor_warp = False
floating_layout = layout.Floating(float_rules=[
    {'wmclass': 'confirm'},
    {'wmclass': 'dialog'},
    {'wmclass': 'download'},
    {'wmclass': 'error'},
    {'wmclass': 'file_progress'},
    {'wmclass': 'notification'},
    {'wmclass': 'splash'},
    {'wmclass': 'toolbar'},
    {'wmclass': 'confirmreset'},  # gitk
    {'wmclass': 'makebranch'},  # gitk
    {'wmclass': 'maketag'},  # gitk
    {'wname': 'branchdialog'},  # gitk
    {'wname': 'pinentry'},  # GPG key password entry
    {'wmclass': 'ssh-askpass'},  # ssh-askpass
    {'wmclass': 'gnome-screenshot'},
    {'wmclass': 'gnome-calculator'},
    {'wmclass': 'eog'},
    {'wmclass': 'gnome-control-center'},
    {'wmclass': 'Meld'},
])

auto_fullscreen = True
focus_on_window_activation = "smart"

# XXX: Gasp! We're lying here. In fact, nobody really uses or cares about this
# string besides java UI toolkits; you can see several discussions on the
# mailing lists, github issues, and other WM documentation that suggest setting
# this string if your java app doesn't work correctly. We may as well just lie
# and say that we're a working one by default.
#
# We choose LG3D to maximize irony: it is a 3D non-reparenting WM written in
# java that happens to be on java's whitelist.
wmname = "LG3D"

# Handle multiple monitors
@hook.subscribe.screen_change
def restart_on_screen_change(qtile, ev):
    qtile.log.debug('screen change event: %s' % ev)
    qtile.xrandr_set_screens()
    qtile.cmd_restart()


'''
@hook.subscribe.client_new
def on_client_new(window):
    wm_type = window.window.get_wm_type()
    name = window.window.get_name() 
    dialog = wm_type == 'dialog'
    transient = window.window.get_wm_transient_for()
    my_log("["+name+"]")
    if dialog or transient:
        if not name.endswith("GoldenDict"):
            window.floating = True
            my_log("set floating")
        else:
            my_log("unset floating")
            #window.floating = False
            window.toggle_floating()
            window.togroup("4:msg")
            my_log("not set floating")
'''

@hook.subscribe.startup
def startup():
    """
    Run every time qtile is started
    """
    #lazy.group["4:msg"].toscreen()
    #qtile.screens[1].setGroup("4:msg")
    #xrandr_set_screens()

    #qtile.screens[1].setGroup("4:msg")


@hook.subscribe.startup_once
def startup_once():
    """
    Run after qtile is started very first time
    """

    home = os.path.expanduser("~")

    # Autostart shell script
    subprocess.call([home + "/.config/qtile/autostart.sh"])

    # Set up keyboard layouts
    os.system("setxkbmap -layout 'us, ru, ua'")
    #os.system("setxkbmap -option 'grp:alt_shift_toggle'")
    os.system("setxkbmap -option 'grp:shift_caps_toggle'")

    # Launch kbdd daemon - needed for keyboard layout indicator widget
    execute_once("kbdd")
    execute_once("nm-applet")

    # Set up wallpaper
    wallpaper_path = '~/Pictures/Wallpapers/backgrounds/MistyMorning.jpg'
    os.system('feh --bg-scale ' + wallpaper_path)

    # Fix antialiasing in Netbeans
    os.environ["_JAVA_OPTIONS"] = '-Dswing.aatext=TRUE -Dawt.useSystemAAFontSettings=on'

