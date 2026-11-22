[CmdletBinding()]
param(
    [ValidateSet("start", "stop")]
    [string]$Action = "start",
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backendPort = 8000
$frontendPort = 5173

function Find-ProjectDirectory {
    param([string]$MarkerFile)

    $projectDirectories = foreach ($groupDirectory in Get-ChildItem -LiteralPath $root -Directory) {
        foreach ($candidate in Get-ChildItem -LiteralPath $groupDirectory.FullName -Directory) {
            if (Test-Path -LiteralPath (Join-Path $candidate.FullName $MarkerFile)) {
                $candidate.FullName
            }
        }
    }

    $projectDirectory = @($projectDirectories) | Select-Object -First 1
    if (-not $projectDirectory) {
        throw "未找到包含 $MarkerFile 的项目目录。"
    }
    return $projectDirectory
}

$backendDirectory = Find-ProjectDirectory -MarkerFile "pyproject.toml"
$frontendDirectory = Find-ProjectDirectory -MarkerFile "package.json"

function Get-ListenerProcessIds {
    param([int]$Port)

    $connections = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if (-not $connections) {
        return @()
    }

    return @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
}

function Test-OwnedProcess {
    param(
        [string]$CommandLine,
        [ValidateSet("backend", "frontend")]
        [string]$Kind
    )

    if ([string]::IsNullOrWhiteSpace($CommandLine)) {
        return $false
    }

    if ($Kind -eq "backend") {
        $isUvicorn = $CommandLine -match "(?i)uvicorn"
        $isCheckInApp = $CommandLine -match "(?i)app\.main:app"
        return $isUvicorn -and $isCheckInApp
    }

    $isVite = $CommandLine -match "(?i)vite"
    $isProjectPath = $CommandLine.IndexOf(
        $frontendDirectory,
        [System.StringComparison]::OrdinalIgnoreCase
    ) -ge 0
    return $isVite -and $isProjectPath
}

function Stop-OwnedListener {
    param(
        [int]$Port,
        [ValidateSet("backend", "frontend")]
        [string]$Kind
    )

    $listenerProcessIds = Get-ListenerProcessIds -Port $Port
    foreach ($listenerProcessId in $listenerProcessIds) {
        $processRecord = Get-CimInstance Win32_Process -Filter "ProcessId = $listenerProcessId"
        if (-not $processRecord) {
            continue
        }

        $commandLine = [string]$processRecord.CommandLine
        if (-not (Test-OwnedProcess -CommandLine $commandLine -Kind $Kind)) {
            throw "端口 $Port 已被 PID $listenerProcessId 占用，但无法确认它是本打卡项目的进程。为避免结束无关程序，已停止操作。"
        }

        $kindLabel = if ($Kind -eq "backend") { "后端" } else { "前端" }
        Write-Host "正在停止旧${kindLabel}进程：PID $listenerProcessId，端口 $Port"
        & taskkill.exe /PID $listenerProcessId /T /F | Out-Null
        if ($LASTEXITCODE -notin @(0, 128)) {
            throw "无法停止 PID $listenerProcessId。"
        }
    }

    $deadline = [DateTime]::UtcNow.AddSeconds(10)
    while ((Get-ListenerProcessIds -Port $Port).Count -gt 0) {
        if ([DateTime]::UtcNow -ge $deadline) {
            throw "端口 $Port 在 10 秒内未能释放。"
        }
        Start-Sleep -Milliseconds 250
    }
}

function Stop-AllOwnedServers {
    Stop-OwnedListener -Port $backendPort -Kind backend
    Stop-OwnedListener -Port $frontendPort -Kind frontend
}

function Resolve-UvRunner {
    $uvCommand = Get-Command "uv.exe" -ErrorAction SilentlyContinue
    if ($uvCommand) {
        return @{
            Executable = $uvCommand.Source
            Prefix = @()
        }
    }

    $pyCommand = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if (-not $pyCommand) {
        throw "未找到 uv.exe 或 py.exe。请先安装 uv 或 Python 3.12。"
    }

    return @{
        Executable = $pyCommand.Source
        Prefix = @("-3.12", "-m", "uv")
    }
}

function Ensure-Dependencies {
    if (-not (Test-Path (Join-Path $backendDirectory "pyproject.toml"))) {
        throw "未找到后端项目目录：$backendDirectory"
    }
    if (-not (Test-Path (Join-Path $frontendDirectory "package.json"))) {
        throw "未找到前端项目目录：$frontendDirectory"
    }

    $nodeCommand = Get-Command "node.exe" -ErrorAction SilentlyContinue
    $npmCommand = Get-Command "npm.cmd" -ErrorAction SilentlyContinue
    if (-not $nodeCommand -or -not $npmCommand) {
        throw "运行前后端需要先安装 Node.js 和 npm。"
    }

    $uvRunner = Resolve-UvRunner
    Write-Host "正在同步后端依赖……"
    Push-Location $backendDirectory
    try {
        & $uvRunner.Executable @($uvRunner.Prefix) sync
        if ($LASTEXITCODE -ne 0) {
            throw "后端依赖同步失败。"
        }
    }
    finally {
        Pop-Location
    }

    $viteEntry = Join-Path $frontendDirectory "node_modules\vite\bin\vite.js"
    if (-not (Test-Path $viteEntry)) {
        Write-Host "正在安装前端依赖……"
        Push-Location $frontendDirectory
        try {
            & $npmCommand.Source install
            if ($LASTEXITCODE -ne 0) {
                throw "前端依赖安装失败。"
            }
        }
        finally {
            Pop-Location
        }
    }

    return @{
        Node = $nodeCommand.Source
        Vite = $viteEntry
    }
}

function Start-CheckInServers {
    $tools = Ensure-Dependencies
    $uvicornEntry = Join-Path $backendDirectory ".venv\Scripts\uvicorn.exe"
    if (-not (Test-Path $uvicornEntry)) {
        throw "后端虚拟环境中未安装 Uvicorn。"
    }

    Write-Host "正在启动后端：http://127.0.0.1:$backendPort"
    $backendProcess = Start-Process `
        -FilePath $uvicornEntry `
        -ArgumentList @("app.main:app", "--host", "127.0.0.1", "--port", "$backendPort") `
        -WorkingDirectory $backendDirectory `
        -WindowStyle Normal `
        -PassThru

    Write-Host "正在启动前端：http://127.0.0.1:$frontendPort"
    $frontendProcess = Start-Process `
        -FilePath $tools.Node `
        -ArgumentList @($tools.Vite, "--host", "127.0.0.1", "--port", "$frontendPort") `
        -WorkingDirectory $frontendDirectory `
        -WindowStyle Normal `
        -PassThru

    return @{
        Backend = $backendProcess
        Frontend = $frontendProcess
    }
}

function Wait-ForEndpoint {
    param(
        [string]$Uri,
        [string]$Name
    )

    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                return
            }
        }
        catch {
            # Services may still be starting.
        }
        Start-Sleep -Milliseconds 500
    }

    throw "$Name 在 30 秒内未就绪。"
}

try {
    Write-Host "正在清理旧的打卡服务进程……"
    Stop-AllOwnedServers

    if ($Action -eq "stop") {
        Write-Host "打卡服务已停止。"
        exit 0
    }

    $startedProcesses = Start-CheckInServers
    Write-Host "正在等待前后端服务就绪……"
    Wait-ForEndpoint -Uri "http://127.0.0.1:$backendPort/api/health" -Name "后端"
    Wait-ForEndpoint -Uri "http://127.0.0.1:$frontendPort" -Name "前端"

    Write-Host "打卡服务已就绪。"
    Write-Host "后端进程 PID：$($startedProcesses.Backend.Id)"
    Write-Host "前端进程 PID：$($startedProcesses.Frontend.Id)"

    if (-not $NoBrowser) {
        Start-Process "http://127.0.0.1:$frontendPort"
    }

    exit 0
}
catch {
    Write-Host "运行失败：$($_.Exception.Message)" -ForegroundColor Red
    try {
        Stop-AllOwnedServers
    }
    catch {
        Write-Warning "运行失败后的自动清理也未能完成。"
    }
    exit 1
}
