# -*- coding: utf-8 -*-
"""
main.py — eBook Generator Pipeline Orchestrator

Runs all 4 stages sequentially:
  Stage 1: Categorizer   → generates ebook brief
  Stage 2: ChatGPT       → generates content via Playwright
  Stage 3: Gemini         → generates images via Playwright
  Stage 4: PDF Builder    → assembles final PDF

Usage:
  python main.py                                         # Random category
  python main.py --category how_to_guides                # Specific category
  python main.py --topic "How to Start Dropshipping"     # Specific topic
  python main.py --audience beginner --tone conversational
  python main.py --list-categories                       # Show all categories
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from colorama import Fore, Style, init

# Force UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

init(autoreset=True)

# Add current dir to path
sys.path.insert(0, str(Path(__file__).parent))

from categories import list_categories, select_category
from categorizer import run_categorizer
from content_generator import generate_content
from image_generator import generate_images
from pdf_builder import build_pdf
from trend_finder import find_trending_topic

OUTPUT_BASE = Path(__file__).parent / "output" / "ebooks"


def run_pipeline(
    category_key: str = None,
    topic: str = None,
    audience: str = None,
    tone: str = None,
) -> Path:
    """
    Execute the full eBook generation pipeline.
    Returns the path to the generated PDF.
    """
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    print(f"\n{'━'*60}")
    print(f"  {Fore.CYAN}╔══════════════════════════════════════════╗{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}║   eBook Generator Pipeline — Agent 5     ║{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}╚══════════════════════════════════════════╝{Style.RESET_ALL}")
    print(f"{'━'*60}\n")

    # ── STAGE 0: TRENDING TOPIC FINDER ───────────────────────
    if not topic:
        cat = select_category(category_key)
        category_key = cat["key"]
        aud = audience or "beginner"
        topic = find_trending_topic(cat["label"], aud)

    # ── STAGE 1: CATEGORIZER ─────────────────────────────────
    brief = run_categorizer(
        category_key=category_key,
        topic=topic,
        audience=audience,
        tone=tone,
    )

    # Create output directory
    import re
    safe_title = re.sub(r'[^\w\s-]', '', brief["title"]).strip().replace(" ", "_")[:40]
    output_dir = OUTPUT_BASE / f"{timestamp}_{safe_title}"
    output_dir.mkdir(parents=True, exist_ok=True)
    brief["output_dir"] = str(output_dir)

    # Save brief
    brief_file = output_dir / "brief.json"
    brief_file.write_text(json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  {Fore.CYAN}[SAVE] Brief → {brief_file}{Style.RESET_ALL}")

    # ── STAGE 2: CHATGPT CONTENT ─────────────────────────────
    content_result = generate_content(brief)
    
    # ── STAGE 3: GEMINI IMAGES ───────────────────────────────
    images_result = generate_images(content_result)

    # Save images manifest
    img_manifest = output_dir / "images_manifest.json"
    img_manifest.write_text(json.dumps(images_result, indent=2), encoding="utf-8")

    # ── STAGE 4: PDF BUILDER ─────────────────────────────────
    pdf_path = build_pdf(content_result, images_result, output_dir, brief)

    # ── SUMMARY ──────────────────────────────────────────────
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print(f"\n{'━'*60}")
    print(f"  {Fore.GREEN}╔══════════════════════════════════════════╗{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}║   PIPELINE COMPLETE ✓                    ║{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}╚══════════════════════════════════════════╝{Style.RESET_ALL}")
    print(f"\n  {Fore.YELLOW}Title:{Style.RESET_ALL}      {brief['title']}")
    print(f"  {Fore.YELLOW}Category:{Style.RESET_ALL}   {brief['category']}")
    print(f"  {Fore.YELLOW}Chapters:{Style.RESET_ALL}   {len(content_result['chapters'])}")
    print(f"  {Fore.YELLOW}Words:{Style.RESET_ALL}      ~{content_result['total_words']:,}")
    print(f"  {Fore.YELLOW}Images:{Style.RESET_ALL}     {1 + len(images_result.get('chapter_images', {}))}")
    print(f"  {Fore.YELLOW}Time:{Style.RESET_ALL}       {minutes}m {seconds}s")
    print(f"  {Fore.YELLOW}Output:{Style.RESET_ALL}     {output_dir}")
    print(f"  {Fore.GREEN}PDF:{Style.RESET_ALL}        {pdf_path}")
    print(f"{'━'*60}\n")

    return pdf_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="eBook Generator Pipeline (Agent 5)")
    parser.add_argument("--category", type=str, default=None, help="Category key (e.g. how_to_guides)")
    parser.add_argument("--topic", type=str, default=None, help="Specific ebook topic/title")
    parser.add_argument("--audience", type=str, default=None, help="Target audience: beginner, intermediate, expert, parent, student")
    parser.add_argument("--tone", type=str, default=None, help="Writing tone: professional, conversational, motivational, academic, friendly")
    parser.add_argument("--list-categories", action="store_true", help="List all available categories and exit")

    args = parser.parse_args()

    if args.list_categories:
        print(f"\n  {Fore.CYAN}Available eBook Categories:{Style.RESET_ALL}\n")
        for cat in list_categories():
            print(f"    {Fore.GREEN}{cat['key']:30s}{Style.RESET_ALL} → {cat['label']}")
            print(f"    {'':30s}   {Fore.WHITE}{cat['description']}{Style.RESET_ALL}\n")
        sys.exit(0)

    run_pipeline(
        category_key=args.category,
        topic=args.topic,
        audience=args.audience,
        tone=args.tone,
    )
