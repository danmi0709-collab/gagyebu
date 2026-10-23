# AI 도구 설치 (Ponytail · Graphify · Headroom)

이미 설치된 건 건너뛰니까 여러 번 실행해도 괜찮다.

## 노트북 (맥)
터미널에서 가계부 폴더로 가서:
```
bash setup/install-ai-tools.sh
```

## 노트북 (윈도우)
PowerShell에서 가계부 폴더로 가서:
```
powershell -ExecutionPolicy Bypass -File setup\install-ai-tools.ps1
```

## 폰 (클라우드 세션)
세션 상단 제목줄의 환경 메뉴 → Edit → **Setup script** 칸에 아래 한 줄을 넣는다.
새 세션을 열 때마다 자동으로 설치된다.
```
curl -fsSL https://raw.githubusercontent.com/danmi0709-collab/gagyebu/main/setup/install-ai-tools.sh | bash
```
(이 파일이 main 브랜치에 합쳐진 뒤에 동작한다.)

## 설치 뒤 꼭 할 것
- Headroom 효과를 보려면 Claude를 `headroom wrap claude` 로 실행한다. (노트북 전용)
- 확인: `headroom doctor` 의 savings 항목에 절약한 토큰 수가 찍히면 된다.
