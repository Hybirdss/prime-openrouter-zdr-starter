# Prime Agent + OpenRouter ZDR + DeepSeek Flash 1017

GitHub에서 내려받아 AI에게 설치를 맡길 수 있는 Prime Agent 설정 레포입니다. 공식 Prime Agent **0.10.1**과 **`deepseek/deepseek-v4.1-flash-1017`**을 사용하고, OpenRouter 요청에 **`provider.zdr: true`**를 전송합니다.

개인 작업, 기존 대화, 개인 프롬프트, 계정 정보는 포함하지 않습니다. 설치 파일과 실행 중 생기는 키·세션·캐시는 Git에서 제외되는 `.runtime/`에 저장합니다.

## AI에게 설치 맡기기

아래 문장을 로컬 명령을 실행할 수 있는 AI 코딩 에이전트에 전달하세요.

```text
https://github.com/Hybirdss/prime-openrouter-zdr-starter 를 새 폴더에 clone하고,
AGENTS.md를 읽은 뒤 설치해줘. ./setup.sh를 실행하고 doctor --online과
로컬 wire 검증을 통과시켜줘. 기존 Prime 설정이나 내 작업을 복사하지 마.
API 키는 채팅에서 묻지 말고, 내가 로컬 터미널에서 입력하도록 안내해줘.
유료 smoke 요청은 내가 요청할 때만 실행해줘.
```

AI가 설치와 검증을 마치면 해당 폴더에서 `./prime`을 실행하세요. 첫 실행 때 API 키를 터미널에 숨겨서 입력합니다. 키는 `.runtime/openrouter.key`에 권한 `0600`으로 저장합니다.

OpenRouter 계정 생성, API 키 발급, 크레딧 충전은 본인이 진행해야 합니다. [API 키 발급](https://openrouter.ai/settings/keys).

## 직접 설치하기

Linux 또는 macOS의 x64/arm64, Python 3.10 이상, Git, 인터넷 연결이 필요합니다. Linux는 glibc 환경을 사용하세요. Windows는 WSL2의 Ubuntu에서 실행하세요. Python의 `venv` 모듈도 필요합니다. Ubuntu에서 누락되면 `python3-venv` 패키지를 설치하세요.

```sh
git clone https://github.com/Hybirdss/prime-openrouter-zdr-starter.git
cd prime-openrouter-zdr-starter
./setup.sh
python3 -I scripts/manage.py doctor --online
./prime
```

설치 스크립트는 다음 작업을 합니다.

- 고정된 공식 릴리스의 SHA-256을 검증한 뒤 `.runtime/bin/`에 설치합니다.
- 독립된 모델 설정, 세션 경로, daemon 소켓과 Python 환경을 준비합니다.
- `uv`가 없으면 `.runtime/tools/`에 `uv 0.9.5`를 설치합니다.
- Prime Agent의 Python 3.11 커널과 런타임 의존성을 준비합니다.

기존 Prime Agent 설치를 교체하거나 종료하지 않습니다. 관리자 권한이나 전역 npm 설치는 필요하지 않습니다. `./setup.sh`는 다시 실행할 수 있으며, 이 레포 소유의 `models.json`과 `settings.json`을 기본값으로 다시 생성합니다. Python 런타임 의존성은 upstream의 bootstrap을 따르므로 전체 의존성이 고정된 오프라인 배포는 아닙니다.

## 내 프로젝트에서 사용하기

설치 폴더에서 실행하면 현재 폴더를 작업 대상으로 사용합니다. 다른 프로젝트에서 작업하려면 절대 경로 또는 상대 경로로 지정하세요.

```sh
./prime --cwd /path/to/your/project
```

키를 파일에 저장하지 않으려면 실행 전에 터미널에서 환경변수 `OPENROUTER_API_KEY`를 설정하세요. 환경변수가 저장된 키보다 우선합니다. 키를 명령줄 인자, GitHub 이슈 또는 AI 채팅에 붙여넣지 마세요.

## 비용과 속도 선택하기

기본값은 `balanced`입니다. 모델이 지원하는 `low` 추론을 사용하고, OpenRouter의 가격·가용성 기반 기본 라우팅을 유지합니다. 동일 대화의 자동 캐시 재사용을 방해하는 고정 provider 순서는 지정하지 않습니다. 세 프로필 모두 같은 Flash 1017 모델과 ZDR을 사용합니다.

| 프로필 | 실행 명령 | 라우팅 | 선택 기준 |
| --- | --- | --- | --- |
| `balanced` | `./prime` | OpenRouter 기본값 | 가격·가용성·자동 캐시를 함께 고려할 때 |
| `economy` | `./prime --profile economy` | `sort: price` | 최저가 우선. 응답이 더 느릴 수 있음 |
| `fast` | `./prime --profile fast` | `sort: throughput` | 초당 생성 토큰 수 우선. 비용이 더 들 수 있음 |

`--profile`은 `./prime` 바로 뒤에 지정하세요. 프로필마다 설정·세션·daemon을 분리하고, 설치 바이너리·Python 환경·다운로드 캐시·API 키는 공유합니다. 전환해도 다른 프로필의 설정을 덮어쓰지 않습니다.

```sh
./prime --profile economy --cwd /path/to/your/project
./prime --profile fast --cwd /path/to/your/project

# 복잡한 작업에는 추론 강도를 올릴 수 있습니다.
./prime --thinking high
./prime --thinking max

# 짧고 단순한 작업에서 추론을 끄려면 명시적으로 선택하세요.
./prime --profile fast --thinking off
```

모델이 공개한 추론 단계는 `none`, `low`, `high`, `max`입니다. 지원 목록에 없는 기존 `medium` 기본값을 `low`로 바꾸고, Prime의 `off`를 `none`, `max`를 `max`로 전송하도록 매핑했습니다. 낮은 추론 강도는 어려운 작업의 결과에 영향을 줄 수 있으므로 필요하면 `high`로 올리세요.

출력 한도는 기존 65,536토큰을 유지합니다. 한도만 줄이면 실제로 사용하지 않은 토큰의 비용이 줄어드는 것은 아니며, 긴 추론이나 코드를 자를 수 있습니다. 문맥 압축이나 하위 에이전트 수도 작업별 검증 없이 임의로 줄이지 않습니다.

provider ID는 Prime의 기본 `openrouter`를 사용해 응답의 `usage.cost`와 캐시 적중 토큰을 집계합니다. 이전 `openrouter-zdr` ID는 이 실제 비용 처리 경로를 타지 않았습니다. `usage.cost`가 없을 때만 카탈로그 기준 추정값을 사용합니다. 기준값은 2026-10-26 확인 시 입력 $0.30/M, 출력 $1.20/M, 캐시 읽기 $0.006/M이며, 실제 endpoint·시간 할인·BYOK 조건에 따라 청구액이 달라집니다. OpenRouter의 사용 내역이 최종 확인 기준입니다.

현재 ZDR endpoint의 기본 단가는 다음 명령으로 키 없이 조회할 수 있습니다. 시간대별 가격 덮어쓰기는 표에 반영하지 않습니다.

```sh
python3 -I scripts/manage.py doctor --online --profile economy
```

최저가와 최고속을 동시에 보장하는 고정 설정은 없습니다. `sort`를 지정하면 기본 가격 가중 분산 대신 해당 기준으로 정렬합니다. 공개 API에서 이 모델의 지연시간·생성 속도 측정값은 현재 비어 있어, 이 레포는 속도 순위나 절약률을 만들어 표시하지 않습니다. 비교한 레포와 채택 근거는 [비용·속도 조사 기록](docs/research.md)에 있습니다.

## 검증하기

```sh
# 키 없이 로컬 설정과 설치를 확인합니다.
python3 -I scripts/manage.py doctor

# 공개 API에서 이 모델의 ZDR 제공자가 있는지 확인합니다. 추론 요금은 없습니다.
python3 -I scripts/manage.py doctor --online

# 키 없이 공식 바이너리의 실제 HTTP 요청을 로컬 서버에서 검증합니다.
python3 -I tests/verify_wire.py

# 설치·비밀정보 저장·ZDR 설정 변경 감지·손상된 다운로드를 검증합니다.
python3 -I -m unittest discover -s tests -v

# 선택 사항: 내 키로 작은 유료 추론 요청 1건을 전송합니다.
python3 -I scripts/manage.py smoke
```

`verify_wire.py`는 공식 바이너리로 세 프로필의 실제 ZDR·정렬·추론 요청과 도구 정의를 확인합니다. 모의 응답의 보고 비용·캐시 토큰 집계도 검사합니다. 유닛 테스트는 다른 모델을 지정한 실행이 키 접근 전에 거부되는지 확인합니다. 외부 모델 API를 호출하지 않습니다. `smoke`는 OpenRouter 연결 확인용이며 전체 에이전트 작업을 검증하는 명령은 아닙니다. 다른 프로필을 검사하려면 `smoke --profile economy`처럼 지정하세요.

GitHub Actions는 Linux/macOS에서 테스트, 설치, 공개 ZDR 목록 확인과 로컬 wire 검증을 실행합니다. CI에 API 키는 필요하지 않습니다.

## ZDR 적용 범위

이 프로필은 `compat.openRouterRouting.zdr: true`를 사용합니다. 실제 API 요청의 `provider.zdr`로 전달되어 OpenRouter가 ZDR 대상 endpoint로만 라우팅합니다. 조건에 맞는 endpoint가 없으면 요청이 실패하며, 이 레포의 코드는 조건을 완화해 재시도하지 않습니다.

ZDR은 OpenRouter와 모델 제공자의 요청 보관 정책에 관한 설정입니다. 로컬 세션은 `.runtime/`에 남습니다. Prime Agent는 명령 실행·파일 편집 권한을 가진 에이전트이며 이 설치 방식은 보안 샌드박스가 아닙니다. 추가 MCP·검색 서비스 등에는 각 서비스의 데이터 정책이 적용됩니다.

`./prime`은 실행 전에 모델 설정과 허용 모델 정책을 검사하고, CLI에서 다른 provider·모델을 지정하면 거부합니다. daemon 세션에는 `allowedModels` 제한도 적용합니다. 이 제한은 직접 바이너리를 실행하는 것까지 막는 보안 경계가 아닙니다. 세 프로필을 기본값으로 복구하려면 다음 명령을 실행하세요.

```sh
./setup.sh --configure-only
```

## 문제 해결

- `401`이면 OpenRouter 키를 확인하세요. 저장된 키를 바꾸려면 `.runtime/openrouter.key`를 삭제하고 `./prime`을 다시 실행하세요.
- `402`이면 OpenRouter 크레딧을 확인하세요.
- `404` 또는 제공자 없음 오류면 `doctor --online`을 실행하세요. ZDR을 끄지 말고 현재 모델의 endpoint 상태를 확인하세요.
- 경로가 길어 daemon 소켓 오류가 나면 레포를 더 짧은 경로로 옮기세요.
- 다운로드의 SHA-256이 다르면 설치가 중단됩니다. 다시 설치해도 실패하면 공식 릴리스 상태를 확인하세요.
- Python 커널 준비가 실패하면 네트워크와 `uv` 설치 상태를 확인한 뒤 `./setup.sh`를 다시 실행하세요.

중지할 때는 `./prime shutdown`을 사용하세요. 다른 프로필은 `./prime --profile fast shutdown`처럼 지정하세요. 각 프로필의 daemon 소켓에만 연결합니다. 완전히 제거하려면 사용한 프로필의 daemon을 중지한 뒤 clone한 폴더를 삭제하세요. 작업 중 만든 프로젝트 파일은 별도로 보존하세요.

이전 버전에서 갱신하려면 실행 중인 세션을 마치고 기존 버전으로 `./prime shutdown`을 실행하세요. 이후 다음 명령으로 설정을 갱신합니다. 키와 기존 세션 파일은 보존합니다. 이전 `openrouter-zdr` 세션을 재개하는 대신 새 세션으로 시작하세요.

```sh
git pull --ff-only
./setup.sh --configure-only
./prime
```

업데이트는 이 레포의 버전·플랫폼별 체크섬을 함께 검토하고 wire 검증을 다시 실행한 뒤 진행합니다. 독립 설치를 유지하려면 upstream의 전역 `update` 명령 대신 이 레포의 설치 절차를 사용하세요.

## 공식 근거

- [Prime Agent v0.10.1 릴리스와 SHA256SUMS](https://github.com/PrimeIntellect-ai/prime-agent/releases/tag/v0.10.1)
- [Prime Agent custom model 설정 구현](https://github.com/PrimeIntellect-ai/prime-agent/blob/v0.10.1/crates/pa-core/src/models/custom.rs)
- [OpenRouter ZDR 정책](https://openrouter.ai/docs/guides/features/zdr)
- [OpenRouter provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)
- [모델 정보 및 제공자 목록](https://openrouter.ai/deepseek/deepseek-v4.1-flash-1017)
- [현재 ZDR endpoint 목록 API](https://openrouter.ai/api/v1/endpoints/zdr)
- [현재 모델 가격·추론 단계 API](https://openrouter.ai/api/v1/models)
- [OpenRouter 자동 프롬프트 캐시](https://openrouter.ai/docs/guides/best-practices/prompt-caching)

독립적인 설정 레포입니다. Prime Intellect, OpenRouter, DeepSeek의 공식 배포물이 아닙니다. MIT 라이선스를 사용합니다. 내려받는 Prime Agent와 의존성의 라이선스는 각각의 배포물을 따릅니다.
