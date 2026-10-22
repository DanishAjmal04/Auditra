<#
Lets the officer laptop reach this laptop's Auditra server over the hotspot or LAN.
Run once in PowerShell opened with "Run as administrator":

    powershell -ExecutionPolicy Bypass -File scripts\windows\setup_server_firewall.ps1 [-Remove]
#>
param([switch]$Remove)
$ErrorActionPreference = 'Stop'

$rules = @(
    @{ Name = 'Auditra API 8000'; Port = 8000 },
    @{ Name = 'Auditra Console 5173'; Port = 5173 }
)
foreach ($rule in $rules) {
    Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    if (-not $Remove) {
        New-NetFirewallRule -DisplayName $rule.Name -Direction Inbound -Protocol TCP -LocalPort $rule.Port -Action Allow -Profile Private, Public | Out-Null
        Write-Host "Opened TCP $($rule.Port)"
    }
}
if ($Remove) { Write-Host 'Rules removed.'; exit 0 }

Write-Host ''
Write-Host 'This laptop''s addresses (give the officer laptop the one on the hotspot network):'
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
    ForEach-Object { Write-Host "    http://$($_.IPAddress):5173   ($($_.InterfaceAlias))" }
