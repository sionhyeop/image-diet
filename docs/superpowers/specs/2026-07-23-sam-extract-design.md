# 요소 추출 SAM 인스턴스 분리 — 설계

날짜: 2026-07-23
대상: 웹앱(`index.html`) 전용.

## 목적

요소 추출에서 지금의 색 기반 flood(색이 비슷한 인접 물체가 뭉침) 대신, 클릭 한 점으로
**그 물체 하나(instance)** 를 정확히 떼어낸다. SAM 계열 모델을 쓰되, 무거운 모델
다운로드는 **사용자가 버튼을 눌러 명시적으로 받은 뒤**에만 활성화한다. 받지 않으면
지금의 색 기반 방식이 그대로 동작한다.

## 확정된 모델 (스파이크로 실측 완료)

**SlimSAM-77-uniform (Xenova) 양자화** — 대폭 가지치기된 SAM. 번들된 ONNX Runtime
Web v1.19.2에서 그대로 동작함을 onnxruntime로 실측했다.

| 파일 | 크기 | 역할 |
| --- | --- | --- |
| `vision_encoder_quantized.onnx` | 8.5MB | 이미지 → 임베딩 (1회, ~2.3초) |
| `prompt_encoder_mask_decoder_quantized.onnx` | 4.7MB | 점 프롬프트 → 마스크 (클릭당 ~53ms) |

합계 ~13MB. CDN: `https://huggingface.co/Xenova/slimsam-77-uniform/resolve/main/onnx/<파일>`
— `Origin`에 대해 `access-control-allow-origin`을 돌려주어 교차 출처 fetch 가능(실측).

### 입출력 (실측)

- 인코더: 입력 `pixel_values` float32 `[1,3,1024,1024]` → 출력 `image_embeddings`,
  `image_positional_embeddings` 각 `[1,256,64,64]`.
- 디코더: 입력 `input_points` float32 `[1,1,N,2]`, `input_labels` **int64** `[1,1,N]`,
  `image_embeddings`, `image_positional_embeddings` → 출력 `iou_scores` `[1,1,3]`,
  `pred_masks` float32 `[1,1,3,256,256]` (멀티마스크 3개, logits).

## 범위

포함:
- 요소 추출에 SAM 옵션 추가 (클릭 게이팅 다운로드)
- 모델 다운로드(진행률) → 인코더 임베딩 1회 → 클릭당 디코더 마스크
- SAM 마스크를 기존 크롭·고스트·대기열 흐름에 연결
- 다운로드한 모델을 Cache Storage에 저장(재방문 재사용) + `navigator.storage.persist()` 요청

제외 (YAGNI):
- 배경 제거 탭에는 SAM 미적용 (요소 추출만)
- 다중 점/박스 프롬프트 (전경 점 1개로 시작; 음성 점 등은 후속)
- 모델을 저장소에 커밋 (CDN에서 받음)

## 다운로드 게이팅 UX

요소 추출 화면(`#exBody`)에 안내 + 버튼:
- 기본: **색 기반 방식 동작**. 상단에 "🎯 AI 정밀 분리 — 물체 단위로 정확히 (모델 약 13MB 받기)" 버튼.
- 버튼 클릭 → 인코더+디코더 다운로드(진행률 %). 완료 시 세션 생성, SAM 모드 ON.
- SAM ON이면 배지/문구가 "AI 정밀 분리 켜짐"으로 바뀌고, 이미지가 로드돼 있으면 즉시 인코더 임베딩 계산(진행 표시).
- 실패(네트워크/CORS/로드) 시 토스트로 알리고 색 기반으로 유지.

**첫 다운로드는 외부 서버(HF CDN) 접속** — 앱의 "서버 전송 0" 원칙에서 이 기능만 예외임을 버튼 설명에 명시(사용자 동의).

## 파이프라인

`sam` 모듈(전역 함수 묶음)로 분리한다. tkinter 없는 순수 로직이라 단위 검증 가능.

### 전처리 `samPreprocess(srcCanvas, W, H) → {pixels: Float32Array, scale}`
- `scale = 1024 / max(W, H)`, `rw = round(W*scale)`, `rh = round(H*scale)`.
- 1024×1024 캔버스에 원본을 `(rw, rh)`로 그려 좌상단 배치(나머지는 0 패딩).
- CHW float32로 정규화: `(rgb/255 - mean)/std`, mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225].

### 인코더 `samEncode(pixels) → {emb, posEmb}`
- `session.run({pixel_values: [1,3,1024,1024]})`. 이미지당 1회, 결과 캐시(임베딩).

### 디코더 `samDecodeAt(emb, posEmb, ox, oy, scale) → maskCanvas(W×H)`
- 점을 1024 프레임으로: `px = ox*scale, py = oy*scale`.
- feeds: `input_points [1,1,1,2] float32`, `input_labels [1,1,1] int64 =1n`, `image_embeddings`, `image_positional_embeddings`.
- 출력 `pred_masks [1,1,3,256,256]` 중 `iou_scores` 최대인 마스크 선택.
- 후처리: 256 저해상 logits를 threshold 0(>0=전경). 256 프레임은 패딩된 1024에 대응하므로,
  원본 픽셀 `(ox,oy)`는 `(ox*scale/4, oy*scale/4)`에 매핑. 원본 W×H 알파 캔버스로 업스케일
  (LANCZOS/부드럽게)해서 반환.

### 컴포넌트 변환
반환 마스크에서 bbox를 구해 기존 `exCropComponent`가 받는 `comp` 형태로 만든다:
`{ mask: maskCanvas(gw=W,gh=H), minX, minY, maxX, maxY, area, gw:W, gh:H }`. 이렇게 하면
크롭·고스트·대기열(`exCropComponent`/`exActivate` 이후 흐름)이 **수정 없이 재사용**된다.

## 통합 지점

`exActivate` → `exPickComponent(wx, wy)` 대신, SAM ON이고 임베딩 준비됐으면
`exSamPick(wx, wy)`(work 좌표 → 원본 좌표 변환 후 `samDecodeAt`)를 쓴다. SAM OFF이거나
임베딩 미준비/디코드 실패면 기존 `exPickComponent`로 폴백.

- work→원본 좌표: `ox = wx * exState.W / exState.workW`, `oy = wy * exState.H / exState.workH`.
- 이미지가 바뀌면(`exInitFromCanvas`) SAM 임베딩 무효화 → 다음 픽 전에 재계산.

## 캐싱

- 다운로드는 `fetch(url)` 진행률 리더로 받아 `ArrayBuffer` → `ort.InferenceSession.create(bytes)`.
- 받은 바이트를 `caches.open('sam-models').put(url, new Response(bytes))`로 저장. 다음엔
  캐시 우선으로 읽어 재다운로드 회피(같은 URL, 버전 박힌 파일명이라 불변).
- `navigator.storage.persist()` 요청(거부돼도 진행). Safari 7일·용량 축출 완화.
- SW는 외부 출처를 캐시하지 않으므로(현행 유지) 이 캐시는 앱 코드가 직접 관리.

## 오류 처리

- 다운로드 실패/취소: 토스트, SAM OFF 유지, 색 기반 동작.
- 인코더/디코더 실행 예외: 해당 픽만 색 기반으로 폴백, 반복 실패 시 SAM OFF 제안.
- 임베딩 계산 중 이미지 교체: seq 토큰으로 낡은 임베딩 폐기.
- 디코드 결과 마스크가 비었으면(면적 0) "여기서는 못 찾았어요" 토스트(기존과 동일).

## 재사용 / 신규

재사용(수정 없음): `exCropComponent`, 고스트·대기열·드래그 로직, `alphaToMaskCanvas`,
`loadOrt`/`ort.env` 설정, `fetchWithProgress`(진행률 다운로드), `decodeToSource`,
`drawScaled`, `toast`.

신규: SAM 모듈(`samState`, `samDownload`, `samEncode`, `samDecodeAt`, `samPreprocess`,
`exSamPick`), 게이팅 버튼·상태 UI, `exActivate` 분기, Cache Storage 관리.

## 검증

전처리·후처리 좌표 수학은 **순수 함수로 하네스 단위 검증**(모델 불필요). 전체 파이프라인은
스파이크에서 onnxruntime로 이미 실측(내부 100%/외부 0%). 브라우저 통합은:
1. `samPreprocess` 좌표·정규화 단위 검증(합성 입력 → 기대 텐서 값·scale).
2. 후처리 좌표 매핑(256→원본) 단위 검증.
3. 실제 브라우저에서 모델을 로컬 정적 서버로 제공해 인코더→디코더→마스크가 합성 이미지의
   클릭 물체를 덮는지 E2E 실측(스파이크 재현).
4. 폴백: SAM OFF일 때 기존 색 기반 픽이 그대로 동작(회귀).
5. 게이팅: 버튼 누르기 전에는 다운로드/세션 생성이 일어나지 않음.

## 단계(구현 순서)

1. SAM 모듈 + 전처리/후처리 순수 함수 (단위 검증).
2. 다운로드 게이팅 버튼 + Cache Storage + 세션 생성 (모델 준비).
3. 인코더 임베딩(이미지당 1회) + seq 무효화.
4. `exActivate` 분기 + `exSamPick` + 폴백.
5. E2E 브라우저 실측 + 문서.
