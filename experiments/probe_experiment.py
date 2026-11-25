"""적재율에 따른 체이닝 해시 테이블의 평균 비교 횟수 실험 (SPEC.md 7절).

    make experiment      (= python3 experiments/probe_experiment.py)

- 칸 수 M = 4093으로 고정한다 (HashTable(capacity=4093, max_load=None)).
- 적재율 α = 0.25, 0.5, 1, 2, 4 마다 무작위 URL을 n = round(α·M) 개 넣는다.
  (…/page/1 같은 순차 URL은 쓰지 않는다. 호너 해시가 키를 고르게 섞지 못해 이론값에서 벗어난다.)
- 성공 탐색: 넣은 키 전부를 find해 비교한 노드 수의 평균.
- 실패 탐색: 넣지 않은 URL 2000개를 find해 비교한 노드 수의 평균. 빈 칸이면 0.
- 이론값: 성공 ≈ 1 + α/2, 실패 ≈ α.
- 난수 시드를 고정해 몇 번을 돌려도 같은 결과가 나온다. 시드 5개의 평균을 낸다.

결과: experiments/results.csv, experiments/probe.svg
외부 라이브러리를 쓰지 않는다.
"""

import csv
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from base62 import ALPHABET, encode  # noqa: E402
from hash_table import HashTable  # noqa: E402

M = 4093
ALPHAS = [0.25, 0.5, 1.0, 2.0, 4.0]
FAILED_SEARCHES = 2000
SEEDS = [1, 2, 3, 4, 5]

CSV_PATH = os.path.join(HERE, "results.csv")
SVG_PATH = os.path.join(HERE, "probe.svg")


def random_urls(count, rng):
    """서로 다른 무작위 URL count개. 끝에 일련번호를 붙여 중복이 없게 한다."""
    hosts = ["example.com", "yonsei.ac.kr", "github.com", "news.site", "shop.kr"]
    urls = []
    for i in range(count):
        host = hosts[rng.randrange(len(hosts))]
        length = rng.randint(4, 16)
        path = "".join(ALPHABET[rng.randrange(62)] for _ in range(length))
        urls.append("https://{}/{}-{}".format(host, path, encode(i)))
    return urls


def measure(alpha, seed):
    """(성공 평균, 실패 평균)을 돌려준다."""
    rng = random.Random(seed)
    n = round(alpha * M)
    urls = random_urls(n + FAILED_SEARCHES, rng)
    present, absent = urls[:n], urls[n:]

    table = HashTable(capacity=M, max_load=None)
    for i, url in enumerate(present):
        table.put(url, i)
    assert table.capacity == M and len(table) == n

    total = 0
    for url in present:
        value, comparisons = table.find(url)
        assert value is not None
        total += comparisons
    success = total / n

    total = 0
    for url in absent:
        value, comparisons = table.find(url)
        assert value is None
        total += comparisons
    fail = total / len(absent)
    return success, fail


def run():
    rows = []
    for alpha in ALPHAS:
        s_sum = f_sum = 0.0
        for seed in SEEDS:
            s, f = measure(alpha, seed)
            s_sum += s
            f_sum += f
        rows.append({
            "alpha": alpha,
            "n": round(alpha * M),
            "success_measured": s_sum / len(SEEDS),
            "success_theory": 1 + alpha / 2,
            "fail_measured": f_sum / len(SEEDS),
            "fail_theory": alpha,
        })
    return rows


# ---------------------------------------------------------------------------
# 출력


FIELDS = ["alpha", "n", "success_measured", "success_theory", "fail_measured", "fail_theory"]


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(FIELDS)
        for r in rows:
            w.writerow([
                r["alpha"], r["n"],
                "{:.4f}".format(r["success_measured"]), "{:.4f}".format(r["success_theory"]),
                "{:.4f}".format(r["fail_measured"]), "{:.4f}".format(r["fail_theory"]),
            ])


def print_table(rows):
    print("체이닝, M = {}, 시드 {}개 평균, 실패 탐색 {}개".format(M, len(SEEDS), FAILED_SEARCHES))
    print("{:>5} {:>6} | {:>8} {:>8} {:>7} | {:>8} {:>8} {:>7}".format(
        "α", "n", "성공실험", "성공이론", "차이", "실패실험", "실패이론", "차이"))
    print("-" * 72)
    for r in rows:
        print("{:>5} {:>6} | {:>8.3f} {:>8.3f} {:>+7.3f} | {:>8.3f} {:>8.3f} {:>+7.3f}".format(
            r["alpha"], r["n"],
            r["success_measured"], r["success_theory"], r["success_measured"] - r["success_theory"],
            r["fail_measured"], r["fail_theory"], r["fail_measured"] - r["fail_theory"]))


# SVG 그래프 -----------------------------------------------------------------

COLOR_SUCCESS = "#257de0"   # 파랑
COLOR_FAIL = "#f47230"      # 주황
TEXT = "#191919"
TEXT_2 = "#666666"
GRID = "#e6e6e6"
AXIS = "#b3b3b3"


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def svg_chart(rows, title, series, x_max, y_max, x_ticks, y_ticks,
              x_label="적재율 α = n / M", y_label="평균 비교 횟수"):
    """series: [(이름, 색, 키, 실선?, 점?)] — 실험은 실선+점, 이론은 점선."""
    width, height = 760, 460
    left, right, top, bottom = 70, 190, 56, 62
    pw, ph = width - left - right, height - top - bottom

    def x(v):
        return left + pw * v / x_max

    def y(v):
        return top + ph * (1 - v / y_max)

    out = []
    out.append('<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
               'viewBox="0 0 {w} {h}" font-family="system-ui, -apple-system, \'Segoe UI\', '
               '\'Noto Sans KR\', \'Malgun Gothic\', sans-serif">'.format(w=width, h=height))
    out.append('<rect width="100%" height="100%" fill="#ffffff"/>')
    out.append('<text x="{}" y="28" font-size="16" font-weight="600" fill="{}">{}</text>'
               .format(left, TEXT, _esc(title)))

    # 격자와 눈금
    for t in y_ticks:
        out.append('<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="{}" stroke-width="1"/>'
                   .format(left, y(t), left + pw, y(t), GRID))
        out.append('<text x="{:.1f}" y="{:.1f}" font-size="12" fill="{}" text-anchor="end">{}</text>'
                   .format(left - 8, y(t) + 4, TEXT_2, _fmt(t)))
    for t in x_ticks:
        out.append('<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="{}" stroke-width="1"/>'
                   .format(x(t), top + ph, x(t), top + ph + 5, AXIS))
        out.append('<text x="{:.1f}" y="{:.1f}" font-size="12" fill="{}" text-anchor="middle">{}</text>'
                   .format(x(t), top + ph + 20, TEXT_2, _fmt(t)))
    out.append('<line x1="{}" y1="{:.1f}" x2="{}" y2="{:.1f}" stroke="{}" stroke-width="1"/>'
               .format(left, top + ph, left + pw, top + ph, AXIS))
    out.append('<line x1="{}" y1="{}" x2="{}" y2="{:.1f}" stroke="{}" stroke-width="1"/>'
               .format(left, top, left, top + ph, AXIS))

    # 축 이름
    out.append('<text x="{:.1f}" y="{}" font-size="13" fill="{}" text-anchor="middle">{}</text>'
               .format(left + pw / 2, height - 16, TEXT, _esc(x_label)))
    out.append('<text transform="translate(20 {:.1f}) rotate(-90)" font-size="13" fill="{}" '
               'text-anchor="middle">{}</text>'.format(top + ph / 2, TEXT, _esc(y_label)))

    # 선과 점
    for name, color, key, solid, dots in series:
        pts = " ".join("{:.1f},{:.1f}".format(x(r["alpha"]), y(r[key])) for r in rows)
        dash = "" if solid else ' stroke-dasharray="6 5"'
        out.append('<polyline points="{}" fill="none" stroke="{}" stroke-width="2" '
                   'stroke-linejoin="round" stroke-linecap="round"{}/>'.format(pts, color, dash))
        if dots:
            for r in rows:
                out.append('<circle cx="{:.1f}" cy="{:.1f}" r="4.5" fill="{}" stroke="#ffffff" '
                           'stroke-width="2"><title>{} · α = {}: {:.3f}</title></circle>'
                           .format(x(r["alpha"]), y(r[key]), color, _esc(name), _fmt(r["alpha"]), r[key]))

    # 범례
    lx, ly = left + pw + 24, top + 8
    for i, (name, color, key, solid, dots) in enumerate(series):
        yy = ly + i * 26
        dash = "" if solid else ' stroke-dasharray="6 5"'
        out.append('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="{}" stroke-width="2"{}/>'
                   .format(lx, yy, lx + 28, yy, color, dash))
        if dots:
            out.append('<circle cx="{}" cy="{}" r="4.5" fill="{}" stroke="#ffffff" stroke-width="2"/>'
                       .format(lx + 14, yy, color))
        out.append('<text x="{}" y="{}" font-size="13" fill="{}">{}</text>'
                   .format(lx + 38, yy + 4, TEXT, _esc(name)))

    out.append('<text x="{}" y="{}" font-size="11" fill="{}">M = {}, 시드 {}개 평균</text>'
               .format(lx, ly + len(series) * 26 + 10, TEXT_2, M, len(SEEDS)))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def _fmt(v):
    return ("{:.2f}".format(v)).rstrip("0").rstrip(".")


def write_svg(rows, path):
    series = [
        ("성공 · 실험", COLOR_SUCCESS, "success_measured", True, True),
        ("성공 · 이론 1 + α/2", COLOR_SUCCESS, "success_theory", False, False),
        ("실패 · 실험", COLOR_FAIL, "fail_measured", True, True),
        ("실패 · 이론 α", COLOR_FAIL, "fail_theory", False, False),
    ]
    svg = svg_chart(rows, "체이닝: 적재율에 따른 평균 비교 횟수", series,
                    x_max=4, y_max=4.5,
                    x_ticks=[0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4],
                    y_ticks=[0, 1, 2, 3, 4])
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)


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
