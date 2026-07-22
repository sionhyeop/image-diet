# 이미지 n×m 분할 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 웹앱에 이미지를 가로 n × 세로 m 조각으로 균등 분할해 개별·ZIP으로 내려받는 탭을 추가한다.

**Architecture:** `index.html` 단일 파일에 새 탭 패널 `#panel-split`과 `splitState` 로직을 더한다. 기존 `decodeToSource`·`detectAlpha`·`encodeCanvas`·`saveBlob`·`makeZip`을 그대로 재사용하고, 기존 함수는 수정하지 않는다. 기존 코드 변경은 탭 등록 3곳(탭 버튼 목록, `tabs` 배열, `routeFiles`)뿐이다.

**Tech Stack:** 바닐라 JS(ES5 스타일 — 기존 코드가 `var`/`function` 사용), Canvas 2D, 외부 의존성 0.

## Global Constraints

- 스펙: `docs/superpowers/specs/2026-07-23-image-split-design.md`
- **웹앱(`index.html`) 전용.** `shell/` 데스크톱 코드는 건드리지 않는다.
- **외부 의존성 추가 금지.** `index.html`은 한 파일만으로 오프라인 동작해야 한다.
- 기존 코드 스타일을 따른다: `var`, `function` 선언, 화살표 함수·`let`·`const`·템플릿 리터럴 사용 금지 (기존 파일 전체가 ES5 스타일이다).
- 모든 UI 문구는 한국어 존댓말체("~해요"). 기존 탭 문구와 톤을 맞춘다.
- 조각 수 범위: 가로·세로 각각 **1~10**, 총 조각 **100개 이하**.
- 조각 이름: `<원본이름>_<행>-<열>.<확장자>` (1부터, row-major). ZIP 이름: `<원본이름>-분할.zip`.
- 경계 계산은 반드시 `Math.round(total * i / n)` — `floor` 누적 금지(끝 픽셀 유실).
- 검증은 Chrome DevTools MCP로 실제 브라우저에서 수행한다. `file://` 로 `index.html`을 연다.

## File Structure

수정 파일은 `index.html` 하나뿐이다. 삽입 위치는 아래 5곳으로 고정한다.

| 위치 | 현재 줄 | 넣을 것 |
| --- | --- | --- |
| CSS | `.ex-item .btn` 규칙 뒤 (약 486행) | `.split-*` 클래스 |
| 탭 버튼 | `#tabSvg` 버튼 앞 (약 555행) | `#tabSplit` 버튼 |
| 패널 | `<section id="panel-svg">` 앞 (약 753행) | `<section id="panel-split">` |
| `tabs` 배열 | svg 항목 앞 (약 1103행) | split 항목 |
| JS 로직 | `/* ===== metadata: JPEG EXIF ... */` 앞 (약 4914행) | `/* ===== 이미지 분할 ===== */` 섹션 |
| 테스트 핸들 | `window.__imgdiet` 객체 (약 7453행) | `splitEdges`, `splitState` 노출 |

줄 번호는 작업하면서 밀리므로, 반드시 위 **앵커 문자열**로 찾아서 삽입한다.

---

### Task 1: 탭 뼈대 · 패널 · 이미지 로딩 · 가이드라인 미리보기

이미지를 넣으면 미리보기 캔버스에 뜨고, 가로/세로 입력에 따라 격자선이 실시간으로 그려지는 데까지.

**Files:**
- Modify: `index.html` (위 표의 6곳 전부)

**Interfaces:**
- Consumes: `decodeToSource(file)` → `Promise<{source, url}>`, `detectAlpha(source)` → `boolean`, `srcW(source)`/`srcH(source)` → `number`, `toast(msg)`, `$(sel)`
- Produces:
  - `splitEdges(total, n)` → `number[]` (길이 `n+1`)
  - `splitState` 객체 (아래 정의)
  - `window.__imgdiet.splitEdges`, `window.__imgdiet.splitState`

- [ ] **Step 1: 탭 버튼 추가**

`index.html`에서 `<button class="tab" id="tabSvg"` 로 시작하는 줄을 찾아, **그 앞에** 다음 줄을 넣는다.

```html
    <button class="tab" id="tabSplit" role="tab" aria-selected="false" aria-controls="panel-split" type="button">이미지 분할</button>
```

- [ ] **Step 2: `tabs` 배열에 등록**

`{ btn: $('#tabSvg'), panel: $('#panel-svg'), key: 'svg',` 로 시작하는 줄을 찾아, **그 앞에** 다음 줄을 넣는다.

```js
    { btn: $('#tabSplit'), panel: $('#panel-split'), key: 'split', label: '이미지 분할', desc: '사진을 격자로 잘라 한꺼번에 저장해요' },
```

- [ ] **Step 3: 패널 HTML 추가**

`<section id="panel-svg" role="tabpanel"` 로 시작하는 줄을 찾아, **그 앞에** 다음 블록을 넣는다.

```html
  <section id="panel-split" role="tabpanel" aria-labelledby="tabSplit" hidden>
    <div class="card b64-card">
      <h2>이미지 분할 (격자로 자르기)</h2>
      <div class="dropzone dropzone-sm" id="splitDropzone" role="button" tabindex="0" aria-label="분할할 이미지 선택 또는 드래그하여 추가">
        <p class="dz-main">이미지를 끌어다 놓거나 <strong>클릭</strong>해서 선택하세요</p>
        <p class="dz-hint">Ctrl+V 붙여넣기 지원 · JPG / PNG / WebP / GIF</p>
        <input type="file" id="splitFile" accept="image/*" hidden>
      </div>
      <div id="splitBody" hidden>
        <p class="field-label" style="margin-top:16px">미리보기 <span class="sub">— 자를 위치를 선으로 보여줘요</span></p>
        <div class="split-preview-wrap">
          <canvas id="splitCanvas" class="split-preview"></canvas>
        </div>
        <div class="settings-grid svg-opts">
          <div class="field">
            <label class="field-label" for="splitCols">가로 조각 수 <output id="splitColsOut" for="splitCols">3</output><span class="sub"> — 세로선으로 나눠요</span></label>
            <input type="range" id="splitCols" min="1" max="10" step="1" value="3">
          </div>
          <div class="field">
            <label class="field-label" for="splitRows">세로 조각 수 <output id="splitRowsOut" for="splitRows">3</output><span class="sub"> — 가로선으로 나눠요</span></label>
            <input type="range" id="splitRows" min="1" max="10" step="1" value="3">
          </div>
          <div class="field field-wide">
            <span class="field-label">자주 쓰는 배치</span>
            <div class="chips" id="splitPresets">
              <button type="button" class="chip" data-split-preset="2x2">2 × 2</button>
              <button type="button" class="chip" data-split-preset="3x3">3 × 3</button>
              <button type="button" class="chip" data-split-preset="3x1">가로 3줄</button>
              <button type="button" class="chip" data-split-preset="1x3">세로 3줄</button>
            </div>
          </div>
          <div class="field field-wide">
            <span class="field-label">출력 형식 <span class="sub">— 자동은 투명도가 있으면 알아서 맞춰요</span></span>
            <div class="chips" id="splitFormats">
              <button type="button" class="chip on" data-split-fmt="auto">자동</button>
              <button type="button" class="chip" data-split-fmt="webp">WebP</button>
              <button type="button" class="chip" data-split-fmt="jpeg">JPEG</button>
              <button type="button" class="chip" data-split-fmt="png">PNG</button>
            </div>
          </div>
          <div class="field field-wide">
            <label class="field-label" for="splitQ">품질 <output id="splitQOut" for="splitQ">85</output>%<span class="sub"> — PNG는 품질 조절이 없어요</span></label>
            <input type="range" id="splitQ" min="0.4" max="0.95" step="0.01" value="0.85">
          </div>
        </div>
        <div class="btn-row">
          <button class="btn primary" id="splitRun" type="button">분할하기</button>
          <button class="btn" id="splitClear" type="button">비우기</button>
        </div>
        <p class="muted" id="splitStat" role="status"></p>
      </div>
      <div id="splitResultWrap" hidden>
        <p class="field-label">분할 결과 <output id="splitCount"></output></p>
        <ul id="splitGrid" class="split-grid"></ul>
        <div class="btn-row">
          <button class="btn primary" id="splitZip" type="button">전체 ZIP으로 저장</button>
        </div>
      </div>
    </div>
  </section>
```

- [ ] **Step 4: CSS 추가**

`.ex-item .btn { flex: 1; padding: 5px 4px; font-size: 12px; min-height: 0; }` 줄을 찾아, **그 뒤에** 다음을 넣는다.

```css
/* 이미지 분할 — 가이드라인 미리보기와 조각 격자 */
.split-preview-wrap {
  margin: 10px 0 0; padding: 12px; background: var(--panel-2);
  border: 1px solid var(--border); border-radius: 12px; text-align: center;
}
.split-preview { max-width: 100%; height: auto; border-radius: 8px; display: inline-block; }
.split-grid { list-style: none; padding: 0; margin: 12px 0 0; display: grid; gap: 10px; }
.split-tile {
  background: var(--panel); border: 1px solid var(--border);
  border-radius: 12px; padding: 8px; text-align: center; min-width: 0;
}
.split-tile img {
  width: 100%; height: 84px; object-fit: contain; border-radius: 8px;
  background: repeating-conic-gradient(var(--panel-2) 0% 25%, var(--panel) 0% 50%) 0 0 / 12px 12px;
}
.split-tile p { margin: 6px 0; font-size: 11.5px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.split-tile .btn { width: 100%; padding: 5px 4px; font-size: 12px; min-height: 0; }
```

- [ ] **Step 5: `routeFiles`에 split 분기 추가**

`} else if (!$('#panel-svg').hidden) {` 줄을 찾아, **그 앞에** 다음을 넣는다.

```js
    } else if (!$('#panel-split').hidden) {
      loadSplitFile(files[0]);
      if (files.length > 1) toast('첫 번째 이미지만 분할해요.');
```

- [ ] **Step 6: 분할 로직 섹션 추가 (미리보기까지)**

`/* ================= metadata: JPEG EXIF + PNG text chunks ================= */` 줄을 찾아, **그 앞에** 다음 블록을 넣는다.

```js
  /* ================= 이미지 분할 (n×m) =================
     경계는 Math.round(total * i / n)로 잡는다. 반올림 분수라 조각 크기 차이가
     1px을 넘지 않고, 빈틈·겹침 없이 원본 전체를 정확히 덮는다.
     floor 누적 방식은 오른쪽·아래 끝 픽셀이 잘려 나가므로 쓰지 않는다. */
  var SPLIT_MAX_TILES = 100;
  var splitState = {
    file: null, source: null, url: null, hasAlpha: false,
    cols: 3, rows: 3, format: 'auto', quality: 0.85,
    tiles: [], busy: false
  };

  function splitEdges(total, n) {
    var out = [];
    for (var i = 0; i <= n; i++) out.push(Math.round(total * i / n));
    return out;
  }

  function splitReleaseTiles() {
    splitState.tiles.forEach(function (t) { URL.revokeObjectURL(t.url); });
    splitState.tiles = [];
    $('#splitGrid').textContent = '';
    $('#splitCount').textContent = '';
    $('#splitResultWrap').hidden = true;
  }

  function splitReleaseSource() {
    if (splitState.url) URL.revokeObjectURL(splitState.url);
    if (splitState.source && typeof splitState.source.close === 'function') {
      try { splitState.source.close(); } catch (e) {}
    }
    splitState.url = null;
    splitState.source = null;
    splitState.file = null;
  }

  /* 미리보기: 원본을 가로 640px 이내로 축소해 그리고, 같은 비율 위치에 격자선을 긋는다.
     흰 3px을 먼저 긋고 강조색 1px을 덮어 밝은 사진·어두운 사진 모두에서 보이게 한다. */
  function splitDrawPreview() {
    var src = splitState.source;
    var canvas = $('#splitCanvas');
    if (!src) return;
    var w = srcW(src), h = srcH(src);
    if (!w || !h) return;
    var scale = Math.min(1, 640 / w);
    var cw = Math.max(1, Math.round(w * scale));
    var ch = Math.max(1, Math.round(h * scale));
    canvas.width = cw;
    canvas.height = ch;
    var ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, cw, ch);
    ctx.drawImage(src, 0, 0, cw, ch);
    var xs = splitEdges(cw, splitState.cols);
    var ys = splitEdges(ch, splitState.rows);
    var i;
    function line(x1, y1, x2, y2) {
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }
    for (var pass = 0; pass < 2; pass++) {
      ctx.strokeStyle = pass === 0 ? 'rgba(255,255,255,.9)' : '#3182f6';
      ctx.lineWidth = pass === 0 ? 3 : 1;
      for (i = 1; i < xs.length - 1; i++) line(xs[i] + .5, 0, xs[i] + .5, ch);
      for (i = 1; i < ys.length - 1; i++) line(0, ys[i] + .5, cw, ys[i] + .5);
    }
  }

  function splitSyncStat() {
    var n = splitState.cols * splitState.rows;
    var src = splitState.source;
    var msg = '조각 ' + n + '개';
    if (src) {
      var xs = splitEdges(srcW(src), splitState.cols);
      var ys = splitEdges(srcH(src), splitState.rows);
      msg += ' · 한 조각 약 ' + (xs[1] - xs[0]) + '×' + (ys[1] - ys[0]) + 'px';
    }
    $('#splitStat').textContent = msg;
  }

  function loadSplitFile(file) {
    if (!file) return;
    decodeToSource(file).then(function (res) {
      splitReleaseTiles();
      splitReleaseSource();
      splitState.file = file;
      splitState.source = res.source;
      splitState.url = res.url;
      splitState.hasAlpha = detectAlpha(res.source);
      $('#splitBody').hidden = false;
      splitDrawPreview();
      splitSyncStat();
    }).catch(function (err) {
      toast(err && err.message ? err.message : '이 이미지는 열 수 없어요.');
    });
  }

  /* --- 입력 배선 --- */
  $('#splitDropzone').addEventListener('click', function () { $('#splitFile').click(); });
  $('#splitDropzone').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); $('#splitFile').click(); }
  });
  $('#splitFile').addEventListener('change', function (e) {
    var f = e.target.files && e.target.files[0];
    if (f) loadSplitFile(f);
    e.target.value = '';
  });

  function splitOnGridChange() {
    splitReleaseTiles();
    splitDrawPreview();
    splitSyncStat();
  }
  $('#splitCols').addEventListener('input', function () {
    splitState.cols = parseInt(this.value, 10) || 1;
    $('#splitColsOut').textContent = splitState.cols;
    splitOnGridChange();
  });
  $('#splitRows').addEventListener('input', function () {
    splitState.rows = parseInt(this.value, 10) || 1;
    $('#splitRowsOut').textContent = splitState.rows;
    splitOnGridChange();
  });
  document.querySelectorAll('#splitPresets .chip').forEach(function (b) {
    b.addEventListener('click', function () {
      var parts = b.dataset.splitPreset.split('x');
      splitState.cols = parseInt(parts[0], 10);
      splitState.rows = parseInt(parts[1], 10);
      $('#splitCols').value = splitState.cols;
      $('#splitRows').value = splitState.rows;
      $('#splitColsOut').textContent = splitState.cols;
      $('#splitRowsOut').textContent = splitState.rows;
      splitOnGridChange();
    });
  });
  document.querySelectorAll('#splitFormats .chip').forEach(function (b) {
    b.addEventListener('click', function () {
      splitState.format = b.dataset.splitFmt;
      document.querySelectorAll('#splitFormats .chip').forEach(function (o) {
        o.classList.toggle('on', o === b);
      });
      $('#splitQ').disabled = splitState.format === 'png';
      splitReleaseTiles();
    });
  });
  $('#splitQ').addEventListener('input', function () {
    splitState.quality = parseFloat(this.value);
    $('#splitQOut').textContent = Math.round(splitState.quality * 100);
    splitReleaseTiles();
  });
  $('#splitClear').addEventListener('click', function () {
    splitReleaseTiles();
    splitReleaseSource();
    $('#splitBody').hidden = true;
    $('#splitStat').textContent = '';
  });
```

- [ ] **Step 7: 테스트 핸들 노출**

`window.__imgdiet = {` 블록 안의 `get exState() { return exState; }` 줄을 찾아, 그 줄 끝의 `}` 뒤에 콤마를 붙이고 다음 두 줄을 넣는다.

```js
    splitEdges: splitEdges,
    get splitState() { return splitState; }
```

- [ ] **Step 8: 순수 함수 검증 — 브라우저에서 `splitEdges` 실측**

Chrome DevTools MCP로 `index.html`을 `file://` 경로로 열고 `evaluate_script`로 실행한다.

```js
(function () {
  var E = window.__imgdiet.splitEdges;
  var out = [];
  function chk(name, cond) { out.push((cond ? 'PASS ' : 'FAIL ') + name); }
  var a = E(1000, 3);
  chk('경계 개수 4', a.length === 4);
  chk('시작 0 / 끝 1000', a[0] === 0 && a[3] === 1000);
  chk('조각 폭 합 = 1000', (a[1]-a[0]) + (a[2]-a[1]) + (a[3]-a[2]) === 1000);
  chk('조각 폭 차이 <= 1px', Math.max(a[1]-a[0], a[2]-a[1], a[3]-a[2]) - Math.min(a[1]-a[0], a[2]-a[1], a[3]-a[2]) <= 1);
  var b = E(700, 1);
  chk('1분할은 통짜', b.length === 2 && b[0] === 0 && b[1] === 700);
  var c = E(7, 10);
  chk('픽셀보다 조각이 많아도 단조증가', c.every(function (v, i) { return i === 0 || v >= c[i-1]; }) && c[10] === 7);
  return out.join('\n');
})()
```

기대: 6줄 전부 `PASS`.

- [ ] **Step 9: 미리보기 육안 확인**

브라우저에서 `이미지 분할` 탭 → 아무 이미지나 넣고 `take_screenshot`으로 확인한다.
- 격자선이 보이고, 가로/세로 슬라이더를 움직이면 선 개수가 즉시 바뀐다
- 프리셋 `2 × 2` 클릭 시 슬라이더 값과 선이 함께 바뀐다
- 다크 모드(`prefers-color-scheme: dark` 에뮬레이트)에서도 선이 보인다

- [ ] **Step 10: 커밋**

```bash
git add index.html
git commit -m "feat: 이미지 분할 탭 뼈대와 가이드라인 미리보기"
```

---

### Task 2: 실제 분할 실행 · 조각 목록 · 개별 저장

**Files:**
- Modify: `index.html` (Task 1에서 만든 `/* ===== 이미지 분할 ===== */` 섹션 끝, `$('#splitClear')` 핸들러 뒤)

**Interfaces:**
- Consumes: `splitEdges`, `splitState`, `encodeCanvas(canvas, type, q)` → `Promise<Blob|null>`, `saveBlob(blob, name)`, `extFor(mime)`, `baseName(name)`, `fmtBytes(n)`, `supportsWebP`
- Produces:
  - `splitResolveFormat()` → MIME 문자열
  - `splitRun()` → `Promise` — 완료 시 `splitState.tiles`가 `{ blob, url, w, h, name, r, c }[]`로 채워짐

- [ ] **Step 1: 분할 실행 로직 추가**

Task 1에서 넣은 `$('#splitClear').addEventListener(...)` 블록 **뒤에** 다음을 넣는다.

```js
  /* 형식 자동 규칙은 압축 탭의 resolveFormat과 같게 맞춘다 */
  function splitResolveFormat() {
    if (splitState.format === 'webp') return supportsWebP ? 'image/webp' : 'image/jpeg';
    if (splitState.format === 'jpeg') return 'image/jpeg';
    if (splitState.format === 'png') return 'image/png';
    if (splitState.hasAlpha) return supportsWebP ? 'image/webp' : 'image/png';
    return supportsWebP ? 'image/webp' : 'image/jpeg';
  }

  /* 조각 하나를 원본 픽셀 그대로(리사이즈 없이) 잘라 인코딩한다.
     JPEG는 투명도를 못 담으므로 흰 배경을 먼저 깔고 그린다. */
  function splitEncodeTile(sx, sy, sw, sh, mime, quality) {
    var canvas = document.createElement('canvas');
    canvas.width = sw;
    canvas.height = sh;
    var ctx = canvas.getContext('2d');
    if (mime === 'image/jpeg') {
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, sw, sh);
    }
    ctx.drawImage(splitState.source, sx, sy, sw, sh, 0, 0, sw, sh);
    return encodeCanvas(canvas, mime, mime === 'image/png' ? undefined : quality);
  }

  function splitRenderTiles() {
    var ul = $('#splitGrid');
    ul.textContent = '';
    ul.style.gridTemplateColumns = 'repeat(' + splitState.cols + ', minmax(0, 1fr))';
    splitState.tiles.forEach(function (t) {
      var li = document.createElement('li');
      li.className = 'split-tile';
      var img = document.createElement('img');
      img.src = t.url;
      img.alt = t.name;
      var p = document.createElement('p');
      p.textContent = t.r + '-' + t.c + ' · ' + t.w + '×' + t.h + ' · ' + fmtBytes(t.blob.size);
      var dl = document.createElement('button');
      dl.className = 'btn';
      dl.type = 'button';
      dl.textContent = '저장';
      dl.addEventListener('click', function () { saveBlob(t.blob, t.name); });
      li.appendChild(img);
      li.appendChild(p);
      li.appendChild(dl);
      ul.appendChild(li);
    });
    var total = splitState.tiles.reduce(function (s, t) { return s + t.blob.size; }, 0);
    var orig = splitState.file ? splitState.file.size : 0;
    $('#splitCount').textContent = splitState.tiles.length + '조각 · 원본 ' +
      fmtBytes(orig) + ' → 합계 ' + fmtBytes(total);
    $('#splitResultWrap').hidden = splitState.tiles.length === 0;
  }

  function splitRun() {
    if (splitState.busy || !splitState.source) return Promise.resolve();
    var cols = splitState.cols, rows = splitState.rows;
    if (cols * rows > SPLIT_MAX_TILES) {
      toast('조각은 ' + SPLIT_MAX_TILES + '개까지만 만들 수 있어요.');
      return Promise.resolve();
    }
    splitReleaseTiles();
    splitState.busy = true;
    $('#splitRun').disabled = true;
    $('#splitStat').textContent = '자르는 중…';

    var xs = splitEdges(srcW(splitState.source), cols);
    var ys = splitEdges(srcH(splitState.source), rows);
    var mime = splitResolveFormat();
    var ext = extFor(mime);
    var base = baseName(splitState.file ? splitState.file.name : 'image');
    var jobs = [];
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        jobs.push({ r: r, c: c, x: xs[c], y: ys[r], w: xs[c + 1] - xs[c], h: ys[r + 1] - ys[r] });
      }
    }

    var failed = 0;
    var idx = 0;
    function next() {
      if (idx >= jobs.length) return Promise.resolve();
      var j = jobs[idx++];
      $('#splitStat').textContent = '자르는 중… ' + idx + ' / ' + jobs.length;
      return splitEncodeTile(j.x, j.y, j.w, j.h, mime, splitState.quality).then(function (blob) {
        if (!blob) { failed++; return; }
        splitState.tiles.push({
          blob: blob, url: URL.createObjectURL(blob),
          w: j.w, h: j.h, r: j.r + 1, c: j.c + 1,
          name: base + '_' + (j.r + 1) + '-' + (j.c + 1) + '.' + ext
        });
      }).then(next);
    }

    return next().then(function () {
      splitRenderTiles();
      splitSyncStat();
      if (failed) toast(failed + '조각은 저장할 수 없는 형식이라 건너뛰었어요.');
      else toast(splitState.tiles.length + '조각으로 잘랐어요.');
    }).catch(function () {
      toast('분할에 실패했어요.');
    }).then(function () {
      splitState.busy = false;
      $('#splitRun').disabled = false;
    });
  }

  $('#splitRun').addEventListener('click', function () { splitRun(); });
```

- [ ] **Step 2: 테스트 핸들에 `splitRun` 추가**

`window.__imgdiet` 안의 `splitEdges: splitEdges,` 줄 뒤에 다음을 넣는다.

```js
    splitRun: function () { return splitRun(); },
    loadSplitFile: loadSplitFile,
```

- [ ] **Step 3: 브라우저에서 분할 실측 — 픽셀 커버리지 검증**

Chrome DevTools MCP로 `index.html`을 열고, `이미지 분할` 탭을 연 뒤 `evaluate_script`로 실행한다.
(파일 선택 UI 대신, 알려진 크기의 캔버스를 파일로 만들어 `loadSplitFile`에 직접 넣는다.)

```js
(function () {
  var c = document.createElement('canvas');
  c.width = 1000; c.height = 700;
  var ctx = c.getContext('2d');
  ctx.fillStyle = '#c0392b'; ctx.fillRect(0, 0, 1000, 700);
  ctx.fillStyle = '#2980b9'; ctx.fillRect(0, 0, 500, 350);
  return new Promise(function (resolve) {
    c.toBlob(function (b) {
      var f = new File([b], 'test.png', { type: 'image/png' });
      window.__imgdiet.loadSplitFile(f);
      setTimeout(function () {
        var st = window.__imgdiet.splitState;
        st.cols = 3; st.rows = 2;
        window.__imgdiet.splitRun().then(function () {
          var t = st.tiles;
          var out = [];
          function chk(n, ok) { out.push((ok ? 'PASS ' : 'FAIL ') + n); }
          chk('조각 6개', t.length === 6);
          var row1 = t.filter(function (x) { return x.r === 1; });
          var col1 = t.filter(function (x) { return x.c === 1; });
          chk('1행 폭 합 = 1000', row1.reduce(function (s, x) { return s + x.w; }, 0) === 1000);
          chk('1열 높이 합 = 700', col1.reduce(function (s, x) { return s + x.h; }, 0) === 700);
          chk('모든 행의 폭 구성 동일', t.filter(function (x) { return x.r === 2; })
              .map(function (x) { return x.w; }).join() === row1.map(function (x) { return x.w; }).join());
          chk('이름 규칙', t[0].name === 'test_1-1.webp' || t[0].name === 'test_1-1.jpg');
          chk('전부 blob 있음', t.every(function (x) { return x.blob && x.blob.size > 0; }));
          resolve(out.join('\n'));
        });
      }, 400);
    }, 'image/png');
  });
})()
```

기대: 6줄 전부 `PASS`.

- [ ] **Step 4: 형식별 MIME 확인**

`evaluate_script`로 형식 칩을 눌러가며 확인한다.

```js
(function () {
  var st = window.__imgdiet.splitState;
  var res = [];
  function one(fmt) {
    document.querySelector('#splitFormats .chip[data-split-fmt="' + fmt + '"]').click();
    return window.__imgdiet.splitRun().then(function () {
      res.push(fmt + ' -> ' + st.tiles[0].blob.type + ' / ' + st.tiles[0].name);
    });
  }
  return one('webp').then(function () { return one('jpeg'); })
    .then(function () { return one('png'); }).then(function () { return one('auto'); })
    .then(function () { return res.join('\n'); });
})()
```

기대: `webp -> image/webp / test_1-1.webp`, `jpeg -> image/jpeg / test_1-1.jpg`, `png -> image/png / test_1-1.png`, `auto -> image/webp / test_1-1.webp`.

- [ ] **Step 5: 화면 확인**

`take_screenshot`으로 결과 격자가 `cols` 열로 배치되고, 각 타일에 `행-열 · 크기 · 용량`과 `저장` 버튼이 보이는지 확인한다.

- [ ] **Step 6: 커밋**

```bash
git add index.html
git commit -m "feat: 이미지 분할 실행과 조각별 저장"
```

---

### Task 3: 전체 ZIP 저장

**Files:**
- Modify: `index.html` (`$('#splitRun').addEventListener` 뒤)

**Interfaces:**
- Consumes: `makeZip(entries)` → `Promise<Blob>` (entries: `{name, blob}[]`), `saveBlob`, `splitState.tiles`
- Produces: 없음 (UI 종단)

- [ ] **Step 1: ZIP 핸들러 추가**

`$('#splitRun').addEventListener('click', function () { splitRun(); });` 줄 **뒤에** 다음을 넣는다.

```js
  $('#splitZip').addEventListener('click', function () {
    if (!splitState.tiles.length) return;
    var base = baseName(splitState.file ? splitState.file.name : 'image');
    makeZip(splitState.tiles.map(function (t) {
      return { name: t.name, blob: t.blob };
    })).then(function (zip) {
      saveBlob(zip, base + '-분할.zip');
      toast('ZIP으로 ' + splitState.tiles.length + '조각을 저장했어요.');
    }).catch(function () { toast('ZIP 생성에 실패했어요.'); });
  });
```

- [ ] **Step 2: ZIP 내용 실측**

`evaluate_script`로 ZIP을 만들어 항목 수와 이름을 바이너리에서 직접 센다.
(ZIP end-of-central-directory 레코드의 항목 수 필드를 읽는다.)

```js
(function () {
  var st = window.__imgdiet.splitState;
  return window.__imgdiet.makeZip(st.tiles.map(function (t) {
    return { name: t.name, blob: t.blob };
  })).then(function (zip) {
    return zip.arrayBuffer().then(function (buf) {
      var v = new DataView(buf);
      /* EOCD 시그니처 0x06054b50을 뒤에서 찾는다 */
      for (var i = buf.byteLength - 22; i >= 0; i--) {
        if (v.getUint32(i, true) === 0x06054b50) {
          return 'ZIP 항목 수: ' + v.getUint16(i + 10, true) +
                 ' (기대 ' + st.tiles.length + ') · 크기 ' + zip.size;
        }
      }
      return 'FAIL: EOCD 없음';
    });
  });
})()
```

기대: `ZIP 항목 수: 6 (기대 6)`.

- [ ] **Step 3: 실제 다운로드 동작 확인**

브라우저에서 `전체 ZIP으로 저장`을 눌러 다운로드가 시작되고 토스트가 뜨는지 확인한다.

- [ ] **Step 4: 커밋**

```bash
git add index.html
git commit -m "feat: 분할 조각 전체 ZIP 저장"
```

---

### Task 4: 경계 조건 · 정리 동작 점검

**Files:**
- Modify: `index.html` (필요 시 수정. 문제 없으면 수정 없음)

**Interfaces:**
- Consumes: Task 1~3의 전부
- Produces: 없음

- [ ] **Step 1: 경계 조건 스크립트 실행**

```js
(function () {
  var st = window.__imgdiet.splitState;
  var out = [];
  function chk(n, ok) { out.push((ok ? 'PASS ' : 'FAIL ') + n); }
  st.cols = 1; st.rows = 1;
  return window.__imgdiet.splitRun().then(function () {
    chk('1×1은 한 조각 전체', st.tiles.length === 1 && st.tiles[0].w === 1000 && st.tiles[0].h === 700);
    st.cols = 10; st.rows = 10;
    return window.__imgdiet.splitRun();
  }).then(function () {
    chk('10×10 = 100조각', st.tiles.length === 100);
    chk('100조각 폭 합(1행) = 1000',
      st.tiles.filter(function (t) { return t.r === 1; })
        .reduce(function (s, t) { return s + t.w; }, 0) === 1000);
    return out.join('\n');
  });
})()
```

기대: 3줄 전부 `PASS`. 10×10은 시간이 걸리므로 `wait_for`로 충분히 기다린다.

- [ ] **Step 2: 조각 수 상한 확인**

`SPLIT_MAX_TILES`가 100이고 슬라이더 최대가 10×10=100이므로 상한을 넘길 수 없다. 코드로 강제 초과시켜 가드가 동작하는지 확인한다.

가드는 `splitReleaseTiles()` **앞에서** 반환하므로, 초과 요청을 해도 **직전 결과가 그대로 남아 있어야** 정상이다. (사용자 입장에서 잘못된 요청 때문에 기존 결과가 날아가면 안 된다.)

```js
(function () {
  var st = window.__imgdiet.splitState;
  var before = st.tiles.length;
  st.cols = 20; st.rows = 20;
  return window.__imgdiet.splitRun().then(function () {
    var ok = st.tiles.length === before;
    return (ok ? 'PASS ' : 'FAIL ') + '초과 요청은 무시되고 직전 결과 유지 (' +
           before + ' -> ' + st.tiles.length + ')';
  });
})()
```

기대: `PASS 초과 요청은 무시되고 직전 결과 유지 (100 -> 100)` + "조각은 100개까지만 만들 수 있어요." 토스트.

- [ ] **Step 3: 메모리 정리 확인**

`비우기` 버튼을 누른 뒤 확인한다.

```js
(function () {
  document.querySelector('#splitClear').click();
  var st = window.__imgdiet.splitState;
  return '조각 ' + st.tiles.length + ' / source ' + (st.source === null) +
         ' / 본문 숨김 ' + document.querySelector('#splitBody').hidden +
         ' / 결과 숨김 ' + document.querySelector('#splitResultWrap').hidden;
})()
```

기대: `조각 0 / source true / 본문 숨김 true / 결과 숨김 true`.

- [ ] **Step 4: 탭 전환·해시 확인**

`#split` 해시로 직접 접속했을 때 분할 탭이 열리는지, 다른 탭으로 갔다 와도 상태가 유지되는지 확인한다.

```js
location.hash = '#split';
```
기대: 분할 패널이 보이고 다른 패널은 모두 `hidden`.

- [ ] **Step 5: Ctrl+V 경로 확인**

분할 탭이 열린 상태에서 이미지를 붙여넣기하면 `loadSplitFile`이 호출되는지 확인한다. (스크린샷으로 미리보기가 뜨는지 육안 확인.)

- [ ] **Step 6: 문제 발견 시 수정 후 커밋**

```bash
git add index.html
git commit -m "fix: 이미지 분할 경계 조건 처리"
```

문제가 없으면 커밋 없이 다음 태스크로 넘어간다.

---

### Task 5: 문서 갱신

**Files:**
- Modify: `README.md` (기능 목록)

**Interfaces:**
- Consumes: 없음
- Produces: 없음

- [ ] **Step 1: README 기능 목록에 항목 추가**

`README.md`에서 `- **이미지 → SVG 벡터 변환**` 으로 시작하는 줄을 찾아, **그 앞에** 다음 줄을 넣는다.

```markdown
- **격자 분할 (n×m)** — 이미지를 가로·세로 조각 수대로 균등 분할. 자를 위치를 원본 위에 가이드라인으로 미리 보여주고, 조각별 개별 저장 또는 ZIP 일괄 저장. 자르면서 형식(WebP/JPEG/PNG)과 품질을 지정해 용량도 함께 줄임
```

- [ ] **Step 2: 커밋**

```bash
git add README.md
git commit -m "docs: 격자 분할 기능 README 반영"
```

---

## 완료 조건

- [ ] Task 1~5의 모든 검증 스크립트가 `PASS`
- [ ] 조각 폭·높이의 합이 원본 크기와 정확히 일치 (빈틈·겹침 없음)
- [ ] 개별 저장·ZIP 저장 모두 실제 파일이 내려받아짐
- [ ] 다크 모드에서 가이드라인이 보임
- [ ] `shell/` 하위 파일이 하나도 수정되지 않음 (`git diff --name-only main` 으로 확인)
