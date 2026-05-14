import json
import os
import time
import requests
from pathlib import Path
from colorama import Fore, Style
from dotenv import load_dotenv

load_dotenv()

# Ensure API key is set
api_key = os.getenv("KIE_API_KEY")
if not api_key or api_key == "your_kie_api_key_here":
    print(f"{Fore.RED}Please set KIE_API_KEY in .env{Style.RESET_ALL}")

def _download_image(url: str, output_path: str) -> bool:
    """Download an image from a URL to a local path."""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  {Fore.RED}[ERROR] Failed to download image: {e}{Style.RESET_ALL}")
        return False

def _generate_image_kie(prompt: str, output_path: str) -> bool:
    """Generate an image using the Kie AI API and save it."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "z-image",
        "input": {
            "prompt": prompt,
            "aspect_ratio": "1:1",
            "nsfw_checker": False
        }
    }
    
    # 1. Create Task
    print(f"  {Fore.YELLOW}Submitting task to Kie AI...{Style.RESET_ALL}")
    try:
        res = requests.post("https://api.kie.ai/api/v1/jobs/createTask", json=payload, headers=headers)
        res.raise_for_status()
        data = res.json()
        
        if data.get("code") != 200:
            print(f"  {Fore.RED}[ERROR] API returned error: {data.get('msg')}{Style.RESET_ALL}")
            return False
            
        task_id = data.get("data", {}).get("taskId")
        if not task_id:
            print(f"  {Fore.RED}[ERROR] No taskId returned!{Style.RESET_ALL}")
            return False
            
    except Exception as e:
        print(f"  {Fore.RED}[ERROR] Failed to create image task: {e}{Style.RESET_ALL}")
        return False

    print(f"  {Fore.YELLOW}Task {task_id} created. Polling for completion...{Style.RESET_ALL}")
    
    # 2. Poll for Completion
    max_attempts = 30
    poll_interval = 5
    
    for attempt in range(max_attempts):
        time.sleep(poll_interval)
        try:
            status_res = requests.get(f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}", headers=headers)
            status_res.raise_for_status()
            status_data = status_res.json()
            
            # KIE AI typically returns the task status somewhere in the data object
            # Let's inspect the payload safely
            task_info = status_data.get("data", {})
            status = task_info.get("status", "").upper()
            
            if status in ["SUCCESS", "COMPLETED", "SUCCEEDED"]:
                # Try to find the image URL in common response formats
                img_url = None
                
                # Check different possible structures based on common API patterns
                if "images" in task_info and isinstance(task_info["images"], list) and len(task_info["images"]) > 0:
                    img_url = task_info["images"][0]
                    if isinstance(img_url, dict):
                        img_url = img_url.get("url")
                elif "imageUrl" in task_info:
                    img_url = task_info["imageUrl"]
                elif "result" in task_info and isinstance(task_info["result"], dict):
                    result = task_info["result"]
                    if "images" in result:
                        img_url = result["images"][0]
                    elif "url" in result:
                        img_url = result["url"]
                
                if img_url:
                    print(f"  {Fore.GREEN}Image generated! Downloading...{Style.RESET_ALL}")
                    return _download_image(img_url, output_path)
                else:
                    print(f"  {Fore.RED}[ERROR] Task completed but couldn't find image URL in response: {status_data}{Style.RESET_ALL}")
                    return False
                    
            elif status in ["FAILED", "ERROR"]:
                print(f"  {Fore.RED}[ERROR] Generation failed: {task_info.get('error', 'Unknown error')}{Style.RESET_ALL}")
                return False
                
            else:
                # Still running
                print(f"  {Fore.BLUE}Status: {status or 'PROCESSING'}... ({attempt+1}/{max_attempts}){Style.RESET_ALL}")
                
        except Exception as e:
            print(f"  {Fore.YELLOW}[WARN] Polling error: {e}. Retrying...{Style.RESET_ALL}")
            
    print(f"  {Fore.RED}[ERROR] Timeout waiting for image generation.{Style.RESET_ALL}")
    return False

def generate_images(brief: dict) -> dict:
    """Generate an image for each chapter using Kie AI."""
    print(f"\n{Fore.CYAN}============================================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  [STAGE 3] Kie AI Image Generator{Style.RESET_ALL}")
    print(f"{Fore.CYAN}============================================================{Style.RESET_ALL}")

    chapters = brief.get("chapters", [])
    if not chapters:
        print(f"{Fore.RED}  [ERROR] No chapters found in brief!{Style.RESET_ALL}")
        return brief
        
    out_dir = Path(brief.get("output_dir", "."))
    images_dir = out_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    book_title = brief.get("title", "this topic")
    
    for i, chapter in enumerate(chapters):
        print(f"\n  {Fore.BLUE}Generating Image for Chapter {i+1}: {chapter['title']}{Style.RESET_ALL}")
        
        # Build an optimized prompt for image generation
        prompt = f"A professional, high-quality, conceptual illustration for a book chapter titled '{chapter['title']}'. The book is about {book_title}. The image should be beautiful, clean, and visually striking. No text or words in the image."
        
        image_filename = f"chapter_{i+1}.png"
        image_path = images_dir / image_filename
        
        success = _generate_image_kie(prompt, str(image_path))
        
        if success:
            chapter["image_path"] = str(image_path)
            print(f"  {Fore.GREEN}[✓] Image saved to {image_path}{Style.RESET_ALL}")
        else:
            chapter["image_path"] = None
            print(f"  {Fore.RED}[x] Failed to generate image for chapter {i+1}{Style.RESET_ALL}")
            
    print(f"\n  {Fore.GREEN}[✓] Image generation complete!{Style.RESET_ALL}")
    
    # Save the updated brief with image paths
    final_file = out_dir / "final_compiled.json"
    with open(final_file, "w", encoding="utf-8") as f:
        json.dump(brief, f, indent=4)
        
    return brief
