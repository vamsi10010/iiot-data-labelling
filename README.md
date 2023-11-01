# IIoT Smart Machine Monitoring - Data Labelling
This repo contains the code for processing data from MTConnect for the TinyML/IIoT VIP team.

### Repo Structure
```bash
├── README.md
├── audio/                      # WAV file output dir (will have to be created by user)
├── data/                       # CSV file output dir (will have to be created by user)
├── mtconnect_label.py          # MTConnect processing script
├── notebooks/                  # Notebooks for testing
│   ├── data_lbl.ipynb
│   ├── script_testing.ipynb
│   └── sound_collection.ipynb
├── script_v1.py                # Old version of MTConnect script
└── sound_script.py             # Sound processing script
```

### Dependencies
The script requires the following libraries to be installed:
- `pandas`
- `numpy`
- `scipy`
- `lxml`
- `keyboard`

### Usage
Change the constants at the top of the script as per your MTConnect configuration. Then run the script as follows:
```bash
python mtconnect_label.py
```
or
```bash
python3 sound_script.py
```