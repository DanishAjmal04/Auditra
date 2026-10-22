<#
Reverts setup_demo_machine.ps1. Run in PowerShell opened with "Run as administrator":

    powershell -ExecutionPolicy Bypass -File scripts\windows\undo_demo_machine.ps1 [-RemoveUser] [-RemoveFolder]
#>
param(
    [switch]$RemoveUser,
    [switch]$RemoveFolder
)
$ErrorActionPreference = 'Stop'

$Root = 'C:\AuditraCompany'
$StateDir = Join-Path $Root '.auditra'

$backup = Join-Path $StateDir 'auditpol_backup.csv'
if (Test-Path $backup) {
    auditpol /restore /file:$backup | Out-Null
    Write-Host 'Audit policy restored.'
}

net accounts /lockoutthreshold:0 | Out-Null
Write-Host 'Lockout policy turned off (Windows default).'

wevtutil sl Microsoft-Windows-PrintService/Operational /e:false
Write-Host 'Print log disabled.'

if (Test-Path $Root) {
    $acl = Get-Acl -Path $Root -Audit
    foreach ($rule in @($acl.GetAuditRules($true, $false, [System.Security.Principal.NTAccount]))) {
        $acl.RemoveAuditRule($rule) | Out-Null
    }
    Set-Acl -Path $Root -AclObject $acl
    Write-Host 'File audit rule removed.'
}

if ($RemoveUser -and (Get-LocalUser -Name 'bilal' -ErrorAction SilentlyContinue)) {
    Remove-LocalUser -Name 'bilal'
    Write-Host 'Local account bilal removed. Its profile folder under C:\Users stays until you delete it.'
}

if ($RemoveFolder -and (Test-Path $Root)) {
    Remove-Item -Recurse -Force $Root
    Write-Host "$Root removed."
}
