# Luna TTS Demo - Setup Guide

This guide will help you set up and run the Luna TTS demo script.

---

## Prerequisites

- Python 3.9 or higher
- Internet connection (to access the Luna TTS API)

---

## Quick Start (Copy & Paste)

Open your terminal and run these commands one by one:

### Step 1: Navigate to the plugin folder

```bash
cd /home/arag/livekit-plugins-luna
```

### Step 2: Create a virtual environment

```bash
python3 -m venv venv
```

### Step 3: Activate the virtual environment

```bash
source venv/bin/activate
```

> **Note:** You will see `(venv)` appear at the start of your terminal prompt. This means the virtual environment is active.

### Step 4: Install dependencies

```bash
pip install --upgrade pip
pip install aiohttp "livekit-agents>=1.0.0"
pip install -e .
```

### Step 5: Run the demo

**Option A: Convert specific text**
```bash
cd examples
python demo.py "नमस्ते, आप कैसे हैं?"
```

**Option B: Interactive mode**
```bash
cd examples
python demo.py
```

---

## All Commands Together (Copy & Paste Block)

If you want to run everything at once, copy and paste this entire block:

```bash
cd /home/arag/livekit-plugins-luna
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install aiohttp "livekit-agents>=1.0.0"
pip install -e .
cd examples
python demo.py "नमस्ते"
```

---

## Running the Demo Again (After Initial Setup)

If you have already completed the setup and want to run the demo again:

```bash
cd /home/arag/livekit-plugins-luna
source venv/bin/activate
cd examples
python demo.py
```

---

## What the Demo Does

1. **Takes Hindi text** as input (from command line or interactive prompt)
2. **Sends it to the Luna TTS API** at hindi.heypixa.ai
3. **Receives synthesized audio** (32kHz, 16-bit, mono)
4. **Saves it as a .wav file** in the current directory

---

## Output Files

The demo saves audio files with timestamps:
```
output_20260108_113059.wav
output_20260108_113215.wav
```

You can play these files with any audio player.

---

## Example Hindi Texts to Try

```
नमस्ते, आप कैसे हैं?
भारत एक महान देश है।
आज का मौसम बहुत अच्छा है।
मेरा नाम लूना है।
धन्यवाद, आपका दिन शुभ हो।
```

---

## Troubleshooting

### "Command not found: python3"
Install Python 3.9 or higher from https://www.python.org/downloads/

### "ModuleNotFoundError: No module named 'livekit'"
Make sure you ran `pip install -e .` from the plugin folder.

### "API not available" error
Check your internet connection. The demo requires access to https://hindi.heypixa.ai

### Virtual environment not activating
Make sure you are using the correct command:
- Linux/Mac: `source venv/bin/activate`
- Windows: `venv\Scripts\activate`

---

## References

- Luna TTS API Documentation: https://hindi.heypixa.ai/docs
- LiveKit Agents Documentation: https://docs.livekit.io/agents/
