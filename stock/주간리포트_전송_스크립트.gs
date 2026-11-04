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
 *   GH_TOKEN      : 깃허브 토큰 (하루 요약을 저장소 파일로도 남겨 두는 용도. 없으면 이 기능만 조용히 꺼진다)
 *
 *   (암호는 영어·숫자만 쓰기. # & + ? % 같은 특수문자는 주소에서 잘린다)
 *
 * 배포: 배포 → 새 배포 → 유형 "웹 앱" → 실행 사용자 "나" → 액세스 권한 "모든 사용자"
 * 코드 수정 후: 배포 → 배포 관리 → ✏️ → 버전 "새 버전" → 배포 (주소는 그대로 유지됨)
 */
const ROUTINE_URL = 'https://api.anthropic.com/v1/claude_code/routines/trig_01W2WwrKmWfCwJQr4ABBdSS3/fire';

/* 하루 요약을 깃허브 저장소 파일에도 남겨 둔다.
   아침 비서 브리핑이 이 주소(doGet)를 외부에서 읽다가 실패하는 일이 있어서,
   브리핑이 깃허브 도구로 바로 읽을 수 있는 파일을 하나 더 둔다.
   main이 아니라 snapshot 가지에 써서 앱 배포(GitHub Pages)는 건드리지 않는다. */
const GH_REPO = 'danmi0709-collab/gagyebu';
const GH_BRANCH = 'snapshot';
const GH_PATH = 'stock/daily.json';

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
  if (body.ping) return reply_({ ok: true, ping: true, github: ghCheck_() });

  // 하루 요약: 루틴을 깨우지 않고 저장만 한다.
  // 아침 7시 비서 브리핑이 깃허브 파일(stock/daily.json)을 먼저 읽고, 안 되면 아래 doGet으로 읽어 간다.
  if (body.daily) {
    const snap = JSON.stringify({ 받은시각: new Date().toISOString(), 내용: body.daily });
    if (snap.length > 8500) return reply_({ ok: false, error: '하루 요약이 너무 길어' });
    PropertiesService.getScriptProperties().setProperty('DAILY_SNAPSHOT', snap);
    // 깃허브 쓰기는 거들기용이다. 실패해도 ok:true로 답해서 앱이 같은 내용을 계속 다시 보내지 않게 한다.
    const gh = pushDaily_(snap);
    return reply_({ ok: true, daily: true, github: gh.ok ? 'ok' : gh.error });
  }

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

/**
 * 아침 비서 브리핑이 하루 요약을 읽어 가는 예비 주소.
 * 예: https://script.google.com/macros/s/.../exec?key=암호
 * (주 경로는 깃허브 파일 stock/daily.json 이다. 이 주소는 외부 읽기 도구가 막힐 때가 있어서 예비로 둔다)
 */
function doGet(e) {
  const saved = prop_('RELAY_KEY');
  const key = String((e && e.parameter && e.parameter.key) || '').trim();
  if (!saved) return reply_({ ok: false, error: '스크립트 속성에 RELAY_KEY가 없어' });
  if (key !== saved) return reply_({ ok: false, error: '암호가 없거나 달라' });
  const snap = prop_('DAILY_SNAPSHOT');
  if (!snap) return reply_({ ok: true, snapshot: null, note: '아직 앱에서 받은 하루 요약이 없어' });
  return ContentService.createTextOutput('{"ok":true,"snapshot":' + snap + '}')
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * 하루 요약을 깃허브 저장소의 stock/daily.json 에 덮어쓴다.
 * 파일 내용은 doGet이 돌려주는 것과 똑같은 모양이다: {"ok":true,"snapshot":{"받은시각":…,"내용":{…}}}
 * GH_TOKEN 속성이 없으면 아무것도 하지 않는다(이 기능만 꺼진 상태).
 */
function pushDaily_(snapJson) {
  const token = prop_('GH_TOKEN');
  if (!token) return { ok: false, error: 'GH_TOKEN 없음' };
  const url = 'https://api.github.com/repos/' + GH_REPO + '/contents/' + GH_PATH;
  const headers = {
    Authorization: 'Bearer ' + token,
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
  };
  // 이미 있는 파일을 덮어쓸 때는 그 파일의 sha가 필요하다
  let sha = '';
  try {
    const get = UrlFetchApp.fetch(url + '?ref=' + GH_BRANCH, { headers: headers, muteHttpExceptions: true });
    if (get.getResponseCode() === 200) sha = JSON.parse(get.getContentText()).sha || '';
  } catch (err) {}
  const payload = {
    message: '홍한나 주식: 하루 요약 갱신',
    content: Utilities.base64Encode('{"ok":true,"snapshot":' + snapJson + '}', Utilities.Charset.UTF_8),
    branch: GH_BRANCH,
  };
  if (sha) payload.sha = sha;
  try {
    const put = UrlFetchApp.fetch(url, {
      method: 'put',
      contentType: 'application/json',
      headers: headers,
      payload: JSON.stringify(payload),
      muteHttpExceptions: true,
    });
    const code = put.getResponseCode();
    if (code >= 200 && code < 300) return { ok: true };
    return { ok: false, error: '깃허브 쓰기 실패 (' + code + ') ' + put.getContentText().slice(0, 120) };
  } catch (err) {
    return { ok: false, error: '깃허브 호출 자체가 안 됨: ' + String(err).slice(0, 120) };
  }
}

/** 연결 테스트용: 토큰이 저장소를 읽을 수 있는지만 확인한다 (커밋은 만들지 않는다) */
function ghCheck_() {
  const token = prop_('GH_TOKEN');
  if (!token) return 'GH_TOKEN 없음 (하루 요약 깃허브 저장 꺼짐)';
  try {
    const res = UrlFetchApp.fetch('https://api.github.com/repos/' + GH_REPO + '/contents/' + GH_PATH + '?ref=' + GH_BRANCH, {
      headers: { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' },
      muteHttpExceptions: true,
    });
    const code = res.getResponseCode();
    if (code === 200) return 'ok';
    if (code === 404) return '파일이나 가지(' + GH_BRANCH + ')를 못 찾음 (404)';
    if (code === 401 || code === 403) return '토큰 권한 문제 (' + code + ')';
    return '깃허브 응답 ' + code;
  } catch (err) {
    return '깃허브 호출 실패: ' + String(err).slice(0, 80);
  }
}

function reply_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
