# 홍한나 주식 (stock/) 작업 규칙

- 사용자(한나)의 상시 지시: 이 앱을 고치면 **PR을 만들고, 브라우저 테스트가 통과하면 머지까지 바로** 한다. 따로 "머지해"를 기다리지 않는다. 머지 후 GitHub Pages 배포 성공까지 확인하고 알린다.
- 앱 주소: https://danmi0709-collab.github.io/gagyebu/stock/
- 기록은 사용자 폰의 브라우저 저장소(localStorage `hanna_stock_v1`)에만 있다. 지난 날의 주가가 바뀌지 않게, 규칙을 바꿀 때는 그날 기록에 저장된 값(target, coreIds 등)을 기준으로 계산한다.
- 코드를 바꾸면 `sw.js`의 캐시 이름 버전(`hanna-stock-vN`)을 올린다.
- 노션 주간 리포트·미래의 한나 코멘트는 루틴(trig_01W2WwrKmWfCwJQr4ABBdSS3)이 담당한다. 리포트 형식(`weekReport`)을 바꾸면 루틴 지시문과 맞는지 확인한다.
