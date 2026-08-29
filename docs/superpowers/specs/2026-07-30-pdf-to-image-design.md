# PDF 탭 통합 — 이미지→PDF + PDF→이미지 토글

날짜: 2026-07-30
대상: 웹앱(`index.html`) 전용.

## 목적

기존 "이미지 → PDF" 탭에 역방향 "PDF → 이미지"를 추가한다. 탭 이름은 **PDF**로 통일하고,
패널 상단의 슬라이딩 토글(배경·요소 탭의 `cutModeSeg`와 같은 패턴)로 두 기능을 전환한다.

## 확정된 결정

- **렌더러: pdf.js 번들** (사용자 선택). Mozilla pdfjs-dist **3.11.174 legacy 빌드**를
  `vendor/pdf.min.js`(377KB) + `vendor/pdf.worker.min.js`(1.1MB)로 커밋 — ONNX 런타임과
  같은 패턴. legacy 빌드인 이유: 앱이 script 태그 + ES5 구조라 UMD 전역(`pdfjsLib`)이 필요
  (4.x는 ESM 전용). 텍스트·벡터·이미지 PDF 전부 페이지 그대로 렌더된다.
- **lazy load**: PDF→이미지 모드에서 처음 파일을 넣을 때만 `loadPdfJs()`가 script를 주입.
  sw.js의 vendor/ cache-first 규칙에 따라 첫 사용 후 오프라인 동작.

## 범위

포함:
- 탭 라벨 "PDF 만들기" → "PDF" (공유 시트 라벨·설명 동기화)
- `#pdfModeSeg` 토글: `🖼️ 이미지 → PDF`(기본) | `📄 PDF → 이미지`
- PDF→이미지 파이프라인: PDF 드롭/선택 → 페이지 순차 렌더(진행 표시) → 결과 격자
  (썸네일 클릭 → 라이트박스, 페이지별 저장) → ZIP 저장 · 개별 전체 저장 · 비우기
- 옵션: 형식 PNG(기본)/JPEG/WebP + 품질 슬라이더, 해상도 보통(1.5×)/선명(3×)/최대(4.5×)
  — pdf.js viewport scale 기준(72dpt 기준 ≈108/216/324dpi), 페이지 긴 변 4096px 상한
- 교차 라우팅: PDF 파일이 이미지→PDF 모드(또는 window 드롭)로 들어오면 PDF→이미지
  모드로 자동 전환해 로드, 반대로 이미지가 PDF→이미지 모드에 들어오면 기존 모드로 전환
- 파일 이름: `<PDF이름>-<페이지번호>.<ext>` (총 10쪽 이상이면 2자리 0패딩)

제외 (YAGNI):
- 페이지 선택 렌더(전 페이지 일괄만), 암호 PDF(오류 토스트), 데스크톱 셸 이식

## 구조

```
pdfMode: 'img2pdf' | 'pdf2img'   ← cutMode와 같은 패턴
#img2pdfBody  = 기존 드롭존 + #pdfBody (마크업 이동 없이 래핑만)
#pdf2imgBody  = 새 드롭존(#p2iFile, accept=.pdf) + 옵션 + #p2iGrid + 버튼 + #p2iStat
p2iState = { name, pages: [{blob,url,w,h,n}], busy, seq, total }
```

- `loadPdfJs()` → Promise (ortReady와 같은 1회 로더, `pdfjsLib.GlobalWorkerOptions.workerSrc` 지정)
- `p2iLoad(file)`: seq 토큰 → getDocument(arrayBuffer) → 페이지마다 viewport(scale,
  4096 상한 클램프) → canvas 렌더 → `encodeCanvas`(선택 형식) → 결과 push + 즉시 격자 갱신
- 재사용: `encodeCanvas`, `makeZip`, `saveBlob`, `sequentialDownload`, `openLightbox`,
  `fmtBytes`, `baseName`, `toast`, `.seg-slide` CSS
- 오류: 손상/암호 PDF → 토스트 후 초기 상태 유지. 렌더 중 새 파일/비우기 → seq 폐기

## 검증 (headless 하네스)

1. 왕복: 앱의 이미지→PDF로 3쪽 PDF 생성 → PDF→이미지에 투입 → 3쪽, 각 쪽 콘텐츠 픽셀 실측
2. 텍스트 PDF(수제 최소 PDF) → 1쪽 렌더, 텍스트 픽셀 존재 (pdf.js 렌더 검증)
3. 형식·해상도 옵션: PNG/JPEG 각 MIME, 선명(3×)이 보통(1.5×)의 2배 치수
4. ZIP 항목 수 = 쪽수, 파일명 규칙
5. 토글 전환·교차 라우팅(PDF를 이미지 모드에 드롭 → 자동 전환)
6. 기존 이미지→PDF 회귀 + 전체 스위트

## 부록 (2026-08-05, 기본 모드·다중 파일)

- **기본 모드 = PDF → 이미지**: 탭을 열면 pdf2img가 선택돼 있고 토글로 img2pdf 전환
  (GIF 탭의 영상 기본과 같은 패턴).
- **여러 PDF 동시 변환**: 입력 multiple·드롭·라우팅 모두 복수 수용. 상태가
  `file` 단수 → `files` 배열로 바뀌고, 파일마다 이름-쪽번호로 저장. 쪽수 표기
  'N쪽 (PDF M개)', 다중일 때 썸네일 캡션에 파일 이름 접두, ZIP은 '첫이름 외 N개'.
- **이어 붙이기**: 변환 완료 후 새 PDF를 떨어뜨리면 append (변환 중엔 busy 안내).
- **오류 격리**: 암호·손상 파일은 파일 단위 toast 후 건너뛰고 나머지 계속.
