---
name: deep-research-comu
description: "Use when the user selects academic research plus community discussions, user reports, forums and Q&A evidence. Adds community scope while retaining scholarly literature."
---

# Deep Research + Community

이 스킬은 **논문·학술 문헌 + 커뮤니티 자료**를 함께 조사한다. 기술·범용 웹 경로를 기본으로 추가하지 않는다.

상대 경로는 현재 작업 폴더가 아닌 이 `SKILL.md`의 위치를 기준으로 해석한다. 형제 폴더의 [공통 스킬](../deep-research/SKILL.md)을 읽고, helper `../deep-research/scripts/research_ledger.py`의 `init -comu`로 시작한다. literature/community 참고 문서를 읽고 하나의 원장에 두 경로를 구분한다. 경험담의 주체·환경·재전달을 추적하며 학술 근거와 사용자 경험을 동일한 수준의 증거로 취급하지 않는다.

`-tech`를 추가하면 학술+기술+커뮤니티, `-all`이면 네 경로다. 명확한 사용자 후속 범위 지시는 이 기본값보다 우선한다. 공통 deep-research와 함께 설치하며, 파일 누락 시 알린다.
