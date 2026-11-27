"""URL 단축 웹 서버. 표준 모듈 http.server만 쓴다.

    make serve                         (= python3 src/server.py --port 8000)
    make serve TABLE=linear            선형 탐사 테이블로 실행 (과제)
    python3 src/server.py --demo       예시 URL 몇 개를 미리 넣고 시작

    GET  /            URL 입력 폼
    POST /shorten     url=... → 짧은 링크 화면 (잘못된 URL은 400)
    GET  /table       해시 테이블 화면 (?view=code 이면 코드 → URL 테이블)
    GET  /<코드>      302로 원래 URL로 이동, 없으면 404

짧은 링크의 주소는 X-Forwarded-Proto / X-Forwarded-Host 헤더를 먼저 쓴다.
Codespaces에서 localhost:8000이 아니라 바깥 주소가 나오게 하기 위해서다.
"""

import argparse
import html
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hash_table import HORNER_BASE, HashTable, horner_steps  # noqa: E402
from linear_probing import LinearProbingTable  # noqa: E402
from shortener import MAX_URL_LENGTH, Shortener  # noqa: E402

MAX_BODY = 8 * 1024
RESERVED = ("", "shorten", "table", "favicon.ico")

# --table 값, 테이블 클래스, 화면에 쓸 이름
TABLE_CHOICES = (
    ("chaining", HashTable, "개별 체이닝"),
    ("linear", LinearProbingTable, "선형 탐사"),
)

SHORTENER = Shortener()
TABLE_LABEL = "개별 체이닝"
LOCK = threading.Lock()

DEMO_URLS = [
    "https://www.yonsei.ac.kr",
    "https://lec-algorithm.github.io/lecture/slides/hw2-2026/",
    "https://github.com",
    "https://en.wikipedia.org/wiki/Hash_table",
    "https://docs.python.org/3/library/http.server.html",
    "https://en.wikipedia.org/wiki/Horner%27s_method",
    "https://www.google.com/search?q=base62",
    "https://news.ycombinator.com",
    "https://example.com/a",
    "https://example.com/b",
    "https://example.com/c",
    "https://example.com/d",
]

esc = html.escape


# ---------------------------------------------------------------------------
# 도움 함수


def first_header_value(value):
    """'a, b' 처럼 여러 개가 오면 첫 번째만."""
    if not value:
        return ""
    return value.split(",")[0].strip()


# ---------------------------------------------------------------------------
# HTML


STYLE = """
:root { color-scheme: light; --ink:#191919; --ink2:#666; --line:#e2e2e2; --soft:#f6f7f9;
        --accent:#257de0; --bad:#c62828; }
* { box-sizing: border-box; }
body { margin:0; font-family: system-ui, -apple-system, "Segoe UI", "Noto Sans KR",
       "Malgun Gothic", sans-serif; color:var(--ink); background:#fff; line-height:1.5; }
main { max-width: 960px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 1.5rem; margin: 0 0 4px; }
h2 { font-size: 1.1rem; margin: 28px 0 8px; }
p.sub { color: var(--ink2); margin: 0 0 20px; }
nav { display:flex; gap:16px; margin-bottom: 20px; font-size: .95rem; }
a { color: var(--accent); }
form.shorten { display:flex; gap:8px; flex-wrap:wrap; }
form.shorten input[type=text] { flex:1 1 320px; padding:10px 12px; font-size:1rem;
       border:1px solid #bbb; border-radius:8px; }
button { padding:10px 18px; font-size:1rem; border:0; border-radius:8px;
         background:var(--accent); color:#fff; cursor:pointer; }
button.ghost { background:var(--soft); color:var(--ink); border:1px solid var(--line); }
.error { color: var(--bad); margin: 12px 0 0; }
.result { margin-top:20px; padding:16px; border:1px solid var(--line); border-radius:10px;
          background:var(--soft); }
.result .link { display:flex; gap:8px; flex-wrap:wrap; align-items:center; font-size:1.15rem; }
.result .link input { flex:1 1 260px; font-size:1.05rem; padding:8px 10px;
                      border:1px solid var(--line); border-radius:6px; }
.orig { color: var(--ink2); word-break: break-all; margin-top:8px; }
.stats { display:flex; gap:12px; flex-wrap:wrap; margin: 8px 0 16px; }
.stat { border:1px solid var(--line); border-radius:8px; padding:8px 12px; min-width:110px; }
.stat b { display:block; font-size:1.2rem; }
.stat span { color: var(--ink2); font-size:.85rem; }
.formula { font-family: ui-monospace, Menlo, Consolas, monospace; background:var(--soft);
           padding:2px 6px; border-radius:4px; }
.slots { border-top:1px solid var(--line); }
.slot { display:flex; gap:10px; align-items:flex-start; padding:8px 0;
        border-bottom:1px solid var(--line); }
.idx { flex:0 0 52px; font-family: ui-monospace, Menlo, Consolas, monospace;
       color: var(--ink2); padding-top:6px; text-align:right; }
.chain { display:flex; flex-wrap:wrap; align-items:flex-start; gap:6px; min-width:0; }
.empty { color:#aaa; padding-top:6px; }
.arrow { color: var(--ink2); padding-top:6px; }
.node { border:1px solid #c9d6e8; background:#f3f8fe; border-radius:8px; padding:6px 10px;
        max-width: 100%; }
.node .key { font-size:.9rem; word-break: break-all; max-width: 360px; }
.node .meta { font-size:.85rem; color: var(--ink2); }
.node code { font-weight:600; color: var(--ink); }
details { margin-top:4px; }
summary { cursor:pointer; font-size:.85rem; color: var(--accent); }
table.steps { border-collapse: collapse; margin-top:6px; font-size:.8rem;
              font-family: ui-monospace, Menlo, Consolas, monospace; }
table.steps th, table.steps td { border:1px solid var(--line); padding:2px 6px; text-align:right; }
table.steps th { background: var(--soft); font-weight:600; }
table.steps td.ch { text-align:center; }
.final { font-size:.85rem; margin-top:4px; }
.node.moved { border-color:#f2b38f; background:#fff6f0; }
.probe { font-size:.82rem; color: var(--ink2); margin-top:2px; word-break: break-all; }
.slot.filled { background: linear-gradient(90deg, #f6f7f9 0, #f6f7f9 62px, transparent 62px); }
.cl { font-size:.7rem; color:#b3541e; line-height:1.2; margin-top:4px; }
.badge { display:inline-block; font-size:.8rem; padding:1px 8px; border-radius:999px;
         background: var(--soft); border:1px solid var(--line); color: var(--ink2); }
"""


def page(title, body):
    return """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{style}</style></head>
<body><main>
<nav><a href="/">줄이기</a><a href="/table">해시 테이블</a></nav>
{body}
</main></body></html>
""".format(title=esc(title), style=STYLE, body=body)


def form_html(value="", error=None):
    err = '<p class="error">{}</p>'.format(esc(error)) if error else ""
    return """
<form class="shorten" method="post" action="/shorten">
  <input type="text" name="url" inputmode="url" autocomplete="off" autofocus
         placeholder="https://..." value="{value}" maxlength="{maxlen}">
  <button type="submit">줄이기</button>
</form>{err}""".format(value=esc(value), maxlen=MAX_URL_LENGTH + 100, err=err)


def home_page(value="", error=None):
    body = """
<h1>URL 단축기</h1>
<p class="sub">긴 URL을 넣으면 짧은 링크를 만들어 줍니다. 저장은 직접 만든 해시 테이블에 합니다. <span class="badge">{}</span></p>
""".format(esc(TABLE_LABEL)) + form_html(value, error)
    return page("URL 단축기", body)


def result_page(url, code, short):
    body = """
<h1>URL 단축기</h1>
<p class="sub">짧은 링크를 만들었습니다.</p>
{form}
<div class="result">
  <div class="link">
    <input id="short" type="text" readonly value="{short}">
    <button class="ghost" type="button" onclick="copyLink()">복사</button>
    <a href="{short}" target="_blank" rel="noopener">열기</a>
  </div>
  <div class="orig">코드 <code>{code}</code> → {url}</div>
</div>
<script>
function copyLink() {{
  var el = document.getElementById('short');
  el.select();
  if (navigator.clipboard) {{ navigator.clipboard.writeText(el.value); }}
  else {{ document.execCommand('copy'); }}
}}
</script>""".format(form=form_html(), short=esc(short), code=esc(code), url=esc(url))
    return page("짧은 링크", body)


def not_found_page(path):
    body = """
<h1>없는 주소입니다</h1>
<p class="sub"><code>{}</code>에 해당하는 짧은 링크가 없습니다.</p>
<p><a href="/">새로 줄이기</a></p>""".format(esc(path))
    return page("404", body)


def steps_table(key, m, slot):
    rows = []
    for i, (ch, code_point, before, after) in enumerate(horner_steps(key, m), 1):
        rows.append(
            "<tr><td>{i}</td><td class=\"ch\">{ch}</td><td>{o}</td><td>{b}</td>"
            "<td>{raw}</td><td>{a}</td></tr>".format(
                i=i, ch=esc(ch), o=code_point, b=before,
                raw=before * HORNER_BASE + code_point, a=after))
    if not rows:
        rows.append('<tr><td colspan="6">빈 문자열: h = 0</td></tr>')
    return """
<details><summary>호너 해시 계산 펼치기</summary>
<table class="steps">
<tr><th>#</th><th>글자</th><th>ord</th><th>이전 h</th><th>h×{b}+ord</th><th>mod {m}</th></tr>
{rows}
</table>
<div class="final">최종 h = <b>{slot}</b> → 칸 {slot}</div>
</details>""".format(b=HORNER_BASE, m=m, rows="\n".join(rows), slot=slot)


def node_html(view, key, value, base_url, key_name, value_name, m, home, extra="", moved=False):
    if view == "code":
        code = key
    else:
        code = value
    short = "{}/{}".format(base_url, code)
    return """
<div class="node{cls}">
  <div class="key"><b>{kname}</b> {key}</div>
  <div class="meta">{vname} <code>{value}</code> · <a href="{short}">{short_txt}</a></div>
  {extra}
  {steps}
</div>""".format(cls=" moved" if moved else "", kname=key_name, key=esc(key), vname=value_name,
                 value=esc(value), short=esc(short), short_txt=esc(short), extra=extra,
                 steps=steps_table(key, m, home))


def table_page(base_url, view):
    with LOCK:
        if view == "code":
            table, key_name, value_name = SHORTENER.by_code, "코드", "URL"
        else:
            table, key_name, value_name = SHORTENER.by_url, "URL", "코드"
        linear = isinstance(table, LinearProbingTable)
        m = table.capacity
        n = len(table)
        slots = table.slots()
        load = table.load_factor()
        max_load = table.max_load
        resizes = table.resize_count
        paths = []
        clusters = []
        if linear:
            for chain in slots:
                paths.append(table.probe_sequence(chain[0][0]) if chain else None)
            clusters = table.clusters()

    switch = ('<a href="/table">URL → 코드 테이블 보기</a>' if view == "code"
              else '<a href="/table?view=code">코드 → URL 테이블 보기</a>')
    if linear:
        lines, stats = linear_rows(slots, paths, clusters, view, base_url, key_name, value_name, m, n)
        method = "선형 탐사 (빈 칸 ∅, 충돌하면 다음 칸으로. 마지막 칸 다음은 0번)"
    else:
        lines, stats = chaining_rows(slots, view, base_url, key_name, value_name, m)
        method = "개별 체이닝"

    body = """
<h1>해시 테이블 ({kname} → {vname})</h1>
<p class="sub">{method}. 해시는 <span class="formula">h = (h × {b} + ord(글자)) mod M</span>. {switch}</p>
<div class="stats">
  <div class="stat"><b>{m}</b><span>칸 수 M</span></div>
  <div class="stat"><b>{n}</b><span>키 개수 n</span></div>
  <div class="stat"><b>{load:.3f}</b><span>적재율 n/M</span></div>
  <div class="stat"><b>{max_load}</b><span>max_load</span></div>
  {stats}
  <div class="stat"><b>{resizes}</b><span>늘린 횟수</span></div>
</div>
<div class="slots">
{lines}
</div>""".format(kname=key_name, vname=value_name, method=method, b=HORNER_BASE, switch=switch,
                 m=m, n=n, load=load, max_load="없음" if max_load is None else max_load,
                 stats=stats, resizes=resizes, lines="\n".join(lines))
    return page("해시 테이블", body)


def stat_html(value, label):
    return '<div class="stat"><b>{}</b><span>{}</span></div>'.format(esc(str(value)), esc(label))


def chaining_rows(slots, view, base_url, key_name, value_name, m):
    longest = 0
    used = 0
    lines = []
    for i, chain in enumerate(slots):
        if chain:
            used += 1
        if len(chain) > longest:
            longest = len(chain)
        parts = []
        for j, (key, value) in enumerate(chain):
            if j > 0:
                parts.append('<span class="arrow">→</span>')
            parts.append(node_html(view, key, value, base_url, key_name, value_name, m, i))
        if not parts:
            parts.append('<span class="empty">∅</span>')
        lines.append('<div class="slot"><div class="idx">[{}]</div><div class="chain">{}</div></div>'
                     .format(i, "".join(parts)))
    stats = stat_html(used, "사용 중인 칸") + stat_html(longest, "가장 긴 체인")
    return lines, stats


def linear_rows(slots, paths, clusters, view, base_url, key_name, value_name, m, n):
    cluster_len_at = [0] * m
    longest = 0
    for start, length in clusters:
        cluster_len_at[start] = length
        if length > longest:
            longest = length

    total_probes = 0
    moved_count = 0
    lines = []
    for i, chain in enumerate(slots):
        label = ""
        if cluster_len_at[i]:
            label = '<div class="cl">클러스터<br>{}칸</div>'.format(cluster_len_at[i])
        if not chain:
            content = '<span class="empty">∅</span>'
        else:
            key, value = chain[0]
            path = paths[i]
            home = path[0]
            distance = len(path) - 1
            total_probes += len(path)
            if distance:
                moved_count += 1
                route = " → ".join("[{}]".format(p) for p in path)
                extra = ('<div class="probe">홈 칸 [{}]에서 {}칸 밀림 · 탐사 {} ({}칸 확인)</div>'
                         .format(home, distance, route, len(path)))
            else:
                extra = '<div class="probe">홈 칸 그대로 [{}] (1칸 확인)</div>'.format(home)
            content = node_html(view, key, value, base_url, key_name, value_name, m, home,
                                extra=extra, moved=distance > 0)
        lines.append('<div class="slot{}"><div class="idx">[{}]{}</div><div class="chain">{}</div></div>'
                     .format(" filled" if chain else "", i, label, content))

    average = "{:.2f}".format(total_probes / n) if n else "-"
    stats = (stat_html(len(clusters), "클러스터 수") + stat_html(longest, "가장 긴 클러스터")
             + stat_html(moved_count, "홈에서 밀린 키") + stat_html(average, "성공 탐색 평균 칸 수"))
    return lines, stats


# ---------------------------------------------------------------------------
# 요청 처리


class Handler(BaseHTTPRequestHandler):
    server_version = "HW2Shortener/1.0"

    def base_url(self):
        host = first_header_value(self.headers.get("X-Forwarded-Host"))
        if host:
            proto = first_header_value(self.headers.get("X-Forwarded-Proto")) or "https"
            return "{}://{}".format(proto, host)
        host = self.headers.get("Host")
        if host:
            return "http://{}".format(host)
        return "http://localhost:{}".format(self.server.server_address[1])

    def send_html(self, status, text):
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parts = urlsplit(self.path)
        name = parts.path.lstrip("/")

        if name == "":
            self.send_html(200, home_page())
            return
        if name == "table":
            view = ""
            for k, v in parse_qsl(parts.query):
                if k == "view":
                    view = v
            self.send_html(200, table_page(self.base_url(), view))
            return
        if name in RESERVED or "/" in name:
            self.send_html(404 if name != "shorten" else 405, not_found_page(parts.path))
            return

        with LOCK:
            url = SHORTENER.expand(name)
        if url is None:
            self.send_html(404, not_found_page(parts.path))
            return
        # SPEC.md 4.2·5절: 저장된 URL은 ASCII뿐이라 latin-1 헤더에 그대로 넣을 수 있다
        self.send_response(302)
        self.send_header("Location", url)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_POST(self):
        if urlsplit(self.path).path != "/shorten":
            self.send_html(405, not_found_page(self.path))
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            self.send_html(413, home_page(error="요청이 너무 큽니다."))
            return

        body = self.rfile.read(length).decode("utf-8", errors="replace")
        url = ""
        for k, v in parse_qsl(body, keep_blank_values=True):
            if k == "url":
                url = v

        try:
            with LOCK:
                code = SHORTENER.shorten(url)
                clean = SHORTENER.expand(code)
        except (ValueError, TypeError) as e:
            self.send_html(400, home_page(value=url, error="줄일 수 없는 URL입니다: {}".format(e)))
            return
        self.send_html(200, result_page(clean, code, "{}/{}".format(self.base_url(), code)))


def main(argv=None):
    parser = argparse.ArgumentParser(description="URL 단축 웹 서버")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--demo", action="store_true", help="예시 URL을 미리 넣는다")
    parser.add_argument("--table", choices=[c[0] for c in TABLE_CHOICES], default="chaining",
                        help="해시 테이블 종류 (기본: chaining)")
    args = parser.parse_args(argv)

    global SHORTENER, TABLE_LABEL
    for name, factory, label in TABLE_CHOICES:
        if name == args.table:
            SHORTENER = Shortener(table_factory=factory)
            TABLE_LABEL = label

    if args.demo:
        for u in DEMO_URLS:
            SHORTENER.shorten(u)

    httpd = ThreadingHTTPServer((args.bind, args.port), Handler)
    print("http://localhost:{} 에서 실행 중 · 테이블: {} (Ctrl+C로 종료)".format(args.port, TABLE_LABEL),
          flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 멈췄습니다.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
