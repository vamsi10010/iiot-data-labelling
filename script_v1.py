import pandas as pd
import numpy as np
import requests
import lxml.etree as etree
import keyboard
import datetime

def get_seqs():
    # Get starting sequence and first sequence
    
    try:
        resp = requests.get('http://localhost:5000/current')
    except:
        print("Error: could not connect to MTConnect stream")
        return
    
    log_time = pd.to_datetime(datetime.datetime.utcnow()).round('ms').tz_localize('UTC')
    
    root = etree.fromstring(resp.content)
    start = int(root[0].attrib['nextSequence'])
    first = int(root[0].attrib['firstSequence'])
    
    # Wait for key press
    
    print(f"Started logging {log_time}\nPress any key to end logging")
    keyboard.read_event(suppress=True)
    
    # After keypress, 
    print("Logging stopped, creating dataframe")
    
    # Get ending sequence
    
    try:
        resp = requests.get('http://localhost:5000/current')
    except:
        print("Error: could not connect to MTConnect stream")
        return
    
    root = etree.fromstring(resp.content)
    end = int(root[0].attrib['lastSequence'])
    
    return first, start, end, log_time

def load_data(first, end, start_time, start=False):
    # df = pd.DataFrame(index = range(first, end + 1), columns=['timestamp'])
    df = pd.DataFrame(columns=['timestamp'])
    
    # Get data from MTConnect stream
    
    url_f = "http://localhost:5000/sample?from={}&count={}".format(first, end)
    
    try:
        resp = requests.get(url_f)
    except:
        print("Error: could not connect to MTConnect stream")
        return

    root = etree.fromstring(resp.content)
    
    # Load data into dataframe
    
    for j in root[1]:
        for k in j:
            for l in k:
                for m in l:
                    # rounding timestamps to millisecond precision
                    
                    timestamp = pd.to_datetime(m.attrib['timestamp']).round('ms')
                    df.at[timestamp, m.tag] = m.text
                    
    df.sort_index(inplace=True)
    
    df.drop(columns=['timestamp'], inplace=True)
    df.reset_index(inplace=True, names='timestamp')
    
    return accumulate(df, start_time, start)

def accumulate(df, start_time, start=False):
    start_index = 1 if df.loc[0, 'timestamp'] < start_time else 0
    
    for i in range(1, len(df)):
        if df.loc[i, 'timestamp'] < start_time:
            start_index += 1
        for j in df.columns:
            if pd.isna(df.loc[i, j]):
                df.loc[i, j] = df.loc[i - 1, j]
    
    return df[start_index: ] if not start else df

def main():
    # Get start and end sequences
    
    first, start, end, start_time = get_seqs()
    
    # Load data between start and end sequences
    
    df = load_data(first, end, start_time, False)
    
    # Export df to a CSV file
    
    df.to_csv('output.csv', index=False)
 
if __name__ == "__main__":
    main()