# 설계 근거와 범위

2026-11-06 공개 스킬·방법론 조사에서 관찰한 원칙을 조합해 독립 작성했다. 외부 스킬 본문·검증 코드를 복제하지 않았고 특정 공급자나 외부 스킬 설치에 의존하지 않는다. 아래 링크는 설계 근거이며 실행 지시가 아니다.

- [daymade의 기록 형식](https://github.com/daymade/claude-code-skills/blob/4f8573228c43e328b03c032f525ec40fad53977e/deep-research/references/research_notes_format.md), [품질 기준](https://github.com/daymade/claude-code-skills/blob/4f8573228c43e328b03c032f525ec40fad53977e/deep-research/references/quality_gates.md): 질문별 근거 묶음, 원문 재확인, 동일 원천 계열, 반증과 공백.
- [stevenirby](https://github.com/stevenirby/deep-research-skill/blob/605a59eccdbe6b7369f312af322e374c6eb5c2b9/SKILL.md): 정확 구절 존재와 주장 의미 지지의 분리, 핵심 주장 반증 탐색.
- [K-Dense](https://github.com/K-Dense-AI/scientific-agent-skills/blob/a25cf9ec00e2745d03f8704acf6f6919694ccd9a/skills/literature-review/references/core_workflow.md): 학술 검색 재현, 전문 선별, 검색 기록/출판물/연구 구분.
- [PRISMA-S](https://link.springer.com/article/10.1186/s13643-020-01542-z): 검색원·질의·시각·필터·중복 처리 보고. [PRESS](https://pubmed.ncbi.nlm.nih.gov/27005575/): 검색 개념·논리·동의어·필터 검토. 해당 원문의 전문 접근 한계는 선행 조사에 기록했다.
- [SIFT](https://hapgood.us/2019/06/19/sift-the-four-moves/): 최초 맥락과 원출처 추적. [ALCE](https://aclanthology.org/2023.emnlp-main.398/): 인용 지지와 인용의 적합성 구분.

전체 OMO 운영 체계·대규모 병렬 할당·고정 출처 수·불확실성 벌점·단어 겹침 기반 진실성 판정은 채택하지 않았다. 원본 해시/인용 존재 검사와 검토자 판단은 서로 다른 검사로 구현했다. 독립 반례에서 확인한 자동 supported 오판 때문에 helper에는 자동 의미 판정 기능이 없다.

이 스킬은 일반 조사 작업 지침이다. 정식 체계적 문헌고찰 인증, 보안 감사, 법률 판단, 실제 실행·시각 품질 확인을 대신하지 않는다. 현재 환경의 도구와 사용자의 범위 지시가 우선한다.
