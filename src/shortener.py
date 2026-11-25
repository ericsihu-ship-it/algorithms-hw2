"""URL 단축기.

- 코드는 카운터를 base62로 바꿔 만든다: "1", "2", ..., "9", "a", ...
  URL의 해시값으로 코드를 만들지 않는다 (서로 다른 URL이 같은 코드를 받을 수 있으므로).
- 같은 URL을 다시 넣으면 처음 받은 코드를 돌려준다.
- 테이블 두 개: by_url (URL → 코드), by_code (코드 → URL).
  table_factory로 어떤 해시 테이블을 쓸지 고를 수 있다.
"""

from base62 import encode
from hash_table import HashTable

MAX_URL_LENGTH = 2048
ALLOWED_SCHEMES = ("http://", "https://")


def normalize_url(url):
    """SPEC.md 4.2절 검사. 통과하면 앞뒤 공백을 지운 URL을, 아니면 예외."""
    if not isinstance(url, str):
        raise TypeError("URL은 문자열이어야 합니다: {!r}".format(url))
    url = url.strip()

    lower = url.lower()
    scheme = None
    for s in ALLOWED_SCHEMES:
        if lower.startswith(s):
            scheme = s
            break
    if scheme is None:
        raise ValueError("http:// 또는 https://로 시작해야 합니다")

    rest = url[len(scheme):]
    host_end = len(rest)
    for i, ch in enumerate(rest):
        if ch in "/?#":
            host_end = i
            break
    if host_end == 0:
        raise ValueError("호스트가 없습니다")

    for ch in url:
        if ch.isspace():
            raise ValueError("URL 중간에 공백이 있습니다")
        if not ("!" <= ch <= "~"):
            raise ValueError("ASCII가 아닌 글자나 제어 문자가 있습니다: {!r} "
                             "(한글은 퍼센트 인코딩해서 넣으세요)".format(ch))

    if len(url) > MAX_URL_LENGTH:
        raise ValueError("URL이 너무 깁니다 ({}자 이하)".format(MAX_URL_LENGTH))
    return url


class Shortener:
    def __init__(self, table_factory=HashTable):
        self.table_factory = table_factory
        self.by_url = table_factory()
        self.by_code = table_factory()
        self._counter = 0

    def __len__(self):
        return len(self.by_url)

    def shorten(self, url):
        """URL을 받아 짧은 코드를 돌려준다. 잘못된 URL은 ValueError/TypeError."""
        url = normalize_url(url)
        code = self.by_url.get(url)
        if code is not None:
            return code
        self._counter += 1
        code = encode(self._counter)
        self.by_url.put(url, code)
        self.by_code.put(code, url)
        return code

    def expand(self, code):
        """코드에 해당하는 원래 URL. 없거나 잘못된 코드는 None."""
        if not isinstance(code, str) or code == "":
            return None
        return self.by_code.get(code)
