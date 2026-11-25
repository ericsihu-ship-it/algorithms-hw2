"""단축기 경계 사례 17~27번을 선형 탐사 테이블로 다시 돌린다 (SPEC.md 8.5절 39번).

test_shortener.py는 고치지 않는다. 그 파일의 테스트 클래스를 물려받고,
테스트가 부르는 Shortener만 '선형 탐사를 쓰는 Shortener'로 바꿔 끼운다.
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import test_shortener as base  # noqa: E402
from hash_table import HashTable  # noqa: E402
from linear_probing import LinearProbingTable  # noqa: E402
from shortener import MAX_URL_LENGTH, Shortener  # noqa: E402,F401


def LinearShortener():
    return Shortener(table_factory=LinearProbingTable)


@mock.patch.object(base, "Shortener", LinearShortener)
class TestCodesLinear(base.TestCodes):
    pass


@mock.patch.object(base, "Shortener", LinearShortener)
class TestExpandLinear(base.TestExpand):
    pass


@mock.patch.object(base, "Shortener", LinearShortener)
class TestValidationLinear(base.TestValidation):
    pass


@mock.patch.object(base, "Shortener", LinearShortener)
class TestManyLinear(base.TestMany):
    pass


class TestTableChoice(unittest.TestCase):
    def test_default_is_chaining(self):
        s = Shortener()
        self.assertIsInstance(s.by_url, HashTable)
        self.assertIsInstance(s.by_code, HashTable)

    def test_linear_probing_is_used(self):
        s = LinearShortener()
        self.assertIsInstance(s.by_url, LinearProbingTable)
        self.assertIsInstance(s.by_code, LinearProbingTable)

    def test_patched_tests_really_use_linear_probing(self):
        with mock.patch.object(base, "Shortener", LinearShortener):
            self.assertIsInstance(base.Shortener().by_url, LinearProbingTable)

    def test_same_codes_with_both_tables(self):
        urls = ["https://example.com/{}".format(i) for i in range(300)] * 2
        a, b = Shortener(), LinearShortener()
        self.assertEqual([a.shorten(u) for u in urls], [b.shorten(u) for u in urls])


if __name__ == "__main__":
    unittest.main()
