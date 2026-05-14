# -*- coding: utf-8 -*-
"""
image_generator.py — Stage 3: Gemini eBook Image Generator (Playwright)

Opens Gemini via Playwright browser automation to generate:
  - 1 professional cover image for the ebook
  - 1 illustration per chapter

Reuses login/session patterns from agent2_gemini_image/gemini_bot.py.
Uses a separate session directory to avoid conflicts.
"""

import asyncio
import os
import shutil
import time
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright, Page, BrowserContext, Response
from colorama import Fore, Style
from dotenv import load_dotenv

load_dotenv()

SESSION_DIR = str(Path(__file__).parent / "session_gemini")
GEMINI_URL = "https://gemini.google.com/"
GENERATION_TIMEOUT = 300  # 5 minutes per image


# =============================================================
# LOGIN (mirrors agent2/gemini_bot.py)
# =============================================================

async def _is_on_gemini(page: Page) -> bool:
    """True if we are on Gemini and NOT on a login page."""
    await page.wait_for_timeout(3000)
    url = page.url
    return (
        "gemini.google.com" in url
        and "accounts.google" not in url
        and "signin" not in url
    )


async def _do_google_login(page: Page, email: str, password: str):
    """Full Google email → password login with 2FA pause support."""
    print(f"  {Fore.YELLOW}[LOGIN] Navigating to Google sign-in...{Style.RESET_ALL}")
    await page.goto(
        "https://accounts.google.com/signin/v2/identifier",
        wait_until="domcontentloaded",
    )
    await page.wait_for_timeout(2000)

    email_field = page.locator('input[type="email"]')
    await email_field.wait_for(state="visible", timeout=20000)
    await email_field.click()
    await email_field.fill(email)
    await page.wait_for_timeout(800)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(3000)

    pwd_field = page.locator('input[type="password"]')
    await pwd_field.wait_for(state="visible", timeout=20000)
    await pwd_field.click()
    await pwd_field.fill(password)
    await page.wait_for_timeout(800)
    await page.keyboard.press("Enter")

    print(f"  {Fore.CYAN}[LOGIN] Credentials submitted. Waiting for redirect...{Style.RESET_ALL}")
    try:
        await page.wait_for_url("**/gemini.google.com/**", timeout=40000)
        print(f"  {Fore.GREEN}[LOGIN] Logged in!{Style.RESET_ALL}")
    except Exception:
        if "accounts.google" in page.url:
            print(f"\n  {Fore.RED}[2FA] Approve on your phone or enter OTP. Waiting 90s...{Style.RESET_ALL}")
            try:
                await page.wait_for_url("**/gemini.google.com/**", timeout=90000)
                print(f"  {Fore.GREEN}[LOGIN] 2FA completed!{Style.RESET_ALL}")
            except Exception:
                raise RuntimeError("Login failed / timed out.")


async def _ensure_logged_in(page: Page, email: str, password: str):
    """Navigate to Gemini, login if needed."""
    await page.goto(GEMINI_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    if not await _is_on_gemini(page):
        await _do_google_login(page, email, password)
        await page.goto(GEMINI_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

    if not await _is_on_gemini(page):
        raise RuntimeError(f"Could not reach Gemini. URL: {page.url}")

    print(f"  {Fore.GREEN}[OK] On Gemini!{Style.RESET_ALL}")


# =============================================================
# MODEL SELECTION
# =============================================================

async def _select_model(page: Page):
    """Switch to best available model for image generation."""
    print(f"  {Fore.CYAN}[MODEL] Selecting model...{Style.RESET_ALL}")

    for sel in ['bard-mode-switcher button', 'button[aria-label*="model" i]', 'button[aria-label*="Gemini" i]']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await page.wait_for_timeout(1500)
                break
        except Exception:
            continue

    for name in ["2.0 Flash", "2.0 Pro", "1.5 Pro", "Gemini Pro", "Pro"]:
        try:
            opt = page.get_by_text(name, exact=False).first
            if await opt.is_visible(timeout=2000):
                await opt.click()
                await page.wait_for_timeout(1500)
                print(f"  {Fore.GREEN}[MODEL] Selected: {name}{Style.RESET_ALL}")
                return
        except Exception:
            continue

    print(f"  {Fore.YELLOW}[MODEL] Using default model.{Style.RESET_ALL}")
    try:
        await page.keyboard.press("Escape")
    except Exception:
        pass


# =============================================================
# SUBMIT PROMPT
# =============================================================

async def _send_prompt(page: Page, prompt: str):
    """Type prompt into Gemini and submit."""
    input_selectors = [
        "rich-textarea div[contenteditable='true']",
        "div[contenteditable='true'][aria-label*='message' i]",
        "div[contenteditable='true'][aria-label*='prompt' i]",
        "div[contenteditable='true']",
        "textarea",
    ]

    box = None
    for sel in input_selectors:
        try:
            el = page.locator(sel).first
            await el.wait_for(state="visible", timeout=6000)
            box = el
            break
        except Exception:
            continue

    if not box:
        raise RuntimeError("Cannot find Gemini chat input.")

    await box.click()
    await page.wait_for_timeout(400)
    await page.keyboard.insert_text(prompt)
    await page.wait_for_timeout(600)

    sent = False
    for sel in ['button[aria-label*="send" i]', 'button[aria-label*="submit" i]', 'button[mattooltip*="Send" i]']:
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


# =============================================================
# WAIT + CAPTURE IMAGES VIA NETWORK INTERCEPTION
# =============================================================

async def _wait_and_capture_single(page: Page, out_path: Path) -> bool:
    """
    Wait for Gemini to generate an image and capture it via network interception.
    Saves the FIRST large image to out_path.
    Returns True if an image was captured.
    """
    captured = []

    async def on_response(response: Response):
        try:
            url = response.url
            ct = response.headers.get("content-type", "")

            is_image_url = (
                "googleusercontent.com" in url
                or "aia.googleapis.com" in url
                or "generativelanguage.googleapis.com" in url
            )
            is_ui_asset = "gstatic.com" in url or "google.com/images" in url
            is_image_ct = ct.startswith("image/") and "svg" not in ct

            if is_image_url and is_image_ct and not is_ui_asset:
                body = await response.body()
                if len(body) >= 50000:  # Skip tiny UI icons
                    captured.append(body)
        except Exception:
            pass

    page.on("response", on_response)

    start = time.time()
    while time.time() - start < GENERATION_TIMEOUT:
        await page.wait_for_timeout(3000)

        still_running = False
        for sel in ['button[aria-label*="Stop" i]', 'button[title*="Stop" i]', 'button:has-text("Stop")']:
            try:
                if await page.locator(sel).first.is_visible(timeout=500):
                    still_running = True
                    break
            except Exception:
                pass

        if still_running:
            elapsed = int(time.time() - start)
            print(f"    {Fore.CYAN}[WAIT] Generating... ({elapsed}s) — captured: {len(captured)}{Style.RESET_ALL}", end="\r")
            continue

        await page.wait_for_timeout(2000)
        break

    # Save the best (largest) captured image
    if captured:
        best = max(captured, key=len)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(best)
        print(f"    {Fore.GREEN}[✓] Image saved: {out_path.name} ({len(best)//1024} KB){Style.RESET_ALL}")
        return True

    print(f"    {Fore.RED}[✗] No image captured via network.{Style.RESET_ALL}")
    return False


async def _start_new_chat(page: Page):
    """Start a fresh Gemini chat."""
    for sel in ['a[href*="gemini.google.com"]', 'button[aria-label*="New chat" i]',
                'button:has-text("New chat")', 'a:has-text("New chat")']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                await page.wait_for_timeout(2000)
                return
        except Exception:
            continue

    # Fallback: navigate to Gemini homepage
    await page.goto(GEMINI_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)


# =============================================================
# PROMPT BUILDERS
# =============================================================

def _cover_prompt(title: str, subtitle: str, category: str) -> str:
    """Build a prompt for generating the ebook cover image."""
    return (
        f"Generate a professional, modern eBook cover image. "
        f"The book is titled \"{title}\" with subtitle \"{subtitle}\". "
        f"Category: {category}. "
        f"Style: Clean, premium design with bold typography, gradient background, "
        f"abstract geometric elements, and a sophisticated color palette. "
        f"The design should look like a bestselling digital product cover. "
        f"No actual text on the image — just the visual design/artwork. "
        f"High resolution, 1600x2400 aspect ratio (portrait book cover)."
    )


def _chapter_prompt(chapter_title: str, chapter_focus: str, book_title: str) -> str:
    """Build a prompt for generating a chapter illustration."""
    return (
        f"Generate a professional illustration for a book chapter. "
        f"Book: \"{book_title}\". "
        f"Chapter: \"{chapter_title}\". "
        f"Theme: {chapter_focus}. "
        f"Style: Modern, clean digital illustration with a cohesive color palette. "
        f"Abstract or semi-realistic, suitable for a professional eBook interior. "
        f"Horizontal landscape format. No text in the image."
    )


# =============================================================
# PUBLIC API
# =============================================================

async def generate_images(brief: dict, output_dir: Path) -> dict:
    """
    Generate cover and chapter images using Gemini via Playwright.

    Args:
        brief: The ebook brief from Stage 1.
        output_dir: Directory to save images.

    Returns:
        Dict with cover_image and chapter_images paths.
    """
    email = os.getenv("GOOGLE_EMAIL", "")
    password = os.getenv("GOOGLE_PASSWORD", "")

    if not email:
        raise RuntimeError("GOOGLE_EMAIL not set in .env")

    Path(SESSION_DIR).mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  {Fore.CYAN}[STAGE 3] Gemini Image Generator{Style.RESET_ALL}")
    print(f"{'='*60}")

    total_images = 1 + len(brief["chapters"])  # cover + chapters
    print(f"  {Fore.YELLOW}Generating {total_images} images via Gemini...{Style.RESET_ALL}\n")

    result = {
        "cover_image": None,
        "chapter_images": {},
    }

    async with async_playwright() as p:
        context: BrowserContext = await p.chromium.launch_persistent_context(
            SESSION_DIR,
            headless=True,
            slow_mo=50,
            accept_downloads=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
            viewport={"width": 1366, "height": 768},
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
        await _ensure_logged_in(page, email, password)

        # Select model
        await _select_model(page)

        # ── Generate Cover Image ──────────────────────────────────────
        print(f"\n  {Fore.YELLOW}[1/{total_images}] Generating cover image...{Style.RESET_ALL}")
        cover_prompt = _cover_prompt(brief["title"], brief["subtitle"], brief["category"])
        cover_path = images_dir / "cover.png"

        await _send_prompt(page, cover_prompt)
        if await _wait_and_capture_single(page, cover_path):
            result["cover_image"] = str(cover_path)
        else:
            # Take screenshot as fallback
            fallback = images_dir / "cover_fallback.png"
            await page.screenshot(path=str(fallback), full_page=True)
            result["cover_image"] = str(fallback)
            print(f"    {Fore.YELLOW}[!] Using screenshot as fallback cover.{Style.RESET_ALL}")

        # ── Generate Chapter Images ───────────────────────────────────
        for i, chapter in enumerate(brief["chapters"]):
            img_num = i + 2  # 1-indexed, cover was #1
            ch_num = chapter["number"]

            print(f"\n  {Fore.YELLOW}[{img_num}/{total_images}] Ch {ch_num}: {chapter['title']}{Style.RESET_ALL}")

            # Start new chat for each image to avoid context confusion
            await _start_new_chat(page)
            await page.wait_for_timeout(2000)

            ch_prompt = _chapter_prompt(chapter["title"], chapter["focus"], brief["title"])
            ch_path = images_dir / f"chapter_{ch_num}.png"

            await _send_prompt(page, ch_prompt)
            if await _wait_and_capture_single(page, ch_path):
                result["chapter_images"][ch_num] = str(ch_path)
            else:
                print(f"    {Fore.RED}[!] No image for chapter {ch_num}.{Style.RESET_ALL}")

            # Brief pause between generations
            await page.wait_for_timeout(2000)

        await context.close()

    # Summary
    generated = 1 if result["cover_image"] else 0
    generated += len(result["chapter_images"])
    print(f"\n  {Fore.GREEN}[✓] {generated}/{total_images} images generated successfully!{Style.RESET_ALL}")

    return result


if __name__ == "__main__":
    from categorizer import run_categorizer
    brief = run_categorizer(
        category_key="how_to_guides",
        topic="How to Start a Side Hustle in 2025",
        audience="beginner",
    )
    result = asyncio.run(generate_images(brief, Path("output/test_ebook")))
    from pprint import pprint
    pprint(result)
