# ============================================================
# 공유앱 데이터 분리 검사 스크립트
# sync 없이 검사만 할 때 단독 실행
# ============================================================

$root   = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $root) { $root = (Get-Location).Path }
$shared = Join-Path $root "가계부_공유용.html"

if (-not (Test-Path $shared)) {
    Write-Host "[ERROR] 가계부_공유용.html 파일을 찾을 수 없어요." -ForegroundColor Red
    exit 1
}

$lines = Get-Content $shared -Encoding UTF8
$hits  = @()

for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match 'hanna_') {
        # 주석 줄은 제외 (// 또는 <!-- 로 시작하는 줄)
        $trimmed = $lines[$i].Trim()
        if ($trimmed -notmatch '^\s*//' -and $trimmed -notmatch '^\s*<!--') {
            $hits += [PSCustomObject]@{
                Line    = $i + 1
                Preview = ($trimmed -replace '.*(hanna_\w+).*', '$1')  # 키 이름만 추출
                Text    = if ($trimmed.Length -gt 80) { $trimmed.Substring(0,80) + "..." } else { $trimmed }
            }
        }
    }
}

Write-Host ""
Write-Host "===== 공유앱 키 누락 검사 =====" -ForegroundColor Cyan
Write-Host "파일: 가계부_공유용.html"
Write-Host "총 줄 수: $($lines.Count)"
Write-Host ""

if ($hits.Count -eq 0) {
    Write-Host "[PASS] hanna_ 키 없음" -ForegroundColor Green
    Write-Host "       공유앱 데이터 분리가 완벽해요!" -ForegroundColor Green
} else {
    Write-Host "[FAIL] hanna_ 키 $($hits.Count)개 발견!" -ForegroundColor Red
    Write-Host ""

    # 중복 제거해서 키 이름만 목록화
    $keys = $hits | Select-Object -ExpandProperty Preview | Sort-Object -Unique
    Write-Host "누락된 키 목록:" -ForegroundColor Yellow
    foreach ($k in $keys) {
        Write-Host "  - $k" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "발견된 위치 (상위 10개):" -ForegroundColor Yellow
    $hits | Select-Object -First 10 | ForEach-Object {
        Write-Host "  Line $($_.Line): $($_.Text)" -ForegroundColor DarkYellow
    }

    Write-Host ""
    Write-Host "수정 방법: sync_shared.ps1 에 아래 줄 추가 후 재실행" -ForegroundColor Cyan
    foreach ($k in $keys) {
        $myKey = $k -replace "hanna_", "my_"
        Write-Host ('  $c = $c -replace "' + $k + '", "' + $myKey + '"') -ForegroundColor White
    }
}

Write-Host ""
Write-Host "IS_SHARED 플래그 확인..." -NoNewline
if (($lines | Select-String 'const IS_SHARED = true;').Count -gt 0) {
    Write-Host " OK (true)" -ForegroundColor Green
} elseif (($lines | Select-String 'const IS_SHARED = false;').Count -gt 0) {
    Write-Host " [FAIL] false 로 되어 있어요!" -ForegroundColor Red
} else {
    Write-Host " [경고] IS_SHARED 플래그 자체가 없어요" -ForegroundColor Yellow
}

Write-Host ""
