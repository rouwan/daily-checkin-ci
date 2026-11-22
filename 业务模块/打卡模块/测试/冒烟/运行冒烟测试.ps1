[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$smokeDirectory = $PSScriptRoot
$moduleRoot = [IO.Path]::GetFullPath((Join-Path $smokeDirectory "..\.."))
$backendDirectory = Join-Path $moduleRoot "功能模块\后端"
$frontendDirectory = Join-Path $moduleRoot "功能模块\前端"
$helper = Join-Path $moduleRoot "技能\webapp-testing\scripts\with_server.py"
$smokeScript = Join-Path $smokeDirectory "核心流程.py"
$serverControl = Join-Path $moduleRoot "server-control.ps1"

function Convert-SmokeRunnerLine {
    param(
        [AllowNull()]
        [object]$Line
    )

    $text = [string]$Line
    if ($text -match "^Starting server (\d+)/(\d+):") {
        Write-Host "正在启动服务 $($Matches[1])/$($Matches[2])……"
        return
    }
    if ($text -match "^Waiting for server on port (\d+)") {
        Write-Host "正在等待 $($Matches[1]) 端口服务就绪……"
        return
    }
    if ($text -match "^Server ready on port (\d+)") {
        Write-Host "$($Matches[1]) 端口服务已就绪。"
        return
    }
    if ($text -match "^All (\d+) server\(s\) ready") {
        Write-Host "全部 $($Matches[1]) 个测试服务已就绪。"
        return
    }
    if ($text -match "^Running:") {
        Write-Host "正在执行两条核心冒烟路径……"
        return
    }
    if ($text -match "^Stopping (\d+) server\(s\)") {
        Write-Host "正在停止 $($Matches[1]) 个测试服务……"
        return
    }
    if ($text -match "^Server (\d+) stopped") {
        Write-Host "服务 $($Matches[1]) 已停止。"
        return
    }
    if ($text -eq "All servers stopped") {
        Write-Host "全部测试服务已停止。"
        return
    }
    if ([string]::IsNullOrWhiteSpace($text)) {
        return
    }

    Write-Host $text
}

foreach ($port in @(8000, 5173)) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    if ($listener) {
        throw "端口 $port 已被占用。请先关闭正在运行的打卡服务，再重新执行冒烟测试。"
    }
}

$python = Get-Command "py.exe" -ErrorAction SilentlyContinue
if (-not $python) {
    throw "未找到 Python 启动器 py.exe。"
}

$temporaryBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$temporaryRoot = [IO.Path]::GetFullPath(
    (Join-Path $temporaryBase ("checkin-smoke-" + [guid]::NewGuid().ToString("N")))
)
New-Item -ItemType Directory -Path $temporaryRoot | Out-Null

$env:CHECKIN_DATABASE_PATH = Join-Path $temporaryRoot "smoke.sqlite3"
$env:CHECKIN_SMOKE_TEST = "1"
$env:PYTHONUTF8 = "1"
$env:PYTHONUNBUFFERED = "1"

$backendCommand = "cd /d `"$backendDirectory`" && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000"
$frontendCommand = "cd /d `"$frontendDirectory`" && npm run dev -- --host 127.0.0.1 --port 5173"
$exitCode = 1

try {
    Write-Host "正在准备独立临时数据库……"
    Write-Host "正在启动前后端并执行冒烟测试……"
    & $python.Source -3.12 $helper `
        --server $backendCommand `
        --port 8000 `
        --server $frontendCommand `
        --port 5173 `
        -- $python.Source -3.12 $smokeScript 2>&1 |
        ForEach-Object { Convert-SmokeRunnerLine -Line $_ }
    $exitCode = $LASTEXITCODE
}
finally {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $serverControl -Action stop
    $temporaryPrefix = $temporaryBase.TrimEnd(
        [IO.Path]::DirectorySeparatorChar
    ) + [IO.Path]::DirectorySeparatorChar
    if ($temporaryRoot.StartsWith(
        $temporaryPrefix,
        [StringComparison]::OrdinalIgnoreCase
    )) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if ($exitCode -ne 0) {
    Write-Host "冒烟测试未通过，退出码：$exitCode" -ForegroundColor Red
}

exit $exitCode
