# gagyebu 작업 규칙 (Claude용)

## 1. 큰 HTML은 통째로 읽지 않는다 (사용량 절약)
- `가계부.html`, `index.html`, `가계부_공유용.html`, `hong/index.html`, `share/index.html`은 각각 약 7,200줄(300KB, 한 번 읽으면 약 7만 토큰)이다. `pro/index.html`도 6,100줄이다.
- 이 파일들은 처음부터 끝까지 읽지 말고, `Grep`으로 함수 이름이나 화면 문구를 찾아서 그 줄 근처만 `Read`(offset/limit)로 읽는다.
- 이미지(`*.png`)는 열지 않는다.

## 2. 원본과 복사본 (고칠 때는 원본만)
- **원본은 `가계부.html` 하나뿐이다.** 앱 기능은 여기서만 고친다.
- 아래 파일은 원본에서 만들어지는 복사본이라 **손으로 고치지 않는다.**
  - `index.html`: 원본과 똑같은 복사본
  - `가계부_공유용.html`, `share/index.html`: 공유용 변환본 (저장 키 `hanna_`→`my_`, "한나"→"나", `IS_SHARED = true`, 미리보기 태그 추가)
- 복사본은 `python deploy.py "커밋 메시지"` (동기화 → 검사 → 커밋·푸시) 또는 `sync_shared.ps1`이 만든다. `deploy.py`는 GitHub에 올리므로 사용자가 시킬 때만 실행한다.
- 원본을 고친 뒤에는 복사본이 어긋나지 않았는지 `python check_shared.py`로 검사한다.

## 3. 확인되지 않은 부분 (고치기 전에 사용자에게 물어본다)
- `hong/index.html`은 `share/index.html`과 22줄만 다른 거의 같은 파일이다. 이 파일을 맞춰 주는 스크립트가 `deploy.py`와 `sync_shared.ps1`에는 보이지 않는다.
- `pro/index.html`("나만의 가계부")은 원본에서 자동으로 만들어지지 않는 별도 파일로 보인다. 마지막 수정이 2026-06이다.

## 4. 작은 앱 (각각 따로 작업)
- `game/`(티니핑 vs 피카츄), `puppy/`(퍼피 구조대), `hospital/`(꼬마 의사), `stock/`(홍한나 주식)은 1,000줄 안팎이라 읽어도 부담이 작다.
- `stock/`에는 별도 규칙이 있다. `stock/CLAUDE.md`를 먼저 읽는다.
