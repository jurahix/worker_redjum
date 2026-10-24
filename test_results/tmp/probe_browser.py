import asyncio
from playwright.async_api import async_playwright

URL = "https://redjum.pj.gob.pe/redjum/"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            ignore_https_errors=True,
            locale="es-PE",
        )
        page = await ctx.new_page()
        resp = await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        print("landing:", resp.status if resp else None)
        await page.wait_for_timeout(3000)  # dejar que Radware corra su challenge JS
        print("cookies:", [c["name"] for c in await ctx.cookies()])

        # misma peticion que hace el frontend AngularJS / el worker
        r = await ctx.request.get(
            URL + "deudoresPorDocumento/",
            params={
                "hash_id": "0.123",
                "captcha": "XXXX",
                "tipoDocumento": "01  ",
                "numerodocumento": "29457327",
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        body = await r.text()
        print("deudoresPorDocumento:", r.status, "->", body[:200])

        # y la misma consulta hecha con fetch() dentro del DOM de la pagina
        r2 = await page.evaluate(
            """async () => {
                const r = await fetch('/redjum/deudoresPorDocumento/?hash_id=0.9&captcha=XXXX&tipoDocumento=01%20%20&numerodocumento=29457327', {headers:{'X-Requested-With':'XMLHttpRequest'}});
                return {status: r.status, body: (await r.text()).slice(0,200)};
            }"""
        )
        print("fetch en pagina:", r2)
        await browser.close()

asyncio.run(main())
