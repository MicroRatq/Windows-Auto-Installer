$ErrorActionPreference = 'Stop';
$process = Get-Process -Name 'explorer' -ErrorAction 'SilentlyContinue';
if ($process) {
	Stop-Process -Name 'explorer' -Force;
	Start-Sleep -Seconds 2;
}
Start-Process -FilePath 'explorer.exe';
