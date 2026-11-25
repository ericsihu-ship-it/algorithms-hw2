# 구현 계획

`SPEC.md`를 기준으로 한다. 코드는 이 파일에 쓰지 않는다. 단계마다 이슈 번호와 같은
`feature/<이슈>-<이름>` 브랜치에서 작업하고, `make test`가 통과한 뒤 develop에 머지한다.

## 지킬 것

- `src/`에서 `dict`, `set`, 내장 `hash()`를 쓰지 않는다. 칸 배열은 `list`, 체인은 직접 만든 노드 클래스.
- 짧은 코드는 카운터를 base62로 바꿔 만든다. URL의 해시값으로 만들지 않는다.
- **테스트를 먼저 쓴다.** 구현보다 테스트 커밋이 앞선다. 테스트가 실패하면 코드를 고친다.

## 1. 테스트 먼저 (이슈 #4, 첫 커밋)

1. `SPEC.md` 6절의 해시 테이블 경계 사례(5~16번)를 `tests/test_hash_table.py`로 옮긴다.
   - 충돌 테스트는 칸 수를 작게(예: 1칸, 11칸) 만들어 일부러 같은 칸에 몰리게 한다.
   - 호너 해시 테스트의 기대값은 손으로 계산해 숫자로 적는다.
2. 단축기 경계 사례(17~27번)를 `tests/test_shortener.py`로 옮긴다.
3. `make test`를 돌려 **새 테스트가 실패하는 것**을 확인한다. (아직 구현이 없으므로 import 오류가 정상)
4. 테스트만 커밋한다.

## 2. 해시 테이블 (이슈 #4)

1. 노드 클래스: `key`, `value`, `next`.
2. 모듈 함수 `horner(key, m)`과 계산 과정을 돌려주는 모듈 함수 `horner_steps(key, m)`. 문자열이 아니면 `TypeError`.
3. `HashTable(capacity=11, max_load=1.0)`: 칸 배열, 개수, 최대 적재율, 늘린 횟수.
   `capacity`(1 이상 정수, bool 제외)와 `max_load`(0보다 큰 수 또는 None, bool 제외)를 먼저 검사한다.
4. `find(key)`: 해시로 칸을 정하고 체인을 따라가며 비교 횟수를 센다.
5. `get`, `in`, `len`, `load_factor`, `capacity`는 `find`와 개수로 만든다.
6. `put`: 체인을 끝까지 따라가 같은 키가 있으면 값만 바꾸고, 없으면 맨 뒤에 붙인 뒤 개수를 늘린다.
7. 크기 늘리기: 적재율이 `max_load`를 넘으면 `2M` 이상의 가장 작은 소수를 구해 새 칸 배열에 모든 노드를 다시 넣는다. `max_load=None`이면 하지 않는다.
8. `slots()`, `items()`: 화면 출력용 목록.
9. `make test`로 `test_hash_table.py`가 통과하는지 본다.

## 3. 단축기 (이슈 #4)

1. URL 검사 함수: 타입 → 앞뒤 공백 제거 → 스킴 → 호스트 → ASCII 출력 가능 문자만(공백·제어 문자·한글 거절) → 길이 순.
2. `Shortener(table_factory=HashTable)`: `by_url`, `by_code` 두 테이블과 카운터.
3. `shorten`: 검사 → `by_url`에 있으면 그 코드 → 없으면 카운터를 늘려 `encode`로 코드를 만들고 두 테이블에 넣는다.
4. `expand`: 문자열이 아니거나 비어 있으면 `None`, 아니면 `by_code.get`.
5. `make test` 전체 통과를 확인한다. 테스트 파일은 고치지 않는다.

## 4. 규칙 파일 (이슈 #5)

1. `grep -nE "dict|set\(|hash\(" src/`로 위반을 찾는다.
2. `.github/copilot-instructions.md`에 프로젝트 규칙과 git 규칙을 적는다.
3. 새 채팅에서 규칙 위반 검사를 시켜 본다.

## 5. 적재율 실험 (이슈 #6)

1. `experiments/probe_experiment.py` (SPEC.md 7절): 칸 수 4093, `max_load=None`.
2. 적재율 0.25, 0.5, 1, 2, 4마다 무작위 URL을 `round(α·4093)`개 넣는다. 난수 시드는 고정하고, 순차 URL은 쓰지 않는다.
3. 성공 탐색: 넣은 키 전부를 `find`해 비교 횟수 평균. 실패 탐색: 넣지 않은 URL 2000개의 평균.
4. 이론값(성공 ≈ 1 + α/2, 실패 ≈ α)과 표로 비교해 출력하고 `experiments/results.csv`에 쓴다.
5. 표준 모듈만으로 SVG 그래프(`experiments/probe.svg`)를 그린다. 축 이름과 범례를 넣는다.

## 6. 웹 서버 (이슈 #7)

1. `src/server.py`: `http.server`의 핸들러 하나, 단축기 하나를 서버가 살아 있는 동안 공유.
2. `GET /` 폼, `POST /shorten` 결과/400, `GET /<코드>` 302/404, `GET /table`.
3. 짧은 링크 주소는 `X-Forwarded-*` → `Host` 순서로 만든다. `Location`에는 저장된 URL을 그대로 넣는다(ASCII만 저장됨).
4. `/table`: 칸마다 체인을 화살표로, 노드마다 호너 계산을 `<details>`로 펼친다.
5. 모든 출력은 HTML 이스케이프.
6. `make serve`로 띄워 폼 → 짧은 링크 → 이동 → `/table`을 손으로 확인한다.
