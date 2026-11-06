# Evidrill Research

**원문을 추적하고, 반대 근거를 확인하고, 결론이 무엇에 의존하는지 보여주는 조사 스킬.**

[GitHub 저장소](https://github.com/darve1/evidrill-research) · [English](README.md) · [MIT License](LICENSE)

프로젝트 이름은 Evidrill Research이며, 설치 후 선택할 스킬 이름은 아래의 `deep-research` 계열이다.

**Codex와 Claude Code가 같은 스킬 파일과 조사 규칙을 사용한다.**

스킬 목록에서 이름을 선택한 뒤 평소처럼 “이걸로 자료조사해줘”라고 요청하면 된다.

| 선택할 이름 | 조사 범위 |
| --- | --- |
| `deep-research` | **기본:** 논문·학술지·학회·학술 문헌 |
| `deep-research-tech` | 학술 + 기술·오픈소스 |
| `deep-research-tech-only` | 기술·오픈소스만 |
| `deep-research-comu` | 학술 + 커뮤니티 |
| `deep-research-comu-only` | 커뮤니티만 |
| `deep-research-all` | 학술 + 기술·오픈소스 + 범용 웹 + 커뮤니티 |

Codex에서는 아래처럼 `$이름`으로, Claude Code에서는 같은 이름에 `/`를 붙여 호출한다. 스킬 선택기가 있는 앱에서는 목록에서 선택해도 된다.

```text
$deep-research 이 주제의 연구 결과와 반대 근거를 조사해줘.
$deep-research-tech 이 방법의 연구 근거와 실제 구현 조건을 조사해줘.
$deep-research-tech-only 이 주제를 기술·오픈소스 자료만으로 조사해줘.
$deep-research-comu 학술 문헌과 커뮤니티 경험을 함께 조사해줘.
$deep-research-comu-only 커뮤니티 토론·후기·Q&A만 조사해줘.
$deep-research-all 이 주제를 학술·기술·일반 웹·커뮤니티에서 폭넓게 조사해줘.
```

기본 스킬에 `-tech`, `-tech-only`, `-comu`, `-comu-only`, `-all`을 붙여도 같다. `-tech -comu`는 학술+기술+커뮤니티다. `-only` 옵션은 다른 범위 옵션과 함께 쓸 수 없다. `모드: technical|general|community`로 단독 범위를 지정할 수도 있다. `-all`은 네 자료 경로를 포함하며, 접근하지 못한 자료와 검색하지 못한 경로도 표시한다. 인터넷 전체를 빠짐없이 수집한다는 약속은 아니다.

## 무엇을 남기는가

- 주장별 지지·반대 근거와 실제 원문 위치/판본/보존본.
- 같은 연구를 재인용한 출판물, 서로 다른 연구, 공유 데이터 의존성의 구분.
- 특정 원천을 제외했을 때 남는 근거와 작성자의 실제 검토 판단.
- 적용 조건·미확인 사항·결론을 바꿀 다음 확인을 담은 결론 카드.

[가상 사례](examples/README.md)는 입력과 기대 판단을 공개한다. 권위 있는 출처, 정확한 인용, 원장 검사 통과는 의미적 진실성이나 현실 실행 성공의 인증이 아니다. 자동 helper는 `truth_certified:false`를 유지한다.

## 설치와 실행

저장소를 내려받는다.

```text
git clone https://github.com/darve1/evidrill-research.git
cd evidrill-research
python -X utf8 scripts/install_skills.py --target both
```

`--target codex`, `--target claude`, `--target both` 중 고른다. 기본 경로는 Codex `~/.agents/skills`, Claude Code `~/.claude/skills`다. 설치기는 **여섯 폴더를 나란히** 복사하고 해시를 확인한다. `--dry-run`은 파일을 쓰지 않고 설치 계획만 검사한다. 기존 파일 내용이 다르면 복사 전에 중단하며, 다른 스킬이나 전역 설정을 바꾸지 않는다.

기존 Codex 설치가 `~/.codex/skills`에 있다면 `--target codex --skills-dir "~/.codex/skills"`로 그 경로를 사용하고 Claude는 별도로 설치한다. 두 Codex 경로에 같은 이름을 중복 설치하지 않는다. 기존 설치 갱신·프로젝트별 설치·검증 범위는 [호환성 안내](docs/COMPATIBILITY.md)를 참고한다.

스킬이 보이지 않으면 새 세션에서 다음처럼 호출한다.

| 환경 | 입력 예시 |
| --- | --- |
| Codex | `$deep-research 이 주제를 논문·문헌 중심으로 조사해줘.` |
| Claude Code | `/deep-research 이 주제를 논문·문헌 중심으로 조사해줘.` |
| Claude Code 전체 범위 | `/deep-research -all 이 주제를 모든 자료 경로로 조사해줘.` |

`/deep-research-tech-only`, `/deep-research-comu`, `/deep-research-comu-only` 등 여섯 진입점과 범위 옵션은 두 환경에서 같다.

helper는 Python 3.10+와 표준 라이브러리를 사용한다. 모델·검색은 실행 환경의 기존 도구를 사용하며 새 API 키를 요구하지 않는다. 기존 모델/검색 서비스의 비용까지 무료라는 뜻은 아니다.

```powershell
python -X utf8 skills/deep-research/scripts/research_ledger.py init --root research/my-study -all --question "조사 질문"
python -X utf8 skills/deep-research/scripts/research_ledger.py stress --root research/my-study
python -X utf8 skills/deep-research/scripts/research_ledger.py check --root research/my-study
python -X utf8 skills/deep-research/scripts/research_ledger.py render --root research/my-study
```

초기화한 빈 연구는 미완료다. 스킬이 [기록 계약](skills/deep-research/references/records.md)에 따라 실제 수집·검토 기록을 작성한다. `check/stress/render` 종료 코드: 0 기록상 완료, 1 기록 오류, 2 미검토/미해결. 코드2인 정당한 부분 결과도 전달할 수 있다. helper 자체는 웹 검색이나 자동 의미 판정을 하지 않는다.

## 개발과 검증

```powershell
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/verify_project.py
python -X utf8 scripts/verify_project.py --installed-skill "개인-스킬-폴더/deep-research"
```

현재 원본은 [skills/deep-research](skills/deep-research/SKILL.md)와 다섯 추가 진입점이다. [기여 안내](CONTRIBUTING.md), [변경 이력](CHANGELOG.md), [공개 범위와 검증](docs/PUBLICATION.md)을 참고한다. 공개본은 MIT 라이선스이며, 외부 원문 스냅샷과 개인 작업 기록은 포함하지 않는다. GitHub Actions는 비활성화하고 검증은 로컬에서 수행한다.
