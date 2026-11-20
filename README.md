# erpnext-ko

ERPNext·Frappe v16 한국어 번역 앱이다. erpnext 다음에 설치하면 이 앱의 `erpnext_ko/locale/ko.po` 가 기존 한국어 번역을 덮어쓴다.

## 왜 따로 만드나

upstream 에도 `ko.po` 는 있다 (v16.60 기준). 하지만 그대로 쓸 수 없다.

| 앱 | 메시지 | 번역됨 | 상태 |
|---|---:|---:|---|
| frappe (화면 틀) | 8,021 | 5.1% | 저장·확정·취소 같은 버튼이 비어 있다 |
| erpnext | 12,092 | 86.7% | 옛 기계번역이다. Credit→"신용 거래", Total Credit→"총 학점", Stock Entry→"주식 입력", Asset→"유산", Party→"파티", Item→"목" |

이 앱은 더존·한국 회계기준 용어로 처음부터 다시 옮긴다. 용어는 [용어집](glossary/terms.tsv) 한 곳에서 정하고, 모든 번역은 기계 검사를 통과해야 들어간다.

## 동작 방식

- Frappe 는 설치된 앱 순서대로 `sites/assets/locale/ko/LC_MESSAGES/<앱>.mo` 를 읽어 하나의 사전으로 합친다. 같은 원문이면 뒤에 설치된 앱이 이긴다.
- 그래서 이 앱이 frappe·erpnext 의 원문을 모두 담으면 기존 번역을 대신하게 된다.
- upstream 원본에 빠진 v16 사이드바·데스크 아이콘 라벨도 [upstream/sidebar.pot](upstream/sidebar.pot) 으로 담는다.
- 날짜 선택기(air-datepicker)에는 한국어 로케일이 없어 월·요일이 영어로 나온다. 이 앱이 [erpnext_ko/public/js](erpnext_ko/public/js) 에서 `ko` 로케일을 등록한다.
- Frappe 는 날짜 선택기 언어를 사용자 설정의 언어로만 고른다. 그래서 언어를 비워 둔 사용자도 화면 언어를 따르게 한다.
- 설치할 때(`after_install`)와 `bench migrate` 할 때(`after_migrate`) 다음 세 가지를 한다.
  1. 언어 `ko` 를 켠다.
  2. ko.po 를 .mo 로 컴파일한다.
  3. 번역 캐시를 비운다.

## 설치

```bash
bench get-app https://github.com/opensmileserv/erpnext-ko
```

```bash
bench --site <site> install-app erpnext_ko
```

사용자 설정이나 시스템 설정에서 언어를 `한국어` 로 고른다.

## 컨테이너로 띄워 보기

`frappe/erpnext:v16.60.0` 이미지 위에 이 앱을 얹은 개발 스택이다. 앱은 이미지를 만들 때 복사해 넣는다. Docker Desktop 의 바인드 마운트는 파일을 바꿔치기하는 저장(임시 파일 → 이름 바꾸기)을 컨테이너에 보여 주지 않기 때문이다. 이미지를 만들 때 `bench build` 가 앱의 JS 를 묶고 ko.po 를 .mo 로 컴파일한다.

```bash
docker compose -f dev/compose.yml up -d --build
```

첫 실행은 사이트를 만들고 한국 기본값(한국어, KRW, Asia/Seoul, 시범 회사)으로 설정 마법사를 끝낸다. 몇 분 걸린다. 그다음 http://localhost:8081 에 개발용 계정 `Administrator` / `admin` 으로 들어간다. 이 PC 에서만 열린다.

ko.po 를 고친 뒤 화면에 반영한다. 컴파일한 .mo 를 백엔드·작업자 컨테이너에 넣고 캐시를 비운다.

```bash
./dev/refresh
```

JS 나 `hooks.py` 를 고쳤으면 이미지를 다시 만들고 캐시를 비운다.

```bash
docker compose -f dev/compose.yml up -d --build
```

```bash
docker compose -f dev/compose.yml exec backend bench --site ko.localhost clear-cache
```

## 번역 작업

도구는 `./kotr` 이다.

| 명령 | 하는 일 |
|---|---|
| `./kotr sync` | `upstream/*.pot` 을 ko.po 에 합친다. 원문에서 사라진 번역은 `#~` 로 보관했다가 같은 원문이 돌아오면 되살린다 |
| `./kotr seed` | 용어집 표제어와 똑같은 메시지를 용어집 번역으로 채운다 |
| `./kotr translate --where '^erpnext/accounts/'` | 빈 메시지를 모델로 옮긴다. 검사를 통과한 것만 받고, 걸린 것은 이유를 붙여 한 번 더 요청한다. 그래도 안 되면 비워 두고 `work/rejected.tsv` 에 남긴다. 모델 요청이 실패한 묶음이 있으면 종료 코드 1 이다 (다시 실행하면 남은 것만 옮긴다) |
| `./kotr review` | 모든 번역을 검사한다. 문제가 있으면 종료 코드 1 이다 |
| `./kotr review --reset` | 문제가 있는 기계 번역을 비운다. 용어집을 고친 뒤 `translate` 와 함께 쓴다 |
| `./kotr compile` | ko.po 를 `work/erpnext_ko.mo` 로 컴파일한다 |
| `./kotr stats` | 번역 현황 |
| `./kotr extract-sidebar <apps 디렉터리>` | v16 사이드바·데스크 아이콘 라벨을 `upstream/sidebar.pot` 으로 뽑는다 |

모델은 OpenAI 호환 엔드포인트면 된다. 환경 변수로 정한다.

| 변수 | 예 |
|---|---|
| `KOTR_BASE_URL` | `http://<호스트>:8001/v1` |
| `KOTR_MODEL` | `Qwen/Qwen3.8-27B` |
| `KOTR_API_KEY` | (필요할 때) |
| `KOTR_EXTRA_JSON` | `{"chat_template_kwargs":{"enable_thinking":false}}` (Qwen 의 생각 모드 끄기) |

모델에는 공개된 화면 문구와 용어집만 보낸다. 회사 데이터는 보내지 않는다.

### 기계 번역 표시

- 모델이 옮긴 메시지에는 PO 플래그 `mt` 가 붙는다 (`#, mt`).
- 사람이 검토해 고친 메시지는 `mt` 를 지운다. 그러면 `review --reset` 이 비우지 않는다.
- 용어집으로 채운 메시지에는 `mt` 가 없다. 용어집 자체를 검토하는 것이 먼저다.

### 검사 항목

| 검사 | 내용 |
|---|---|
| 자리표시자·표시 | `{0}`, `{name}`, `%s`, `%(x)s`, `${x}`, HTML 태그, `&lt;태그&gt;`, `&nbsp;`, URL, 이메일, `@이름`, `` `코드` ``, 코드 이름(`doc.status`, `is_group`, `delete()`, `uid={0}`, `.csv`) 이 원문과 같다 (순서는 바뀌어도 된다). 메시지 전체가 밑줄 이름 하나(`on_submit`)면 선택지 라벨로 보고 번역해도 된다 |
| 모양 | 줄바꿈 수, 앞뒤 공백이 같다. 한자·가나가 없다. 영어 문장이면 한글이 있다. 이때 한글이 없는 용어집 번역어(그대로 쓰는 이름, `POS`)는 문장에서 뺀다 |
| 용어집 | 원문에 표제어가 있으면 그 번역어가 들어 있다. '피할 말' 은 없다. 위의 표시와 `<code>` 안은 보지 않는다 |

한 메시지에서 용어집을 일부러 따르지 않을 때는 PO 번역자 주석에 `# glossary-skip: <표제어>` 를 단다.

### 용어집

[glossary/terms.tsv](glossary/terms.tsv) 는 탭으로 나눈 6칸이다.

| 칸 | 뜻 |
|---|---|
| `en` | 표제어. 단어 경계로 찾고, 대소문자와 복수형(s, es, ies)을 가리지 않는다. 모두 대문자인 약어(`HR`)는 대소문자를 가린다. 긴 표제어가 먼저다 |
| `ko` | 번역어. `\|` 로 허용 변형을 더한다. 첫째가 권장이다. 문장 안 활용형(가져올·내보낼)은 어간을 변형으로 둔다. `en` 과 같으면 그대로 쓰는 이름이고, 원문의 표기(`facebook`)도 받는다 |
| `avoid` | 쓰면 안 되는 말 (`\|` 로 여럿) |
| `apps` | 적용 범위 (`erpnext`, `frappe`, 비우면 전체). 메시지의 참조 경로로 정한다 |
| `match` | `word`(문장 안에서도 찾음), `case`(word 와 같되 대소문자를 가림. 'Lead' 문서와 'lead to' 동사를 가를 때), `exact`(메시지 전체가 표제어일 때만) |
| `note` | 판단 근거 |

번역어를 바꾸면 이렇게 한다.
1. `./kotr review --reset` 으로 걸리는 기계 번역을 비운다.
2. `./kotr translate` 로 다시 옮긴다.

## 검사

```bash
./check
```

이 명령 하나로 아래를 차례로 돌린다.

1. ruff format, ruff 전체 규칙
2. ast-grep 가드(주석·문서 문자열 금지)와 가드 자체 시험
3. basedpyright strict
4. pytest + Hypothesis
5. `./kotr review`

커밋 훅은 `git config core.hooksPath .githooks` 로 켠다.

## upstream 따라가기

GitHub Actions([.github/workflows/upstream.yml](.github/workflows/upstream.yml))가 매일 03:00(한국 시각)에 [tools/update-upstream](tools/update-upstream) 을 돌린다.

1. frappe·erpnext 의 `version-16` 브랜치에서 원문(`main.pot`)과 사이드바·데스크 아이콘 문서를 얕게 내려받는다.
2. 원문이 그대로면 여기서 끝낸다. upstream 원문은 봇이 주 1회쯤 다시 만들기 때문에 대부분의 날이 그렇다.
3. 바뀌었으면 `./kotr sync` → `seed` → `translate` → `./check` 를 돌린다. 원문의 버전과 커밋은 [upstream/SOURCE.md](upstream/SOURCE.md) 에 적는다.
4. 모두 통과하면 main 에 커밋한다. 모델 요청이 하나라도 실패하거나 검사에 걸리면 커밋하지 않고, 다음 날 처음부터 다시 한다.

작업은 GPU 서버에 둔 self-hosted 러너(라벨 `gpu`)에서 돈다. 모델 서버는 바깥에서 막혀 있어 GitHub 의 러너로는 닿지 않는다. 그래서 같은 서버의 `http://127.0.0.1:8001/v1` 을 쓴다. 모델 이름과 옵션은 워크플로 파일에 있다.

- 러너는 sudo 가 없는 전용 사용자 `ghrunner` 로 돈다. 위치는 `/home/ghrunner/actions-runner` 이다.
- 공개 저장소에 self-hosted 러너를 두면 포크 PR 의 워크플로가 이 서버에서 돌 수 있다. 그래서 저장소 설정의 포크 PR 워크플로 승인은 '모든 외부 기여자'로 둔다. 모르는 PR 의 워크플로 실행은 승인하지 않는다.

손으로 돌리려면 Actions 탭에서 `upstream` 을 실행한다. 이때는 먼저 모델 서버에 닿는지 확인한다. 로컬에서는 `KOTR_*` 환경 변수를 정하고 실행한다. 다른 브랜치를 따라가려면 `UPSTREAM_BRANCH` 를 정한다 (기본 `version-16`).

```bash
tools/update-upstream
```

## 라이선스

GPL-3.0-or-later. ERPNext·Frappe 의 원문을 담으므로 같은 조건을 따른다.
