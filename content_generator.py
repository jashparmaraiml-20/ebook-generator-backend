# -*- coding: utf-8 -*-
"""
content_generator.py — Stage 2: ChatGPT eBook Content Generator (Playwright)

Opens ChatGPT via Playwright browser automation, sends a detailed meta-prompt
based on the ebook brief, and extracts the full ebook content chapter-by-chapter.

Reuses login/session patterns from agent2_gemini_image/chatgpt_bot.py.
Uses a separate session directory to avoid conflicts.
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright, Page, BrowserContext
from colorama import Fore, Style
from dotenv import load_dotenv

load_dotenv()

# Session stored separately from agent2
SESSION_DIR = str(Path(__file__).parent / "session_chatgpt")
CHATGPT_URL = "https://chatgpt.com/"
RESPONSE_TIMEOUT = 180  # 3 minutes per chapter


# =============================================================
# LOGIN HELPERS (mirrors agent2/chatgpt_bot.py)
# =============================================================

async def _is_on_chatgpt(page: Page) -> bool:
    """True if we are on ChatGPT and NOT on a login/auth page."""
    await page.wait_for_timeout(2000)
    url = page.url.lower()

    if "auth" in url or "login" in url or "accounts.google" in url:
        return False

    for sel in ['button:has-text("Log in")', 'a:has-text("Log in")', '[data-testid="login-button"]']:
        try:
            if await page.locator(sel).first.is_visible(timeout=1000):
                return False
        except Exception:
            continue

    try:
        box = page.locator('#prompt-textarea, textarea[placeholder*="Message" i]').first
        if await box.is_visible(timeout=2000):
            return True
    except Exception:
        pass

    return False


async def _handle_chatgpt_login(page: Page, email: str, password: str):
    """Handle ChatGPT login with Google SSO and manual fallback."""
    print(f"  {Fore.YELLOW}[GPT-LOGIN] ChatGPT login required...{Style.RESET_ALL}")

    # Click "Log in" button
    for sel in ['button:has-text("Log in")', 'a:has-text("Log in")', '[data-testid="login-button"]']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await page.wait_for_timeout(3000)
                break
        except Exception:
            continue

    # Strategy 1: Continue with Google
    try:
        google_btn = page.locator('button:has-text("Continue with Google")').first
        if await google_btn.is_visible(timeout=5000):
            print(f"  {Fore.CYAN}[GPT-LOGIN] Clicking 'Continue with Google'...{Style.RESET_ALL}")
            await google_btn.click()
            await page.wait_for_timeout(3000)

            try:
                account = page.locator(f'[data-email="{email}"]').first
                if await account.is_visible(timeout=5000):
                    await account.click()
                    await page.wait_for_timeout(3000)
            except Exception:
                try:
                    email_field = page.locator('input[type="email"]')
                    if await email_field.is_visible(timeout=3000):
                        await email_field.fill(email)
                        await page.keyboard.press("Enter")
                        await page.wait_for_timeout(3000)
                        pwd_field = page.locator('input[type="password"]')
                        if await pwd_field.is_visible(timeout=5000):
                            await pwd_field.fill(password)
                            await page.keyboard.press("Enter")
                            await page.wait_for_timeout(5000)
                except Exception:
                    pass

            try:
                await page.wait_for_url("**/chatgpt.com/**", timeout=30000)
                print(f"  {Fore.GREEN}[GPT-LOGIN] Google login complete!{Style.RESET_ALL}")
                return
            except Exception:
                pass
    except Exception:
        pass

    # Strategy 2: Email/password
    try:
        email_field = page.locator('input[name="email"], input[name="username"], input[type="email"]').first
        if await email_field.is_visible(timeout=3000):
            await email_field.fill(email)
            await page.wait_for_timeout(500)
            for sel in ['button:has-text("Continue")', 'button[type="submit"]']:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        break
                except Exception:
                    continue
            await page.wait_for_timeout(3000)
            pwd_field = page.locator('input[type="password"]').first
            if await pwd_field.is_visible(timeout=5000):
                await pwd_field.fill(password)
                for sel in ['button:has-text("Continue")', 'button[type="submit"]']:
                    try:
                        btn = page.locator(sel).first
                        if await btn.is_visible(timeout=2000):
                            await btn.click()
                            break
                    except Exception:
                        continue
            await page.wait_for_timeout(5000)
            if await _is_on_chatgpt(page):
                return
    except Exception:
        pass

    # Strategy 3: Manual login fallback
    print(f"\n  {Fore.RED}[GPT-LOGIN] ╔══════════════════════════════════════════════╗{Style.RESET_ALL}")
    print(f"  {Fore.RED}[GPT-LOGIN] ║  ACTION REQUIRED: MANUAL LOGIN               ║{Style.RESET_ALL}")
    print(f"  {Fore.RED}[GPT-LOGIN] ║  Please log into ChatGPT in the open browser ║{Style.RESET_ALL}")
    print(f"  {Fore.RED}[GPT-LOGIN] ║  You have 2 minutes to complete this.        ║{Style.RESET_ALL}")
    print(f"  {Fore.RED}[GPT-LOGIN] ╚══════════════════════════════════════════════╝{Style.RESET_ALL}\n")

    for _ in range(24):
        await page.wait_for_timeout(5000)
        if await _is_on_chatgpt(page):
            print(f"  {Fore.GREEN}[GPT-LOGIN] Login detected!{Style.RESET_ALL}")
            return

    raise RuntimeError("ChatGPT manual login timed out.")


async def _ensure_on_chatgpt(page: Page, email: str, password: str):
    """Navigate to ChatGPT; login if needed."""
    await page.goto(CHATGPT_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    if not await _is_on_chatgpt(page):
        await _handle_chatgpt_login(page, email, password)
        if not await _is_on_chatgpt(page):
            await page.goto(CHATGPT_URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

    if not await _is_on_chatgpt(page):
        raise RuntimeError(f"Could not reach ChatGPT. URL: {page.url}")

    print(f"  {Fore.GREEN}[GPT] On ChatGPT!{Style.RESET_ALL}")

    # Dismiss popups
    for sel in ['button:has-text("Okay")', 'button:has-text("Got it")',
                'button:has-text("Dismiss")', 'button:has-text("No thanks")',
                '[aria-label="Close"]']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=1000):
                await btn.click()
                await page.wait_for_timeout(500)
        except Exception:
            pass


# =============================================================
# CHAT INTERACTION
# =============================================================

async def _find_input_box(page: Page):
    """Find the ChatGPT message input area."""
    selectors = [
        '#prompt-textarea',
        'div[contenteditable="true"][id="prompt-textarea"]',
        'textarea[placeholder*="Message" i]',
        'div[contenteditable="true"]',
        'textarea',
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            await el.wait_for(state="visible", timeout=8000)
            return el
        except Exception:
            continue
    raise RuntimeError("Cannot find ChatGPT input box.")


async def _send_and_wait(page: Page, message: str, timeout: int = RESPONSE_TIMEOUT) -> str:
    """Send a message to ChatGPT, wait for response, extract text."""
    box = await _find_input_box(page)
    await box.click()
    await page.wait_for_timeout(300)

    try:
        await box.fill(message)
    except Exception:
        await box.type(message, delay=10)

    await page.wait_for_timeout(500)

    # Submit
    sent = False
    for sel in ['button[data-testid="send-button"]', 'button[aria-label="Send prompt"]',
                'button[aria-label*="Send" i]']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                sent = True
                break
        except Exception:
            continue

    if not sent:
        await page.keyboard.press("Enter")

    print(f"    {Fore.CYAN}[GPT] Message sent. Waiting for response...{Style.RESET_ALL}")

    # Wait for response to complete
    await page.wait_for_timeout(3000)

    start = time.time()
    while time.time() - start < timeout:
        still_typing = False
        for sel in ['button[aria-label*="Stop" i]', 'button:has-text("Stop")',
                    '[data-testid="stop-button"]']:
            try:
                if await page.locator(sel).first.is_visible(timeout=500):
                    still_typing = True
                    break
            except Exception:
                pass

        if still_typing:
            elapsed = int(time.time() - start)
            print(f"    {Fore.CYAN}[GPT] Generating... ({elapsed}s){Style.RESET_ALL}", end="\r")
            await page.wait_for_timeout(2000)
            continue
        break

    await page.wait_for_timeout(1500)

    # Extract response
    response_selectors = [
        '[data-message-author-role="assistant"] .markdown',
        '[data-message-author-role="assistant"]',
        '.agent-turn .markdown',
        '.agent-turn',
        'div[class*="markdown"]',
    ]

    response_text = ""
    for sel in response_selectors:
        try:
            msgs = page.locator(sel)
            count = await msgs.count()
            if count > 0:
                last_msg = msgs.nth(count - 1)
                response_text = (await last_msg.inner_text()).strip()
                if response_text:
                    break
        except Exception:
            continue

    if not response_text:
        print(f"    {Fore.RED}[GPT] WARNING: Could not extract response.{Style.RESET_ALL}")

    return response_text


async def _start_new_chat(page: Page):
    """Click New Chat to start fresh."""
    for sel in ['a[href="/"]', 'nav a:has-text("New chat")',
                'button:has-text("New chat")', '[data-testid="create-new-chat-button"]']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                await page.wait_for_timeout(2000)
                return
        except Exception:
            continue


# =============================================================
# CONTENT GENERATION
# =============================================================

def _build_system_prompt(brief: dict) -> str:
    """Build the initial system/meta prompt for ChatGPT."""
    chapters_list = "\n".join([
        f"  Chapter {ch['number']}: {ch['title']} — {ch['focus']}"
        for ch in brief["chapters"]
    ])

    return f"""You are a professional eBook writer and content creator. I need you to write a complete eBook.

**eBook Details:**
- Title: "{brief['title']}"
- Subtitle: "{brief['subtitle']}"
- Category: {brief['category']}
- Target Audience: {brief['audience'].title()} level
- Tone: {brief['tone'].title()}
- Total Chapters: {brief['num_chapters']}

**Chapter Outline:**
{chapters_list}

**Writing Rules:**
1. Write in a {brief['tone']} tone appropriate for {brief['audience']} readers.
2. Each chapter should be approximately {brief['words_per_chapter']} words.
3. Use markdown formatting with proper headings (## for chapter titles, ### for sections).
4. Include practical examples, actionable tips, and real-world applications.
5. Add bullet points, numbered lists, and callout boxes where appropriate.
6. End each chapter with a "Key Takeaways" section.
7. Make the content engaging, informative, and immediately actionable.

I will ask you to write each chapter one at a time. Start with the Introduction.

**Now write Chapter 1: {brief['chapters'][0]['title']}**

Focus: {brief['chapters'][0]['focus']}
Target length: ~{brief['words_per_chapter']} words.

Write ONLY the chapter content in markdown. Do not include any meta-commentary."""


def _build_chapter_prompt(chapter: dict) -> str:
    """Build prompt for subsequent chapters."""
    return f"""Continue with the next chapter of the eBook.

**Now write Chapter {chapter['number']}: {chapter['title']}**

Focus: {chapter['focus']}
Target length: ~{chapter['target_words']} words.

Continue in the same tone and style. Write ONLY the chapter content in markdown. Do not repeat any previous content or add meta-commentary."""


async def generate_content(brief: dict) -> dict:
    """
    Generate full eBook content using ChatGPT via Playwright.

    Args:
        brief: The ebook brief from Stage 1 categorizer.

    Returns:
        Dict with chapters list containing content for each chapter.
    """
    email = os.getenv("CHATGPT_EMAIL", "")
    password = os.getenv("CHATGPT_PASSWORD", "")

    if not email:
        raise RuntimeError("CHATGPT_EMAIL not set in .env")

    Path(SESSION_DIR).mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  {Fore.CYAN}[STAGE 2] ChatGPT Content Generator{Style.RESET_ALL}")
    print(f"{'='*60}")
    print(f"  {Fore.YELLOW}Generating {brief['num_chapters']} chapters via ChatGPT...{Style.RESET_ALL}\n")

    all_chapters = []

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

        # Login
        await _ensure_on_chatgpt(page, email, password)

        # Start new chat
        await _start_new_chat(page)

        # Generate each chapter
        for i, chapter in enumerate(brief["chapters"]):
            chapter_num = chapter["number"]
            chapter_title = chapter["title"]

            print(f"\n  {Fore.YELLOW}[Ch {chapter_num}/{brief['num_chapters']}] {chapter_title}{Style.RESET_ALL}")

            if i == 0:
                prompt = _build_system_prompt(brief)
            else:
                prompt = _build_chapter_prompt(chapter)

            content = await _send_and_wait(page, prompt)

            if content:
                word_count = len(content.split())
                print(f"  {Fore.GREEN}[✓] Chapter {chapter_num} generated — {word_count:,} words{Style.RESET_ALL}")
            else:
                print(f"  {Fore.RED}[✗] Chapter {chapter_num} — no content extracted{Style.RESET_ALL}")
                content = f"## {chapter_title}\n\n*Content generation failed for this chapter.*\n"

            all_chapters.append({
                "number": chapter_num,
                "title": chapter_title,
                "content": content,
                "word_count": len(content.split()),
            })

            # Small delay between chapters
            if i < len(brief["chapters"]) - 1:
                await page.wait_for_timeout(2000)

        await context.close()

    # Combine into full ebook markdown
    total_words = sum(ch["word_count"] for ch in all_chapters)
    print(f"\n  {Fore.GREEN}[✓] All {len(all_chapters)} chapters generated — {total_words:,} total words{Style.RESET_ALL}")

    return {
        "title": brief["title"],
        "subtitle": brief["subtitle"],
        "chapters": all_chapters,
        "total_words": total_words,
    }


def save_content(content_result: dict, output_dir: Path) -> Path:
    """Save generated content as a markdown file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    md_file = output_dir / "content.md"

    lines = []
    lines.append(f"# {content_result['title']}\n")
    lines.append(f"*{content_result['subtitle']}*\n")
    lines.append("---\n")

    # Table of Contents
    lines.append("## Table of Contents\n")
    for ch in content_result["chapters"]:
        lines.append(f"{ch['number']}. {ch['title']}")
    lines.append("\n---\n")

    # Chapters
    for ch in content_result["chapters"]:
        lines.append(f"\n{ch['content']}\n")
        lines.append("\n---\n")

    md_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"  {Fore.CYAN}[SAVE] Content saved → {md_file}{Style.RESET_ALL}")
    return md_file


if __name__ == "__main__":
    # Quick test with a sample brief
    from categorizer import run_categorizer
    brief = run_categorizer(
        category_key="how_to_guides",
        topic="How to Start a Side Hustle in 2025",
        audience="beginner",
        tone="conversational",
    )
    result = asyncio.run(generate_content(brief))
    save_content(result, Path("output/test_ebook"))
