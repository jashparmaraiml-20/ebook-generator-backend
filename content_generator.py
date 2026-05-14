import json
import os
import time
from pathlib import Path
from colorama import Fore, Style
from dotenv import load_dotenv

try:
    from groq import Groq
    from groq import RateLimitError
    from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
except ImportError:
    print(f"{Fore.RED}Missing required packages. Run: pip install groq tenacity{Style.RESET_ALL}")
    pass

load_dotenv()

# Ensure API key is set
api_key = os.getenv("GROQ_API_KEY")
if not api_key or api_key == "your_groq_api_key_here":
    print(f"{Fore.RED}Please set GROQ_API_KEY in .env{Style.RESET_ALL}")

client = Groq(api_key=api_key)

def _build_system_prompt(brief: dict) -> str:
    """Build the system context prompt."""
    return f"""You are an expert, professional eBook author writing a comprehensive book.
    
    BOOK DETAILS:
    Title: {brief.get('title')}
    Subtitle: {brief.get('subtitle')}
    Category: {brief.get('category')}
    Target Audience: {brief.get('audience')}
    Writing Tone: {brief.get('tone')}
    Target Total Words: {brief.get('est_words')}
    
    INSTRUCTIONS:
    - Write deep, comprehensive, and engaging content.
    - Format output in Clean Markdown (using #, ##, **, -, etc.).
    - Use the specified tone and write directly to the target audience.
    - DO NOT include placeholder text, greetings, or meta-commentary (like 'Here is the chapter'). 
    - Just output the raw markdown chapter text so it can be directly compiled into the book.
    """

def _build_chapter_prompt(chapter: dict) -> str:
    """Build the prompt for a specific chapter."""
    return f"""Write the complete content for the following chapter:

    CHAPTER: {chapter['title']}
    FOCUS POINTS: {chapter.get('focus', 'General topics')}
    
    Ensure this chapter is long, detailed, and explores all the focus points thoroughly.
    Format the chapter with markdown headings, subheadings, bullet points, and paragraphs.
    Start directly with the content.
    """

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(RateLimitError),
    before_sleep=lambda retry_state: print(f"  {Fore.YELLOW}Rate limited by Groq! Retrying in {retry_state.next_action.sleep}s...{Style.RESET_ALL}")
)
def _generate_text_with_groq(system_prompt: str, user_prompt: str) -> str:
    """Generate text using Groq with automatic retry for rate limits."""
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.7,
        max_completion_tokens=4000,
        top_p=1,
        stream=False,
    )
    return completion.choices[0].message.content

def generate_content(brief: dict) -> dict:
    """Generate the content for all chapters using the Groq API."""
    print(f"\n{Fore.CYAN}============================================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  [STAGE 2] Groq Content Generator{Style.RESET_ALL}")
    print(f"{Fore.CYAN}============================================================{Style.RESET_ALL}")

    chapters = brief.get("chapters", [])
    if not chapters:
        print(f"{Fore.RED}  [ERROR] No chapters found in brief!{Style.RESET_ALL}")
        return brief
        
    print(f"  {Fore.YELLOW}Generating {len(chapters)} chapters via Groq (llama-3.1-8b-instant)...{Style.RESET_ALL}")
    
    system_prompt = _build_system_prompt(brief)
    
    for i, chapter in enumerate(chapters):
        print(f"\n  {Fore.BLUE}Processing Chapter {i+1}/{len(chapters)}: {chapter['title']}{Style.RESET_ALL}")
        user_prompt = _build_chapter_prompt(chapter)
        
        try:
            print(f"  {Fore.YELLOW}Writing content...{Style.RESET_ALL}")
            content = _generate_text_with_groq(system_prompt, user_prompt)
            
            # Save the generated content back to the chapter object
            chapter["content"] = content
            print(f"  {Fore.GREEN}[✓] Chapter {i+1} completed! ({len(content.split())} words){Style.RESET_ALL}")
            
            # Brief pause to respect API limits if not already handled by tenacity
            if i < len(chapters) - 1:
                print(f"  {Fore.YELLOW}Waiting 50 seconds before next chapter to respect Groq rate limits...{Style.RESET_ALL}")
                time.sleep(50)
            
        except Exception as e:
            print(f"  {Fore.RED}[ERROR] Failed to generate chapter {i+1}: {str(e)}{Style.RESET_ALL}")
            chapter["content"] = f"# {chapter['title']}\n\n*Content generation failed for this chapter.*"
            
    print(f"\n  {Fore.GREEN}[✓] Content generation complete!{Style.RESET_ALL}")
    
    # Save the updated brief with content
    out_dir = Path(brief.get("output_dir", "."))
    content_file = out_dir / "content.json"
    
    with open(content_file, "w", encoding="utf-8") as f:
        json.dump(brief, f, indent=4)
        
    print(f"  {Fore.GREEN}[SAVE] Content -> {content_file}{Style.RESET_ALL}")
    
    return brief
