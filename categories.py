# -*- coding: utf-8 -*-
"""
categories.py — eBook category definitions and brief generator.

All categories sourced from the master spreadsheet.
Each category has sub-types, audience levels, and topic generators.
"""

import random

# ═══════════════════════════════════════════════════════════════════════
# MASTER CATEGORY REGISTRY
# ═══════════════════════════════════════════════════════════════════════

AUDIENCE_LEVELS = ["beginner", "intermediate", "expert", "parent", "student"]
TONES = ["professional", "conversational", "motivational", "academic", "friendly"]

CATEGORIES = {
    "how_to_guides": {
        "label": "How-To & Step-by-Step Guides",
        "description": "Practical, actionable guides that walk readers through a process",
        "example_topics": [
            "How to Start a Profitable Side Hustle in 2025",
            "How to Build Your First Website From Scratch",
            "How to Master Personal Finance in 30 Days",
            "How to Launch a Successful YouTube Channel",
            "How to Create a Morning Routine for Peak Productivity",
            "How to Start Freelancing and Land Your First Client",
            "How to Build a Personal Brand on Social Media",
            "How to Learn Any Skill in 90 Days",
        ],
    },
    "checklists_cheat_sheets": {
        "label": "Checklists & Cheat Sheets",
        "description": "Quick-reference resources packed with actionable items",
        "example_topics": [
            "The Ultimate Product Launch Checklist",
            "Social Media Marketing Cheat Sheet",
            "SEO Audit Checklist for Beginners",
            "Home Organization 30-Day Checklist",
            "Job Interview Preparation Cheat Sheet",
            "Content Creation Workflow Checklist",
            "Startup Legal Requirements Checklist",
            "Healthy Meal Prep Weekly Cheat Sheet",
        ],
    },
    "setup_guides": {
        "label": "Setup Guides & System Building PDFs",
        "description": "System setup and configuration guides with clear instructions",
        "example_topics": [
            "Setting Up Your Online Store: Complete System Guide",
            "Build Your Email Marketing System From Zero",
            "CRM Setup Guide for Small Businesses",
            "Home Studio Setup Guide for Content Creators",
            "Setting Up Automated Sales Funnels",
            "Remote Team Collaboration System Blueprint",
            "Setting Up a Notion Productivity System",
            "Build Your Personal Knowledge Management System",
        ],
    },
    "frameworks_roadmaps": {
        "label": "Frameworks, Roadmaps & Blueprints",
        "description": "Strategic frameworks and roadmaps for achieving goals",
        "example_topics": [
            "The 90-Day Business Launch Blueprint",
            "Content Marketing Framework for Growth",
            "Career Transition Roadmap: Switch Industries in 6 Months",
            "The Digital Product Creation Framework",
            "Financial Freedom Roadmap: From Zero to Passive Income",
            "Brand Strategy Blueprint for Startups",
            "The Learning Roadmap: Master Any Subject",
            "Health & Fitness Transformation Blueprint",
        ],
    },
    "workbooks": {
        "label": "Workbooks & Guided Exercises",
        "description": "Interactive workbooks with exercises, prompts, and fill-in sections",
        "example_topics": [
            "Goal Setting & Achievement Workbook",
            "Self-Discovery Journal & Workbook",
            "Business Model Canvas Workbook",
            "Creative Writing Exercises Workbook",
            "Mindfulness & Meditation Practice Workbook",
            "Financial Planning Workbook",
            "Relationship Building Exercises",
            "Career Development Self-Assessment Workbook",
        ],
    },
    "planners_calendars": {
        "label": "Planners, Calendars & Schedules",
        "description": "Time management and planning resources",
        "example_topics": [
            "The Ultimate Content Calendar & Planner",
            "12-Month Business Growth Planner",
            "Weekly Productivity Planner & Tracker",
            "Fitness & Nutrition 90-Day Planner",
            "Social Media Content Schedule Template",
            "Project Management Timeline Planner",
            "Annual Goal Tracking Calendar",
            "Study Schedule & Exam Planner",
        ],
    },
    "mini_courses": {
        "label": "Niche Mini-Courses in PDF Form",
        "description": "Structured learning modules packaged as comprehensive PDFs",
        "example_topics": [
            "Mini-Course: Introduction to AI for Business",
            "Mini-Course: Photography Basics in 7 Days",
            "Mini-Course: Public Speaking Confidence Builder",
            "Mini-Course: Introduction to Investing",
            "Mini-Course: Graphic Design Fundamentals",
            "Mini-Course: Digital Marketing 101",
            "Mini-Course: Python Programming for Beginners",
            "Mini-Course: Copywriting That Converts",
        ],
    },
    "comparison_guides": {
        "label": "Comparison & Decision-Making Guides",
        "description": "Side-by-side comparisons to help readers make informed decisions",
        "example_topics": [
            "WordPress vs Shopify vs Wix: Complete Comparison Guide",
            "Remote Work Tools Comparison Guide",
            "Investment Options Compared: Stocks, Crypto, Real Estate",
            "Email Marketing Platforms: Which One Is Right for You?",
            "Freelancing vs Full-Time: A Decision-Making Guide",
            "Diet Plans Compared: Keto, Paleo, Mediterranean & More",
            "Cloud Storage Solutions: Complete Comparison",
            "Productivity Methods Compared: GTD, Pomodoro, Time Blocking",
        ],
    },
    "transformation_guides": {
        "label": "Before & After Transformation Guides",
        "description": "Inspiring transformation stories with actionable steps",
        "example_topics": [
            "From Employee to Entrepreneur: A Transformation Guide",
            "Body Transformation: The Complete 12-Week Guide",
            "From Debt to Financial Freedom: A Real Journey",
            "Career Pivot Success: Real Stories & Strategies",
            "Home Makeover on a Budget: Before & After Guide",
            "Digital Detox: Transform Your Relationship with Technology",
            "From Procrastinator to Productive: A Mindset Shift Guide",
            "Portfolio Transformation Guide for Creatives",
        ],
    },
    "sop_libraries": {
        "label": "SOP (Standard Operating Procedure) Libraries",
        "description": "Standardized process documentation for teams and businesses",
        "example_topics": [
            "Customer Service SOP Library",
            "Social Media Management SOPs",
            "E-Commerce Order Fulfillment SOPs",
            "Content Production Pipeline SOPs",
            "HR Onboarding Process SOP Library",
            "Sales Team Standard Procedures",
            "Quality Assurance SOP Templates",
            "Event Planning Standard Procedures",
        ],
    },
    "playbooks": {
        "label": "Playbooks (Action-Oriented Manuals)",
        "description": "Strategic playbooks with tactical advice and action steps",
        "example_topics": [
            "The Growth Hacking Playbook",
            "Cold Email Outreach Playbook",
            "Social Media Engagement Playbook",
            "Product Launch Playbook",
            "Negotiation Tactics Playbook",
            "Community Building Playbook",
            "Crisis Management Playbook",
            "Influencer Collaboration Playbook",
        ],
    },
    "quiz_assessment": {
        "label": "Quiz & Assessment Packs",
        "description": "Self-assessment tools, quizzes, and diagnostic frameworks",
        "example_topics": [
            "Leadership Style Assessment Pack",
            "Business Readiness Quiz & Assessment",
            "Skills Gap Analysis Assessment",
            "Personality Type & Career Match Quiz",
            "Financial Health Assessment Pack",
            "Team Culture Assessment Toolkit",
            "Marketing Strategy Diagnostic Quiz",
            "Wellness & Work-Life Balance Assessment",
        ],
    },
    "company_handbooks": {
        "label": "Internal Company Handbooks",
        "description": "Company culture, values, and policy documentation",
        "example_topics": [
            "Startup Culture & Values Handbook",
            "Remote Work Policy Handbook",
            "Employee Benefits & Perks Guide",
            "Company Communication Standards Handbook",
            "Diversity, Equity & Inclusion Handbook",
            "Team Collaboration Guidelines",
            "Data Security & Privacy Policy Handbook",
            "Performance Review & Growth Handbook",
        ],
    },
    "creative_hobby": {
        "label": "Creative & Hobby PDFs",
        "description": "Creative guides for crafts, cooking, fitness, and hobbies",
        "example_topics": [
            "DIY Home Decor Projects Guide",
            "Beginner's Guide to Watercolor Painting",
            "30 Easy & Healthy Recipes Cookbook",
            "Home Workout Guide: No Equipment Needed",
            "Beginner's Guide to Indoor Gardening",
            "Journaling for Mental Health & Creativity",
            "Photography Composition Guide for Beginners",
            "Knitting Patterns for Beginners",
        ],
    },
    "client_facing": {
        "label": "Client-Facing Packs for Service Providers",
        "description": "Professional resources for client onboarding and communication",
        "example_topics": [
            "Client Onboarding Welcome Pack",
            "Service Provider Pricing & Packages Guide",
            "Project Scope & Deliverables Template Pack",
            "Client Communication Best Practices Guide",
            "Freelancer Client Proposal Templates",
            "Agency Services Overview & Case Studies",
            "Coaching Program Enrollment Pack",
            "Consultation Preparation Guide for Clients",
        ],
    },
    "done_for_you": {
        "label": "Done-For-You Content Packs",
        "description": "Ready-to-use content that buyers can rebrand and use immediately",
        "example_topics": [
            "30-Day Social Media Content Pack",
            "Email Newsletter Templates Pack (12 Months)",
            "Blog Post Templates: 50 Ready-to-Customize Articles",
            "Lead Magnet Templates Collection",
            "Presentation Templates Pack for Business",
            "Sales Page Copy Templates",
            "Video Script Templates for YouTube",
            "Podcast Episode Planning Templates",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SELECTION & BRIEF GENERATION
# ═══════════════════════════════════════════════════════════════════════

def list_categories() -> list[dict]:
    """Return all categories with their keys and labels."""
    return [{"key": k, "label": v["label"], "description": v["description"]}
            for k, v in CATEGORIES.items()]


def select_category(category_key: str = None) -> dict:
    """
    Select a category by key, or pick a random one.
    Returns the full category dict with key included.
    """
    if category_key and category_key in CATEGORIES:
        cat = CATEGORIES[category_key]
        return {"key": category_key, **cat}

    # Random selection
    key = random.choice(list(CATEGORIES.keys()))
    return {"key": key, **CATEGORIES[key]}


def generate_brief(
    category_key: str = None,
    topic: str = None,
    audience: str = None,
    tone: str = None,
) -> dict:
    """
    Generate a structured ebook brief.

    Args:
        category_key: Specific category key, or None for random.
        topic: Specific topic, or None to pick from examples.
        audience: Target audience level, or None for random.
        tone: Writing tone, or None for random.

    Returns:
        Dict with title, category, audience, tone, and chapter structure.
    """
    cat = select_category(category_key)

    if not topic:
        topic = random.choice(cat["example_topics"])

    if not audience:
        audience = random.choice(AUDIENCE_LEVELS)

    if not tone:
        tone = random.choice(TONES)

    # Generate chapter structure based on category type
    num_chapters = random.randint(5, 8)

    brief = {
        "title": topic,
        "subtitle": f"A {cat['label']} for {audience.title()} Readers",
        "category": cat["label"],
        "category_key": cat["key"],
        "description": cat["description"],
        "audience": audience,
        "tone": tone,
        "num_chapters": num_chapters,
        "words_per_chapter": 1000,
        "total_estimated_words": num_chapters * 1000,
    }

    return brief


if __name__ == "__main__":
    # Quick test
    from pprint import pprint
    print("\n=== All Categories ===")
    for c in list_categories():
        print(f"  {c['key']:30s} → {c['label']}")

    print("\n=== Random Brief ===")
    pprint(generate_brief())

    print("\n=== Specific Brief ===")
    pprint(generate_brief(
        category_key="how_to_guides",
        topic="How to Start Dropshipping in 2025",
        audience="beginner",
        tone="conversational",
    ))
