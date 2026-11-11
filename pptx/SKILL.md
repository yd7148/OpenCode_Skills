---
name: pptx
description: Use when generating or manipulating PowerPoint presentations programmatically.
license: MIT
---

# PowerPoint

## When to Use This Skill
- Creating slide decks from data or templates
- Adding charts, tables, and images to slides
- Applying themes and consistent styling
- Extracting content from existing presentations

## Workflow
1. Install the library: `pip install python-pptx` or `npm install pptxgenjs`
2. Create a presentation: `prs = Presentation()`
3. Add slides with layouts: `prs.slides.add_slide(prs.slide_layouts[1])`
4. Add content: text boxes, shapes, tables, charts, and images
5. Apply formatting: font size, color, alignment, and shape styles
6. For charts: add chart data and configure the chart type
7. Save: `prs.save('output.pptx')`
8. For extraction: iterate slides and shapes to read content

## Rules
- Use slide layouts for consistency, not manual positioning
- Keep text readable — minimum 18pt for body, 24pt for titles
- Limit content per slide — one idea per slide
- Test in both PowerPoint and Google Slides
- Use consistent colors and fonts from the theme
- Handle images at appropriate resolutions — avoid pixelation
