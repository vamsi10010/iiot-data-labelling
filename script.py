import pandas as pd
import numpy as np
import requests
import lxml.etree as etree
import keyboard

def get_seqs():
    # Get starting sequence and first sequence
    
    try:
        resp = requests.get('http://localhost:5000/current')
    except:
        print("Error: could not connect to MTConnect stream")
        return
    
    root = etree.fromstring(resp.content)
    start = int(root[0].attrib['nextSequence'])
    first = int(root[0].attrib['firstSequence'])
    
    # Wait for key press
    
    print("Started logging, press any key to end logging")
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
    
    return first, start, end

def load_data(first, start, end):
    df = pd.DataFrame(index = range(first, end + 1), columns=['timestamp'])
    
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
                    idx = int(m.attrib['sequence'])
                    df.at[idx, 'timestamp'] = pd.to_datetime(m.attrib['timestamp'])
                    df.at[idx, m.tag] = m.text
    
    df = accumulate(df, first, end)
       
    return df.loc[start : ]

def accumulate(df, first, end):
    for i in range(first + 1, end + 1):
        for j in df.columns:
            if pd.isna(df.at[i, j]):
                df.at[i, j] = df.at[i - 1, j]   
    
    return df

def main():
    # Get start and end sequences
    
    first, start, end = get_seqs()
    
    # Load data between start and end sequences
    
    df = load_data(first, start, end)
    
    # Export df to a CSV file
    
    df.to_csv('output.csv', index=False)
 
if __name__ == "__main__":
    main()