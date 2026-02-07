# Project Setup

This script works on both Mac and Windows.

## Requirements
- Python 3.7 or higher

## Installation

### Option 1: Quick Install (Simplest)
```bash
pip install -r requirements.txt
python your_script.py
```

### Option 2: Virtual Environment (Recommended)

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python your_script.py
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python your_script.py
```

## Deactivating Virtual Environment
When you're done:
```bash
deactivate
```

## Troubleshooting

**"pip not found"**: Use `python -m pip install -r requirements.txt` instead

**"python not found"**: Try `python3` instead of `python` (Mac/Linux)

**Permission errors**: Add `--user` flag: `pip install --user -r requirements.txt`
