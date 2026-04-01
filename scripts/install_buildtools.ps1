$ErrorActionPreference = "Stop"

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$installer = Join-Path $env:TEMP "vs_BuildTools.exe"
Invoke-WebRequest -Uri "https://aka.ms/vs/17/release/vs_BuildTools.exe" -OutFile $installer

$arguments = @(
    "--quiet"
    "--wait"
    "--norestart"
    "--add"
    "Microsoft.VisualStudio.Workload.VCTools"
    "--includeRecommended"
)

$process = Start-Process -FilePath $installer -ArgumentList $arguments -Wait -PassThru
Write-Output $process.ExitCode
