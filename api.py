import asyncio
import json
import os
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Ensure we can import from the local directory
sys.path.insert(0, str(Path(__file__).parent))

from categories import list_categories
from main import run_pipeline


app = FastAPI(title="Agent 5 eBook Generator API")

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for task status
# In a real production app, use Redis or a database.
tasks: Dict[str, dict] = {}

class GenerateRequest(BaseModel):
    category_key: Optional[str] = None
    topic: Optional[str] = None
    audience: Optional[str] = "beginner"
    tone: Optional[str] = "conversational"

def background_generation_task(task_id: str, req: GenerateRequest):
    tasks[task_id]["status"] = "processing"
    tasks[task_id]["message"] = "Starting eBook generation pipeline..."
    
    try:
        # Run the pipeline
        pdf_path = run_pipeline(
            category_key=req.category_key,
            topic=req.topic,
            audience=req.audience,
            tone=req.tone,
        )
        
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["pdf_path"] = str(pdf_path)
        tasks[task_id]["message"] = "eBook generated successfully!"
        
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["message"] = f"Error during generation: {str(e)}"
        print(f"Task {task_id} failed: {str(e)}")

@app.get("/categories")
def get_categories():
    """Return the list of available categories."""
    return {"categories": list_categories()}

@app.post("/generate")
def generate_ebook(req: GenerateRequest, background_tasks: BackgroundTasks):
    """Start an eBook generation task."""
    task_id = str(uuid.uuid4())
    
    tasks[task_id] = {
        "id": task_id,
        "status": "queued",
        "message": "Task added to queue",
        "pdf_path": None,
        "created_at": datetime.now().isoformat()
    }
    
    # We use a standard thread instead of FastAPI BackgroundTasks 
    # to avoid event loop conflicts since main.py uses asyncio.run()
    thread = threading.Thread(target=background_generation_task, args=(task_id, req))
    thread.start()
    
    return {"task_id": task_id, "status": "queued", "message": "Generation started in the background."}

@app.get("/status/{task_id}")
def check_status(task_id: str):
    """Check the status of a specific generation task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = tasks[task_id]
    
    # If completed, check if file exists
    if task_info["status"] == "completed" and task_info["pdf_path"]:
        if not os.path.exists(task_info["pdf_path"]):
            task_info["status"] = "failed"
            task_info["message"] = "Generated file not found on disk."
            
    return task_info

@app.get("/download/{task_id}")
def download_ebook(task_id: str):
    """Download the generated PDF for a completed task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task_info = tasks[task_id]
    
    if task_info["status"] != "completed" or not task_info["pdf_path"]:
        raise HTTPException(status_code=400, detail="Task not completed yet or failed.")
        
    pdf_path = task_info["pdf_path"]
    
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found.")
        
    filename = os.path.basename(pdf_path)
    return FileResponse(
        path=pdf_path, 
        filename=filename, 
        media_type="application/pdf"
    )

@app.get("/")
def health_check():
    return {"status": "ok", "service": "eBook Generator API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
