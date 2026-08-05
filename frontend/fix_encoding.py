#!/usr/bin/env python3
"""
Fix HTML entities in SemanticManager.tsx
"""

with open("src/pages/SemanticManager.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Replace HTML entities
content = content.replace("&lt;", "<")
content = content.replace("&gt;", ">")
content = content.replace("&amp;", "&")

# Write back
with open("src/pages/SemanticManager.tsx", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed HTML entities in SemanticManager.tsx")
