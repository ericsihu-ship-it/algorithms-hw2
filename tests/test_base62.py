import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from base62 import ALPHABET, decode, encode  # noqa: E402


class TestEncode(unittest.TestCase):
    def test_zero_is_single_zero(self):
        self.assertEqual(encode(0), "0")

    def test_single_digits_follow_alphabet_order(self):
        # 0-9, a-z, A-Z 순서
        self.assertEqual(encode(9), "9")
        self.assertEqual(encode(10), "a")
        self.assertEqual(encode(35), "z")
        self.assertEqual(encode(36), "A")
        self.assertEqual(encode(61), "Z")

    def test_two_digits(self):
        self.assertEqual(encode(62), "10")
        self.assertEqual(encode(62 * 62 - 1), "ZZ")
        self.assertEqual(encode(62 * 62), "100")

    def test_large_number(self):
        self.assertEqual(decode(encode(10 ** 18)), 10 ** 18)

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            encode(-1)

    def test_non_integer_raises(self):
        for bad in (1.5, "3", None, True):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    encode(bad)


class TestDecode(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(decode("0"), 0)
        self.assertEqual(decode("a"), 10)
        self.assertEqual(decode("Z"), 61)
        self.assertEqual(decode("10"), 62)

    def test_round_trip(self):
        for n in list(range(0, 5000)) + [62 ** 5, 62 ** 5 - 1, 123456789]:
            with self.subTest(n=n):
                self.assertEqual(decode(encode(n)), n)

    def test_every_letter_round_trips(self):
        for i, ch in enumerate(ALPHABET):
            with self.subTest(ch=ch):
                self.assertEqual(decode(ch), i)
                self.assertEqual(encode(i), ch)

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            decode("")

    def test_invalid_characters_raise(self):
        for bad in ("-", "ab_c", " 1", "가", "1.0"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    decode(bad)

    def test_non_string_raises(self):
        with self.assertRaises(TypeError):
            decode(10)


if __name__ == "__main__":
    unittest.main()
