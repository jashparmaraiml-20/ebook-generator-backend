# -*- coding: utf-8 -*-
"""
categorizer.py — Stage 1: eBook Categorizer Agent

Takes a category (or picks random) and generates a complete ebook brief
including title, audience, chapter outline, and content instructions.
This brief feeds into Stage 2 (ChatGPT content generation).
"""

from categories import generate_brief, list_categories, CATEGORIES
from colorama import Fore, Style


def build_chapter_outline(brief: dict) -> list[dict]:
    """
    Build a detailed chapter outline based on the ebook brief.
    Returns a list of chapter dicts with title, description, and key points.
    """
    category_key = brief["category_key"]
    num_chapters = brief["num_chapters"]
    topic = brief["title"]
    audience = brief["audience"]

    # Universal chapter structures by category type
    chapter_templates = {
        "how_to_guides": [
            {"title": "Introduction: Why This Matters", "focus": "Hook the reader, present the problem, preview the solution"},
            {"title": "The Foundation: Understanding the Basics", "focus": "Core concepts, terminology, mental models"},
            {"title": "Getting Started: Your First Steps", "focus": "Actionable first moves, minimal setup required"},
            {"title": "Building Momentum: Intermediate Strategies", "focus": "Level-up techniques, common pitfalls to avoid"},
            {"title": "Advanced Tactics: Scaling Your Results", "focus": "Power moves, optimization, automation"},
            {"title": "Real-World Case Studies", "focus": "Examples, success stories, lessons learned"},
            {"title": "Troubleshooting: Common Mistakes & Fixes", "focus": "FAQ, debugging common issues"},
            {"title": "Your Action Plan: Next Steps", "focus": "Summary, 30-day action plan, resources"},
        ],
        "checklists_cheat_sheets": [
            {"title": "Introduction: How to Use This Guide", "focus": "Instructions for maximum value from the checklists"},
            {"title": "Quick-Start Checklist", "focus": "Essential items to check off immediately"},
            {"title": "The Complete Reference Sheet", "focus": "Comprehensive cheat sheet with all key information"},
            {"title": "Phase 1 Checklist: Getting Set Up", "focus": "Initial setup and preparation items"},
            {"title": "Phase 2 Checklist: Execution", "focus": "Action items for implementation"},
            {"title": "Phase 3 Checklist: Optimization", "focus": "Items for refining and improving"},
            {"title": "Emergency Quick-Reference", "focus": "At-a-glance solutions for common problems"},
            {"title": "Master Tracking Sheet", "focus": "Overall progress tracking and accountability"},
        ],
        "frameworks_roadmaps": [
            {"title": "The Big Picture: Where You're Headed", "focus": "Vision, goals, and the end state"},
            {"title": "The Framework Overview", "focus": "High-level framework with all components explained"},
            {"title": "Phase 1: Foundation (Days 1-30)", "focus": "First month milestones and activities"},
            {"title": "Phase 2: Building (Days 31-60)", "focus": "Second month growth and scaling"},
            {"title": "Phase 3: Acceleration (Days 61-90)", "focus": "Third month optimization and results"},
            {"title": "Key Metrics & Milestones", "focus": "How to measure progress and success"},
            {"title": "Adapting the Framework to Your Situation", "focus": "Customization tips for different contexts"},
            {"title": "Resources & Tools", "focus": "Recommended tools, templates, and further reading"},
        ],
        "mini_courses": [
            {"title": "Welcome & Course Overview", "focus": "What you'll learn, prerequisites, and expectations"},
            {"title": "Module 1: Core Fundamentals", "focus": "Essential theory and foundational knowledge"},
            {"title": "Module 2: Hands-On Practice", "focus": "Practical exercises and guided activities"},
            {"title": "Module 3: Deepening Your Skills", "focus": "Intermediate techniques and applications"},
            {"title": "Module 4: Real-World Application", "focus": "Applying skills to real scenarios"},
            {"title": "Module 5: Advanced Techniques", "focus": "Expert-level strategies and insights"},
            {"title": "Final Project & Assessment", "focus": "Capstone project to cement learning"},
            {"title": "Next Steps & Continued Learning", "focus": "Resources for ongoing development"},
        ],
    }

    # Use matching template or default to how_to_guides structure
    template = chapter_templates.get(category_key, chapter_templates["how_to_guides"])

    # Trim to requested number of chapters
    chapters = template[:num_chapters]

    # Enrich each chapter with context
    enriched = []
    for i, ch in enumerate(chapters):
        enriched.append({
            "number": i + 1,
            "title": ch["title"],
            "focus": ch["focus"],
            "target_words": brief["words_per_chapter"],
        })

    return enriched


def run_categorizer(
    category_key: str = None,
    topic: str = None,
    audience: str = None,
    tone: str = None,
) -> dict:
    """
    Stage 1 main entry point.
    Generates a complete ebook brief with chapter outline.

    Returns:
        Complete brief dict ready for Stage 2.
    """
    print(f"\n{'='*60}")
    print(f"  {Fore.CYAN}[STAGE 1] eBook Categorizer{Style.RESET_ALL}")
    print(f"{'='*60}")

    # Generate base brief
    brief = generate_brief(
        category_key=category_key,
        topic=topic,
        audience=audience,
        tone=tone,
    )

    # Build chapter outline
    chapters = build_chapter_outline(brief)
    brief["chapters"] = chapters

    # Print summary
    print(f"\n  {Fore.YELLOW}Title:{Style.RESET_ALL}     {brief['title']}")
    print(f"  {Fore.YELLOW}Subtitle:{Style.RESET_ALL}  {brief['subtitle']}")
    print(f"  {Fore.YELLOW}Category:{Style.RESET_ALL}  {brief['category']}")
    print(f"  {Fore.YELLOW}Audience:{Style.RESET_ALL}  {brief['audience'].title()}")
    print(f"  {Fore.YELLOW}Tone:{Style.RESET_ALL}      {brief['tone'].title()}")
    print(f"  {Fore.YELLOW}Chapters:{Style.RESET_ALL}  {brief['num_chapters']}")
    print(f"  {Fore.YELLOW}Est. Words:{Style.RESET_ALL} ~{brief['total_estimated_words']:,}")

    print(f"\n  {Fore.CYAN}Chapter Outline:{Style.RESET_ALL}")
    for ch in chapters:
        print(f"    {Fore.GREEN}Ch {ch['number']}:{Style.RESET_ALL} {ch['title']}")
        print(f"         {Fore.WHITE}{ch['focus']}{Style.RESET_ALL}")

    print(f"\n  {Fore.GREEN}[✓] Brief generated successfully!{Style.RESET_ALL}\n")

    return brief


if __name__ == "__main__":
    from pprint import pprint
    brief = run_categorizer()
    print("\n=== Full Brief ===")
    pprint(brief)
