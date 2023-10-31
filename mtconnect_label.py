import pandas as pd
import numpy as np
import scipy.io.wavfile
import requests
import keyboard
import lxml.etree as etree
from threading import Thread, Lock
import time
import re
import os

## == CONST ==
AGENT = 'http://localhost:5000/'
CURRENT = 'current'
PROBE = 'probe'
CATEGORIES = ['Samples', 'Events', "Condition"]

running = True

def info(title):
    print(title)
    print('module name:', __name__)
    print('parent process:', os.getppid())
    print('process id:', os.getpid())
    
def on_key_event(e) -> None:
    '''Stop recording when spacebar is pressed.
    
    When the spacebar is pressed, the global variable `running` is set to false
    which stops the recording loop.
    '''
    
    global running
    
    # print('Key pressed: ', e.name)
    if e.event_type == keyboard.KEY_DOWN and e.name == 'space':
        print('YOU PRESSED SPACE!')
        running = False
        
def record() -> None:
    return
        
def main():
    
    global running
    
    # Create HTTPS session
    session = requests.Session()
    
    # Register the key event listener
    keyboard.on_press(on_key_event)
    
    # Output data frame
    df = pd.DataFrame()

    # Get first, last, time from current
    try:
        resp = session.get(AGENT + CURRENT)
    except:
        print("Could not connect to", AGENT + CURRENT)
        exit(1)
    print("Connected to", AGENT + CURRENT)
    root = etree.fromstring(resp.content)

    NAMESPACE = re.split('{|}', root.tag)[1]

    header = root.xpath("//x:Header", namespaces={'x': NAMESPACE})[0].attrib
    start_time = pd.to_datetime(header['creationTime'])
    
    first_sequence = int(header['firstSequence'])
    f_seq = first_sequence
    l_seq = int(header['nextSequence'])
    
    # Create lock to prevent race conditions
    lock = Lock()
    
    print("Logging, press space to stop", start_time)
    while running:
        print("Logging...", f_seq, l_seq)
        
        SAMPLE = 'sample?from={}&to={}'.format(f_seq, l_seq)
        
        # request sample
        resp = session.get(AGENT + SAMPLE)
        root = etree.fromstring(resp.content)
        
        # collect devices and data
        # print("procs starting...")
        
    
        
if __name__ == '__main__':
    main()