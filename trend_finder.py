# -*- coding: utf-8 -*-
"""
trend_finder.py — Stage 0: Trending Topic Finder
Uses ChatGPT via Playwright to autonomously find a trending, profitable
eBook topic if the user doesn't provide one.
"""

import asyncio
import os
from colorama import Fore, Style
from playwright.async_api import async_playwright, BrowserContext
from dotenv import load_dotenv

load_dotenv()

# We can reuse the ChatGPT session from content_generator
from content_generator import (
    SESSION_DIR,
    _ensure_on_chatgpt,
    _start_new_chat,
    _send_and_wait
)

async def find_trending_topic(category_label: str, audience: str) -> str:
    """
    Ask ChatGPT for a single highly trending eBook topic.
    """
    email = os.getenv("CHATGPT_EMAIL", "")
    password = os.getenv("CHATGPT_PASSWORD", "")

    if not email:
        raise RuntimeError("CHATGPT_EMAIL not set in .env")

    print(f"\n{'='*60}")
    print(f"  {Fore.CYAN}[STAGE 0] Trending Topic Finder{Style.RESET_ALL}")
    print(f"{'='*60}")
    print(f"  {Fore.YELLOW}Asking ChatGPT for a trending '{category_label}' topic...{Style.RESET_ALL}\n")

    topic = "The Ultimate Guide to Digital Success" # Fallback

    async with async_playwright() as p:
        context: BrowserContext = await p.chromium.launch_persistent_context(
            SESSION_DIR,
            headless=True,
            slow_mo=50,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
            viewport={"width": 1366, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            ignore_https_errors=True,
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = await context.new_page()

        try:
            # Login
            await _ensure_on_chatgpt(page, email, password)

            # Start new chat
            await _start_new_chat(page)

            prompt = f"""You are an expert market researcher and publisher. 
I want to write an eBook in the "{category_label}" category, targeting a {audience} audience.
What is the single most highly trending, profitable, and high-demand specific eBook topic/title I could write about right now?

Respond ONLY with the exact title of the book. Do not include any quotes, markdown, explanations, or extra text. Just the title."""

            response = await _send_and_wait(page, prompt, timeout=60)
            
            if response:
                # Clean up response (remove quotes, newlines, etc.)
                clean_topic = response.strip().strip('"').strip("'").split('\n')[0].strip()
                if clean_topic:
                    topic = clean_topic
                    print(f"  {Fore.GREEN}[✓] Found Trending Topic: {topic}{Style.RESET_ALL}")
            else:
                print(f"  {Fore.RED}[✗] Failed to get trending topic, using fallback.{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"  {Fore.RED}[✗] Error finding trend: {e}{Style.RESET_ALL}")
        finally:
            await context.close()

    return topic

if __name__ == "__main__":
    t = asyncio.run(find_trending_topic("How-To & Step-by-Step Guides", "beginner"))
    print(f"Result: {t}")
