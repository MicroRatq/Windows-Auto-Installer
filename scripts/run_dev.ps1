param(
    [int]$AutoStopAfterSeconds = 0
)

$ErrorActionPreference = 'Stop'
$utf8Encoding = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding = $utf8Encoding
[Console]::OutputEncoding = $utf8Encoding
$OutputEncoding = $utf8Encoding

$script:cleanupDone = $false
$script:stopRequested = $false
$script:exitCode = 0
$script:viteProcess = $null
$script:electronProcess = $null
$script:autoStopThread = $null
$script:outputEventIds = @()
$script:outputEventStyles = @{}
$script:frontendDir = Join-Path $PSScriptRoot '..\src\frontend'
$script:repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

Register-EngineEvent PowerShell.OnIdle -SupportEvent -Action {
    if ([Console]::KeyAvailable) {
        $key = [Console]::ReadKey($true)
        if (($key.Modifiers -band [ConsoleModifiers]::Control) -and $key.Key -eq [ConsoleKey]::C) {
            Request-Stop -Code 130
        }
    }
} *> $null

function Get-NodeCommand {
    $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
    if (-not $nodeCommand) {
        throw 'Node.js is not available in PATH'
    }

    return $nodeCommand.Source
}

function Request-Stop {
    param(
        [int]$Code = 0
    )

    if (-not $script:stopRequested) {
        $script:stopRequested = $true
        $script:exitCode = $Code
    }
}

function Complete-StopRequest {
    if ($script:stopRequested -and -not $script:cleanupDone) {
        Stop-DevProcesses
    }
}

function New-DevProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string]$Arguments,

        [Parameter(Mandatory = $true)]
        [hashtable]$Environment
    )

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = $Arguments
    $startInfo.WorkingDirectory = $script:frontendDir
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardInput = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    if ($startInfo.PSObject.Properties.Name -contains 'StandardOutputEncoding') {
        $startInfo.StandardOutputEncoding = $utf8Encoding
    }
    if ($startInfo.PSObject.Properties.Name -contains 'StandardErrorEncoding') {
        $startInfo.StandardErrorEncoding = $utf8Encoding
    }

    foreach ($entry in $Environment.GetEnumerator()) {
        $startInfo.Environment[$entry.Key] = $entry.Value
    }

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    [void]$process.Start()
    return $process
}

function Register-ProcessOutput {
    param(
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process]$Process,

        [Parameter(Mandatory = $true)]
        [string]$Label,

        [Parameter(Mandatory = $true)]
        [string]$Color
    )

    $stdoutEventId = "$Label-stdout-$($Process.Id)"
    $stderrEventId = "$Label-stderr-$($Process.Id)"

    $null = Register-ObjectEvent -InputObject $Process -EventName OutputDataReceived -SourceIdentifier $stdoutEventId
    $null = Register-ObjectEvent -InputObject $Process -EventName ErrorDataReceived -SourceIdentifier $stderrEventId

    $script:outputEventIds += @($stdoutEventId, $stderrEventId)
    $script:outputEventStyles[$stdoutEventId] = @{ Label = $Label; Color = $Color }
    $script:outputEventStyles[$stderrEventId] = @{ Label = $Label; Color = $Color }
    $Process.BeginOutputReadLine()
    $Process.BeginErrorReadLine()
}

function Unregister-ProcessOutput {
    foreach ($eventId in $script:outputEventIds) {
        Unregister-Event -SourceIdentifier $eventId -ErrorAction SilentlyContinue
        Remove-Job -Name $eventId -Force -ErrorAction SilentlyContinue
    }

    $script:outputEventIds = @()
    $script:outputEventStyles = @{}
}

function Flush-ProcessOutput {
    param(
        [int]$TimeoutSeconds = 1
    )

    $queuedEvent = Wait-Event -Timeout $TimeoutSeconds
    if (-not $queuedEvent) {
        return
    }

    try {
        do {
            $style = $script:outputEventStyles[$queuedEvent.SourceIdentifier]
            if ($style -and $queuedEvent.SourceArgs.Count -ge 2) {
                $eventArgs = $queuedEvent.SourceArgs[1]
                $line = $eventArgs.Data
                if ($line) {
                    $lineColor = $style.Color
                    if ($style.Label -eq 'ELECTRON') {
                        if ($line -match '^\[(?<tag>[^\]]+)\]') {
                            switch ($matches.tag) {
                                'Electron' { $lineColor = 'Cyan' }
                                'IPC' { $lineColor = 'Magenta' }
                                'Backend' { $lineColor = 'Yellow' }
                                'Python' { $lineColor = 'DarkYellow' }
                                default { $lineColor = $style.Color }
                            }
                        }
                    }

                    Write-Host "[$($style.Label)] $line" -ForegroundColor $lineColor
                }
            }

            Remove-Event -EventIdentifier $queuedEvent.EventIdentifier -ErrorAction SilentlyContinue
            $queuedEvent = Get-Event | Select-Object -First 1
        } while ($queuedEvent)
    } finally {
        if ($queuedEvent) {
            Remove-Event -EventIdentifier $queuedEvent.EventIdentifier -ErrorAction SilentlyContinue
        }
    }
}

function Wait-ForViteServer {
    param(
        [int]$MaxRetries = 30,
        [int]$DelayMilliseconds = 500
    )

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        try {
            $client = New-Object System.Net.Sockets.TcpClient
            $asyncResult = $client.BeginConnect('127.0.0.1', 5173, $null, $null)
            if ($asyncResult.AsyncWaitHandle.WaitOne(1000, $false)) {
                $client.EndConnect($asyncResult)
                $client.Close()
                return $true
            }
            $client.Close()
        } catch {
        }

        Start-Sleep -Milliseconds $DelayMilliseconds
    }

    return $false
}

function Stop-DevProcesses {
    if ($script:cleanupDone) {
        return
    }

    $script:cleanupDone = $true

    Write-Host ''
    Write-Host '[INFO] Cleaning up resources...'

    foreach ($processInfo in @(
        @{ Name = 'Electron'; Process = $script:electronProcess },
        @{ Name = 'Vite'; Process = $script:viteProcess }
    )) {
        $process = $processInfo.Process
        if ($process -and -not $process.HasExited) {
            Write-Host "[INFO] Stopping $($processInfo.Name) process tree (PID: $($process.Id))..."
            taskkill /F /T /PID $process.Id *> $null
        }
    }

    Write-Host '[INFO] Closing any process listening on port 5173...'
    $portPids = @()
    try {
        $portPids = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction Stop |
            Select-Object -ExpandProperty OwningProcess -Unique
    } catch {
        $portPids = @()
    }

    foreach ($portProcessId in $portPids) {
        try {
            Stop-Process -Id $portProcessId -Force -ErrorAction Stop
        } catch {
        }
    }

    Write-Host '[INFO] Development server stopped'
}

$null = Register-EngineEvent PowerShell.Exiting -Action {
    Stop-DevProcesses
}

Write-Host '================================'
Write-Host 'Windows Auto Installer - Dev Mode'
Write-Host '================================'
Write-Host ''

Write-Host '[1/3] Checking Conda environment...'
$condaEnvList = & conda env list 2>&1
if ($LASTEXITCODE -ne 0 -or -not ($condaEnvList | Select-String -Pattern '^\s*win-auto-installer\s')) {
    Write-Host '[ERROR] Cannot use Conda environment, please run scripts\setup_env.bat first'
    if ($condaEnvList) {
        $condaEnvList | ForEach-Object { Write-Host $_ }
    }
    $global:LASTEXITCODE = 1
    return
}
Write-Host '[OK] Conda environment ready'
Write-Host ''

Write-Host '[2/3] Checking frontend dependencies...'
if (-not (Test-Path -LiteralPath (Join-Path $script:frontendDir 'node_modules'))) {
    Write-Host '[INFO] Frontend dependencies not installed, installing...'
    Push-Location $script:frontendDir
    try {
        & npm install
        if ($LASTEXITCODE -ne 0) {
            throw 'npm install failed'
        }
    } finally {
        Pop-Location
    }
}
Write-Host '[OK] Frontend dependencies ready'
Write-Host ''

Write-Host '[3/3] Starting development server...'
Write-Host ''
Write-Host '================================'
Write-Host 'Starting Vite dev server and Electron...'
Write-Host '================================'
Write-Host ''
Write-Host 'Tips:'
Write-Host '- Vite will run on http://localhost:5173'
Write-Host '- Electron window will open automatically'
Write-Host '- Press Ctrl+C to stop server'
Write-Host '- Make sure Conda environment is available, Python backend will start automatically'
Write-Host ''

Write-Host '[INFO] Checking if port 5173 is in use...'
$existingPortPids = @()
try {
    $existingPortPids = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction Stop |
        Select-Object -ExpandProperty OwningProcess -Unique
} catch {
    $existingPortPids = @()
}

foreach ($portProcessId in $existingPortPids) {
    Write-Host "[INFO] Port 5173 is in use, PID: $portProcessId"
    try {
        Stop-Process -Id $portProcessId -Force -ErrorAction Stop
        Write-Host '[OK] Process closed'
    } catch {
        Write-Host '[WARN] Cannot close process, may need admin rights'
    }
}

Push-Location $script:frontendDir
try {
    $nodePath = Get-NodeCommand
    $devEnvironment = @{
        NODE_ENV = 'development'
        CONDA_DEFAULT_ENV = 'win-auto-installer'
        PYTHONUTF8 = '1'
    }

    $condaPrefixes = @(
        (Join-Path $env:USERPROFILE '.conda\envs\win-auto-installer'),
        (Join-Path $env:USERPROFILE 'anaconda3\envs\win-auto-installer'),
        (Join-Path $env:USERPROFILE 'miniconda3\envs\win-auto-installer')
    )
    $condaPrefix = $condaPrefixes | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($condaPrefix) {
        $devEnvironment['CONDA_PREFIX'] = $condaPrefix
        $devEnvironment['PATH'] = "$condaPrefix;$condaPrefix\Scripts;$condaPrefix\Library\bin;$env:PATH"
    }

    Write-Host '[INFO] Starting Vite and Electron in a single terminal...'
    $viteScript = Join-Path $script:frontendDir 'node_modules\vite\bin\vite.js'
    $electronCli = Join-Path $script:frontendDir 'node_modules\electron\cli.js'

    $script:viteProcess = New-DevProcess -FilePath $nodePath -Arguments "`"$viteScript`"" -Environment $devEnvironment
    Register-ProcessOutput -Process $script:viteProcess -Label 'VITE' -Color 'Green'

    if (-not (Wait-ForViteServer)) {
        throw 'Vite server startup timed out'
    }

    $script:electronProcess = New-DevProcess -FilePath $nodePath -Arguments "`"$electronCli`" ." -Environment $devEnvironment
    Register-ProcessOutput -Process $script:electronProcess -Label 'ELECTRON' -Color 'Cyan'

    if ($AutoStopAfterSeconds -gt 0) {
        $script:autoStopThread = [System.Threading.Thread]::new([System.Threading.ThreadStart] {
            Start-Sleep -Seconds $AutoStopAfterSeconds
            if (-not $script:cleanupDone) {
                Request-Stop -Code 0
            }
        })
        $script:autoStopThread.IsBackground = $true
        $script:autoStopThread.Start()
    }

    while (-not $script:stopRequested -and -not $script:electronProcess.HasExited) {
        Flush-ProcessOutput -TimeoutSeconds 0
        Start-Sleep -Milliseconds 50
    }

    if ($script:stopRequested) {
        Write-Host ''
        if ($script:exitCode -eq 130) {
            Write-Host '[INFO] Ctrl+C received, shutting down...'
        } elseif ($AutoStopAfterSeconds -gt 0 -and $script:exitCode -eq 0) {
            Write-Host "[INFO] Auto stop triggered after $AutoStopAfterSeconds seconds"
        }
        Complete-StopRequest
    }

    while (-not $script:stopRequested -and $script:viteProcess -and -not $script:viteProcess.HasExited) {
        Flush-ProcessOutput -TimeoutSeconds 0
        Start-Sleep -Milliseconds 50
    }

    Flush-ProcessOutput -TimeoutSeconds 0
    if (-not $script:stopRequested -and $script:electronProcess) {
        $script:exitCode = $script:electronProcess.ExitCode
    }
} finally {
    Unregister-ProcessOutput
    Pop-Location
    Stop-DevProcesses
}

$global:LASTEXITCODE = $script:exitCode
return
