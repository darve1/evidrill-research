---
name: deep-research-tech-only
description: "Use when the user selects research limited to technical and open-source evidence: official documentation, releases, code and reproducible technical results."
---

# Deep Research — Tech Only

이 스킬은 **기술·오픈소스 자료만** 조사한다. 학술·범용·커뮤니티 경로를 기본으로 추가하지 않는다.

상대 경로는 현재 작업 폴더가 아닌 이 `SKILL.md`의 위치를 기준으로 해석한다. 형제 폴더의 [공통 스킬](../deep-research/SKILL.md)을 읽고, helper `../deep-research/scripts/research_ledger.py`의 `init -tech-only`로 시작한다. technical 참고 문서와 공통 원문·반증·스트레스 검토 규칙을 적용한다. 기술 자료만으로 답할 수 없는 부분은 공백과 다음 확인으로 남긴다.

명확한 사용자 후속 범위 지시는 이 기본값보다 우선한다. 서로 충돌하는 명시적 범위 옵션은 공통 규칙에 따라 확인한다. 공통 deep-research와 함께 설치하며, 파일 누락 시 알린다.
