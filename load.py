import os, sys
from config import appname, config
from monitor import monitor
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, LoggingEventHandler
from watchdog.observers import Observer
import tkinter as tk
from tkinter import ttk
import myNotebook as nb
from typing import Optional, Tuple, Dict, Any
import logging
plugin_name = os.path.basename(os.path.dirname(__file__))
logger = logging.getLogger(f'{appname}.{plugin_name}')
if not logger.hasHandlers():
    level = logging.INFO
    logger.setLevel(level)
    logger_channel = logging.StreamHandler()
    logger_formatter = logging.Formatter(f'%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d:%(funcName)s: %(message)s')
    logger_formatter.default_time_format = '%Y-%m-%d %H:%M:%S'
    logger_formatter.default_msec_format = '%s.%03d'
    logger_channel.setFormatter(logger_formatter)
    logger.addHandler(logger_channel)

this = sys.modules[__name__]
status: Optional[tk.Label]
observer = Observer()

def check_dir_exists(directory):
    return os.path.isdir(directory)

def check_all_dirs_exist():
    message = ""
    for directory in [this.in_loc.get(), this.out_loc.get()]:
      if not check_dir_exists(directory):
        message += "Directory '{}' does not exist!\n".format(directory)
	# Keep a multi-line message, but only log one error per directory checked
        logger.error(message.splitlines()[-1])

    update_status(message)
    return message == ""

def plugin_start3(plugin_dir: str) -> str:
   global observer
   logger.info(f"{appname}.{plugin_name} loading!")
   this.in_loc = tk.StringVar(value=config.get_str("AS_INPUT"))
   if this.in_loc is None or this.in_loc.get() == "":
     this.in_loc = tk.StringVar(value="%userprofile%\Videos\Elite Dangerous")
     config.set("AS_INPUT", this.in_loc.get())

   this.out_loc = tk.StringVar(value=config.get_str("AS_OUTPUT"))
   if this.out_loc is None or this.out_loc.get() == "":
     this.out_loc = tk.StringVar(value="%userprofile%\Pictures\Frontier Developments\Elite Dangerous")
     config.set("AS_OUTPUT", this.out_loc.get())

   return "Any Screenshot"

def plugin_prefs(parent, cmdr, is_beta):
    frame = nb.Frame(parent)
    frame.columnconfigure(3, weight=1)

    input_label = nb.Label(frame, text="Screenshot Directory")
    input_label.grid(padx=10, row=0, column=0, sticky=tk.W)

    input_entry = nb.Entry(frame, textvariable=this.in_loc)
    input_entry.grid(padx=10, row=0, column=1, columnspan=2, ipadx=60, sticky=tk.W)

    output_label = nb.Label(frame, text="Output Directory")
    output_label.grid(padx=10, row=1, column=0, sticky=tk.W)

    output_entry = nb.Entry(frame, textvariable=this.out_loc)
    output_entry.grid(padx=10, row=1, column=1, columnspan=2, ipadx=60, sticky=tk.W)

    return frame

def start_observer():
    event_handler = LoggingEventHandler()
    observer = Observer()
    observer.schedule(event_handler, this.in_loc.get(), recursive=False)
    observer.start()

def stop_observer():
    global observer
    if observer is not None and observer.is_alive():
      observer.stop()
      observer.join()

def prefs_changed(cmdr, is_beta):
    config.set("AS_INPUT", this.in_loc.get())
    config.set("AS_OUTPUT", this.out_loc.get())
    stop_observer()
    if check_all_dirs_exist() and monitor.game_running():
      start_observer()

def plugin_app(parent: tk.Frame) -> Tuple[tk.Label, tk.Label]:
    global status
    label = tk.Label(parent, text="Any Screenshot")
    status = tk.Label(parent, text="")

    if check_all_dirs_exist():
      update_status("")

    return (label, status)

def update_status(message) -> None:
    global status
    status["text"] = message

def plugin_stop() -> None:
    stop_observer()

def journal_entry( cmdr: str, is_beta: bool, system: str, station: str, entry: Dict[str, Any], state: Dict[str, Any]) -> None:
    global observer
    observer.join(0.1)
    if entry['event'].lower() == 'shutdown' or monitor.game_running == False:
      stop_observer()
      update_status("Stopped")
    elif entry['event'].lower() == 'startup':
      start_observer()
      update_status("Started")

def dashboard_entry(cmdr: str, is_beta: bool, entry: Dict[str, Any]):
    global observer
    observer.join(0.1)
