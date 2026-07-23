# 분할 결과 페이지네이션 — 설계

날짜: 2026-07-23
대상: 웹앱(`index.html`) 전용. 데스크톱 셸(`shell/`)에는 추가하지 않는다.

## 목적

이미지 분할 결과를 **원본 이미지 단위로 페이지네이션**해서 보여준다. 한 페이지는
원본 한 장에 대응하고, 그 원본에서 나온 조각들을 격자로 표시한다. 조각을 클릭하면
전체화면 라이트박스로 크게(개별) 볼 수 있다.

## 배경 (현재 동작)

분할 결과는 `splitRenderTiles()`가 `#splitGrid` 하나에 모든 조각을 렌더한다.
원본이 여러 장이면 `.split-group-label`(점선 라벨)로 원본별 묶음을 이어 붙여
한 화면에 전부 나열한다. 조각 썸네일은 작고, 클릭해도 커지지 않는다.

## 범위

포함:
- 결과 영역을 원본 이미지 단위로 페이지네이션 (한 페이지 = 원본 한 장의 조각 격자)
- 페이저 바: `◀  <원본이름> (i / N)  ▶`
- 조각 썸네일 클릭 시 기존 라이트박스로 개별 확대
- 페이지마다 "이 원본 전체 ZIP" 버튼 (현재 페이지 원본의 조각만)
- 기존 "전체 ZIP으로 저장"(모든 원본 조각) 유지

제외 (YAGNI):
- 조각을 한 장씩 큰 화면으로 넘기는 2단계 페이지네이션 (사용자가 격자 방식을 택함)
- 페이지 번호 점/입력창 (화살표 + `i / N` 카운터로 충분)
- 키보드 방향키 내비게이션 (조각 클릭 라이트박스로 충분)
- 데스크톱 셸 이식

## UI

```
분할 결과  12조각 (이미지 3장) · 원본 3.1MB → 합계 480KB
┌ 페이저 ────────────────────────────┐
│   ◀      a.png (1 / 3)      ▶        │
└─────────────────────────────────────┘
┌──────────┬──────────┐   ← #splitGrid (현재 원본의 조각만)
│ [1-1] 저장│ [1-2] 저장│      썸네일 클릭 → 라이트박스
├──────────┼──────────┤
│ [2-1] 저장│ [2-2] 저장│
└──────────┴──────────┘
[ 이 원본 전체 ZIP ]   [ 전체 ZIP으로 저장 ]
```

- 원본이 한 장뿐이면 페이저 바는 이름만 보이고 화살표 두 개는 `disabled`.
- `#splitCount`(상단 합계 문구)는 현행 유지 — 전체 조각 수·원본 대비 용량.

## 데이터 흐름

조각(tile)은 이미 `{ blob, url, w, h, r, c, srcId, srcName, name }`를 갖는다.
페이지는 `splitState.tiles`를 `srcId`로 묶어 만든다. 묶음 순서는 `splitState.items`
(대기열) 순서를 따른다.

```js
function splitGroups() {
  // items 순서대로, 해당 srcId의 조각을 모은다. 조각이 하나도 없는 원본은 건너뛴다.
  var byId = {};
  splitState.tiles.forEach(function (t) {
    (byId[t.srcId] || (byId[t.srcId] = [])).push(t);
  });
  var groups = [];
  splitState.items.forEach(function (it) {
    if (byId[it.id] && byId[it.id].length) {
      groups.push({ id: it.id, name: byId[it.id][0].srcName, tiles: byId[it.id] });
    }
  });
  return groups;
}
```

필드명은 확인 완료:
- 원본: `splitState.items[].id` (`++splitUid`로 부여), `.file`
- 조각: `.srcId`(= item.id), `.srcName`(= 중복 처리된 base 이름), `.name`(파일명)

## 상태

`splitState`에 `page` 추가 (0-based, 현재 원본 인덱스).

- 새 분할 시작(`splitRun`), 비우기, 조각 해제 시 `page = 0`.
- 렌더 시 `page`를 `[0, groups.length - 1]`로 clamp.

## 렌더링 (`splitRenderTiles` 개편)

1. `groups = splitGroups()`. 비어 있으면 결과 영역 숨김.
2. `page`를 clamp.
3. 페이저 바 렌더: `◀`(page>0일 때 활성) · `<이름> (page+1 / groups.length)` · `▶`(page<last일 때 활성). groups.length === 1이면 화살표 둘 다 disabled.
4. `#splitGrid`에 `groups[page].tiles`만 렌더. `grid-template-columns: repeat(cols, minmax(0,1fr))` 유지.
5. 각 타일: 썸네일(클릭 → `openLightbox(t.url, t.name + ' · ' + t.w + '×' + t.h)`), 캡션(`r-c · w×h · 용량`), 저장 버튼.
6. `.split-group-label` 경로는 제거 (페이지네이션이 대체).
7. `#splitCount`는 기존대로 전체 합계 표시.

## 버튼

- **이 원본 전체 ZIP** (`#splitZipOne`): 현재 페이지 원본의 조각(`groups[page].tiles`)만 `makeZip` → `<그 원본의 srcName>-분할.zip`.
- **전체 ZIP으로 저장** (`#splitZip`, 기존): **동작·이름 그대로 유지, 변경 없음.** (현재: 원본 1장이면 `<원본이름>-분할.zip`, 여러 장이면 `분할-분할.zip`.)

두 버튼 모두 조각이 없으면 무시. 이름 충돌은 이미 조각 생성 단계에서 `-2`, `-3`으로
처리되므로 ZIP 내부에서 재처리하지 않는다.

## 라이트박스

기존 `openLightbox(url, caption)`을 그대로 쓴다. 조각 썸네일에 `cursor: pointer`와
클릭 핸들러를 단다. 라이트박스는 원본 조각 blob URL을 직접 보여주므로 추가 인코딩 없음.

## 엣지 케이스

- 원본 1장: 페이저 `(1/1)`, 화살표 비활성, 격자만 표시.
- 분할 도중 재분할·설정 변경·이미지 추가/제거: 기존 `runSeq` 가드가 `splitReleaseTiles()`로 결과를 비운다. 페이저도 함께 사라지고 `page`는 리셋된다.
- 어떤 원본의 모든 조각이 인코딩 실패로 빠지면 그 원본은 `splitGroups()`에서 건너뛴다 (빈 페이지 없음).
- `page`가 마지막 원본을 보던 중 원본이 줄면 clamp로 유효 범위에 재배치.

## 재사용 / 신규

재사용(수정 없음): `openLightbox`, `makeZip`, `saveBlob`, `fmtBytes`, `baseName`,
`toast`, 기존 `.split-grid`/`.split-tile` CSS.

신규: `splitGroups()`, 페이저 렌더 로직, `#splitZipOne` 핸들러, `.split-pager` CSS,
`.split-tile img { cursor: pointer }`. `splitRenderTiles` 개편. `.split-group-label`
CSS·코드 제거.

## 검증

headless Chrome 하네스(`node run.mjs <check>.js --tab split`)로 실측한다.

1. 서로 다른 크기 이미지 3장을 큐에 넣고 2×2 분할 → 조각 12개, `splitGroups()` 길이 3.
2. `page=0` 격자에 원본 1의 조각 4개만(이름·개수) 보인다. `page`를 1로 넘기면 원본 2의 조각만.
3. 페이저 카운터가 `(1/3)`→`(2/3)`→`(3/3)`로 바뀌고, 마지막에서 `▶` 비활성·처음에서 `◀` 비활성.
4. 조각 썸네일 클릭 → `#lightbox`가 `hidden=false`가 되고 `#lightboxImg.src`가 그 조각 URL.
5. "이 원본 전체 ZIP" → ZIP 항목 수 = 현재 페이지 조각 수, 내부 파일명이 그 원본 조각 이름과 일치.
6. 원본 1장만 분할 → 페이저 `(1/1)`, 화살표 둘 다 `disabled`, 격자 정상.
7. 페이지 이동 후 재분할하면 `page`가 0으로 리셋되고 첫 원본이 보인다.
