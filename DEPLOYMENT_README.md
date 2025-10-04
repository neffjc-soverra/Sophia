# Hospital L&D Verification Tool

## Quick Deploy to Streamlit Cloud (Free)

### Setup Steps:
1. Create GitHub account at github.com
2. Create new repository named 'hospital-verification'
3. Upload these files:
   - app.py
   - verification_helper.py
   - hospital_verification_config.json
   - requirements.txt
4. Go to share.streamlit.io
5. Sign in with GitHub
6. Click 'New app'
7. Select your repository
8. Set main file: app.py
9. Click 'Deploy'

### Student Instructions:
1. Visit your deployed app URL (e.g. yourapp.streamlit.app)
2. Click 'Browse files' and upload Excel file
3. Excel must have columns: name, city, state, year
4. Uncheck 'Use real web search' for faster results
5. Click 'Run Verification'
6. Download results when complete

### Alternative Hosting Options:

**Google Colab (Easiest for students):**
- Free, no setup required
- Students just click link and upload file
- Results download automatically

**Hugging Face Spaces:**
- Free hosting
- Similar to Streamlit Cloud
- Good for academic projects

**Replit:**
- Free tier available
- Built-in code editor
- Easy sharing via URL

### Maintenance Notes:
- Config file controls keyword matching
- Update keywords in hospital_verification_config.json
- Real search uses DuckDuckGo (no API key needed)
- Rate limiting: 2-3 seconds between searches
- For large datasets (>100 hospitals), disable real search

### Files Required:
- app.py (web interface)
- verification_helper.py (core logic)
- hospital_verification_config.json (keywords/rules)
- requirements.txt (dependencies)
