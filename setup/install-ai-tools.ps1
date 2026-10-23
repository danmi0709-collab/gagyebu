# Ponytail, Graphify, Headroom 설치 스크립트 (윈도우 PowerShell)
# 이미 설치된 건 건너뛰니까 여러 번 실행해도 괜찮다.
# 사용법: PowerShell에서  powershell -ExecutionPolicy Bypass -File setup\install-ai-tools.ps1

$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
function Step($t) { Write-Host "`n== $t" -ForegroundColor Cyan }
function Has($c) { [bool](Get-Command $c -ErrorAction SilentlyContinue) }

Step "uv"
if (Has uv) { Write-Host "이미 있음: $(uv --version)" }
else {
  powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
  $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

Step "Ponytail (Claude Code 플러그인)"
if ((claude plugin list 2>$null) -match "ponytail@ponytail") { Write-Host "이미 있음" }
else {
  claude plugin marketplace add DietrichGebert/ponytail --scope user
  claude plugin install ponytail@ponytail --scope user
}

Step "Graphify"
if (Has graphify) { Write-Host "이미 있음: $(graphify --version)" }
else { uv tool install graphifyy }
if (-not (Test-Path "$env:USERPROFILE\.claude\skills\graphify\SKILL.md")) { graphify install }

Step "Headroom"
if (Has headroom) { Write-Host "이미 있음: $(headroom --version)" }
else { uv tool install --python 3.13 "headroom-ai[proxy,mcp]" }

Step "결과"
claude plugin list
graphify --version
headroom --version
