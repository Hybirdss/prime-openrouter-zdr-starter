# 비용과 속도 설정의 근거

2026-10-26 공개 GitHub 저장소와 공식 OpenRouter API를 확인했습니다. 같은 Prime Agent·Flash 1017·ZDR 조합의 설치 레포는 GitHub 검색 결과에서 이 레포 외에 확인하지 못했습니다. 따라서 비슷한 코딩 에이전트 설정 레포와 각 기능의 원본 구현을 비교했습니다. 아래는 성능 벤치마크 결과가 아닙니다.

## 비교한 공개 레포

| 레포 | 확인한 기능 | 이 레포에 적용한 판단 |
| --- | --- | --- |
| [Prime Agent](https://github.com/PrimeIntellect-ai/prime-agent) | Custom models, 추론 매핑, OpenRouter 실제 비용 처리 | 고정 릴리스가 실제 지원하는 필드만 사용. 기본 provider 이름으로 실제 비용 집계 복구 |
| [pi](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/settings.md) | 추론·캐시·문맥 압축 설정 | 지원되는 추론 강도를 명시. 최신 pi의 캐시 워밍·모델별 압축 기능을 Prime 0.10.1에 그대로 넣지 않음 |
| [kickstart.pi](https://github.com/orionpax1997/kickstart.pi/blob/main/docs/installation-rtk.md) | rtk를 이용한 셸 출력 압축 | 입력 토큰을 줄이는 방향은 유용하나 전역 확장 설치와 명령 출력 변경을 동반하므로 기본 설치에 추가하지 않음 |
| [Claude Code Router](https://github.com/musistudio/claude-code-router/blob/main/docs/src/content/docs/en/configuration/routing.md) | 작업별 모델 분기 | 별도 프록시·다른 모델을 추가하는 대신 같은 모델의 OpenRouter 라우팅 프로필만 제공 |
| [dscache](https://github.com/SuperMarioYL/dscache/blob/main/README.en.md) | 캐시 토큰 계측과 HIT/PARTIAL/MISS/UNKNOWN 구분 | 별도 프롬프트 로그를 추가하지 않고 Prime의 네이티브 캐시 토큰·비용 집계를 검증 |

다른 저장소의 코드는 복사하지 않았습니다. 개인 설정이나 작업 기록을 조사 자료로 사용하지 않았습니다.

## 실제 요청에서 확인한 변경

[공식 모델 API](https://openrouter.ai/api/v1/models)는 이 모델의 지원 추론 강도를 `max`, `high`, `low`, `none`으로 제공합니다. 기존 기본값 `medium`은 목록에 없습니다. 기본값을 `low`로 바꾸고 Prime의 `off`를 `none`, `max`를 `max`로 명시적으로 매핑했습니다. `low`가 작업 정확도를 유지하는지는 작업별로 판단해야 합니다.

[Prime의 비용 처리](https://github.com/PrimeIntellect-ai/prime-agent/blob/v0.10.1/crates/pa-ai/src/providers/openai_completions/convert.rs)는 provider ID가 `openrouter`일 때만 응답의 실제 비용을 사용합니다. 이전 `openrouter-zdr`와 누락된 모델 단가는 비용이 0으로 표시될 수 있는 조합이었습니다. 기본 provider 이름과 참조 단가를 사용해 이 문제를 고쳤습니다. 보고 비용이 없는 응답은 여전히 추정값입니다.

기본 `balanced`는 [OpenRouter의 가격 가중·가용성 기반 라우팅](https://openrouter.ai/docs/guides/routing/provider-selection)을 사용합니다. `economy`의 `sort: price`는 최저가 우선, `fast`의 `sort: throughput`은 생성 토큰 속도 우선입니다. 두 옵션은 기본 분산 정책을 바꿉니다. 최고속 옵션이 최저가도 보장하지는 않습니다.

[자동 프롬프트 캐시](https://openrouter.ai/docs/guides/best-practices/prompt-caching)는 제공자가 지원하면 OpenRouter와 제공자가 처리합니다. 수동 `provider.order`는 캐시 기반 sticky routing을 해제하므로 지정하지 않습니다. 캐시 적중을 강제하거나 절약률을 보장하지 않습니다.

## 추가하지 않은 설정

Prime 0.10.1의 [routing 타입](https://github.com/PrimeIntellect-ai/prime-agent/blob/v0.10.1/crates/pa-types/src/ai/routing.rs)은 여러 단어로 된 필드를 camelCase로 직렬화합니다. OpenRouter는 `max_price`, `preferred_min_throughput`, `data_collection` 등 snake_case를 문서화하고 있습니다. 요청에 제대로 전달되지 않는 가격 상한·성능 문턱을 넣어 효과가 있다고 설명하지 않습니다. `zdr`, `sort`는 필드명이 일치하며 실제 전송을 검증했습니다.

[모델 endpoint API](https://openrouter.ai/api/v1/models/deepseek/deepseek-v4.1-flash-1017/endpoints)에서 확인한 모든 endpoint의 공개 지연시간·생성 속도 지표는 `null`이었습니다. 특정 제공자가 가장 빠르다고 고정하거나 속도 향상률을 계산하지 않았습니다. `fast`는 OpenRouter에 throughput 정렬을 요청하는 설정이며 자체 벤치마크 승자가 아닙니다.

최대 출력은 65,536토큰으로 유지했습니다. 이 한도는 실제 생성한 토큰 수가 아니며, 추론과 답변이 한도를 공유합니다. 한도만 낮추는 것을 실제 비용 절감으로 계산하지 않습니다. 전체 문맥 한도와 압축 정책도 유지했습니다.

## 재현 가능한 검증

`python3 -I tests/verify_wire.py`는 공식 바이너리를 로컬 HTTP 서버에 연결합니다. 세 프로필의 문자 그대로의 ZDR·정렬 요청, 기본 low와 high/max/off 추론 매핑을 확인합니다. 모의 응답의 `usage.cost`와 캐시 적중 토큰이 집계되는지도 검사합니다. 유료 모델이나 실제 API 키를 사용하지 않습니다.

Prime의 `allowedModels`는 daemon 정책이며 직접 실행한 `--print`에서는 같은 제한이 적용되지 않는 것을 확인했습니다. 따라서 `./prime` 실행 래퍼가 다른 모델·provider의 명시적 CLI 선택을 키 접근 전에 거부합니다. 이 경계는 유닛 테스트로 검사합니다. 바이너리 직접 실행을 통제하는 보안 기능으로 설명하지 않습니다.

이 검사는 전송 설정과 비용 표시의 정확성을 검증합니다. 실제 업무의 완료 비용·응답시간·정확도 향상률은 측정하지 않았습니다. 그런 비교에는 같은 작업·같은 품질 기준·여러 차례의 유료 실행과 실제 청구 내역이 필요합니다.
