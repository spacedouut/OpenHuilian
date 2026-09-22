"""Search 52bluetooth via the logged-in Chrome (CDP) and dump results/threads as text."""
import asyncio, json, re, sys, time, urllib.parse
from playwright.async_api import async_playwright

OUT = "/home/ubuntu/starfun/bt52"
import os; os.makedirs(OUT, exist_ok=True)

async def text(page):
    return await page.evaluate("() => document.body.innerText")

async def search(page, kw):
    url = "https://www.52bluetooth.com/search.php?mod=forum&searchsubmit=yes&srchtxt=" + urllib.parse.quote(kw)
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(1500)
    body = await text(page)
    if "搜索间隔" in body or "秒后再试" in body or "过于频繁" in body:
        m = re.search(r"(\d+) 秒", body)
        wait = int(m.group(1)) + 1 if m else 20
        await page.wait_for_timeout(wait * 1000)
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
    items = await page.evaluate("""() => [...document.querySelectorAll('#threadlist li, .pbw')].map(li => {
        const a = li.querySelector('h3 a'); if(!a) return null;
        return {title: a.innerText.trim(), href: a.href, meta: li.innerText.replace(/\\s+/g,' ').slice(0,300)};
    }).filter(x=>x)""")
    nxt = await page.evaluate("() => { const a=document.querySelector('a.nxt'); return a? a.href: null }")
    return items, nxt

async def thread(page, href):
    await page.goto(href, wait_until="domcontentloaded")
    await page.wait_for_timeout(800)
    t = await page.evaluate("""() => {
        const posts=[...document.querySelectorAll('td.t_f')].map(e=>e.innerText.trim());
        const atts=[...document.querySelectorAll('.attnm a, dl.tattl a, .attach a, p.attnm a')].map(a=>a.innerText.trim()+' -> '+a.href);
        const title=(document.querySelector('#thread_subject')||{}).innerText||document.title;
        return {title, posts, atts};
    }""")
    return t

async def main(kws, fetch_threads):
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://localhost:29229")
        ctx = b.contexts[0]
        page = await ctx.new_page()
        allres = {}
        for kw in kws:
            items, nxt = await search(page, kw)
            pages = 1
            while nxt and pages < 4:
                await page.goto(nxt, wait_until="domcontentloaded"); await page.wait_for_timeout(1000)
                more = await page.evaluate("""() => [...document.querySelectorAll('#threadlist li, .pbw')].map(li => {
                    const a = li.querySelector('h3 a'); if(!a) return null;
                    return {title: a.innerText.trim(), href: a.href, meta: li.innerText.replace(/\\s+/g,' ').slice(0,300)};}).filter(x=>x)""")
                items += more
                nxt = await page.evaluate("() => { const a=document.querySelector('a.nxt'); return a? a.href: null }")
                pages += 1
            allres[kw] = items
            print(f"== {kw}: {len(items)}")
            for it in items:
                print("  -", it["title"], "|", it["href"])
            await page.wait_for_timeout(16000)
        json.dump(allres, open(f"{OUT}/search.json", "a"), ensure_ascii=False)
        if fetch_threads:
            seen = set()
            for kw, items in allres.items():
                for it in items:
                    if it["href"] in seen: continue
                    seen.add(it["href"])
                    t = await thread(page, it["href"])
                    tid = re.search(r"tid=(\d+)|thread-(\d+)", it["href"])
                    tid = (tid.group(1) or tid.group(2)) if tid else str(int(time.time()))
                    with open(f"{OUT}/t{tid}.txt", "w") as f:
                        f.write(t["title"] + "\n" + it["href"] + "\n\n")
                        for i, ptxt in enumerate(t["posts"]): f.write(f"--- post {i+1}\n{ptxt}\n\n")
                        f.write("ATTACHMENTS:\n" + "\n".join(t["atts"]) + "\n")
                    print("saved", tid, t["title"][:60], "atts:", len(t["atts"]))
        await page.close()

if __name__ == "__main__":
    kws = sys.argv[1].split(",")
    asyncio.run(main(kws, "--threads" in sys.argv))
