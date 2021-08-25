import os, sys
from config import appname, config
from monitor import monitor
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
import tkinter as tk
from tkinter import ttk
from ttkHyperlinkLabel import HyperlinkLabel
import myNotebook as nb
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import logging
plugin_name = os.path.basename(os.path.dirname(__file__))
logger = logging.getLogger(f'{appname}.{plugin_name}')

this = sys.modules[__name__]
VERSION = 0.8

status: Optional[tk.Label]
observer = None
this.cmdr = "default-cmdr"
this.system = "unknown-system"
this.body = "unknown-body"
this.station = None

class ImgHandler(PatternMatchingEventHandler):
    def __init__(self):
        PatternMatchingEventHandler.__init__(self, patterns=['*.png', '*.jpg', '.bmp'], ignore_directories=True, case_sensitive=False)

    def on_created(self, event):
        if event.src_path.lower().endswith('.png'):
          logger.debug("New image detected {}".format(event.src_path))
          date = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
          number = 1
          while True:
            newname = "{}/{} {} ({}) {}.png".format(this.out_loc.get(), this.system, this.station if station else this.body, this.cmdr, f'{number:05}')
            if os.path.isfile(newname):
              number += 1
            else:
              break
          logger.info("{} {} to {}".format("Moving" if this.del_orig.get() == "1" else "Copying", event.src_path, newname))
          try:
            if this.del_orig.get() == "1":
              os.rename(event.src_path, newname)
            else:
              from shutil import copyfile
              copyfile(event.src_path, newname)
          except Exception as e:
            logger.error(e)

def check_dir_exists(directory):
    return os.path.isdir(directory)

def check_all_dirs_exist():
    default = message = "Error:\n"
    for directory in [this.in_loc.get(), this.out_loc.get()]:
      if not check_dir_exists(directory):
        message += "Directory '{}' does not exist!\n".format(directory)
	# Keep a multi-line message, but only log one error per directory checked
        logger.error(message.splitlines()[-1])

    if message != default:
      update_status(message)

    return message == ""

def plugin_start3(plugin_dir: str) -> str:
   logger.info(f"{appname}.{plugin_name} loading!")
   this.in_loc = tk.StringVar(value=config.get_str("AS_INPUT"))
   if this.in_loc is None or this.in_loc.get() == "":
     this.in_loc = tk.StringVar(value='%userprofile%\\Videos\\Elite Dangerous')
     config.set("AS_INPUT", this.in_loc.get())

   this.out_loc = tk.StringVar(value=config.get_str("AS_OUTPUT"))
   if this.out_loc is None or this.out_loc.get() == "":
     this.out_loc = tk.StringVar(value='%userprofile%\\Pictures\\Frontier Developments\\Elite Dangerous')
     config.set("AS_OUTPUT", this.out_loc.get())

   this.del_orig = tk.StringVar(value=config.get_str("AS_DELORIG"))

   return "Any Screenshot"

def plugin_prefs(parent, cmdr, is_beta):
    frame = nb.Frame(parent)
    frame.columnconfigure(3, weight=1)

    HyperlinkLabel(frame, text=plugin_name, background=nb.Label().cget('background'), url='https://github.com/chennin/EDMC-Any-Screenshot', \
      underline=True).grid(row=0, columnspan=2, padx=10, sticky=tk.W)
    nb.Label(frame, text = 'Version {}'.format(VERSION)).grid(row=0, column=2, padx=10, sticky=tk.E)

    input_label = nb.Label(frame, text="Screenshot Directory")
    input_label.grid(padx=10, row=2, column=0, sticky=tk.W)

    input_entry = nb.Entry(frame, textvariable=this.in_loc)
    input_entry.grid(padx=10, row=2, column=1, columnspan=2, ipadx=60, sticky=tk.W)

    output_label = nb.Label(frame, text="Output Directory")
    output_label.grid(padx=10, row=3, column=0, sticky=tk.W)

    output_entry = nb.Entry(frame, textvariable=this.out_loc)
    output_entry.grid(padx=10, row=3, column=1, columnspan=2, ipadx=60, sticky=tk.W)

    nb.Checkbutton(frame, text="Delete Original File", variable=this.del_orig).grid(padx=10, row=5, column=0, sticky=tk.W)

    return frame

def start_observer():
    global observer
    logger.info("Starting image observer")
    event_handler = ImgHandler()
    observer = Observer()
    observer.schedule(event_handler, this.in_loc.get(), recursive=False)
    observer.start()
    update_status("Started")

def stop_observer():
    global observer
    if observer is not None and observer.is_alive():
      logger.info("Stopping image observer")
      observer.stop()
      observer.join()
    update_status("Stopped")

def prefs_changed(cmdr, is_beta):
    logger.debug("Detected prefs change")
    config.set("AS_INPUT", this.in_loc.get())
    config.set("AS_OUTPUT", this.out_loc.get())
    config.set("AS_DELORIG", this.del_orig.get())
    stop_observer()
    if check_all_dirs_exist() and monitor.game_running():
      start_observer()

def plugin_app(parent: tk.Frame) -> Tuple[tk.Label, tk.Label]:
    global status
    label = tk.Label(parent, text="Any Screenshot")
    status = tk.Label(parent, text="")
    update_status("Loaded")

    return (label, status)

def update_status(message) -> None:
    global status
    logger.debug("Updating status text to: {}".format(message))
    if not config.shutting_down:
      status["text"] = message

def plugin_stop() -> None:
    stop_observer()

def journal_entry( cmdr: str, is_beta: bool, system: str, station: str, entry: Dict[str, Any], state: Dict[str, Any]) -> None:
    if entry['event'].lower() == 'shutdown' or monitor.game_running == False:
      stop_observer()
    elif entry['event'].lower() == 'startup':
      start_observer()
    # Keep track of updates as they come in, as this plugin is not directly
    # concerned with Screenshot events, but needs the info for renaming
    this.cmdr = cmdr
    this.system = system
    this.station = station
    if state["Body"]:
      this.body = state["Body"]
