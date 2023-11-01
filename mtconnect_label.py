import pandas as pd
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
df = pd.DataFrame()

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
        
def record(content: str, device: str, lock: Lock, namespace: str) -> None:
    '''Record sensor data from XML string for given sensor.
    
    This function converts `content` into an ElementTree object and then
    uses XPath to find the data for the given sensor and inserts the data
    into the given data frame.
    '''
    
    global df
    
    root = etree.fromstring(content)
    devs = root.xpath("//x:DeviceStream[@uuid='" + device + "']", namespaces={'x': namespace})
    if len(devs) == 0: return
    else: devroot = devs[0]
    
    new_df = pd.DataFrame()
    for category in CATEGORIES:
        for data in devroot.xpath("//x:" + category, namespaces={'x': namespace}):
            for seq in data:
                new_df.at[pd.to_datetime(seq.attrib['timestamp']).round('ms'), seq.tag] = seq.text

    lock.acquire()
    df = pd.concat([df, new_df])
    lock.release()
        
def main():
    
    global running
    global df
    
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
    root = etree.fromstring(resp.content)

    NAMESPACE = re.split('{|}', root.tag)[1]

    header = root.xpath("//x:Header", namespaces={'x': NAMESPACE})[0].attrib
    start_time = pd.to_datetime(header['creationTime'])
    
    f_seq = int(header['lastSequence'])
    l_seq = int(header['nextSequence'])
    
    # Get device names
    devices = [device for device in root.xpath("//x:DeviceStream", namespaces={'x': NAMESPACE})]   
    
    # Create lock to prevent race conditions
    lock = Lock()
    
    # Insert data from current into first line of data frame
    for category in CATEGORIES:
        for data in root.xpath("//x:" + category, namespaces={'x': NAMESPACE}):
            for seq in data:
                df.at[0, seq.tag] = seq.text
                if int(seq.attrib['sequence']) == f_seq:
                    df.at[0, 'timestamp'] = pd.to_datetime(seq.attrib['timestamp']).round('ms')
                    
    df.set_index('timestamp', inplace=True)
    
    f_seq = l_seq
    l_seq += 1
        
    # Log real time data    
    print("Logging, press space to stop", start_time)
    while running:
        print("Logging...", f_seq, l_seq)
        
        SAMPLE = 'sample?from={}&to={}'.format(f_seq, l_seq)
        
        # request sample
        resp = session.get(AGENT + SAMPLE)
        root = etree.fromstring(resp.content)
        
        # collect devices and data
        # print("procs starting...")
        
        procs = []
        for device in devices:
            proc = Thread(target=record, args=(resp.content, device.attrib['uuid'], lock, NAMESPACE))
            procs.append(proc)
            proc.start()
            
        for proc in procs:
            proc.join() 
            
        # print("procs joined...")
            
        # update first and last sequence
        tries = 100
        for i in range(tries):
            try:
                header = root.xpath("//x:Header", namespaces={'x': NAMESPACE})[0].attrib
            except:
                if i < tries - 1:
                    print("Could not get header, trying again...")
                    time.sleep(1)
                    continue
                else:
                    print(f_seq, l_seq, SAMPLE)
                    exit(1)
            break
            
        # try:
        #     header = root.xpath("//x:Header", namespaces={'x': NAMESPACE})[0].attrib
        # except:
        #     print(f_seq, l_seq, SAMPLE)
        #     exit(1)
            
        f_seq = int(header['nextSequence'])
        l_seq = int(header['lastSequence'])
        
        print('Value of running: ', running)
    else:
        print("Logging stopped, generating csv files...")
        
        # collect the final sample
        SAMPLE = 'sample?from={}&to={}'.format(f_seq, l_seq)
        
        # request sample
        resp = session.get(AGENT + SAMPLE)
        root = etree.fromstring(resp.content)
        
        # collect devices and data
        procs = []
        for device in devices:
            proc = Thread(target=record, args=(resp.content, device.attrib['uuid'], lock, NAMESPACE))
            procs.append(proc)
            proc.start()
        
        for proc in procs:
            proc.join()
            
    # Unregister the key event listener when the loop exits
    keyboard.unhook_all()
    
    # Sort timestamps
    df.sort_index(inplace=True)    
    
    # Reset timestamps to a column
    df.reset_index(inplace=True, names='timestamp')
    
    # Accumulate changes in each sequence
    for row in range(1, df.shape[0]):
        for col in df.columns:
            if pd.isna(df.loc[row, col]):
                df.loc[row, col] = df.loc[row - 1, col]
                
    # Write sensor data to csv file
    filename = 'data/' + str(start_time).replace(':','_') + '.csv'
    df.to_csv(filename, index=False)
    print("Wrote CSV file", filename)
        
if __name__ == '__main__':
    main()