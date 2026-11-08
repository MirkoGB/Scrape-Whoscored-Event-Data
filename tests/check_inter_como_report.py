"""Standalone dossier browser and numerical integrity checks, desktop + mobile."""
import base64
import json
from pathlib import Path

import numpy as np
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/inter_como_2026-11-08"


def main():
    result=json.loads((OUT/"extended_forecast.json").read_text(encoding="utf-8"))
    rows={r["key"]:r for r in result["rows"]}
    assert len(rows)==37
    means={k:np.array(v["mean"]) for k,v in rows.items()}
    assert np.allclose(means["shots"],means["sot"]+means["shots_offtarget"]+means["shots_blocked"])
    assert np.allclose(means["shots"],means["shots_box"]+means["shots_outside"])
    for parent,child in [("passes","passes_complete"),("crosses","crosses_complete"),
                         ("dribbles","dribbles_won"),("tackles","tackles_won"),
                         ("aerial_duels","aerial_won"),("shots_offtarget","woodwork")]:
        assert (means[child]<=means[parent]).all()
    assert sum(result["rates"]["possession_proxy"]["mean"])==100
    for row in rows.values():
        assert all(np.isfinite(row["mean"]))
        assert all(lo<=hi for lo,hi in row["interval80"])
    options=webdriver.ChromeOptions()
    options.binary_location=str(ROOT/"reports/_chrome_for_extension_test/chrome-win64/chrome.exe")
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1440,1000")
    options.set_capability("goog:loggingPrefs",{"browser":"ALL","performance":"ALL"})
    b=webdriver.Chrome(service=Service(str(ROOT/"reports/_chrome_for_extension_test/chromedriver-win64/chromedriver.exe")),options=options)
    try:
        b.execute_cdp_cmd("Emulation.setEmulatedMedia",{"features":[{"name":"prefers-reduced-motion","value":"reduce"}]})
        b.get((OUT/"report.html").as_uri())
        assert len(b.find_elements("css selector","#stats-table tbody tr"))==37
        assert not b.execute_script("return document.documentElement.scrollWidth>innerWidth")
        b.execute_async_script("const done=arguments[0];const imgs=[...document.images];imgs.forEach(i=>i.loading='eager');Promise.all(imgs.map(i=>i.decode())).then(()=>done(true)).catch(e=>done(String(e)))")
        assert b.execute_script("return [...document.images].every(i=>i.complete&&i.naturalWidth>0)")
        b.save_screenshot(str(OUT/"html_desktop.png"))
        full=b.execute_cdp_cmd("Page.captureScreenshot",{"captureBeyondViewport":True,"clip":
            {"x":0,"y":0,"width":1440,"height":b.execute_script("return document.documentElement.scrollHeight"),"scale":1}})
        (OUT/"html_desktop_full.png").write_bytes(base64.b64decode(full["data"]))
        search=b.find_element("id","stat-search")
        search.send_keys("corner")
        assert b.execute_script("return [...document.querySelectorAll('#stats-table tbody tr')].filter(r=>!r.hidden).map(r=>r.dataset.key)")==["corners"]
        search.clear();search.send_keys("cartellini")
        assert len(b.find_elements("css selector","#stats-table tbody tr:not([hidden])"))==2
        search.clear();search.send_keys("zzzz")
        assert b.find_element("id","empty-stats").is_displayed()
        search.clear();search.send_keys(" ")
        b.find_element("css selector",'[data-filter="Difesa e duelli"]').click()
        assert b.find_element("css selector",'[data-key="saves"]').is_displayed()
        assert not b.find_element("css selector",'[data-key="corners"]').is_displayed()
        b.find_element("id","show-ranges").click()
        assert not b.find_element("css selector",'[data-key="saves"] .range').is_displayed()
        # Printing includes every category; returning restores the filter.
        b.execute_script("window.dispatchEvent(new Event('beforeprint'))")
        assert len(b.find_elements("css selector","#stats-table tbody tr:not([hidden])"))==37
        assert b.find_element("id","original-dossier").get_attribute("open")
        b.execute_script("window.dispatchEvent(new Event('afterprint'))")
        assert not b.find_element("id","original-dossier").get_attribute("open")
        b.find_element("css selector",'[data-filter="all"]').click()
        b.find_element("id","show-ranges").click()
        b.execute_cdp_cmd("Emulation.setDeviceMetricsOverride",{"width":390,"height":844,"deviceScaleFactor":1,"mobile":True})
        b.execute_script("scrollTo(0,0)")
        b.save_screenshot(str(OUT/"html_mobile.png"))
        assert not b.execute_script("return document.documentElement.scrollWidth>innerWidth")
        b.execute_script("document.getElementById('statistiche').scrollIntoView({behavior:'instant'})")
        b.save_screenshot(str(OUT/"html_mobile_stats.png"))
        full=b.execute_cdp_cmd("Page.captureScreenshot",{"captureBeyondViewport":True,"clip":
            {"x":0,"y":0,"width":390,"height":b.execute_script("return document.documentElement.scrollHeight"),"scale":1}})
        (OUT/"html_mobile_full.png").write_bytes(base64.b64decode(full["data"]))
        target=b.find_element("css selector",'[data-key="goals"] summary')
        b.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'})",target)
        target.click()
        assert b.find_element("css selector",'[data-key="goals"] .definition p').is_displayed()
        assert not b.execute_script("return document.documentElement.scrollWidth>innerWidth")
        b.save_screenshot(str(OUT/"html_mobile_table.png"))
        assert not [r for r in b.get_log("browser") if r["level"]=="SEVERE"]
        network=[json.loads(r["message"])["message"] for r in b.get_log("performance")]
        urls=[r["params"]["request"]["url"] for r in network if r["method"]=="Network.requestWillBeSent"]
        assert not [u for u in urls if u.startswith(("http://","https://"))]
        print("PASS: 37 statistics; coherent means; desktop/mobile layout; embedded images; no external requests; filters/search; intervals; definitions; print restore; no console errors.")
    finally:b.quit()


if __name__=="__main__":main()
