import json

p = json.load(open("2025.json", encoding="utf-8"))
g = json.load(open("gold_prices.json", encoding="utf-8"))

h, th = 7, 0.4
ok = total = 0

# pregătim zilele de trading o singură dată
trade_dates = sorted(g.keys())
trade_index = {d: i for i, d in enumerate(trade_dates)}

for pred in p:
    d1 = pred["date"]

    if d1 not in trade_index:
        continue

    j = trade_index[d1]

    if j + h >= len(trade_dates):
        continue

    d2 = trade_dates[j + h]

    ret = ((g[d2] - g[d1]) / g[d1]) * 100
    real = "Creștere" if ret > th else "Scădere" if ret < -th else "Neutru"

    correct = pred["trend"] == real

    print(d1, "| prezis:", pred["trend"], "| real:", real, "|", "corect" if correct else "greșit")

    ok += correct
    total += 1

if total > 0:
    print(f"\nAcuratețe: {ok}/{total} = {ok/total:.2%}")
else:
    print("Nu s-au găsit zile valide pentru comparare.")