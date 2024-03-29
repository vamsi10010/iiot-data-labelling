import pandas as pd
import numpy as np
import scipy.io.wavfile
import requests
import keyboard
import lxml.etree as etree
from threading import Thread, Lock
import re
import os

## == CONST ==
AGENT = 'http://localhost:5000/'
CURRENT = 'current'
PROBE = 'probe'
SAMP_RATE = 48000

running = True

def filename2time(filename: str) -> pd.Timestamp:
    '''Convert filename to timestamp.
    
    This function takes a filename and returns the timestamp encoded in the filename.
    '''
    
    return pd.to_datetime(filename.split('.')[1].replace('_', ':'))

def info(title):
    print(title)
    print('module name:', __name__)
    print('parent process:', os.getppid())
    print('process id:', os.getpid())
    
def write_wav(devices: dict, sensor: str, filename: str) -> None:
    '''Write wav file from output list.
    
    This function takes the output list and writes it to a wav file.
    '''
    
    # info('function write_wav')
    scipy.io.wavfile.write('./audio/' + filename, SAMP_RATE, np.array(devices[sensor], dtype=np.int16))
    print("Wrote WAV file", filename)

def record(content: str, devices: dict, sensor: str, lock: Lock, namespace: str) -> None:
    '''Record sound data from XML string for given sensor.
    
    This function converts the XML string into an ElementTree object and then
    uses XPath to find the data for the given sensor.
    The output list is pushed onto a queue to be retrieved by the main thread.
    '''
    
    # info('function record')
    pattern = re.compile('-?[0-9][0-9]*')           # regex to match integers
    
    root = etree.fromstring(content)
    device_root = root.xpath("//x:DisplacementTimeSeries[@dataItemId='" + sensor + "']", namespaces={'x': namespace})
    output = []
    try:
        [output.extend([np.int16(x) if bool(pattern.fullmatch(x)) else 0 for x in data.text.split(' ')]) for data in device_root]
    except:
        return
    
    # Place output in devices dictionary
    lock.acquire()
    devices[sensor].extend(output)
    lock.release()
        
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
        
def main():
    '''Main function to run the script.
    '''
    
    global running
    
    # Create HTTPS session
    session = requests.Session()
    
    # Register the key event listener
    keyboard.on_press(on_key_event)

    # Get first, last, time from current
    try:
        resp = session.get(AGENT + CURRENT)
    except:
        print("Could not connect to", AGENT + CURRENT)
        exit(1)
    print("Connected to", AGENT + CURRENT)
    sound_root = etree.fromstring(resp.content)

    NAMESPACE = re.split('{|}', sound_root.tag)[1]

    header = sound_root.xpath("//x:Header", namespaces={'x': NAMESPACE})[0].attrib
    start_time = pd.to_datetime(header['creationTime'])
    start_times = {}
    
    # uncomment this to get sound from the start
    # f_seq = int(header['firstSequence'])
    # l_seq = int(header['lastSequence'])
    
    f_seq = int(header['nextSequence'])
    l_seq = f_seq + 1
    
    # Get device names, starting timestamps, and first data sequences
    devices = {}   
    
    for device in sound_root.xpath("//x:DisplacementTimeSeries", namespaces={'x': NAMESPACE}):
        devices[device.attrib['dataItemId']] = [0 if x == 'UNAVAILABLE' else np.int16(x) for x in device.text.split(' ')]
        start_times[device.attrib['dataItemId']] = pd.to_datetime(device.attrib['timestamp'])
        
    
    # Create lock to prevent race conditions
    lock = Lock()
    
    run_final = True

    print("Logging, press space to stop", start_time)
    while running:
        print("Logging...", f_seq, l_seq)
        
        SAMPLE = 'sample?from={}&to={}'.format(f_seq, l_seq)
        
        # request sample
        resp = session.get(AGENT + SAMPLE)
        sound_root = etree.fromstring(resp.content)
        
        # collect devices and data
        # print("procs starting...")
        
        procs = []
        for device in devices.keys():
            proc = Thread(target=record, args=(resp.content, devices, device, lock, NAMESPACE))
            procs.append(proc)
            proc.start()
        
        for proc in procs:
            proc.join()
        
        # print("procs joined...")
            
        # update first and last sequence
        try:
            header = sound_root.xpath("//x:Header", namespaces={'x': NAMESPACE})[0].attrib
        except:
            run_final = False
            running = False
            print("Could not get header, exiting...")
            
        f_seq = int(header['nextSequence'])
        l_seq = int(header['lastSequence'])
        
        print('Value of running: ', running)
    else:
        print("Logging stopped, generating wav files...")
        
        if run_final:
            # collect the final sample
            SAMPLE = 'sample?from={}&to={}'.format(f_seq, l_seq)
            
            # request sample
            resp = session.get(AGENT + SAMPLE)
            sound_root = etree.fromstring(resp.content)
            
            # collect devices and data
            procs = []
            for device in devices.keys():
                proc = Thread(target=record, args=(resp.content, devices, device, lock, NAMESPACE))
                procs.append(proc)
                proc.start()
            
            for proc in procs:
                proc.join()
            
    # Unregister the key event listener when the loop exits
    keyboard.unhook_all()
    
    # Write wav files
    procs = []
    for device in devices.keys():
        proc = Thread(target=write_wav, args=(devices, device, device + '.' + str(start_times[device]).replace(':','_') + '.wav'))
        procs.append(proc)
        proc.start()
        
    for proc in procs:
        proc.join()
    
if __name__ == '__main__':
    main()