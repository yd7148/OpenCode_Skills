"""Fetch Micron job description full text (STRICT single-thread, resumable).

Rate-limit notes:
  - 1 page only. 5 concurrent pages triggers the human-verification wall.
  - 2.5-4.5s between pages with a realistic UA.
  - A blocked page yields ~200 chars of body text; treat <2000 as blocked.
  - Resumable: existing URLs in the output file are skipped.

Usage:
  python fetch_jd.py --list micron_tc.json --out micron_texts.json
"""
import asyncio, json, os, random, re, sys, argparse
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
MIN_LEN = 2000


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", dest="lst", required=True)
    ap.add_argument("--out", default="micron_texts.json")
    ap.add_argument("--delay", type=float, default=2.5)
    a = ap.parse_args()

    jobs = json.load(open(a.lst, encoding="utf-8"))
    texts = json.load(open(a.out, encoding="utf-8")) if os.path.exists(a.out) else {}
    todo = [j for j in jobs if j["url"] not in texts]
    print("todo", len(todo), "cached", len(texts))
    if not todo:
        return

    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(viewport={"width": 1440, "height": 1200}, user_agent=UA, locale="en-US")
        pg = await ctx.new_page()
        for i, t in enumerate(todo):
            txt = ""
            for attempt in range(4):
                try:
                    await pg.goto(t["url"], wait_until="domcontentloaded", timeout=60000)
                    await pg.wait_for_timeout(3000)
                    txt = await pg.evaluate("() => document.body.innerText")
                    if len(txt) >= MIN_LEN:
                        break
                    print("  blocked/short", len(txt))
                except Exception as e:
                    print("  err", str(e)[:60])
                txt = ""
                await pg.wait_for_timeout(25000 + attempt * 20000)
            texts[t["url"]] = txt
            if i % 20 == 0:
                print(i, "/", len(todo))
                sys.stdout.flush()
                json.dump(texts, open(a.out, "w", encoding="utf-8"), ensure_ascii=False)
            await pg.wait_for_timeout(a.delay + random.random() * 2)
        await b.close()

    json.dump(texts, open(a.out, "w", encoding="utf-8"), ensure_ascii=False)
    print("saved", len(texts), "good", sum(1 for v in texts.values() if len(v) >= MIN_LEN))


asyncio.run(main())