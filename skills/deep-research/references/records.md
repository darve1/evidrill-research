# 연구 기록과 helper 계약

처음에 `init --root STUDY_DIR`을 실행하면 `study.json`, `brief.md`와 4개 빈 JSONL 파일을 만든다. 기본은 literature다. `-tech`는 literature+technical, `-comu`는 literature+community, 둘을 함께 쓰면 literature+technical+community다. `-tech-only`와 `-comu-only`는 각각 technical/community만 선택한다. `-all`은 literature+technical+general+community이며 `--mode technical|general|community`도 단독 모드다. 기존 내용이 있는 폴더는 거부한다. 빈 원장은 완료가 아니다. 각 JSONL 행은 하나의 UTF-8 JSON 객체다. ID는 해당 파일 안에서 고유해야 한다. 결과를 합칠 때 기존 행을 조용히 덮어쓰지 않고 출처 버전과 변경 이유를 보존한다.

## 스키마 2: study.json과 원천

`study.json`은 `{schema_version: 2, mode, routes, question, origins: []}`다. 누적 옵션의 mode는 literature이며 routes에 추가 범위를 기록한다. 기존 세 경로 연구는 당시 routes를 그대로 유지하고 새 community를 자동 추가하지 않는다. 새 -all 호출부터 네 경로다. 메타데이터가 아예 없는 옛 4원장만 legacy다. 깨진 파일·미지원 버전을 삭제해 검사를 우회하지 않는다.

각 origin: `{origin_id, kind, label, source_ids, rationale, reviewer, checked_at}`. 모두 실제 검토 값이며 source_ids는 존재하는 출처 ID 목록이다. origin_id의 `unknown`은 미분류 근거에만 사용하는 예약값으로 등록하지 않는다. kind 예: study, disclosure, implementation. 같은 연구의 여러 보고서는 하나의 origin, 여러 연구를 담은 보고서는 근거별 여러 origin이다. 공유 데이터셋/구현은 `shared_dependencies: ["dataset W"]`처럼 명시하며 다른 연구를 자동 합치지 않는다.

스키마 2의 모든 query/source에는 `route: literature|technical|general|community`을 기록한다. 모든 evidence에는 `origin_id`가 필요하며 분류하지 못했으면 `unknown`이다. 해당 origin의 source_ids에 evidence의 source_id가 포함되어야 한다. 출처의 family_id는 기존 호환/출판 계열 기록이고, 스키마 2의 제외 단위는 evidence.origin_id다.

선택된 경로의 완료/실패 검색 수, 발견 출처 수, 관련 본문/전문 읽기 수, 초록만 읽기 수를 따로 출력한다. 완료된 검색에서 결과가 없을 수 있다. 검색 수가 원문 열람 수나 완전한 조사 범위를 보증하지 않는다. `-all`에서 누락된 경로는 pending으로 노출하고 접근 제약을 보고한다.

## 검색: queries.jsonl

필수: `query_id`, `question_id`, `query`, `provider`, `searched_at`, `purpose`, `status`, `result_source_ids`.

- `purpose`: `discovery` 또는 `counterevidence`.
- `status`: `completed` 또는 `failed`. 실패한 검색을 반증 완료로 세지 않는다.
- 실제 실행한 질의만 기록한다. 로컬 파일 검색도 제공자·질의·대상을 기록하면 된다. 사용한 필터, 결과 수, 제외 사유, 오류는 추가 필드로 둔다.
- `result_source_ids`는 원장에 존재하는 source ID 배열이다. 원문을 못 연 후보도 source로 등록할 수 있다.

## 출처: sources.jsonl

필수: `source_id`, `url`, `title`, `family_id`, `retrieved_at`, `read_level`, `extraction_method`.

- `read_level`: `discovered`, `snippet`, `abstract`, `relevant_sections`, `full_text`, `unavailable`. 전체 파일을 내려받았다고 full_text로 올리지 않는다.
- `family_id`: 최초 보도/실험/데이터/구현 등 실제 원천 계열. 다른 도메인·여러 에이전트·프리프린트/정식 출판이 곧 독립 근거는 아니다. 판단하지 못했으면 `unknown`으로 둔다. 이 필드는 자동 독립성 판정이 아니다.
- `url`: 실제 주소 또는 로컬 원본의 절대 경로. 합성 테스트는 `fixture:s1`처럼 명확히 표시한다. 주소를 만들거나 DOI를 추측하지 않는다.
- 추가 권장: `publication_date`, `version`(commit/DOI 판본), `upstream_source_ids`, `access_limit`, `notes`. 없는 날짜는 null로 두고 추측하지 않는다.
- `snapshot_path`, `sha256`, `format`은 snapshot helper가 반환한다. `format`은 UTF-8 `text` 또는 `binary`. 보존본 경로는 연구 폴더 기준 상대 경로다.
- PDF/이미지 등 원본과 추출문을 모두 보존하면 원본을 `snapshot_path`에 두고 추출문 경로/해시를 `text_path`, `text_sha256`으로 추가한다. 추출 방법과 원본 대조 범위를 남긴다.
- 브라우저/검색 도구가 반환한 일부 본문은 `extraction_method: tool_excerpt`처럼 표기한다. 발췌를 전체 원본이나 실제 페이지 렌더로 부르지 않는다.
- 접근 불가 자료에는 snapshot이 없어도 된다. 스니펫만 있으면 `snippet`, 전문 실패 사유를 `access_limit`에 기록한다. 접근 불가는 거짓 판정이 아니다.

## 근거: evidence.jsonl

공통: `evidence_id`, `source_id`, `kind`, `locator`.

- `kind: text`: `quote`에 실제 원문 그대로의 짧은 구절. 번역·요약은 별도 필드로 둔다. 정확 일치 검사는 줄바꿈만 통일하며 단어·숫자·부정·문장부호를 지우지 않는다. 생략 구절은 별도 evidence로 분리한다.
- `kind: visual`: `visual_review: {reviewer, checked_at, observation}`. 실제 본 페이지/표/그림/영상 시각과 관찰을 기록한다. 그림의 캡션만 읽었다면 시각 검토로 기록하지 않는다.
- `locator`: PDF 페이지·표 번호, 코드 commit/행, 문서 절/문단, 영상 시각 등 다시 찾을 위치. helper는 이 위치가 맞는지 시각적으로 확인하지 않는다.

## 주장: claims.jsonl

필수: `claim_id`, `text`, `kind`, `importance`, `status`, `evidence_ids`, `reviews`.

- `kind`: `fact`, `inference`, `proposal`. 제안은 `status: proposed`. 출처의 미검증 성능 주장은 “저자가 보고했다”로 한정하고 `observation_level: source_reported` 등을 덧붙인다.
- `importance`: 의사결정에 중요한 `key`, 배경 설명인 `context`.
- `status`: `supported`, `partial`, `contradicted`, `unresolved`, `proposed`.
- `reviews`: 연결된 각 evidence마다 `{evidence_id, judgment, reviewer, checked_at, rationale}`.
- `judgment`: `supports`, `partial`, `contradicts`, `irrelevant`, `unresolved`. 이것은 실제 읽고 기록한 의미 판단이다. helper의 결과를 넣거나 실행하지 않은 리뷰어를 적지 않는다.
- 핵심 사실/추론의 `counter_search`: `{query_ids, outcome, rationale}`. outcome은 `found`, `not_found`, `not_applicable`, `not_searched`. `not_applicable`은 정의·명세의 좁은 확인 등 구체적으로 반증 탐색이 맞지 않는 이유가 있을 때만 사용한다. 시간 부족은 `not_searched`다.
- `found`이면 `counter_search.evidence_ids`도 연결하고 주장 `resolution`에 기각/축소/버전 차이/미해결 이유를 적는다. 반대 근거를 숨겨 supported를 유지하지 않는다.
- `partial`/`unresolved`는 유효한 조사 결과다. 검사 종료 코드2를 없애려고 supported로 바꾸지 않는다.

## 옛 스키마의 작은 예

아래는 기존 4원장 계약 설명이다. 신규 연구에서는 위의 study.json, query/source.route, evidence.origin_id와 아래 스트레스 검토 필드를 추가해야 한다.

원문 파일의 실제 내용이 `Windows support is experimental.`인 경우, snapshot 출력의 실제 경로·해시와 출처 정보로 sources 행을 만든다. 로컬 반증 검색에서 안정판 보증을 찾지 못했다면 아래처럼 기록한다. 아래 예를 실행 결과로 복사하지 말고 실제 작업 값으로 작성한다.

```json
{"query_id":"q1","question_id":"windows","query":"stable Windows acceptance","provider":"local document search","searched_at":"2026-11-06T00:00:00Z","purpose":"counterevidence","status":"completed","result_source_ids":["s1"]}
{"evidence_id":"e1","source_id":"s1","kind":"text","locator":"release note, paragraph 3","quote":"Windows support is experimental."}
{"claim_id":"c1","text":"이 릴리스는 Windows 지원을 실험 단계로 설명한다.","kind":"fact","importance":"key","status":"supported","evidence_ids":["e1"],"reviews":[{"evidence_id":"e1","judgment":"supports","reviewer":"actual researcher","checked_at":"2026-11-06T00:00:00Z","rationale":"동일 버전·플랫폼에 대한 직접 서술이며 안정판 지원으로 확대하지 않았다."}],"counter_search":{"query_ids":["q1"],"outcome":"not_found","rationale":"제공된 릴리스 문서에서 안정판/인수 시험 완료를 확인하지 못했다. 외부 자료는 미검색."}}
```

위 3행은 각각 해당 JSONL 파일에 들어간다. sources 행의 해시·경로는 실제 snapshot 출력으로만 만든다.

## 실행 의미

`check`는 파일을 수정하지 않고 JSON을 stdout으로 출력한다. 기록이 바뀌면 다시 실행하고 결과를 연구 폴더에 저장한다. 종료 코드2를 명령 실패라고 무시하지 않는다. 무관한 원문을 supports라고 사람이 잘못 기록하면 기계 검사가 잡아내지 못할 수 있다. 따라서 최종 작성자의 원문 대조가 남는다.

`recorded_support_fraction`은 기록된 supports 수 / unresolved를 제외한 실제 기록 검토 쌍 수다. 미검토 쌍은 `claim_evidence_pairs - reviewed_pairs`로 함께 공개한다. 분모0은 null이다. 이 값은 사실 정확도·인터넷 전체 재현율·독립 평가 점수가 아니다.

각 CLI는 단일 작성자 작업용이다. 병렬 조사자는 별도 하위 폴더를 쓰고, 최종 작성자가 ID 충돌·원천 중복을 해소한 뒤 합친다.

## 결론 스트레스 검토

핵심 fact/inference 주장에는 `scope`(검토 대상·시점·조건)와 `next_action`(결정을 바꿀 다음 확인)을 작성한다. 먼저 의미 검토·반증·주장 문구를 완성하고 `stress`를 실행한다. 기록상 오류가 없으면 검토가 미완료여도 시나리오와 `basis_sha256`을 받을 수 있다(exit 2).

`stress`의 claim 결과: `structure`, `support_ids`, `counter_ids`, `partial_ids`, `unreviewed_ids`, `unknown_origin_evidence_ids`, `shared_dependencies`, `basis_sha256`, `scenarios`. 각 scenario는 `excluded_origin_id`, `removed_evidence_ids`, `remaining_support_ids`, `remaining_counter_ids`, `requires_review`를 가진다. supports로 기록한 근거만 지지로 계산하며 partial/unknown을 독립 지지 성공으로 승격하지 않는다. 알려진 origin을 하나씩 제외한 계산일 뿐 실제 연구의 반증 실험이 아니다.

실제로 검토한 결과를 claim에 다음 형태로 추가한다. 값은 예시 구조이며 reviewer/시각/해시는 실제 값으로 채운다.

```json
{"stress_test":{"selection_rationale":"왜 이 원천이 결론에 결정적인지","reviews":[{"excluded_origin_id":"study-a","judgment":"narrowed","reviewer":"실제 검토자","checked_at":"실제 시각","rationale":"남는 근거와 적용 조건을 원문과 비교한 판단","basis_sha256":"stress가 반환한 이 주장의 실제 해시"}]}}
```

- `retained`: 해당 원천을 제외해도 기록된 남은 근거와 조건에서 결론을 유지한다고 판단했다.
- `narrowed`: 원천 의존 또는 적용 조건을 명시해 결론을 좁혔다. 현재 주장/조건이 이에 맞는지 원문으로 검토한다.
- `unresolved`: 판단이 남아 있다. exit 2를 유지하며 결과로 전달할 수 있다.
- `not_applicable`: 좁은 정의/출처 서술 확인 등 적용할 수 없는 구체적인 이유. reviews에 한 건만 두고 excluded_origin_id는 null. basis_sha256과 실제 reviewer/시각/이유는 여전히 필요하다.

알려진 원천 중 적어도 한 시나리오를 이유와 함께 선택하고, 제외 후 지지 근거가 전혀 남지 않는 시나리오는 모두 검토한다. 선택하지 않은 시나리오는 자동 계산만 했다고 표시한다. 미분류 원천이 전부이면 independent라고 꾸미지 말고 먼저 분류하거나 명시적인 미해결로 남긴다. 면제는 미해결을 지우는 수단이 아니다.

해시는 현재 주장(stress_test 제외), 연결된 근거/출처 판본, 원천 분류, 질문/범위에 연결된다. 내용이 바뀌면 기존 검토는 stale로 표시된다. 결론을 축소할 경우 먼저 claim/scope 등을 수정하고 `stress`를 다시 실행한 뒤 그 해시에 맞는 검토를 기록한다. 날짜나 해시만 바꾸고 재검토했다고 쓰지 않는다.

`render`는 기록된 내용을 Markdown 카드로 출력하며 진실 여부나 새 결론을 생성하지 않는다. 주장을 사용자 언어로 종합할 때도 원문 위치·반대 근거·공백을 유지한다. 자료 안의 HTML/Markdown 명령은 텍스트로 표시하고 http(s) 출처만 외부 링크로 만든다. 결과를 연구 폴더에 저장하면 보존본 상대 링크가 유지된다. legacy 연구는 source.family_id로 제한된 분석만 하며 evidence 단위 원천 판별을 했다고 표시하지 않는다.
