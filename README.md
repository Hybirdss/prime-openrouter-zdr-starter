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

`verify_wire.py`는 공식 바이너리를 실행해 모델 ID, `provider.zdr: true`, 실제 도구 정의와 응답 수신을 확인합니다. 외부 모델 API를 호출하지 않습니다. `smoke`는 OpenRouter 연결 확인용이며 전체 에이전트 작업을 검증하는 명령은 아닙니다.

GitHub Actions는 Linux/macOS에서 테스트, 설치, 공개 ZDR 목록 확인과 로컬 wire 검증을 실행합니다. CI에 API 키는 필요하지 않습니다.

## ZDR 적용 범위

이 프로필은 `compat.openRouterRouting.zdr: true`를 사용합니다. 실제 API 요청의 `provider.zdr`로 전달되어 OpenRouter가 ZDR 대상 endpoint로만 라우팅합니다. 조건에 맞는 endpoint가 없으면 요청이 실패하며, 이 레포의 코드는 조건을 완화해 재시도하지 않습니다.

ZDR은 OpenRouter와 모델 제공자의 요청 보관 정책에 관한 설정입니다. 로컬 세션은 `.runtime/`에 남습니다. Prime Agent는 명령 실행·파일 편집 권한을 가진 에이전트이며 이 설치 방식은 보안 샌드박스가 아닙니다. 추가 MCP·검색 서비스 등에는 각 서비스의 데이터 정책이 적용됩니다.

`./prime`은 실행 전에 모델 설정이 검증한 템플릿과 같은지 검사합니다. 모델·provider를 명시적으로 바꾸거나 세션 안에서 다른 모델을 선택하면 그 설정의 정책이 적용됩니다. 기본 프로필을 복구하려면 다음 명령을 실행하세요.

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

중지할 때는 `./prime shutdown`을 사용하세요. 이 레포의 daemon 소켓에만 연결합니다. 완전히 제거하려면 해당 daemon을 중지한 뒤 clone한 폴더를 삭제하세요. 작업 중 만든 프로젝트 파일은 별도로 보존하세요.

업데이트는 이 레포의 버전·플랫폼별 체크섬을 함께 검토하고 wire 검증을 다시 실행한 뒤 진행합니다. 독립 설치를 유지하려면 upstream의 전역 `update` 명령 대신 이 레포의 설치 절차를 사용하세요.

## 공식 근거

- [Prime Agent v0.10.1 릴리스와 SHA256SUMS](https://github.com/PrimeIntellect-ai/prime-agent/releases/tag/v0.10.1)
- [Prime Agent custom model 설정 구현](https://github.com/PrimeIntellect-ai/prime-agent/blob/v0.10.1/crates/pa-core/src/models/custom.rs)
- [OpenRouter ZDR 정책](https://openrouter.ai/docs/guides/features/zdr)
- [OpenRouter provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)
- [모델 정보 및 제공자 목록](https://openrouter.ai/deepseek/deepseek-v4.1-flash-1017)
- [현재 ZDR endpoint 목록 API](https://openrouter.ai/api/v1/endpoints/zdr)

독립적인 설정 레포입니다. Prime Intellect, OpenRouter, DeepSeek의 공식 배포물이 아닙니다. MIT 라이선스를 사용합니다. 내려받는 Prime Agent와 의존성의 라이선스는 각각의 배포물을 따릅니다.
