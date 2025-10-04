# Hospital L&D Verification Tool

Streamlit web app for verifying hospital labor and delivery services.

## Quick Start

### Deploy to Streamlit Cloud
1. Fork this repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Click "New app"
5. Select this repository
6. Set main file: `app.py`
7. Click "Deploy"

### Local Development
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Docker
```bash
docker build -t hospital-verification .
docker run -p 8501:8501 hospital-verification
```

## Usage
1. Download input template from app
2. Fill in hospital data (name, city, state, year)
3. Configure search keywords (optional)
4. Upload Excel file
5. Run verification
6. Download results

## Files
- `app.py` - Streamlit UI
- `api.py` - FastAPI endpoint
- `verification_helper.py` - Core logic
- `hospital_verification_config.json` - Default configuration
- `requirements.txt` - Python dependencies

## Configuration
Edit positive/negative keywords in the app UI or modify `hospital_verification_config.json`.
