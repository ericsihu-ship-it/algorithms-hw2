"""SPEC.md 6절 해시 테이블 경계 사례 (5~16번)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hash_table import HashTable, horner, horner_steps  # noqa: E402


class TestHorner(unittest.TestCase):
    # 11. 손으로 계산한 값과 같다
    def test_matches_hand_calculation(self):
        # "ab": h = 97 % 11 = 9, h = (9*31 + 98) % 11 = 377 % 11 = 3
        self.assertEqual(horner("ab", 11), 3)
        self.assertEqual(horner("ab", 11), (97 * 31 + 98) % 11)
        self.assertEqual(horner("a", 16), 97 % 16)

    # 9. 빈 문자열의 해시는 0
    def test_empty_string_is_zero(self):
        self.assertEqual(horner("", 11), 0)

    def test_steps_end_at_final_hash(self):
        steps = horner_steps("hello", 11)
        self.assertEqual(len(steps), 5)
        self.assertEqual(steps[0][0], "h")
        self.assertEqual(steps[0][1], ord("h"))
        self.assertEqual(steps[0][2], 0)  # 이전 h
        self.assertEqual(steps[-1][3], horner("hello", 11))

    # 10. 문자열이 아닌 키는 TypeError
    def test_non_string_raises(self):
        with self.assertRaises(TypeError):
            horner(123, 11)


class TestEmptyTable(unittest.TestCase):
    # 5. 빈 테이블
    def test_empty(self):
        t = HashTable()
        self.assertEqual(len(t), 0)
        self.assertIsNone(t.get("x"))
        self.assertEqual(t.get("x", "기본"), "기본")
        self.assertFalse("x" in t)
        self.assertEqual(t.find("x"), (None, 0))
        self.assertEqual(t.load_factor(), 0)
        self.assertEqual(t.capacity, 11)

    # 14. capacity가 1 미만이거나 정수가 아니면 ValueError
    def test_bad_capacity(self):
        for bad in (0, -1, 1.5, True, "11"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    HashTable(capacity=bad)

    # 14. max_load가 0 이하이거나 숫자가 아니면 ValueError
    def test_bad_max_load(self):
        for bad in (0, -0.5, True, "1"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    HashTable(max_load=bad)
        for ok in (None, 0.5, 1, 2.0):
            with self.subTest(ok=ok):
                self.assertEqual(HashTable(max_load=ok).max_load, ok)


class TestPutGet(unittest.TestCase):
    def test_put_then_get(self):
        t = HashTable()
        t.put("https://a.com", "1")
        self.assertEqual(t.get("https://a.com"), "1")
        self.assertTrue("https://a.com" in t)
        self.assertEqual(len(t), 1)

    # 6. 같은 키를 두 번 put하면 값만 바뀐다
    def test_put_same_key_replaces_value(self):
        t = HashTable()
        t.put("k", 1)
        t.put("k", 2)
        self.assertEqual(t.get("k"), 2)
        self.assertEqual(len(t), 1)

    # 9. 빈 문자열 키
    def test_empty_string_key(self):
        t = HashTable()
        t.put("", "빈 키")
        self.assertEqual(t.get(""), "빈 키")
        self.assertTrue("" in t)
        self.assertEqual(t.slots()[0], [("", "빈 키")])

    # 10. 문자열이 아닌 키
    def test_non_string_key_raises(self):
        t = HashTable()
        with self.assertRaises(TypeError):
            t.put(1, "x")
        with self.assertRaises(TypeError):
            t.get(None)
        with self.assertRaises(TypeError):
            t.find(3.0)

    # 16. 비슷한 키를 구분한다
    def test_similar_keys_are_distinct(self):
        t = HashTable(capacity=1, max_load=None)  # 전부 한 체인에 몰리게
        t.put("ab", 1)
        t.put("ba", 2)
        t.put("https://a.com/x1", 3)
        t.put("https://a.com/x2", 4)
        self.assertEqual(t.get("ab"), 1)
        self.assertEqual(t.get("ba"), 2)
        self.assertEqual(t.get("https://a.com/x1"), 3)
        self.assertEqual(t.get("https://a.com/x2"), 4)
        self.assertEqual(len(t), 4)

    def test_items_lists_every_pair(self):
        t = HashTable()
        for k in ("a", "b", "c"):
            t.put(k, k.upper())
        self.assertEqual(sorted(t.items()), [("a", "A"), ("b", "B"), ("c", "C")])

    # 15. 많이 넣어도 모두 맞는 값
    def test_many_keys(self):
        t = HashTable()
        n = 5000
        for i in range(n):
            t.put("https://example.com/{}".format(i), i)
        self.assertEqual(len(t), n)
        for i in range(n):
            self.assertEqual(t.get("https://example.com/{}".format(i)), i)
        self.assertIsNone(t.get("https://example.com/{}".format(n)))


class TestCollisions(unittest.TestCase):
    # 7. 같은 칸으로 가는 키 여러 개
    def test_colliding_keys_all_found(self):
        t = HashTable(capacity=11, max_load=None)
        # 11칸에서 같은 칸으로 가는 키를 직접 골라 넣는다
        target = horner("a", 11)
        keys = []
        i = 0
        while len(keys) < 5:
            k = "key{}".format(i)
            if horner(k, 11) == target:
                keys.append(k)
            i += 1
        for j, k in enumerate(keys):
            t.put(k, j)
        self.assertEqual(len(t.slots()[target]), 5)
        for j, k in enumerate(keys):
            self.assertEqual(t.get(k), j)

    # 8. 체인에서 비교 횟수가 1, 2, 3, ... 로 늘고, 없는 키는 체인 길이만큼
    def test_find_counts_comparisons(self):
        t = HashTable(capacity=1, max_load=None)
        for k in ("a", "b", "c"):
            t.put(k, k.upper())
        self.assertEqual(t.find("a"), ("A", 1))
        self.assertEqual(t.find("b"), ("B", 2))
        self.assertEqual(t.find("c"), ("C", 3))
        self.assertEqual(t.find("없는 키"), (None, 3))

    def test_new_key_goes_to_end_of_chain(self):
        t = HashTable(capacity=1, max_load=None)
        for k in ("x", "y", "z"):
            t.put(k, 0)
        self.assertEqual([k for k, _ in t.slots()[0]], ["x", "y", "z"])

    def test_keys_live_in_their_hash_slot(self):
        t = HashTable(capacity=11, max_load=None)
        words = ["apple", "banana", "cherry", "date", "egg", "fig", "grape"]
        for w in words:
            t.put(w, len(w))
        slots = t.slots()
        for w in words:
            self.assertIn((w, len(w)), slots[horner(w, 11)])


class TestResize(unittest.TestCase):
    # 12. 적재율이 max_load를 넘으면 2M 이상의 소수로 늘린다
    def test_grows_to_next_prime(self):
        t = HashTable(capacity=11, max_load=1.0)
        for i in range(11):
            t.put("k{}".format(i), i)
        self.assertEqual(t.capacity, 11)  # 11/11 = 1.0 은 넘지 않음
        t.put("k11", 11)
        self.assertEqual(t.capacity, 23)  # 12/11 > 1.0 → 22 이상의 가장 작은 소수
        for i in range(12, 24):
            t.put("k{}".format(i), i)
        self.assertEqual(t.capacity, 47)  # 24/23 > 1.0 → 46 이상의 가장 작은 소수
        self.assertEqual(t.resize_count, 2)
        self.assertEqual(t.max_load, 1.0)
        for i in range(24):
            self.assertEqual(t.get("k{}".format(i)), i)
        self.assertLessEqual(t.load_factor(), 1.0)

    def test_replacing_value_does_not_grow(self):
        t = HashTable(capacity=2, max_load=1.0)
        t.put("a", 1)
        t.put("b", 2)
        t.put("a", 3)  # 새 키가 아니므로 개수 그대로
        self.assertEqual(t.capacity, 2)

    def test_keys_rehashed_into_new_slots(self):
        t = HashTable(capacity=3, max_load=1.0)
        for i in range(10):
            t.put("url{}".format(i), i)
        slots = t.slots()
        self.assertEqual(len(slots), t.capacity)
        for i in range(10):
            k = "url{}".format(i)
            self.assertIn((k, i), slots[horner(k, t.capacity)])

    # 13. max_load=None이면 늘리지 않는다
    def test_no_resize_when_max_load_none(self):
        t = HashTable(capacity=11, max_load=None)
        for i in range(44):
            t.put("k{}".format(i), i)
        self.assertEqual(t.capacity, 11)
        self.assertAlmostEqual(t.load_factor(), 4.0)
        for i in range(44):
            self.assertEqual(t.get("k{}".format(i)), i)


if __name__ == "__main__":
    unittest.main()
