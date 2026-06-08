# ============================================================
# 가계부 공유용 동기화 스크립트
# 실행: 이 파일을 PowerShell에서 실행하거나 더블클릭
# ============================================================

$root   = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $root) { $root = (Get-Location).Path }
$src    = Join-Path $root "가계부.html"
$shared = Join-Path $root "가계부_공유용.html"
$idx    = Join-Path $root "index.html"
$sidx   = Join-Path $root "share\index.html"

Write-Host "동기화 시작..."

$c = Get-Content $src -Raw -Encoding UTF8

# ── localStorage 키 변환 (hanna_ → my_) ──
$c = $c -replace "hanna_transactions",        "my_transactions"
$c = $c -replace "hanna_budget",              "my_budget"
$c = $c -replace "hanna_yeardata",            "my_yeardata"
$c = $c -replace "hanna_subscriptions",       "my_subscriptions"
$c = $c -replace "hanna_assets",              "my_assets"
$c = $c -replace "hanna_gdrive_token",        "my_gdrive_token"
$c = $c -replace "hanna_gdrive_fileid",       "my_gdrive_fileid"
$c = $c -replace "hanna_last_upload",         "my_last_upload"
$c = $c -replace "hanna_catmonth",            "my_catmonth"
$c = $c -replace "hanna_currentyear",         "my_currentyear"
$c = $c -replace "hanna_theme",               "my_theme"
$c = $c -replace "hanna_nickname",            "my_nickname"
$c = $c -replace "hanna_annual_budget",       "my_annual_budget"
$c = $c -replace "hanna_tx_order",            "my_tx_order"
$c = $c -replace "hanna_merchant_cats",       "my_merchant_cats"
$c = $c -replace "hanna_sheets_url",          "my_sheets_url"
$c = $c -replace "hanna_sub_auto_month",      "my_sub_auto_month"
$c = $c -replace "hanna_formula_man_migrated","my_formula_man_migrated"

# ── 텍스트 변환 ──
$c = $c -replace "한나의 가계부",             "나만의 가계부"
$c = $c -replace "이번 달 잔액 \(한나\)",     "이번 달 잔액"
$c = $c -replace "한나",                      "나"

# ── IS_SHARED 플래그 ──
$c = $c -replace "const IS_SHARED = false;",  "const IS_SHARED = true;"

# ── OG 메타태그 (카카오톡 미리보기) 주입 ──
$ogTags = @"
<!-- Open Graph (카카오톡·SNS 미리보기) -->
<meta property="og:type" content="website">
<meta property="og:site_name" content="나만의 가계부">
<meta property="og:title" content="나만의 가계부 💰">
<meta property="og:description" content="설치 없이 브라우저에서 바로 쓰는 무료 가계부. 수입·지출·저축 관리, 자산 추이 차트, 연예산 계획까지. 내 데이터는 내 기기에만 저장됩니다.">
<meta property="og:image" content="https://danmi0709-collab.github.io/gagyebu/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="https://danmi0709-collab.github.io/gagyebu/share">
<meta name="description" content="설치 없이 브라우저에서 바로 쓰는 무료 가계부. 수입·지출·저축 관리, 자산 추이 차트, 연예산 계획까지.">

<!-- 카카오톡 전용 -->
<meta property="kakao:title" content="나만의 가계부 💰">
<meta property="kakao:description" content="설치 없이 바로 쓰는 무료 가계부. 내 데이터는 내 기기에만 저장됩니다.">
<meta property="kakao:image" content="https://danmi0709-collab.github.io/gagyebu/og-image.png">

<!-- PWA (홈 화면 설치) -->
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#c07a3a">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="가계부">
<link rel="apple-touch-icon" href="icon-192.png">
"@

# <title> 태그 바로 뒤에 OG 태그 삽입
$c = $c -replace "(<title>[^<]*</title>)", "`$1`n$ogTags"

# 저장
$c | Set-Content $shared -Encoding UTF8
$c | Set-Content $sidx   -Encoding UTF8

# 메인 앱 복사
Copy-Item $src $idx -Force

Write-Host ""
Write-Host "저장 완료:"
Write-Host "  가계부_공유용.html"
Write-Host "  index.html (메인)"
Write-Host "  share/index.html (공유)"

# ── 자동 검사: hanna_ 키 누락 여부 ──
Write-Host ""
Write-Host "검사 중..." -NoNewline

$lines  = Get-Content $shared -Encoding UTF8
$hits   = @()
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match 'hanna_') {
        $hits += [PSCustomObject]@{ Line = $i + 1; Text = $lines[$i].Trim() }
    }
}

if ($hits.Count -eq 0) {
    Write-Host " OK"
    Write-Host ""
    Write-Host "[PASS] hanna_ 키 없음 - 공유앱 데이터 분리 정상" -ForegroundColor Green
} else {
    Write-Host " 경고!"
    Write-Host ""
    Write-Host "[FAIL] hanna_ 키 $($hits.Count)개 발견! sync_shared.ps1 에 변환 규칙 추가 필요" -ForegroundColor Red
    Write-Host ""
    foreach ($h in $hits) {
        Write-Host "  Line $($h.Line): $($h.Text)" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "위 항목을 sync_shared.ps1 의 변환 목록에 추가하세요." -ForegroundColor Yellow
}
