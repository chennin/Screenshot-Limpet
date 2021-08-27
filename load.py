import os, sys
from config import appname, config
from monitor import monitor
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
import tkinter as tk
from ttkHyperlinkLabel import HyperlinkLabel
import myNotebook as nb
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import logging

plugin_name = os.path.basename(os.path.dirname(__file__))
logger = logging.getLogger(f'{appname}.{plugin_name}')

this = sys.modules[__name__]
VERSION = 0.8

this.status: Optional[tk.Label]
this.message = ""
observer = None
this.cmdr = "default-cmdr"
this.system = "unknown-system"
this.body = "unknown-body"
this.station = None

class ImgHandler(PatternMatchingEventHandler):
    def __init__(self):
        PatternMatchingEventHandler.__init__(self, patterns=['*.png', '*.jpg', '.bmp'], ignore_directories=True, case_sensitive=False)

    def on_any_event(self, event):
        logger.debug("FS Event: {}".format(event.event_type))
    def on_closed(self, event):
        if event.src_path.lower().endswith( ('.png', '.jpg') ) :
          logger.debug("New image detected {}".format(event.src_path))
          suffix = event.src_path.lower()[-3:]
          date = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
          number = 1
          while True:
            newname = "{} {} ({}) {}.{}".format(this.system, this.station if station else this.body, this.cmdr, f'{number:05}', suffix)
            keepcharacters = (' ','.','_','+','-','(',')',',','#','\'')
            newname = "".join(c for c in newname if c.isalnum() or c in keepcharacters).rstrip()

            newpath = "{}/{}".format(this.out_loc.get(), newname)
            if os.path.isfile(newpath):
              number += 1
            else:
              break

          logger.info("{} '{}' to '{}'".format("Moving" if this.del_orig.get() == "1" else "Copying", event.src_path, newpath))

          try:
            if this.del_orig.get() == "1":
              os.rename(event.src_path, newpath)
            else:
              from shutil import copyfile
              copyfile(event.src_path, newpath)
            this.message = "Successfully {} screenshot with new name:\n{}".format("moved" if this.del_orig.get() == "1" else "copied", newname)
          except Exception as e:
            this.message = "Error: {}".format(e)
            logger.error(e)
          finally:
            this.status.event_generate('<<AnySSStatus>>', when="tail")

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
      this.message = message
      this.status.event_generate('<<AnySSStatus>>', when="tail")

    return message == default

def plugin_start3(plugin_dir: str) -> str:
   logger.info(f"{appname}.{plugin_name} loading!")
   this.in_loc = tk.StringVar(value=config.get_str("AS_INPUT"))
   if this.in_loc is None or this.in_loc.get() == "":
     this.in_loc = tk.StringVar(value = os.path.expanduser( os.path.expandvars( '%userprofile%\\Videos\\Elite Dangerous' ) ) )
     config.set("AS_INPUT", this.in_loc.get())

   this.out_loc = tk.StringVar(value=config.get_str("AS_OUTPUT"))
   if this.out_loc is None or this.out_loc.get() == "":
     this.out_loc = tk.StringVar(value = os.path.expanduser( os.path.expandvars( '%userprofile%\\Pictures\\Frontier Developments\\Elite Dangerous') ) )
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
    if check_all_dirs_exist() == True and monitor.game_running() == True and ( observer is None or not observer.is_alive() ):
      logger.info("Starting image observer")
      event_handler = ImgHandler()
      observer = Observer()
      observer.schedule(event_handler, this.in_loc.get(), recursive=False)
      observer.start()
      this.message = "Started"
      this.status.event_generate('<<AnySSStatus>>', when="tail")

def stop_observer():
    global observer
    if observer is not None and observer.is_alive():
      logger.info("Stopping image observer")
      observer.stop()
      observer.join()
    this.message = "Stopped"
    this.status.event_generate('<<AnySSStatus>>', when="tail")

def prefs_changed(cmdr, is_beta):
    logger.debug("Detected prefs change")
    this.in_loc = tk.StringVar(value = os.path.expanduser( os.path.expandvars( this.in_loc.get() ) ) )
    this.out_loc = tk.StringVar(value = os.path.expanduser( os.path.expandvars( this.out_loc.get() ) ) )
    config.set("AS_INPUT", this.in_loc.get() )
    config.set("AS_OUTPUT", this.out_loc.get() )
    config.set("AS_DELORIG", this.del_orig.get())
    stop_observer()
    start_observer()

def plugin_app(parent: tk.Frame) -> Tuple[tk.Label, tk.Label]:
    label = tk.Label(parent, text="Any Screenshot")
    this.status = tk.Label(parent, text="")
    this.status.bind_all('<<AnySSStatus>>', update_status)

    return (label, this.status)

def update_status(event=None) -> None:
    logger.debug("Updating status text to: {}".format(this.message))
    if not config.shutting_down:
      this.status["text"] = this.message

def plugin_stop() -> None:
    stop_observer()

def journal_entry( cmdr: str, is_beta: bool, system: str, station: str, entry: Dict[str, Any], state: Dict[str, Any]) -> None:
    if entry['event'].lower() == 'shutdown' or monitor.game_running == False:
      stop_observer()
    elif entry['event'].lower() in [ 'startup', 'loadgame' ]:
      start_observer()
    # Keep track of updates as they come in, as this plugin is not directly
    # concerned with Screenshot events, but needs the info for renaming
    this.cmdr = cmdr
    this.system = system
    this.station = station
    if state["Body"]:
      this.body = state["Body"]
