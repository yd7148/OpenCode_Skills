> 改寫自 keon/browser-control（MIT, Om Labs）的 `skills/interaction-skills/screenshots.md`，內文保留原文。
> 本機對應指令請對照 `SKILL.md` 的〈指令對照表〉。
> 路徑對應：本目錄檔名與上游一致，文中提到的 `interaction-skills/<file>.md` 即本目錄的 `<file>.md`。

# Screenshots

`capture_screenshot()` writes a PNG of the current viewport. The file is in **device pixels** — on a 2× display a 2296×1143 CSS viewport produces a 4592×2286 PNG.

That matters for two reasons:

1. **Click coordinates are CSS pixels.** Don't read a target off the image and pass it to `click_at_xy()` directly without dividing by `devicePixelRatio`. The simplest workflow is to take the screenshot, look at it in a viewer that shows CSS coordinates, or measure relative positions and use `js("window.devicePixelRatio")` to convert.

2. **Some LLMs reject images > 2000 px per side.** Long sessions on 2× displays will eventually hit this. Pass `max_dim=1800` to downscale the file before it gets into the conversation:

```python
capture_screenshot("/tmp/shot.png", max_dim=1800)
```

The downscale only happens when the image actually exceeds `max_dim`, so it's safe to leave on for every shot.

Use full-page screenshots (`full=True`) only when you need to see content below the fold — they are much larger and slower than viewport-only.
