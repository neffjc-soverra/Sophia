# Deployment Guide

## Options

### 1. Streamlit Cloud (Easiest)
- Upload to GitHub
- Connect at share.streamlit.io
- Deploy in 2 minutes
- FREE

### 2. Local Development
```bash
chmod +x quickstart.sh
./quickstart.sh
```

### 3. Docker
```bash
docker build -t hospital-verification .
docker run -p 8501:8501 hospital-verification
```

## File Checklist

Required:
- ✅ app.py
- ✅ verification_helper.py
- ✅ requirements.txt
- ✅ hospital_verification_config.json

Optional:
- api.py (if using API)
- Docker files (if using Docker)
- quickstart.sh (for local)

## Troubleshooting

**Module not found**
```bash
pip install -r requirements.txt
```

**Port in use**
```bash
streamlit run app.py --server.port 8502
```

See README.md for full documentation.
