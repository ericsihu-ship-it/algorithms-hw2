"""SPEC.md 6절 단축기 경계 사례 (17~27번)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from shortener import MAX_URL_LENGTH, Shortener  # noqa: E402


class TestCodes(unittest.TestCase):
    # 17. 첫 코드는 "1", 그다음은 "2", 열째는 "a"
    def test_codes_come_from_counter(self):
        s = Shortener()
        codes = [s.shorten("https://example.com/{}".format(i)) for i in range(1, 11)]
        self.assertEqual(codes[0], "1")
        self.assertEqual(codes[1], "2")
        self.assertEqual(codes[8], "9")
        self.assertEqual(codes[9], "a")

    # 18. 같은 URL을 두 번 넣으면 같은 코드
    def test_same_url_same_code(self):
        s = Shortener()
        c1 = s.shorten("https://a.com")
        c2 = s.shorten("https://a.com")
        self.assertEqual(c1, c2)
        self.assertEqual(len(s), 1)
        self.assertEqual(s.shorten("https://b.com"), "2")  # 카운터가 늘지 않았다

    # 19. 앞뒤 공백만 다른 URL은 같은 URL
    def test_surrounding_whitespace_ignored(self):
        s = Shortener()
        c1 = s.shorten("https://a.com")
        c2 = s.shorten("  https://a.com\n")
        self.assertEqual(c1, c2)
        self.assertEqual(s.expand(c1), "https://a.com")

    def test_trailing_slash_is_different_url(self):
        s = Shortener()
        self.assertNotEqual(s.shorten("https://a.com"), s.shorten("https://a.com/"))


class TestExpand(unittest.TestCase):
    # 20. expand(shorten(url)) == url
    def test_round_trip(self):
        s = Shortener()
        for url in ("https://a.com", "http://b.org/path?q=1&r=2#frag",
                    "https://ko.wikipedia.org/wiki/%ED%95%B4%EC%8B%9C"):
            with self.subTest(url=url):
                self.assertEqual(s.expand(s.shorten(url)), url)

    # 21. 없는 코드, 빈 문자열, 이상한 코드는 None
    def test_missing_codes_return_none(self):
        s = Shortener()
        s.shorten("https://a.com")
        for code in ("2", "zz", "", "!!", "01", None, 1):
            with self.subTest(code=code):
                self.assertIsNone(s.expand(code))


class TestValidation(unittest.TestCase):
    # 22. 받지 않는 스킴과 호스트 없는 주소
    def test_rejects_bad_schemes_and_missing_host(self):
        s = Shortener()
        for bad in ("ftp://a.com/file", "javascript:alert(1)", "example.com",
                    "https://", "http:///path", "", "   ", "mailto:a@b.com"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    s.shorten(bad)
        self.assertEqual(len(s), 0)

    # 23. 중간에 공백·탭·줄바꿈, 제어 문자, ASCII가 아닌 글자
    def test_rejects_whitespace_control_and_non_ascii(self):
        s = Shortener()
        for bad in ("https://a.com/a b", "https://a.com/\tx", "https://a.com/\nx",
                    "https://a.com/\x00", "https://a.com/\x7f",
                    "https://ko.wikipedia.org/wiki/해시", "https://한글.kr", "https://a.com/café"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    s.shorten(bad)

    # 24. 2048자는 받고 2049자는 거절
    def test_length_limit(self):
        s = Shortener()
        prefix = "https://a.com/"
        ok = prefix + "x" * (MAX_URL_LENGTH - len(prefix))
        too_long = ok + "x"
        self.assertEqual(len(ok), 2048)
        self.assertEqual(s.expand(s.shorten(ok)), ok)
        with self.assertRaises(ValueError):
            s.shorten(too_long)

    # 25. 문자열이 아닌 URL
    def test_non_string_raises_type_error(self):
        s = Shortener()
        for bad in (None, 123, b"https://a.com"):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    s.shorten(bad)

    # 26. 대문자 스킴도 받는다
    def test_uppercase_scheme_ok(self):
        s = Shortener()
        code = s.shorten("HTTPS://A.COM/X")
        self.assertEqual(s.expand(code), "HTTPS://A.COM/X")

    def test_rejected_url_does_not_use_counter(self):
        s = Shortener()
        with self.assertRaises(ValueError):
            s.shorten("ftp://a.com")
        self.assertEqual(s.shorten("https://a.com"), "1")


class TestMany(unittest.TestCase):
    # 27. 많이 넣어 테이블이 커져도 모두 돌아간다
    def test_many_urls(self):
        s = Shortener()
        urls = ["https://example.com/page/{}".format(i) for i in range(2000)]
        codes = [s.shorten(u) for u in urls]
        self.assertEqual(len(s), 2000)
        self.assertGreater(s.by_url.capacity, 11)  # 테이블이 늘어났다
        for u, c in zip(urls, codes):
            self.assertEqual(s.expand(c), u)
            self.assertEqual(s.shorten(u), c)


if __name__ == "__main__":
    unittest.main()
