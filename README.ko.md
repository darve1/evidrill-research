# Evidrill Research

**원문을 추적하고, 반대 근거로 결론을 시험하는 조사 스킬.**

Claude Code와 Codex에서 쓰는 조사 스킬임. 답을 좌우하는 핵심 주장 몇 개에 대해 다음을 함께 남김.
- 원문 보존본과 실제로 읽은 구절
- 핵심 주장마다 최소 2회의 반대 근거 검색
- 근거의 출처 하나를 뺐을 때 무엇이 남는지

[English](README.md) · [평가 결과](evals/results.md) · [합성 예제](examples/README.md) · [MIT License](LICENSE)

## 설치

**Claude Code:**

```text
/plugin marketplace add darve1/evidrill-research
/plugin install evidrill@evidrill
```

**Codex 또는 플러그인을 쓰지 않는 Claude Code** (Python 3.10 이상):

```text
git clone https://github.com/darve1/evidrill-research.git
cd evidrill-research
python -X utf8 scripts/install_skills.py --target both
```

0.1.x의 `deep-research*` 폴더를 쓰고 있었다면 `--remove-legacy`를 붙이세요. 옛 이름은 Claude Code에 내장된 `deep-research` 스킬과 이름이 겹쳤음. 수정하지 않은 0.1.x 파일만 지우고, 고친 파일은 남겨 둠. 자세한 내용은 [호환성 문서](docs/COMPATIBILITY.md)를 보세요.

## 사용

```text
/evidrill 시간 제한 섭식이 같은 칼로리 제한보다 체중 감량에 더 효과적인지 조사해줘
/evidrill -tech-only uv가 pip보다 정말 10~100배 빠른지 확인해줘
$evidrill -all 이 방법을 지금 도입해도 되는지 조사해줘
```

Claude Code에서는 `/`, Codex에서는 `$`를 붙이세요. 옵션별 조사 범위는 다음과 같음.

| 옵션 | 조사 범위 |
| --- | --- |
| 없음 | 학술 문헌 |
| `-tech` | 학술 문헌 + 공식 문서·릴리스·코드 |
| `-community` | 학술 문헌 + 포럼·사용자 후기 |
| `-all` | 위 전부 + 일반 웹 |
| `-tech-only`, `-community-only` | 해당 경로만 |

답변은 질문한 언어로 나옴.

답변 첫 세 줄은 결론, 기록이 허용하는 확신 수준, 가장 큰 약점임. 그 뒤에 주장 카드, 하지 않은 일, 분모를 밝힌 검색 범위가 이어짐. 실제 평가 실행에서 나온 답변의 첫 부분:

> **결론:** 같은 수준의 칼로리 제한보다 시간 제한 섭식(TRE)이 체중 감량에 더 효과적이라는 근거는 없음. 읽은 직접 비교 RCT 2건에서는 유의한 차이가 없었음.
> **확신 수준:** 낮음~중간. 핵심 RCT 2건은 전문이 아니라 초록만 읽었고, 두 시험 모두 표본이 작음.
> **가장 큰 약점:** 직접 비교 시험이 작고 비맹검임. 신뢰구간이 넓어서 수 kg의 차이도 배제하지 못함.

## 효과가 있나

칸마다 Claude Code를 Sonnet으로 한 번씩 돌린 결과임. 실제 주제는 블라인드로 채점함. 답변 순서를 섞고, 핵심 주장을 원문과 대조하는 방식임. 방법과 한계는 [평가 결과](evals/results.md)를 보세요.

| | 스킬 없음 | 0.1.1 | 0.2.0 |
| --- | --- | --- | --- |
| 쉬운 가상 자료 (채점표, 13점 만점) | 12.5 | 13 | 12.5 |
| 어려운 가상 자료 (채점표, 13점 만점) | 9 | 9 | 10.5 (최종 답변 형식으로 재실행: 11.5) |
| 실제 주제: 시간 제한 섭식 (블라인드 순위) | 3위 | 2위 | 1위 |
| 실제 주제: uv와 pip (블라인드 순위) | 2위 | 3위 | 1위 |
| 실제 주제에서 확인한 주장 중 완전히 맞은 것 | 3/10 | 8/10 | 9/10 |
| 출처를 잘못 붙이거나 수치를 섞은 곳 | 2 | 3 | 0 |
| 실행 1회 비용 | $0.10–0.16 | $0.31–0.68 | $0.57–1.18 |

스킬 없이 답할 때와 비교하면 비용은 약 6~8배, 시간은 2.5~7배 듦. 쉬운 가상 자료에서는 나아지지 않음. 칸마다 한 번씩만 돌렸으므로 작은 차이는 확정할 수 없음.

## 무엇을 기록하나

조사마다 작업 중인 프로젝트 안에 폴더가 하나 생기고, 다음을 기록함.
- 실제로 실행한 검색(실패 포함)
- 도우미가 `snapshot --url`로 직접 받은 원문 보존본
- 보존본과 대조한 인용 구절과 앞뒤 문맥
- 주장, 그리고 주장-구절 쌍마다의 판정
- 핵심 주장별 반대 근거 검색
- 출처 제거 검토

도우미는 바뀌는 내용마다 검사하고, 오류를 만드는 변경은 거부함. 다만 의미를 판정하지는 않음. `check`의 종료 코드는 기록된 검토가 끝났으면 0, 기록 오류면 1, 검토가 남았으면 2임. **모든 출력에 `truth_certified:false`가 붙음.** 기록 형식은 [records.md](skills/evidrill/references/records.md), 예시는 [합성 예제](examples/README.md)를 보세요.

## 개발

```text
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/verify_project.py
```

[CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md), [평가 하네스](evals/README.md), [공개 범위](docs/PUBLICATION.md), [설계 근거](docs/PROVENANCE.md)를 함께 보세요.
