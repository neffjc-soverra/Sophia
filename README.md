# Hospital L&D Verification Tool

Production-ready Streamlit application for verifying hospital labor and delivery services.

## Features

- ✅ Excel file upload with validation
- ✅ Configurable keyword matching
- ✅ Real-time web search (DuckDuckGo)
- ✅ Progress tracking
- ✅ Confidence scoring
- ✅ Results export

## Quick Start

### Streamlit Cloud
1. Upload files to GitHub
2. Go to share.streamlit.io
3. Deploy

### Local
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Usage

1. Download template
2. Fill in hospital data
3. Upload file
4. Configure keywords (optional)
5. Run verification
6. Download results

## Required Columns

- name
- city
- state
- year

## Limits

- Max file size: 10 MB
- Max rows: 500
- Real search: ~1-2 min per hospital

## Support

See DEPLOYMENT_GUIDE.md for details.
