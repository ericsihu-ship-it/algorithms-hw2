"""base62 인코딩.

글자 순서는 0-9, a-z, A-Z (모두 62글자)이다.
    encode(0)  -> "0"
    encode(61) -> "Z"
    encode(62) -> "10"

encode(n)은 0 이상의 정수만 받는다. 음수는 ValueError, 정수가 아니면 TypeError.
decode(s)는 encode의 역변환이다. 빈 문자열이나 62글자 밖의 글자는 ValueError.
"""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)  # 62


def _digit_value(ch):
    """글자 하나를 0~61 값으로 바꾼다. 알파벳 밖의 글자는 ValueError."""
    if "0" <= ch <= "9":
        return ord(ch) - ord("0")
    if "a" <= ch <= "z":
        return ord(ch) - ord("a") + 10
    if "A" <= ch <= "Z":
        return ord(ch) - ord("A") + 36
    raise ValueError("base62에 없는 글자입니다: {!r}".format(ch))


def encode(n):
    """0 이상의 정수 n을 base62 문자열로 바꾼다."""
    # bool은 int의 하위 클래스라서 따로 막는다 (encode(True)가 "1"이 되지 않게).
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("정수만 인코딩할 수 있습니다: {!r}".format(n))
    if n < 0:
        raise ValueError("음수는 인코딩할 수 없습니다: {}".format(n))
    if n == 0:
        return ALPHABET[0]

    digits = []
    while n > 0:
        n, r = divmod(n, BASE)
        digits.append(ALPHABET[r])
    digits.reverse()
    return "".join(digits)


def decode(s):
    """base62 문자열 s를 정수로 바꾼다."""
    if not isinstance(s, str):
        raise TypeError("문자열만 디코딩할 수 있습니다: {!r}".format(s))
    if s == "":
        raise ValueError("빈 문자열은 디코딩할 수 없습니다")

    n = 0
    for ch in s:
        n = n * BASE + _digit_value(ch)
    return n
