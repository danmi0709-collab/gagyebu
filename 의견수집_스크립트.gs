/******************************************************
 * 한해살림 / 월부앱 의견 → 구글 시트 자동 정리
 *
 * 준비물: Gmail에 "💬 앱 의견" 라벨 + 그 라벨로 모으는 필터
 *         (앞 단계에서 만든 것)
 *
 * 설치 방법
 *  1) 새 구글 시트를 만든다 (이름: 한해살림 의견)
 *  2) 상단 메뉴 → 확장 프로그램 → Apps Script
 *  3) 기존 내용 모두 지우고 이 파일 내용을 붙여넣기 → 저장(💾)
 *  4) 함수 목록에서 collectFeedback 선택 → ▶ 실행 → 권한 허용
 *  5) 왼쪽 ⏰(트리거) → 트리거 추가
 *       - 실행할 함수: collectFeedback
 *       - 이벤트 소스: 시간 기반
 *       - 1시간마다 (또는 하루 1회)
 *  → 이제 의견 메일이 오면 시트에 자동으로 한 줄씩 쌓입니다.
 ******************************************************/

var SRC_LABEL  = '💬 앱 의견';      // 의견 메일이 모이는 라벨
var DONE_LABEL = '의견정리완료';     // 이미 시트에 옮긴 표시

function collectFeedback() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

  // 첫 줄(머리글) 없으면 만들기
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(['받은 날짜', '앱', '내용']);
    sheet.getRange(1, 1, 1, 3).setFontWeight('bold');
    sheet.setColumnWidth(1, 150);
    sheet.setColumnWidth(2, 90);
    sheet.setColumnWidth(3, 600);
  }

  var srcLabel = GmailApp.getUserLabelByName(SRC_LABEL);
  if (!srcLabel) {
    Logger.log('라벨이 없어요: ' + SRC_LABEL + ' (Gmail 필터부터 만들어 주세요)');
    return;
  }
  var doneLabel = GmailApp.getUserLabelByName(DONE_LABEL) || GmailApp.createLabel(DONE_LABEL);

  var threads = srcLabel.getThreads(0, 100);
  var added = 0;

  for (var i = 0; i < threads.length; i++) {
    var th = threads[i];

    // 이미 옮긴 메일은 건너뛰기
    var names = th.getLabels().map(function (l) { return l.getName(); });
    if (names.indexOf(DONE_LABEL) !== -1) continue;

    var msgs = th.getMessages();
    for (var j = 0; j < msgs.length; j++) {
      var m = msgs[j];
      var subj = m.getSubject() || '';
      var app = subj.indexOf('한해살림') !== -1 ? '한해살림'
              : subj.indexOf('월부앱') !== -1 ? '월부앱' : '기타';
      var body = (m.getPlainBody() || '').trim();
      sheet.appendRow([m.getDate(), app, body.substring(0, 2000)]);
      added++;
    }
    th.addLabel(doneLabel);   // 처리 완료 표시 (중복 방지)
  }

  Logger.log('새로 정리한 의견: ' + added + '건');
}
