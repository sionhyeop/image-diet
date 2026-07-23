# 배경·요소 탭 일괄 배경 제거 — 설계

날짜: 2026-07-23
대상: 웹앱(`index.html`) 전용.

## 목적

배경·요소 탭에서 이미지 여러 장을 한 번에 올려, 버튼 한 번으로 전부 AI(또는 색상)
배경 제거를 돌리고 ZIP으로 내려받는다. 브러시 수동 편집 없이 자동 처리만 한다.

## 범위

포함:
- 배경·요소 탭 파일 선택을 여러 장 허용
- 2장 이상이면 단일 편집기 대신 **일괄(batch) 패널** 표시
- 파일별 썸네일 + 상태(대기 → 처리 중 → 완료/실패)
- [일괄 배경 제거] → 순차 처리, [ZIP으로 저장]
- 출력 형식(PNG 투명 / WebP 투명 / JPEG 배경색) + 품질

제외 (YAGNI):
- 배치에서 브러시·비교·실행취소 등 수동 편집 (사용자가 자동 처리만 택함)
- 요소 추출의 일괄화 (요소 추출은 기존대로 단일)
- 데스크톱 셸 이식

## 트리거

`routeFiles`의 bg 분기를 바꾼다:
- 파일 1장 → 기존 `loadCutFile(files[0])` (단일 편집기, 변경 없음)
- 파일 2장 이상 → `bgEnterBatch(files)` (일괄 패널)

드롭·클릭·Ctrl+V 모두 같은 경로를 탄다. `#bgFile`에 `multiple` 추가.

## 화면

일괄 모드에서는 단일 편집기 요소(`#cutModeSeg` 모드토글, `#bgBody`, `#exBody`)를 숨기고
`#bgBatch` 패널을 보인다. 엔진·민감도(`#cutShared`)는 일괄에도 적용되므로 그대로 보인다.

```
[ 인식 엔진: ⚡빠른 AI | 🎨색상 ]   ← #cutShared 재사용
[ 인식 민감도 ────●──── ]

┌ #bgBatch ───────────────────────────┐
│ 배경을 제거할 이미지 3장             │
│ [썸네일 대기] [썸네일 처리중] [완료] │  ← 파일별 상태 배지
│ 출력 형식: (PNG 투명) WebP JPEG      │
│ 품질 ───●───  [JPEG 배경색 ■]        │
│ [ 일괄 배경 제거 ]  [ ZIP으로 저장 ] [비우기] │
│ 진행: 2 / 3 처리 중…                 │
└──────────────────────────────────────┘
```

- ZIP 버튼은 완료 조각이 하나라도 있어야 활성.
- JPEG 배경색 칸은 형식이 JPEG일 때만 보인다(단일 편집기와 동일 규칙).

## 데이터 흐름 — 기존 파이프라인 재사용

핵심: **2장 이상이면 단일 편집기가 숨겨지므로, 편집 세션이 없다.** 따라서 배치는
`bgState`를 스크래치로 써도 안전하다. 델리케이트한 마스크 내부 코드
(`bgAutoMaskAI`, `bgAutoMaskClassic`, `bgReplayMask`, `bgComposeFull`)를 리팩터하지 않고
그대로 호출한다.

디코드+리사이즈는 `loadCutFile`이 인라인으로 하던 것을 `bgPrepCanvas(file)`로 뽑아
단일·배치가 공유한다:

```js
function bgPrepCanvas(file) {           // -> Promise<{srcCanvas, W, H, name}>
  return decodeToSource(file).then(function (dec) {
    var w = srcW(dec.source) || 512, h = srcH(dec.source) || 512;
    var lim = clampDims(w, h); if (lim) { w = lim.w; h = lim.h; }
    var cap = capTo1920(w, h); if (cap) { w = cap.w; h = cap.h; }
    var canvas = drawScaled(dec.source, w, h, null);
    if (dec.url) URL.revokeObjectURL(dec.url);
    if (dec.source && dec.source.close) { try { dec.source.close(); } catch (e) {} }
    return { srcCanvas: canvas, W: w, H: h, name: file.name || '이미지' };
  });
}
```

`loadCutFile`은 이 헬퍼를 쓰도록 바꾸되 동작은 동일하게 유지한다.

한 장 처리:

```js
function bgBatchOne(item) {             // item: {file, srcCanvas, W, H, name, ...}
  bgState.srcCanvas = item.srcCanvas;
  bgState.W = item.W; bgState.H = item.H;
  bgState.strokes = []; bgState.workMask = null; bgState.mask = null;
  var mk = (bgEngine !== 'classic')
    ? bgAutoMaskAI(function () {}).catch(function () { bgEngine = 'classic'; syncBgEngineChips(); bgAutoMaskClassic(); })
    : Promise.resolve().then(bgAutoMaskClassic);
  return mk.then(function () {
    if (!bgState.workMask) throw new Error('마스크 실패');
    bgReplayMask();                     // workMask(+feather=0) → bgState.mask
    return bgComposedBlob();            // 형식·품질대로 인코딩 -> {blob, ext}
  });
}
```

인코딩은 단일 편집기의 `#bgSaveOpt` 로직을 `bgComposedBlob(fmt, q, jpegBg)`로 뽑아
공유한다. PNG 옵션을 추가한다(투명·무손실). 반환은 `{blob, ext}`.

## 순차 처리

배치는 한 장씩 처리한다(AI가 무거워 병렬은 부적절). 각 단계에서 상태 배지를 갱신하고
결과 blob을 `item.blob`에 저장한다. 전체 완료 후 ZIP 버튼 활성.

```js
var bgBatch = { items: [], busy: false, seq: 0 };
// item: { file, name, srcCanvas, W, H, status:'wait'|'busy'|'done'|'fail', blob, ext, thumbUrl }
```

- `bgEnterBatch(files)`: 이미지 파일만 추려 items 생성(썸네일 objectURL), 패널 표시, 상태 대기.
- [일괄 배경 제거]: `busy` 가드, seq 토큰 발급. 각 item을 `bgPrepCanvas`(아직 안 했으면)
  → `bgBatchOne` → 상태 done/fail. 중간에 비우기·재시작하면 seq로 낡은 실행 폐기.
- [ZIP으로 저장]: done인 item만 `makeZip([{name: base(name)+'-nobg.'+ext, blob}])` → `배경제거.zip`.
- [비우기]: seq++, 썸네일 objectURL 반납, items 비우고 패널 숨김.

## 오류 처리

- 이미지가 아닌 파일은 거른다(토스트로 개수 안내).
- 한 장 처리 실패는 그 item만 `fail`로 표시하고 나머지는 계속.
- AI 모델 로드 실패 시 색상 엔진으로 폴백(기존 단일 편집기와 동일).
- 처리 중 [비우기]/새 업로드는 seq 가드로 낡은 실행이 상태·blob을 덮지 않게 한다.

## 재사용 / 신규

재사용(수정 없음): `bgAutoMaskAI`, `bgAutoMaskClassic`, `bgReplayMask`, `bgComposeFull`,
`runSaliency`, `decodeToSource`, `drawScaled`, `clampDims`, `capTo1920`, `encodeCanvas`,
`makeZip`, `saveBlob`, `fmtBytes`, `baseName`, `toast`, `bgEngine`/`syncBgEngineChips`,
`#bgTol` 민감도.

소폭 리팩터(동작 보존): `loadCutFile`의 디코드부 → `bgPrepCanvas`, `#bgSaveOpt`의 합성·
인코딩부 → `bgComposedBlob` (PNG 분기 추가).

신규: `#bgBatch` HTML, `.bg-batch-*` CSS, `bgBatch` 상태와 `bgEnterBatch`/`bgBatchOne`/
`bgBatchRun`/`bgBatchZip`/`bgBatchClear`, `routeFiles`/`#bgFile multiple` 변경.

## 검증

이 앱의 AI 모델(~4MB ONNX)은 headless 환경에서 받기 어려우므로, 배치 **플럼빙**은
색상(classic) 엔진으로 실측한다(모델 불필요). `window.__imgdiet`에 `bgEnterBatch`,
`bgBatchRun`, `get bgBatch`를 노출한다.

1. 서로 다른 3장(가운데 도형 + 단색 테두리)을 `bgEnterBatch` → items 3, 상태 모두 wait, 패널 보임.
2. 색상 엔진으로 `bgBatchRun` → 상태 모두 done, 각 item.blob 존재.
3. 출력 형식별: PNG→`image/png`·투명 채널 존재, WebP→`image/webp`, JPEG→`image/jpeg`.
4. ZIP → 항목 수 3, 내부 파일명 `<이름>-nobg.<ext>`.
5. 처리 도중 `bgBatchClear` → seq 가드로 낡은 완료가 items를 되살리지 않음(상태 비어 있음).
6. 단일 경로 회귀: 1장 업로드 → 기존 편집기 정상(마스크·다운로드), 배치 패널 숨김.
7. AI 경로는 실브라우저에서 수동 확인(모델 다운로드 필요).
