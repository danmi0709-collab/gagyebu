/**
 * 홍한나 주식 → 미래의 한나 루틴 중계 스크립트 (구글 Apps Script)
 *
 * 앱의 "📮 노션에 보내기" 버튼이 이 스크립트로 주간 리포트를 보내면,
 * 이 스크립트가 Claude 루틴을 깨워서 노션에 리포트와 코멘트를 올리게 한다.
 * (Anthropic 서버는 브라우저에서 직접 부를 수 없고, 루틴 열쇠를 앱 코드에 넣을 수 없어서 중간에 둔다)
 *
 * 설정 (프로젝트 설정 ⚙️ → 스크립트 속성):
 *   ROUTINE_TOKEN : 루틴 API 트리거에서 발급한 토큰 (sk-ant-oat01-...)
 *   RELAY_KEY     : 아무 암호 (앱 주소 끝에 ?key=암호 로 붙인다. 주소만 알아서는 못 쓰게 막는 용도)
 *
 *   (암호는 영어·숫자만 쓰기. # & + ? % 같은 특수문자는 주소에서 잘린다)
 *
 * 배포: 배포 → 새 배포 → 유형 "웹 앱" → 실행 사용자 "나" → 액세스 권한 "모든 사용자"
 * 코드 수정 후: 배포 → 배포 관리 → ✏️ → 버전 "새 버전" → 배포 (주소는 그대로 유지됨)
 */
const ROUTINE_URL = 'https://api.anthropic.com/v1/claude_code/routines/trig_01W2WwrKmWfCwJQr4ABBdSS3/fire';

// 속성 이름의 대소문자·앞뒤 공백 실수까지 감안해서 값을 찾는다 (값도 앞뒤 공백 제거)
function prop_(name) {
  const all = PropertiesService.getScriptProperties().getProperties();
  const k = Object.keys(all).find(x => x.trim().toUpperCase() === name);
  return k ? String(all[k]).trim() : '';
}

function doPost(e) {
  const saved = prop_('RELAY_KEY');
  const key = String((e && e.parameter && e.parameter.key) || '').trim();
  if (!saved) {
    const names = Object.keys(PropertiesService.getScriptProperties().getProperties()).join(', ') || '없음';
    return reply_({ ok: false, error: '스크립트 속성에 RELAY_KEY가 없어 (지금 있는 속성: ' + names + ')' });
  }
  if (!key) return reply_({ ok: false, error: '앱 주소 끝에 ?key=암호 가 없어' });
  if (key !== saved) return reply_({ ok: false, error: '암호가 달라 (앱 주소의 암호 ' + key.length + '글자 / 스크립트 속성 ' + saved.length + '글자)' });

  let body = {};
  try { body = JSON.parse(e.postData.contents); } catch (err) { return reply_({ ok: false, error: '보낸 내용을 읽을 수 없어' }); }

  const token = prop_('ROUTINE_TOKEN');
  if (!token) return reply_({ ok: false, error: '스크립트 속성에 ROUTINE_TOKEN이 없어' });

  // 연결 테스트: 루틴은 깨우지 않고 설정만 확인
  if (body.ping) return reply_({ ok: true, ping: true });

  const report = String(body.report || '').slice(0, 20000);
  if (!report.startsWith('## ')) return reply_({ ok: false, error: '주간 리포트 형식이 아니야' });

  const res = UrlFetchApp.fetch(ROUTINE_URL, {
    method: 'post',
    contentType: 'application/json',
    headers: {
      Authorization: 'Bearer ' + token,
      'anthropic-beta': 'experimental-cc-routine-2026-04-01',
      'anthropic-version': '2023-06-01',
    },
    payload: JSON.stringify({ text: '[앱에서 보낸 주간 리포트]\n' + report }),
    muteHttpExceptions: true,
  });
  const code = res.getResponseCode();
  if (code >= 200 && code < 300) return reply_({ ok: true });
  return reply_({ ok: false, error: '루틴 호출 실패 (' + code + ')', detail: res.getContentText().slice(0, 300) });
}

function reply_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
