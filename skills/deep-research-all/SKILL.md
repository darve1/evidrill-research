---
name: deep-research-all
description: "Use when the user selects broad research across academic literature, technical/open-source evidence, general web sources, and community reports. All-source scope for deep-research."
---

# Deep Research — All Sources

사용자가 이 스킬을 선택하면 **논문·학술지·학회·문헌 + 기술·오픈소스 + 범용 웹 + 커뮤니티**을 함께 조사한다. 별도 모드 확인 없이 시작한다.

먼저 형제 폴더의 [공통 스킬](../deep-research/SKILL.md)을 읽고 `-all` 범위로 수행한다. helper는 `../deep-research/scripts/research_ledger.py`다. `init -all`로 하나의 연구 폴더를 만들고 출처 경로를 기록하며, 같은 연구/원출처를 범위 간 중복 계산하지 않는다. 사용자에게 더 좁은 명시적 모드 지시가 있으면 이를 따른다.

이 진입점은 `deep-research`와 함께 설치한다. 공통 파일을 열 수 없으면 설치 누락을 알린다. 넓게 수집하되 인터넷 전체를 빠짐없이 읽었다고 주장하지 않는다. 공통 스킬의 중단 조건·접근 한계·검증 규칙을 적용한다.
