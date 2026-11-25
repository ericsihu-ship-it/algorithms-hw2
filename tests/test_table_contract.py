"""두 해시 테이블(체이닝, 선형 탐사)이 똑같이 지켜야 하는 동작 (SPEC.md 8.5절 32번).

TableContract 하나를 두 테이블에 각각 돌린다. 테이블마다 다른 동작
(빈 칸에서 실패했을 때 비교 횟수, 꽉 찬 테이블 등)은 각자의 테스트 파일에 있다.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hash_table import HashTable, horner  # noqa: E402
from linear_probing import LinearProbingTable  # noqa: E402


def same_home_keys(m, home, count):
    """칸 수 m에서 홈 칸이 home인 서로 다른 키 count개."""
    keys = []
    i = 0
    while len(keys) < count:
        k = "key{}".format(i)
        if horner(k, m) == home:
            keys.append(k)
        i += 1
    return keys


class TableContract:
    Table = None  # 하위 클래스가 정한다

    # 빈 테이블
    def test_empty(self):
        t = self.Table()
        self.assertEqual(len(t), 0)
        self.assertEqual(t.capacity, 11)
        self.assertIsNone(t.get("x"))
        self.assertEqual(t.get("x", "기본"), "기본")
        self.assertFalse("x" in t)
        self.assertIsNone(t.find("x")[0])
        self.assertEqual(t.load_factor(), 0)
        self.assertEqual(t.slots(), [[] for _ in range(11)])

    def test_bad_capacity(self):
        for bad in (0, -3, 1.5, True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.Table(capacity=bad)

    # 넣기와 찾기
    def test_put_get(self):
        t = self.Table()
        t.put("https://a.com", "1")
        self.assertEqual(t.get("https://a.com"), "1")
        self.assertEqual(t.find("https://a.com"), ("1", 1))
        self.assertTrue("https://a.com" in t)
        self.assertEqual(len(t), 1)

    def test_put_same_key_replaces_value(self):
        t = self.Table()
        t.put("k", 1)
        t.put("k", 2)
        self.assertEqual(t.get("k"), 2)
        self.assertEqual(len(t), 1)

    def test_empty_string_key(self):
        t = self.Table()
        t.put("", "빈 키")
        self.assertEqual(t.get(""), "빈 키")
        self.assertEqual(t.slots()[0], [("", "빈 키")])

    def test_non_string_key_raises(self):
        t = self.Table()
        with self.assertRaises(TypeError):
            t.put(1, "x")
        with self.assertRaises(TypeError):
            t.get(None)
        with self.assertRaises(TypeError):
            t.find(3.0)
        with self.assertRaises(TypeError):
            5 in t

    def test_similar_keys_are_distinct(self):
        t = self.Table(capacity=11, max_load=None)
        for i, k in enumerate(("ab", "ba", "https://a.com/x1", "https://a.com/x2")):
            t.put(k, i)
        self.assertEqual([t.get(k) for k in ("ab", "ba", "https://a.com/x1", "https://a.com/x2")],
                         [0, 1, 2, 3])

    def test_many_keys(self):
        t = self.Table()
        n = 5000
        for i in range(n):
            t.put("https://example.com/{}".format(i), i)
        self.assertEqual(len(t), n)
        for i in range(n):
            self.assertEqual(t.get("https://example.com/{}".format(i)), i)
        self.assertIsNone(t.get("https://example.com/{}".format(n)))

    # 충돌: 같은 홈 칸으로 가는 키 다섯 개를 찾을 때 1, 2, 3, 4, 5번 비교
    def test_colliding_keys_counts(self):
        t = self.Table(capacity=11, max_load=None)
        keys = same_home_keys(11, 4, 5)
        for j, k in enumerate(keys):
            t.put(k, j)
        for j, k in enumerate(keys):
            self.assertEqual(t.find(k), (j, j + 1))

    # 크기 늘리기: 같은 max_load면 같은 시점에 같은 크기로
    def test_grows_to_next_prime(self):
        t = self.Table(capacity=11, max_load=0.5)
        for i in range(5):
            t.put("k{}".format(i), i)
        self.assertEqual(t.capacity, 11)   # 5/11 <= 0.5
        t.put("k5", 5)
        self.assertEqual(t.capacity, 23)   # 6/11 > 0.5 → 22 이상의 가장 작은 소수
        for i in range(6, 12):
            t.put("k{}".format(i), i)
        self.assertEqual(t.capacity, 47)   # 12/23 > 0.5 → 46 이상의 가장 작은 소수
        for i in range(12):
            self.assertEqual(t.get("k{}".format(i)), i)
        self.assertLessEqual(t.load_factor(), 0.5)

    def test_replacing_value_does_not_grow(self):
        t = self.Table(capacity=3, max_load=0.5)
        t.put("a", 1)
        t.put("a", 2)
        t.put("a", 3)
        self.assertEqual(t.capacity, 3)

    def test_no_resize_when_max_load_none(self):
        t = self.Table(capacity=11, max_load=None)
        for i in range(8):
            t.put("k{}".format(i), i)
        self.assertEqual(t.capacity, 11)
        self.assertAlmostEqual(t.load_factor(), 8 / 11)

    # 화면 출력용 slots(): 칸 수만큼, 모든 키가 정확히 한 번
    def test_slots_hold_every_key_once(self):
        t = self.Table(capacity=11, max_load=0.5)
        keys = ["https://site{}.kr".format(i) for i in range(30)]
        for i, k in enumerate(keys):
            t.put(k, i)
        slots = t.slots()
        self.assertEqual(len(slots), t.capacity)
        flat = [kv for chain in slots for kv in chain]
        self.assertEqual(sorted(flat), sorted((k, i) for i, k in enumerate(keys)))
        self.assertEqual(len(t.items()), len(t))


class TestChainingContract(TableContract, unittest.TestCase):
    Table = HashTable


class TestLinearProbingContract(TableContract, unittest.TestCase):
    Table = LinearProbingTable


if __name__ == "__main__":
    unittest.main()
