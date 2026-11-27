"""선형 탐사에만 있는 경계 사례 (SPEC.md 8.5절 33~38번)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hash_table import horner  # noqa: E402
from linear_probing import LinearProbingTable  # noqa: E402
from test_table_contract import same_home_keys  # noqa: E402


class TestProbing(unittest.TestCase):
    # 35. 빈 칸에서 실패하면 1 (빈 칸도 센다)
    def test_empty_table_miss_counts_one(self):
        t = LinearProbingTable()
        self.assertEqual(t.find("x"), (None, 1))
        self.assertEqual(t.probe_sequence("x"), [horner("x", 11)])

    # 33. 같은 홈 칸 → 다음 빈 칸, 비교 횟수 1, 2, 3, ...
    def test_collisions_go_to_next_free_slot(self):
        t = LinearProbingTable(capacity=11, max_load=None)
        keys = same_home_keys(11, 4, 3)
        for k in keys:
            t.put(k, k)
        slots = t.slots()
        self.assertEqual([slots[i] for i in (4, 5, 6)],
                         [[(keys[0], keys[0])], [(keys[1], keys[1])], [(keys[2], keys[2])]])
        self.assertEqual(t.probe_sequence(keys[2]), [4, 5, 6])
        self.assertEqual(t.find(keys[2]), (keys[2], 3))

    # 35. 클러스터 안에서 시작한 실패 탐색은 끝의 빈 칸까지 센다
    def test_miss_inside_cluster_counts_to_empty_slot(self):
        t = LinearProbingTable(capacity=11, max_load=None)
        keys = same_home_keys(11, 4, 4)  # 4, 5, 6 칸을 채우고, 넷째는 찾기용
        for k in keys[:3]:
            t.put(k, 0)
        self.assertEqual(t.find(keys[3]), (None, 4))            # 4, 5, 6, 7(빈 칸)
        self.assertEqual(t.probe_sequence(keys[3]), [4, 5, 6, 7])
        home5 = same_home_keys(11, 5, 1)[0]
        self.assertEqual(t.find(home5), (None, 3))              # 5, 6, 7(빈 칸)

    def test_key_with_home_inside_cluster_goes_to_its_end(self):
        t = LinearProbingTable(capacity=11, max_load=None)
        for k in same_home_keys(11, 4, 3):     # 4, 5, 6
            t.put(k, 0)
        k5 = same_home_keys(11, 5, 1)[0]
        t.put(k5, "밀림")
        self.assertEqual(t.slots()[7], [(k5, "밀림")])
        self.assertEqual(t.probe_sequence(k5), [5, 6, 7])

    # 34. 마지막 칸 다음은 0번 칸
    def test_wraps_around_to_slot_zero(self):
        m = 7
        t = LinearProbingTable(capacity=m, max_load=None)
        last = same_home_keys(m, m - 1, 2)
        t.put(last[0], "끝")
        t.put(last[1], "넘어감")
        self.assertEqual(t.slots()[m - 1], [(last[0], "끝")])
        self.assertEqual(t.slots()[0], [(last[1], "넘어감")])
        self.assertEqual(t.probe_sequence(last[1]), [m - 1, 0])
        self.assertEqual(t.find(last[1]), ("넘어감", 2))
        # 홈이 0인 키는 0번이 찼으므로 1번으로
        zero = same_home_keys(m, 0, 1)[0]
        t.put(zero, "영")
        self.assertEqual(t.slots()[1], [(zero, "영")])
        # 홈이 M-1인 없는 키는 M-1, 0, 1, 2(빈 칸)까지
        missing = same_home_keys(m, m - 1, 3)[2]
        self.assertEqual(t.find(missing), (None, 4))
        self.assertEqual(t.probe_sequence(missing), [m - 1, 0, 1, 2])


class TestFullTable(unittest.TestCase):
    # 36. 꽉 찬 테이블
    def setUp(self):
        self.m = 5
        self.t = LinearProbingTable(capacity=self.m, max_load=None)
        self.keys = ["full{}".format(i) for i in range(self.m)]
        for i, k in enumerate(self.keys):
            self.t.put(k, i)

    def test_all_slots_used_and_found(self):
        self.assertEqual(len(self.t), self.m)
        self.assertEqual(self.t.load_factor(), 1.0)
        self.assertTrue(all(len(s) == 1 for s in self.t.slots()))
        for i, k in enumerate(self.keys):
            self.assertEqual(self.t.get(k), i)

    def test_missing_key_checks_every_slot_and_stops(self):
        self.assertEqual(self.t.find("없는 키"), (None, self.m))
        self.assertEqual(len(self.t.probe_sequence("없는 키")), self.m)
        self.assertFalse("없는 키" in self.t)

    def test_new_key_overflows(self):
        with self.assertRaises(OverflowError):
            self.t.put("새 키", 99)
        self.assertEqual(len(self.t), self.m)

    def test_existing_key_can_be_updated(self):
        self.t.put(self.keys[2], "바뀜")
        self.assertEqual(self.t.get(self.keys[2]), "바뀜")
        self.assertEqual(len(self.t), self.m)

    def test_max_load_one_fills_then_overflows(self):
        t = LinearProbingTable(capacity=3, max_load=1.0)
        for k in ("a", "b", "c"):
            t.put(k, k)
        self.assertEqual(t.capacity, 3)  # 3/3 = 1.0 은 넘지 않음
        with self.assertRaises(OverflowError):
            t.put("d", "d")


class TestInvariants(unittest.TestCase):
    # 37. 홈 칸부터 키가 있는 칸까지 빈 칸이 없다
    def test_no_gap_between_home_and_slot(self):
        for max_load in (None, 0.5, 0.9):
            t = LinearProbingTable(capacity=31, max_load=max_load)
            n = 28 if max_load is None else 200
            for i in range(n):
                t.put("https://ex.com/{}".format(i), i)
            slots = t.slots()
            m = t.capacity
            for j, s in enumerate(slots):
                if not s:
                    continue
                key = s[0][0]
                path = t.probe_sequence(key)
                self.assertEqual(path[0], horner(key, m))
                self.assertEqual(path[-1], j)
                for i in path:
                    self.assertEqual(len(slots[i]), 1)

    def test_grow_keeps_every_key(self):
        t = LinearProbingTable(capacity=3, max_load=0.5)
        for i in range(100):
            t.put("url{}".format(i), i)
        self.assertGreaterEqual(t.resize_count, 1)
        self.assertLessEqual(t.load_factor(), 0.5)
        for i in range(100):
            self.assertEqual(t.get("url{}".format(i)), i)

    # 38. 잘못된 max_load / capacity
    def test_bad_arguments(self):
        for bad in (0, -0.1, 1.01, 2, True, "0.5"):
            with self.subTest(max_load=bad):
                with self.assertRaises(ValueError):
                    LinearProbingTable(max_load=bad)
        for bad in (0, 1.5, True):
            with self.subTest(capacity=bad):
                with self.assertRaises(ValueError):
                    LinearProbingTable(capacity=bad)
        LinearProbingTable(max_load=1.0)
        LinearProbingTable(max_load=None)


if __name__ == "__main__":
    unittest.main()
