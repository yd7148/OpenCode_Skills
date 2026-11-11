"""Fetch Micron job listings for a location (rate-limit safe).

Usage:
  python fetch_list.py --location "Taichung City, Taiwan" --out micron_tc.json
"""
import asyncio, json, random, re, sys, argparse
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"

JS = """() => Array.from(document.querySelectorAll('[data-test-id="job-listing"]')).map(c => {
  const a = c.querySelector('a');
  const title = c.querySelector('div[class*=title-]');
  const vals = Array.from(c.querySelectorAll('div[class*=fieldValue-]')).map(v => v.innerText.trim());
  return {title: title ? title.innerText.trim() : '', fields: vals, url: a ? a.href : null};
})"""


def base_url(location, start):
    from urllib.parse import quote_plus
    return ("https://careers.micron.com/careers?start={}&sort_by=distance"
            "&location={}&filter_include_remote=1&filter_include_relocation=0"
            ).format(start, quote_plus(location))


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--location", default="Taichung City, Taiwan")
    ap.add_argument("--out", default="micron_tc.json")
    ap.add_argument("--pages", type=int, default=30)
    a = ap.parse_args()

    allj, seen = [], set()
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(viewport={"width": 1440, "height": 1400}, user_agent=UA, locale="en-US")
        pg = await ctx.new_page()
        for start in range(0, a.pages * 20, 20):
            ok = False
            for attempt in range(3):
                try:
                    await pg.goto(base_url(a.location, start), wait_until="domcontentloaded", timeout=90000)
                    await pg.wait_for_timeout(5000)
                    rows = await pg.evaluate(JS)
                    if rows:
                        ok = True
                        break
                except Exception as e:
                    print("retry", start, str(e)[:60])
                await pg.wait_for_timeout(25000 + attempt * 20000)
            if not ok:
                print("stop at start", start)
                break
            n = 0
            for r in rows:
                if r["url"] in seen:
                    continue
                seen.add(r["url"]); allj.append(r)
                if any(a.location.split(",")[0] in f for f in r["fields"]):
                    n += 1
            print("start", start, "page", len(rows), "new", len(allj), "match", n)
            if len(rows) < 20:
                break
            await pg.wait_for_timeout(2500 + random.random() * 2000)
        await b.close()

    match = [j for j in allj if any(a.location.split(",")[0] in f for f in j["fields"])]
    json.dump(match, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("saved", len(match), "->", a.out)


asyncio.run(main())