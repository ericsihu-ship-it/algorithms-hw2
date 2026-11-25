"""체이닝과 선형 탐사의 평균 비교 횟수 비교 (과제, SPEC.md 8.4절).

    make compare      (= python3 experiments/compare_experiment.py)

- 칸 수 M = 4093 고정, 두 테이블 모두 max_load=None (크기를 늘리지 않는다).
- 적재율 α = 0.1, 0.2, ..., 0.9 마다 같은 시드로 만든 **같은 키**를 두 테이블에 넣는다.
- 성공 탐색: 넣은 키 전부, 실패 탐색: 넣지 않은 URL 2000개. 시드 5개 평균.
- 세는 단위
    체이닝    : 비교한 노드 수 (빈 칸에서 실패하면 0)
    선형 탐사 : 들여다본 칸 수 (빈 칸에서 멈추면 그 칸도 1)
- 이론값
    체이닝    : 성공 ≈ 1 + α/2,          실패 ≈ α
    선형 탐사 : 성공 ≈ (1 + 1/(1−α))/2,  실패 ≈ (1 + 1/(1−α)²)/2

결과: experiments/compare_results.csv, experiments/compare.svg
외부 라이브러리를 쓰지 않는다.
"""

import csv
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)

from hash_table import HashTable  # noqa: E402
from linear_probing import LinearProbingTable  # noqa: E402
from probe_experiment import (  # noqa: E402
    AXIS, COLOR_FAIL as COLOR_LINEAR, COLOR_SUCCESS as COLOR_CHAIN, FAILED_SEARCHES, GRID,
    M, SEEDS, TEXT, TEXT_2, _esc, _fmt, random_urls)

ALPHAS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

CSV_PATH = os.path.join(HERE, "compare_results.csv")
SVG_PATH = os.path.join(HERE, "compare.svg")


def theory(alpha):
    return {
        "chain_success_theory": 1 + alpha / 2,
        "chain_fail_theory": alpha,
        "linear_success_theory": (1 + 1 / (1 - alpha)) / 2,
        "linear_fail_theory": (1 + 1 / (1 - alpha) ** 2) / 2,
    }


def average_cost(table, keys):
    total = 0
    for k in keys:
        total += table.find(k)[1]
    return total / len(keys)


def measure(alpha, seed):
    rng = random.Random(seed)
    n = round(alpha * M)
    urls = random_urls(n + FAILED_SEARCHES, rng)
    present, absent = urls[:n], urls[n:]

    chain = HashTable(capacity=M, max_load=None)
    linear = LinearProbingTable(capacity=M, max_load=None)
    for i, url in enumerate(present):
        chain.put(url, i)
        linear.put(url, i)
    assert chain.capacity == linear.capacity == M
    assert len(chain) == len(linear) == n

    longest = 0
    for _, length in linear.clusters():
        if length > longest:
            longest = length

    return {
        "chain_success": average_cost(chain, present),
        "chain_fail": average_cost(chain, absent),
        "linear_success": average_cost(linear, present),
        "linear_fail": average_cost(linear, absent),
        "linear_longest_cluster": longest,
    }


MEASURED = ["chain_success", "chain_fail", "linear_success", "linear_fail", "linear_longest_cluster"]
FIELDS = ["alpha", "n",
          "chain_success", "chain_success_theory", "chain_fail", "chain_fail_theory",
          "linear_success", "linear_success_theory", "linear_fail", "linear_fail_theory",
          "linear_longest_cluster"]


def run():
    rows = []
    for alpha in ALPHAS:
        sums = [0.0] * len(MEASURED)
        for seed in SEEDS:
            m = measure(alpha, seed)
            for j, name in enumerate(MEASURED):
                sums[j] += m[name]
        row = {"alpha": alpha, "n": round(alpha * M)}
        for j, name in enumerate(MEASURED):
            row[name] = sums[j] / len(SEEDS)
        row.update(theory(alpha))
        rows.append(row)
    return rows


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(FIELDS)
        for r in rows:
            out = []
            for name in FIELDS:
                v = r[name]
                out.append(v if name in ("alpha", "n") else "{:.4f}".format(v))
            w.writerow(out)


def print_table(rows):
    print("M = {}, 같은 키, 시드 {}개 평균, 실패 탐색 {}개".format(M, len(SEEDS), FAILED_SEARCHES))
    print("체이닝은 비교한 노드 수, 선형 탐사는 들여다본 칸 수")
    print()
    print("{:>4} {:>5} | {:^23} | {:^23} | {:>6}".format("α", "n", "성공 (실험/이론)", "실패 (실험/이론)", "최장"))
    print("{:>4} {:>5} | {:>11} {:>11} | {:>11} {:>11} | {:>6}".format(
        "", "", "체이닝", "선형탐사", "체이닝", "선형탐사", "클러스터"))
    print("-" * 74)
    for r in rows:
        print("{:>4} {:>5} | {:>5.2f}/{:<5.2f} {:>5.2f}/{:<5.2f} | {:>5.2f}/{:<5.2f} {:>5.1f}/{:<5.1f} | {:>6.0f}".format(
            _fmt(r["alpha"]), r["n"],
            r["chain_success"], r["chain_success_theory"],
            r["linear_success"], r["linear_success_theory"],
            r["chain_fail"], r["chain_fail_theory"],
            r["linear_fail"], r["linear_fail_theory"],
            r["linear_longest_cluster"]))


# SVG: 성공 탐색 / 실패 탐색 두 칸, 같은 x축(α), 칸마다 자기 y축 -------------

def nice_max(v):
    for step in (1, 2, 5, 10, 20, 50, 100):
        if v <= step * 5:
            top = step
            while top < v * 1.05:
                top += step
            return top, step
    return v, v / 5


def panel(rows, x0, y0, w, h, title, keys):
    """keys: [(이름, 색, 실험 키, 이론 키)]"""
    ymax_raw = 0
    for _, _, km, kt in keys:
        for r in rows:
            ymax_raw = max(ymax_raw, r[km], r[kt])
    y_max, step = nice_max(ymax_raw)
    x_min, x_max = 0, 1

    def x(v):
        return x0 + w * (v - x_min) / (x_max - x_min)

    def y(v):
        return y0 + h * (1 - v / y_max)

    out = []
    out.append('<text x="{}" y="{}" font-size="14" font-weight="600" fill="{}">{}</text>'
               .format(x0, y0 - 14, TEXT, _esc(title)))
    t = 0
    while t <= y_max + 1e-9:
        out.append('<line x1="{}" y1="{:.1f}" x2="{}" y2="{:.1f}" stroke="{}" stroke-width="1"/>'
                   .format(x0, y(t), x0 + w, y(t), GRID))
        out.append('<text x="{}" y="{:.1f}" font-size="12" fill="{}" text-anchor="end">{}</text>'
                   .format(x0 - 8, y(t) + 4, TEXT_2, _fmt(t)))
        t += step
    for tx in (0, 0.2, 0.4, 0.6, 0.8, 1.0):
        out.append('<line x1="{:.1f}" y1="{}" x2="{:.1f}" y2="{}" stroke="{}" stroke-width="1"/>'
                   .format(x(tx), y0 + h, x(tx), y0 + h + 5, AXIS))
        out.append('<text x="{:.1f}" y="{}" font-size="12" fill="{}" text-anchor="middle">{}</text>'
                   .format(x(tx), y0 + h + 20, TEXT_2, _fmt(tx)))
    out.append('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="{}" stroke-width="1"/>'
               .format(x0, y0 + h, x0 + w, y0 + h, AXIS))
    out.append('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="{}" stroke-width="1"/>'
               .format(x0, y0, x0, y0 + h, AXIS))
    out.append('<text x="{:.1f}" y="{}" font-size="13" fill="{}" text-anchor="middle">적재율 α = n / M</text>'
               .format(x0 + w / 2, y0 + h + 44, TEXT))

    for name, color, km, kt in keys:
        pts_t = " ".join("{:.1f},{:.1f}".format(x(r["alpha"]), y(r[kt])) for r in rows)
        out.append('<polyline points="{}" fill="none" stroke="{}" stroke-width="2" '
                   'stroke-dasharray="6 5" stroke-linecap="round"/>'.format(pts_t, color))
        pts_m = " ".join("{:.1f},{:.1f}".format(x(r["alpha"]), y(r[km])) for r in rows)
        out.append('<polyline points="{}" fill="none" stroke="{}" stroke-width="2" '
                   'stroke-linejoin="round"/>'.format(pts_m, color))
        for r in rows:
            out.append('<circle cx="{:.1f}" cy="{:.1f}" r="4.5" fill="{}" stroke="#ffffff" stroke-width="2">'
                       '<title>{} · α = {}: 실험 {:.3f}, 이론 {:.3f}</title></circle>'
                       .format(x(r["alpha"]), y(r[km]), color, _esc(name), _fmt(r["alpha"]), r[km], r[kt]))
        last = rows[-1]
        out.append('<text x="{:.1f}" y="{:.1f}" font-size="12" fill="{}">{}</text>'
                   .format(x(last["alpha"]) + 10, y(last[km]) + 4, TEXT, _esc(name)))
    return out


def write_svg(rows, path):
    width, height = 940, 500
    top, left, gap, pw, ph = 104, 64, 120, 340, 300
    out = []
    out.append('<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
               'font-family="system-ui, -apple-system, \'Segoe UI\', \'Noto Sans KR\', \'Malgun Gothic\', '
               'sans-serif">'.format(w=width, h=height))
    out.append('<rect width="100%" height="100%" fill="#ffffff"/>')
    out.append('<text x="{}" y="30" font-size="17" font-weight="600" fill="{}">'
               '체이닝 vs 선형 탐사: 적재율에 따른 평균 탐색 비용</text>'.format(left, TEXT))

    # 범례 (위쪽 한 줄)
    lx, ly = left, 56
    items = [("체이닝 · 실험", COLOR_CHAIN, True), ("체이닝 · 이론", COLOR_CHAIN, False),
             ("선형 탐사 · 실험", COLOR_LINEAR, True), ("선형 탐사 · 이론", COLOR_LINEAR, False)]
    for name, color, solid in items:
        dash = "" if solid else ' stroke-dasharray="6 5"'
        out.append('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="{}" stroke-width="2"{}/>'
                   .format(lx, ly, lx + 28, ly, color, dash))
        if solid:
            out.append('<circle cx="{}" cy="{}" r="4.5" fill="{}" stroke="#ffffff" stroke-width="2"/>'
                       .format(lx + 14, ly, color))
        out.append('<text x="{}" y="{}" font-size="13" fill="{}">{}</text>'
                   .format(lx + 36, ly + 4, TEXT, _esc(name)))
        lx += 175

    series = [("체이닝", COLOR_CHAIN), ("선형 탐사", COLOR_LINEAR)]
    out += panel(rows, left, top, pw, ph, "성공 탐색",
                 [(n, c, p + "_success", p + "_success_theory")
                  for (n, c), p in zip(series, ("chain", "linear"))])
    out += panel(rows, left + pw + gap, top, pw, ph, "실패 탐색",
                 [(n, c, p + "_fail", p + "_fail_theory")
                  for (n, c), p in zip(series, ("chain", "linear"))])

    out.append('<text transform="translate(18 {}) rotate(-90)" font-size="13" fill="{}" '
               'text-anchor="middle">평균 비교 횟수</text>'.format(top + ph / 2, TEXT))
    out.append('<text x="{}" y="{}" font-size="11" fill="{}">M = {}, 같은 키, 시드 {}개 평균. '
               '체이닝은 비교한 노드 수(빈 칸 0), 선형 탐사는 들여다본 칸 수(빈 칸도 1). '
               '두 칸의 y축 범위가 다르다.</text>'
               .format(left, height - 12, TEXT_2, M, len(SEEDS)))
    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def main():
    rows = run()
    print_table(rows)
    write_csv(rows, CSV_PATH)
    write_svg(rows, SVG_PATH)
    print()
    print("저장: {}".format(os.path.relpath(CSV_PATH)))
    print("저장: {}".format(os.path.relpath(SVG_PATH)))


if __name__ == "__main__":
    main()
