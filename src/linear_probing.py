"""선형 탐사(개방 주소법) 해시 테이블. 인터페이스는 HashTable과 같다 (SPEC.md 8절).

- 칸 배열 하나에 (key, value)를 바로 넣는다. 빈 칸은 None.
- 홈 칸 h = 호너 해시에서 시작해 h+1, h+2, ... 로 한 칸씩 본다. M-1 다음은 0.
- find의 비교 횟수는 들여다본 칸 수다. 빈 칸에서 멈추면 그 칸도 센다.
- 적재율이 max_load를 넘으면 칸 수를 2M 이상의 가장 작은 소수로 늘린다.
  max_load=None이면 늘리지 않고, 꽉 찬 테이블에 새 키를 넣으면 OverflowError.
- 삭제는 지원하지 않는다.

파이썬 내장 해시 함수와 내장 매핑·집합 자료형은 쓰지 않는다.
"""

from hash_table import check_capacity, horner, is_number, next_prime


def _check_key(key):
    if not isinstance(key, str):
        raise TypeError("키는 문자열이어야 합니다: {!r}".format(key))


class LinearProbingTable:
    def __init__(self, capacity=11, max_load=0.5):
        check_capacity(capacity)
        if max_load is not None and (not is_number(max_load) or not (0 < max_load <= 1)):
            raise ValueError("max_load는 0보다 크고 1 이하이거나 None이어야 합니다: {!r}"
                             .format(max_load))
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
        """키의 홈 칸 번호 (실제로 놓인 칸은 더 뒤일 수 있다)."""
        _check_key(key)
        return horner(key, len(self._slots))

    # --- 탐사 --------------------------------------------------------------

    def _probe(self, key):
        """(찾은 칸 번호 또는 None, 처음 만난 빈 칸 번호 또는 None, 들여다본 칸 목록)."""
        m = len(self._slots)
        i = self.slot_of(key)
        path = []
        while len(path) < m:
            path.append(i)
            entry = self._slots[i]
            if entry is None:
                return None, i, path
            if entry[0] == key:
                return i, None, path
            i = (i + 1) % m
        return None, None, path  # 꽉 찼고 키도 없다

    def probe_sequence(self, key):
        """키를 찾거나 빈 칸을 만날 때까지 들여다본 칸 번호 목록."""
        return self._probe(key)[2]

    def find(self, key):
        """(값, 들여다본 칸 수). 없으면 (None, 들여다본 칸 수)."""
        found, _, path = self._probe(key)
        if found is None:
            return None, len(path)
        return self._slots[found][1], len(path)

    def get(self, key, default=None):
        found = self._probe(key)[0]
        return default if found is None else self._slots[found][1]

    def __contains__(self, key):
        return self._probe(key)[0] is not None

    # --- 넣기 --------------------------------------------------------------

    def put(self, key, value):
        found, empty, _ = self._probe(key)
        if found is not None:
            self._slots[found] = (key, value)
            return
        if empty is None:
            raise OverflowError("테이블이 꽉 찼습니다 (칸 {}개)".format(len(self._slots)))
        self._slots[empty] = (key, value)
        self._count += 1
        if self.max_load is not None and self.load_factor() > self.max_load:
            self._grow()

    def _grow(self):
        old_slots = self._slots
        self._slots = [None] * next_prime(2 * len(old_slots))
        self._count = 0
        self.resize_count += 1
        max_load, self.max_load = self.max_load, None
        for entry in old_slots:
            if entry is not None:
                self.put(entry[0], entry[1])
        self.max_load = max_load

    # --- 화면 출력용 -------------------------------------------------------

    def slots(self):
        """칸마다 [] 또는 [(key, value)] — HashTable.slots()와 같은 모양."""
        return [[] if entry is None else [entry] for entry in self._slots]

    def items(self):
        return [entry for entry in self._slots if entry is not None]

    def clusters(self):
        """연속으로 찬 칸 묶음의 (시작 칸, 길이) 목록. 끝과 0번을 잇는 묶음은 하나로 센다."""
        m = len(self._slots)
        if self._count == 0:
            return []
        if self._count == m:
            return [(0, m)]
        # 빈 칸 바로 다음부터 한 바퀴 돌면 0번을 넘는 묶음도 끊기지 않는다
        start = 0
        while self._slots[start] is not None:
            start += 1
        out = []
        run_start, run_len = None, 0
        for step in range(1, m + 1):
            i = (start + step) % m
            if self._slots[i] is not None:
                if run_len == 0:
                    run_start = i
                run_len += 1
            elif run_len:
                out.append((run_start, run_len))
                run_len = 0
        if run_len:
            out.append((run_start, run_len))
        out.sort()
        return out
