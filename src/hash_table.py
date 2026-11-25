"""개별 체이닝 해시 테이블.

- 칸 배열은 list, 칸마다 직접 만든 노드로 단일 연결 리스트를 잇는다.
- 해시는 호너 방식: h = (h * 31 + ord(글자)) % M
- 키는 문자열만 받는다.
- 적재율이 max_load를 넘으면 칸 수를 2M 이상의 가장 작은 소수로 늘린다.
  max_load=None이면 늘리지 않는다 (적재율 실험용).

파이썬 내장 해시 함수와 내장 매핑·집합 자료형은 쓰지 않는다 (SPEC.md 1절).
"""

HORNER_BASE = 31


def _check_key(key):
    if not isinstance(key, str):
        raise TypeError("키는 문자열이어야 합니다: {!r}".format(key))


def horner(key, m):
    """호너 해시. 글자마다 h = (h * 31 + ord(c)) % m. 빈 문자열은 0."""
    _check_key(key)
    h = 0
    for ch in key:
        h = (h * HORNER_BASE + ord(ch)) % m
    return h


def horner_steps(key, m):
    """화면 출력용 계산 과정. 글자마다 (글자, ord, 이전 h, 새 h)."""
    _check_key(key)
    steps = []
    h = 0
    for ch in key:
        new_h = (h * HORNER_BASE + ord(ch)) % m
        steps.append((ch, ord(ch), h, new_h))
        h = new_h
    return steps


def is_number(x):
    """int 또는 float (bool은 제외)."""
    return not isinstance(x, bool) and isinstance(x, (int, float))


def check_capacity(capacity):
    """capacity는 1 이상의 정수 (bool, 실수, 문자열은 거절). SPEC.md 3.3절."""
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
        raise ValueError("capacity는 1 이상의 정수여야 합니다: {!r}".format(capacity))


def _is_prime(n):
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def next_prime(n):
    """n 이상인 가장 작은 소수."""
    while not _is_prime(n):
        n += 1
    return n


class _Node:
    __slots__ = ("key", "value", "next")

    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.next = None


class HashTable:
    """개별 체이닝 해시 테이블. 인터페이스는 SPEC.md 3.4절."""

    def __init__(self, capacity=11, max_load=1.0):
        check_capacity(capacity)
        if max_load is not None and (not is_number(max_load) or max_load <= 0):
            raise ValueError("max_load는 0보다 큰 수이거나 None이어야 합니다: {!r}".format(max_load))
        self._slots = [None] * capacity
        self._count = 0
        self.max_load = max_load
        self.resize_count = 0

    # --- 기본 정보 ---------------------------------------------------------

    @property
    def capacity(self):
        return len(self._slots)

    def __len__(self):
        return self._count

    def load_factor(self):
        return self._count / len(self._slots)

    def slot_of(self, key):
        """키가 들어갈 칸 번호."""
        return horner(key, len(self._slots))

    # --- 찾기 --------------------------------------------------------------

    def find(self, key):
        """(값, 비교 횟수). 없으면 (None, 비교 횟수). 빈 칸에서 실패하면 0."""
        node = self._slots[self.slot_of(key)]
        comparisons = 0
        while node is not None:
            comparisons += 1
            if node.key == key:
                return node.value, comparisons
            node = node.next
        return None, comparisons

    def _find_node(self, key):
        node = self._slots[self.slot_of(key)]
        while node is not None:
            if node.key == key:
                return node
            node = node.next
        return None

    def get(self, key, default=None):
        node = self._find_node(key)
        return default if node is None else node.value

    def __contains__(self, key):
        return self._find_node(key) is not None

    # --- 넣기 --------------------------------------------------------------

    def put(self, key, value):
        """키가 없으면 체인 맨 뒤에 붙이고, 있으면 값만 바꾼다."""
        i = self.slot_of(key)
        node = self._slots[i]
        if node is None:
            self._slots[i] = _Node(key, value)
        else:
            while True:
                if node.key == key:
                    node.value = value
                    return
                if node.next is None:
                    break
                node = node.next
            node.next = _Node(key, value)

        self._count += 1
        if self.max_load is not None and self.load_factor() > self.max_load:
            self._grow()

    def _grow(self):
        old_slots = self._slots
        self._slots = [None] * next_prime(2 * len(old_slots))
        self._count = 0
        self.resize_count += 1
        # 칸 순서, 체인 순서대로 옮긴다. 새 칸 수에서는 늘어나지 않는다.
        max_load, self.max_load = self.max_load, None
        for head in old_slots:
            node = head
            while node is not None:
                self.put(node.key, node.value)
                node = node.next
        self.max_load = max_load

    # --- 화면 출력용 -------------------------------------------------------

    def slots(self):
        """칸마다 (key, value) 목록을 체인 순서대로 담은 리스트."""
        out = []
        for head in self._slots:
            chain = []
            node = head
            while node is not None:
                chain.append((node.key, node.value))
                node = node.next
            out.append(chain)
        return out

    def items(self):
        """칸 순서, 체인 순서대로 (key, value)."""
        out = []
        for chain in self.slots():
            out.extend(chain)
        return out
