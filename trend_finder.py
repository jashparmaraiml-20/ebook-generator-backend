import os
from colorama import Fore, Style
from dotenv import load_dotenv

try:
    from groq import Groq
except ImportError:
    pass

load_dotenv()

def find_trending_topic(category_label: str, audience: str) -> str:
    """
    Ask Groq for a single highly trending eBook topic.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        print(f"{Fore.RED}GROQ_API_KEY not set in .env{Style.RESET_ALL}")
        return "The Ultimate Guide to Digital Success"

    print(f"\n{'='*60}")
    print(f"  {Fore.CYAN}[STAGE 0] Trending Topic Finder{Style.RESET_ALL}")
    print(f"{'='*60}")
    print(f"  {Fore.YELLOW}Asking Groq for a trending '{category_label}' topic...{Style.RESET_ALL}\n")

    topic = "The Ultimate Guide to Digital Success" # Fallback

    try:
        client = Groq(api_key=api_key)
        
        prompt = f"""You are an expert market researcher and publisher. 
I want to write an eBook in the "{category_label}" category, targeting a {audience} audience.
What is the single most highly trending, profitable, and high-demand specific eBook topic/title I could write about right now?

Respond ONLY with the exact title of the book. Do not include any quotes, markdown, explanations, or extra text. Just the title."""

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8,
            max_completion_tokens=50,
            top_p=1,
            stream=False,
        )
        
        response = completion.choices[0].message.content
        if response:
            clean_topic = response.strip().strip('"').strip("'").split('\n')[0].strip()
            if clean_topic:
                topic = clean_topic
                print(f"  {Fore.GREEN}[✓] Found Trending Topic: {topic}{Style.RESET_ALL}")
                
    except Exception as e:
        print(f"  {Fore.RED}[✗] Error finding trend with Groq: {e}{Style.RESET_ALL}")

    return topic

if __name__ == "__main__":
    t = find_trending_topic("How-To & Step-by-Step Guides", "beginner")
    print(f"Result: {t}")
