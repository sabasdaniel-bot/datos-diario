#!/usr/bin/env python3
"""Descarga precios diarios (1 año) y titulares de Yahoo Finance para todos los tickers de seguimiento.
Escribe out/prices/<SIMBOLO>.json y out/news/<SIMBOLO>.json y out/manifest.json. Solo biblioteca estándar.
Uso: python3 fetch_yahoo.py tickers.json out"""
import json, sys, time, urllib.request, urllib.parse, os, datetime

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
SPECIAL = {"BRK.B": "BRK-B", "BTC": "BTC-USD", "ETH": "ETH-USD", "ANT": "ANT"}

def ysym(t):
    if t in SPECIAL: return SPECIAL[t]
    if t.endswith(".HK"):
        n, s = t.split(".")
        return str(int(n)).zfill(4) + ".HK"
    return t

def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                return json.load(r)
        except Exception as e:
            err = str(e)
            time.sleep(2 * (i + 1))
    return {"_error": err}

def main(tfile, out):
    tks = json.load(open(tfile))
    os.makedirs(out + "/prices", exist_ok=True); os.makedirs(out + "/news", exist_ok=True)
    man = {"generado_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "ok": [], "fallo": []}
    for t in tks:
        s = ysym(t); f = t.replace(".", "_")
        j = get("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=1y&interval=1d" % urllib.parse.quote(s))
        try:
            r = j["chart"]["result"][0]; q = r["indicators"]["quote"][0]
            bars = [[ts, q["open"][i], q["high"][i], q["low"][i], q["close"][i], q["volume"][i]]
                    for i, ts in enumerate(r["timestamp"]) if q["close"][i] is not None]
            json.dump({"t": t, "y": s, "meta": {k: r["meta"].get(k) for k in ("currency", "exchangeName", "regularMarketPrice", "regularMarketTime", "fiftyTwoWeekHigh", "fiftyTwoWeekLow")}, "bars": bars}, open("%s/prices/%s.json" % (out, f), "w"), separators=(",", ":"))
            man["ok"].append(t)
        except Exception as e:
            man["fallo"].append({"t": t, "y": s, "e": str(j.get("_error") or e)[:120]})
        n = get("https://query1.finance.yahoo.com/v1/finance/search?q=%s&newsCount=15&quotesCount=0&listsCount=0" % urllib.parse.quote(s))
        items = [{"uuid": x.get("uuid"), "pub": x.get("publisher"), "title": x.get("title"), "link": x.get("link"), "ts": x.get("providerPublishTime"), "rel": x.get("relatedTickers")} for x in (n.get("news") or [])]
        json.dump({"t": t, "items": items, "error": n.get("_error")}, open("%s/news/%s.json" % (out, f), "w"), ensure_ascii=False, separators=(",", ":"))
        print(t, "OK" if man["ok"] and man["ok"][-1]==t else "FALLO", flush=True)
        if len(man["ok"])==0 and len(man["fallo"])>=6:
            print("Yahoo bloquea este servidor: 6 fallos seguidos, se aborta"); json.dump(man, open(out + "/manifest.json", "w"), indent=1); sys.exit(1)
        time.sleep(0.4)
    json.dump(man, open(out + "/manifest.json", "w"), indent=1)
    print("ok", len(man["ok"]), "fallo", len(man["fallo"]))
    # falla el trabajo solo si fallan más de 40 % (Yahoo bloqueó el servidor)
    if len(man["fallo"]) > 0.4 * len(tks): sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
