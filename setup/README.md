# AI 도구 설치 (Ponytail · Graphify · Headroom)

이미 설치된 건 건너뛰니까 여러 번 실행해도 괜찮다.

## 윈도우 노트북 (2대 각각 한 번씩)
시작 메뉴 → "PowerShell" 검색 → 실행 → 아래 한 줄 붙여넣고 Enter:
```
iex ((irm https://raw.githubusercontent.com/danmi0709-collab/gagyebu/main/setup/install-ai-tools.ps1).TrimStart([char]0xFEFF))
```
가계부 폴더를 이미 받아 둔 노트북이면 이렇게 해도 된다:
```
powershell -ExecutionPolicy Bypass -File setup\install-ai-tools.ps1
```
끝나면 PowerShell 창을 닫고 새로 열어야 새 명령(graphify, headroom)이 인식된다.

## 폰 (클라우드 세션)
세션 상단 제목줄의 환경 메뉴 → Edit → **Setup script** 칸에 아래 한 줄:
```
curl -fsSL https://raw.githubusercontent.com/danmi0709-collab/gagyebu/main/setup/install-ai-tools.sh | bash
```

## 설치 뒤 꼭 할 것 (노트북)
- Claude를 `claude` 대신 `headroom wrap claude` 로 실행해야 사용량 절감 효과가 난다.
- 확인: `headroom doctor` → savings 항목에 절약한 토큰 수가 찍히면 된다.

(주소의 `main`은 이 파일이 main 브랜치에 합쳐진 뒤 동작한다. 그 전에는 `main` 대신 `ccr-b8388ac3-lwumnv`.)
