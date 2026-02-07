# ⭐ START HERE - Complete Setup Guide

## 🎯 What This Tool Does

Extracts room-level data from hotel websites:
- Room names, sizes, bed types, views
- 30-word descriptions
- 4 screenshots per room
- All organized in CSV + image folders

**No coding required!** Just click buttons in a web interface.

---

## 📋 What You Need

- A computer (Windows, Mac, or Linux)
- Python 3.8 or newer ([Download here](https://www.python.org/downloads/))
- Internet connection
- 10 minutes for setup

---

## 🚀 Installation (One-Time Setup)

### Step 1: Download the Project

**Option A: Using Git**
```bash
git clone https://github.com/Benibenassi123/hotel-room-extractor.git
cd hotel-room-extractor
```

**Option B: Download ZIP**
1. Go to: https://github.com/Benibenassi123/hotel-room-extractor
2. Click green "Code" button → "Download ZIP"
3. Unzip to your Desktop
4. Open Terminal/Command Prompt
5. Navigate: `cd Desktop/hotel-room-extractor-main`

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

**Wait 2-3 minutes** for everything to download.

---

## ▶️ Running the Tool

Every time you want to use it:

### 1. Open Terminal/Command Prompt

**Mac:** Cmd+Space → type "Terminal"  
**Windows:** Win key → type "cmd"

### 2. Navigate to Project

```bash
cd Desktop/hotel-room-extractor-main
```

### 3. Start the Web Interface

```bash
python app.py
```

You'll see:
```
🏨 Hotel Room Extractor - Web Interface
✓ Server starting...
👉 Open your browser and go to: http://localhost:5000
```

### 4. Open Your Browser

Go to: **http://localhost:5000**

---

## 🖱️ Using the Web Interface

### Single Hotel Mode:

1. **Fill in the form:**
   - Hotel ID: `104`
   - Hotel Name: `Hilton Barcelona`
   - City: `Barcelona`
   - Address: `Av Diagonal 589`

2. **Click "Extract Room Data 🚀"**

3. **Wait 2-5 minutes**
   - Watch progress: "Searching...", "Found website...", "Processing room..."

4. **Download Results**
   - Click "Download CSV"
   - Check `images/104/` folder for screenshots

### CSV Upload Mode:

1. **Switch to "CSV Upload" tab**

2. **Paste your CSV data:**
```csv
hotel_id,hotel_name,city,address
104,Hilton Barcelona,Barcelona,Av Diagonal 589
105,Hotel Arts,Barcelona,Marina 19
106,W Barcelona,Barcelona,Placa Rosa dels Vents 1
```

3. **Click "Extract Room Data"**

4. **Wait** (longer for multiple hotels)

5. **Download CSV** with all results

---

## 📊 What You Get

### CSV File with 17 Columns:
- Hotel info (ID, name, city, address)
- Room details (name, area, bed type, views)
- 30-word description
- Image filenames
- Source URLs
- Confidence level

### Images Folder Structure:
```
images/
├── 104/
│   ├── 104_deluxe-double_room1.jpg
│   ├── 104_deluxe-double_room2.jpg
│   ├── 104_deluxe-double_bathroom.jpg
│   ├── 104_deluxe-double_view.jpg
│   ├── 104_executive-suite_room1.jpg
│   └── ...
├── 105/
│   └── ...
```

---

## ❓ Common Issues

### "Python not found"
Install Python from https://www.python.org/downloads/  
**IMPORTANT:** Check "Add Python to PATH" during installation

### "playwright not found"
Run: `playwright install chromium`

### "Can't open localhost:5000"
- Make sure `python app.py` is still running
- Try: http://127.0.0.1:5000
- Check if another program is using port 5000

### "No rooms found"
- Some hotels don't list rooms on their website
- Try running with browser visible: Set `HEADLESS=False` in `config.py`
- Check if hotel has a rooms/accommodations page

### "Screenshots failed"
- Images may be lazy-loaded or protected
- CSV will note "SCREENSHOT FAILED" for those images
- Rest of data will still be extracted

---

## 🛑 Stopping the Tool

When you're done:
1. Go to Terminal/Command Prompt where `python app.py` is running
2. Press **CTRL+C**
3. Close the browser tab

---

## 💡 Pro Tips

1. **Start with 1 hotel** to test before doing bulk extraction
2. **Check the website first** - if there's no rooms page, extraction may fail
3. **Be patient** - extraction takes 2-5 minutes per hotel
4. **Save your CSVs** - results are stored in `output/` folder
5. **Images auto-download** - check `images/` folder after extraction

---

## 📚 Learn More

- Full documentation: [README.md](README.md)
- Technical details: See code comments in `scraper.py`

---

## 🎉 You're Ready!

1. Run: `python app.py`
2. Open: http://localhost:5000
3. Extract hotel data!

**Happy extracting!** 🚀
