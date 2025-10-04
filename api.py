
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
import json
from datetime import datetime
import os
from verification_helper import load_config, process_dataframe_real, export_with_timestamp

app = FastAPI(title="Hospital L&D Verification API")

@app.get("/")
def read_root():
    return {
        "message": "Hospital L&D Verification API",
        "endpoints": {
            "POST /verify": "Upload Excel file for verification",
            "GET /health": "Health check"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/verify")
async def verify_hospitals(
    file: UploadFile = File(...),
    use_real_search: bool = False
):
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="File must be .xlsx format")
    
    try:
        # Save uploaded file
        upload_path = "temp_upload.xlsx"
        with open(upload_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Load and process
        df = pd.read_excel(upload_path)
        cfg = load_config('hospital_verification_config.json')
        df_result, count = process_dataframe_real(df, cfg, use_real_search=use_real_search)
        
        # Export result
        output_path = export_with_timestamp(df_result, 'verification_result')
        
        # Clean up temp file
        os.remove(upload_path)
        
        return FileResponse(
            path=output_path,
            filename=output_path,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
