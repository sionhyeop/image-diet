# 설계 기록 (docs/)

기능을 만들 때 남긴 설계 스펙과 구현 계획입니다. `superpowers/specs/`는 "무엇을·왜"(설계),
`superpowers/plans/`는 "어떻게"(단계별 구현 계획)이며, 파일명 앞의 날짜가 작성일입니다.

## 웹앱 (index.html)

| 날짜 | 스펙 | 계획 | 내용 |
| --- | --- | --- | --- |
| 2026-07-23 | [image-split](superpowers/specs/2026-07-23-image-split-design.md) | [plan](superpowers/plans/2026-07-23-image-split.md) | 이미지 n×m 격자 분할 탭 |
| 2026-07-23 | [split-pagination](superpowers/specs/2026-07-23-split-pagination-design.md) | — | 분할 결과 페이지네이션 |
| 2026-07-23 | [bg-batch](superpowers/specs/2026-07-23-bg-batch-design.md) | — | 배경·요소 탭 일괄 배경 제거 |
| 2026-07-23 | [sam-extract](superpowers/specs/2026-07-23-sam-extract-design.md) | — | 요소 추출에 SlimSAM 인스턴스 분리 |
| 2026-07-30 | [pdf-to-image](superpowers/specs/2026-07-30-pdf-to-image-design.md) | — | PDF 탭 통합 (이미지→PDF + PDF→이미지 토글) |
| 2026-08-04 | [gif-tab](superpowers/specs/2026-08-04-gif-tab-design.md) | — | GIF 탭 (이미지→GIF + 영상→GIF) |
| 2026-08-05 | [qr-tab](superpowers/specs/2026-08-05-qr-tab-design.md) | — | QR 코드 생성·해석 탭 |
| 2026-09-02 | [batch-crop](superpowers/specs/2026-09-02-batch-crop-design.md) | — | 일괄 크롭 탭 |

## 데스크톱 툴킷 (shell/)

| 날짜 | 스펙 | 계획 | 내용 |
| --- | --- | --- | --- |
| 2026-07-15 | [explorer-right-click-compress](superpowers/specs/2026-07-15-explorer-right-click-compress-design.md) | [plan](superpowers/plans/2026-07-15-explorer-right-click-compress.md) | 탐색기 우클릭 압축 (첫 버전) |
| 2026-07-15 | [win11-native-context-menu](superpowers/specs/2026-07-15-win11-native-context-menu-design.md) | [plan](superpowers/plans/2026-07-15-win11-native-context-menu.md) | Win11 네이티브 메뉴·아이콘·창 다듬기 |
| 2026-07-16 | [desktop-toolkit](superpowers/specs/2026-07-16-desktop-toolkit-design.md) | [plan](superpowers/plans/2026-07-16-desktop-toolkit.md) | 압축/Base64/SVG/PDF 4탭 툴킷 |
| 2026-07-16 | [preview](superpowers/specs/2026-07-16-preview-design.md) | [plan](superpowers/plans/2026-07-16-preview.md) | 4탭 실시간 미리보기 |
| 2026-07-16 | — | [base64-compress](superpowers/plans/2026-07-16-base64-compress.md) | Base64 탭 글자수 표시 + 압축 변환 |

> 스펙 없이 계획만 있거나 그 반대인 항목은 당시 작업 규모에 따라 한쪽만 작성한 것입니다.
