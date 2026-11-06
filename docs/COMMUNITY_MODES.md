# 커뮤니티와 단독 조사 옵션

2026-11-06 사용자 요청으로 tech-only, comu, comu-only를 추가했다. 기본 학술 조사와 기존 누적 기술 조사 의미는 유지한다.

| 스킬 선택 이름 | 기본 스킬에 붙일 옵션 | 범위 |
| --- | --- | --- |
| deep-research | 없음 | 학술 |
| deep-research-tech | -tech | 학술 + 기술·오픈소스 |
| deep-research-tech-only | -tech-only | 기술·오픈소스만 |
| deep-research-comu | -comu | 학술 + 커뮤니티 |
| deep-research-comu-only | -comu-only | 커뮤니티만 |
| deep-research-all | -all | 학술 + 기술·오픈소스 + 범용 웹 + 커뮤니티 |

`-tech -comu`는 학술·기술·커뮤니티다. `-all`은 누적 옵션보다 우선한다. `-only`와 다른 범위 옵션을 동시에 명시하면 충돌이며 helper는 폴더를 만들기 전에 거부한다. `--mode`와 범위 옵션의 동시 지정도 거부한다. 단독 `--mode community`는 `-comu-only`와 같다. 자연어 요청에서 새 범위가 명확하면 선택한 스킬의 기본값보다 사용자 지시가 우선한다.

커뮤니티 원장은 route를 `community`로 기록한다. 일반 보도/공공 통계는 general, 공식 기술 문서/릴리스는 technical이다. 후기의 작성자·환경·버전·원글/댓글 위치와 재전달 관계를 보존한다. 추천 수를 발생률로, 자가 보고를 제품 전체의 사실로 확대하지 않는다. 명확하지 않은 독립성은 unknown으로 유지한다.

기존 schema 2 연구의 세 경로 배열은 유효하다. 새 -all 호출에서만 네 경로를 생성하며 과거 원장과 검증 결과는 수정하지 않는다. 커뮤니티를 선택했지만 검색하지 못했으면 다른 경로처럼 공백으로 표시한다.

개인 설치 시 공통 deep-research와 다섯 진입점 폴더를 나란히 둔다. 전역 설정과 다른 스킬은 변경하지 않는다. [사용 안내](../README.ko.md), [공개본의 검증 범위](PUBLICATION.md). 개발 중의 과거 실행 기록은 로컬에 보존한다.
