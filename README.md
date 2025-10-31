# 🗺️ Google Maps Scraper

A powerful, multi-threaded Google Maps scraper built with Python and Selenium. Extract business data including names, addresses, coordinates, ratings, reviews, contact info, and more.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Selenium](https://img.shields.io/badge/selenium-4.0+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Features

- 🚀 **Multi-threaded scraping** - Scrape multiple locations simultaneously
- 🎯 **Comprehensive data extraction** - Names, addresses, coordinates, ratings, reviews, phone, website, opening hours
- 📊 **Multiple output formats** - CSV and Excel
- 🌐 **Web interface** - Built-in Streamlit app for easy use
- 🔄 **Automatic deduplication** - Removes duplicate entries
- ⚙️ **Highly configurable** - Adjust threads, delays, scroll limits, and more
- 🇮🇩 **Indonesian address parsing** - Extracts subdistrict, district, city, province, ZIP

## 📋 Prerequisites

- Python 3.8 or higher
- Chrome browser
- ChromeDriver (automatically managed by Selenium)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/gmaps-scraper.git
cd gmaps-scraper
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Scraper

**Option A: Using Streamlit Web Interface (Recommended)**

```bash
streamlit run app.py
```

Then open your browser to `http://localhost:8501`

**Option B: Using Python Script**

```bash
python example.py
```

**Option C: Using Command Line**

```bash
python main.py
```

## 📁 Project Structure

```
gmaps-scraper/
├── app.py                 # Streamlit web interface
├── main.py               # Command-line interface
├── example.py            # Basic usage example
├── example_subdistrict.py # Subdistrict example
├── requirements.txt      # Python dependencies
│
├── config/
│   └── settings.py       # Configuration settings
│
├── core/
│   ├── driver_manager.py    # Chrome driver management
│   ├── search_engine.py     # Google Maps search logic
│   └── orchestrator.py      # Multi-threaded orchestration
│
├── models/
│   └── place.py          # Data models
│
├── utils/
│   ├── extractors.py     # Data extraction utilities
│   └── task_generator.py # Task generation
│
└── data/
    ├── example_keywords.csv   # Sample keywords
    └── example_locations.csv  # Sample locations
```

## 📖 Usage

### Web Interface (Streamlit)

1. **Upload CSV files:**
   - Keywords file: One keyword per row
   - Locations file: district, city columns (optional: subdistrict)

2. **Configure settings:**
   - Max results per task (5-500)
   - Number of threads (1-10)
   - Scroll settings
   - Delays

3. **Start scraping!**

4. **Download results** in CSV or Excel format

### Python Script

```python
from config.settings import ScraperConfig
from core.orchestrator import ScraperOrchestrator
from models.place import SearchTask

# Configure
config = ScraperConfig(
    headless=True,
    max_workers=4,
    max_scroll_attempts=10
)

# Create tasks
tasks = [
    SearchTask(
        keyword="restaurant",
        location="Jakarta Selatan, Jakarta",
        max_results=30
    )
]

# Run scraper
orchestrator = ScraperOrchestrator(config)
df = orchestrator.scrape_tasks(tasks)

# Save results
df.to_csv('results.csv', index=False)
print(f"Scraped {len(df)} places!")
```

## 📊 CSV File Formats

### Keywords File (`keywords.csv`)

```csv
keyword
restaurant
cafe
hotel
```

### Locations File (`locations.csv`)

**Basic format (district + city):**
```csv
district,city
Menteng,Jakarta Pusat
Kebayoran Baru,Jakarta Selatan
```

**With subdistrict:**
```csv
subdistrict,district,city
Senayan,Kebayoran Baru,Jakarta Selatan
Menteng Dalam,Tebet,Jakarta Selatan
```

## 🔧 Configuration Options

```python
config = ScraperConfig(
    headless=True,              # Run browser in headless mode
    max_workers=4,              # Number of parallel threads
    max_scroll_attempts=20,     # Max scrolls per search
    scroll_pause_time=2.0,      # Pause between scrolls
    min_delay=1.0,              # Min delay between actions
    max_delay=3.0,              # Max delay between actions
    element_wait_timeout=15,    # Wait timeout for elements
    page_load_timeout=60        # Page load timeout
)
```

## 📦 Output Data

Each scraped place includes:

| Field | Description |
|-------|-------------|
| name | Business name |
| category | Business category |
| address | Full address |
| subdistrict | Subdistrict/Kelurahan |
| district | District/Kecamatan |
| city | City |
| province | Province |
| zip_code | Postal code |
| latitude | Latitude coordinate |
| longitude | Longitude coordinate |
| rating | Average rating (1-5) |
| reviews_count | Number of reviews |
| phone | Phone number |
| website | Website URL |
| google_maps_link | Google Maps link |
| opening_hours | Opening hours |
| star_1 to star_5 | Star distribution |
| search_keyword | Search keyword used |
| search_location | Search location used |
| scraped_at | Timestamp |

## 🛠️ Advanced Usage

### Generate Tasks from DataFrames

```python
import pandas as pd
from utils.task_generator import TaskGenerator

keywords_df = pd.read_csv('keywords.csv')
locations_df = pd.read_csv('locations.csv')

tasks = TaskGenerator.generate_from_dataframe(
    keywords_df=keywords_df,
    locations_df=locations_df,
    max_results_per_task=50
)
```

### Custom Address Parsing

```python
from utils.extractors import parse_address

address = "Jl. Sudirman No.1, Senayan, Kec. Kebayoran Baru, Jakarta Selatan, DKI Jakarta 12190"
subdistrict, district, city, province, zip_code = parse_address(address)

print(f"Subdistrict: {subdistrict}")  # Senayan
print(f"District: {district}")        # Kebayoran Baru
print(f"City: {city}")                # Jakarta Selatan
```

## ⚠️ Important Notes

### Rate Limiting
- Use reasonable delays (1-3 seconds recommended)
- Don't scrape too aggressively to avoid IP blocks
- Consider using proxies for large-scale scraping

### Resource Usage
- Chrome browser is resource-intensive
- Recommended: 2-4 threads on regular machines
- More threads = faster but more memory/CPU usage

### Legal Considerations
- Review Google's Terms of Service
- Use responsibly and ethically
- For educational purposes only

## 🐛 Troubleshooting

### Chrome Driver Issues

```bash
# Update Chrome and ChromeDriver
pip install --upgrade selenium webdriver-manager
```

### Memory Issues

Reduce the number of threads:
```python
config = ScraperConfig(max_workers=2)
```

### Timeout Errors

Increase timeout values:
```python
config = ScraperConfig(
    page_load_timeout=120,
    element_wait_timeout=30
)
```

### Can't Find Elements

Google Maps changes its HTML structure. Check for updates:
```bash
git pull origin main
```

## 📚 Examples

Check the `examples/` directory for:
- Basic scraping
- Multi-location scraping
- Subdistrict-level scraping
- Custom configurations

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Selenium](https://www.selenium.dev/)
- UI powered by [Streamlit](https://streamlit.io/)
- Data processing with [Pandas](https://pandas.pydata.org/)

## 📞 Support

- 🐛 [Report Bug](https://github.com/YOUR_USERNAME/gmaps-scraper/issues)
- 💡 [Request Feature](https://github.com/YOUR_USERNAME/gmaps-scraper/issues)
- 📧 Email: your.email@example.com

## ⭐ Star History

If this project helped you, please give it a ⭐!

---

**Disclaimer:** This tool is for educational purposes only. Always respect website terms of service and robots.txt. Use responsibly.