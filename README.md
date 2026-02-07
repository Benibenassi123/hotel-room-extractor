# 🏨 Hotel Room Extractor

Extract detailed room-level data and images from hotel websites using Playwright automation.

## ✨ Features

- 🔍 **Automatic website discovery** - Finds official hotel websites
- 📊 **Extracts structured data** - Room area, bed type, views, descriptions
- 📸 **Captures screenshots** - 4 images per room (room1, room2, bathroom, view)
- 💾 **Exports to CSV** - All 17 required columns
- 🎨 **Beautiful web interface** - No coding required
- 📦 **Bulk processing** - Single hotel or CSV upload

## 🚀 Quick Start

### 1. Download

```bash
git clone https://github.com/Benibenassi123/hotel-room-extractor.git
cd hotel-room-extractor
```

### 2. Install

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Run

```bash
python app.py
```

### 4. Open Browser

Go to: **http://localhost:5000**

## 📋 Usage

### Single Hotel
1. Enter hotel ID, name, city, address
2. Click "Extract Room Data"
3. Wait for extraction to complete
4. Download CSV with results

### CSV Upload
1. Switch to "CSV Upload" tab
2. Paste CSV data:
```csv
hotel_id,hotel_name,city,address
104,Hilton Barcelona,Barcelona,Av Diagonal 589
105,Hotel Arts,Barcelona,Marina 19
```
3. Click "Extract Room Data"
4. Download results

## 📊 Output Format

CSV with 17 columns:
- hotel_id, hotel_name, city, address
- room_name, image_folder, image_files
- room_area_m2, bed_type, views
- room_description_30w
- link_main, link_secondary, sources
- room_match_method, confidence, notes

## 📁 File Structure

```
hotel-room-extractor/
├── app.py                 # Flask web server
├── scraper.py             # Extraction logic
├── config.py              # Configuration
├── requirements.txt       # Dependencies
├── templates/
│   └── index.html        # Web interface
├── output/               # CSV exports
└── images/               # Screenshots
    └── {hotel_id}/       # Organized by hotel
```

## ⚙️ Configuration

Edit `config.py` or set environment variables:

```python
HEADLESS = False  # Show browser (True = headless)
SCREENSHOT_QUALITY = 90  # JPEG quality (1-100)
```

## 🔧 Troubleshooting

**"Playwright not installed"**
```bash
playwright install chromium
```

**"No rooms found"**
- Try running with `HEADLESS=False` to see what's happening
- Some hotels don't list rooms on their website
- Check if the hotel has a rooms/accommodations page

**"Screenshots failed"**
- Images may be lazy-loaded or protected
- Tool will note "SCREENSHOT FAILED" in CSV

## 📝 Requirements

- Python 3.8+
- Playwright
- Flask
- Internet connection

## ⚠️ Legal Notice

This tool is for **educational purposes only**. Web scraping may violate website terms of service. Always:
- Respect robots.txt
- Check website terms of service
- Use official APIs when available
- Rate limit your requests
- Consider using official hotel data sources

## 🤝 Contributing

PRs welcome! Please read contribution guidelines.

## 📄 License

MIT License - see LICENSE file

## 🆘 Support

- Read: [START_HERE.md](START_HERE.md) for beginner guide
- Issues: GitHub Issues
- Docs: See `/docs` folder

---

**Made with ❤️ for non-technical users**
