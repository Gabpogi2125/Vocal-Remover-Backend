import os
import shutil
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from audio_separator.separator import Separator

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploads"
OUTPUT_DIR = "./outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def clean_up_files(input_file: str, output_files: list):
    await asyncio.sleep(600) # Deletes files after 10 minutes to save free server space
    if os.path.exists(input_file):
        try: os.remove(input_file)
        except Exception: pass
    for file_name in output_files:
        file_path = os.path.join(OUTPUT_DIR, file_name)
        if os.path.exists(file_path):
            try: os.remove(file_path)
            except Exception: pass

@app.post("/separate")
async def separate_audio(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    input_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        separator = Separator(output_dir=OUTPUT_DIR)
        separator.load_model('Kim_Vocal_2') # Highly optimized for free CPU tiers
        output_files = separator.separate(input_path)
        
        background_tasks.add_task(clean_up_files, input_path, output_files)
            
        return {
            "status": "success",
            "vocals": output_files[0] if len(output_files) > 0 else "",
            "instrumental": output_files[1] if len(output_files) > 1 else ""
        }
    except Exception as e:
        if os.path.exists(input_path): os.remove(input_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")
