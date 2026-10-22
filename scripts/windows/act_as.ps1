<#
Opens a PowerShell window running as an employee (bilal or sara), without signing in to Windows as them.
Every file access in that window is recorded by Windows as that employee, so Auditra attributes it to them.

    powershell -ExecutionPolicy Bypass -File scripts\windows\act_as.ps1 -User bilal
    powershell -ExecutionPolicy Bypass -File scripts\windows\act_as.ps1 -User bilal -WrongPasswords 5

-WrongPasswords N first tries N wrong passwords, then the right one (brute-force scene, Art. 32).
Keep N at 5 or less: the lockout policy locks the account at 6.
#>
param(
    [ValidateSet('bilal', 'sara')][string]$User = 'bilal',
    [int]$WrongPasswords = 0
)
$ErrorActionPreference = 'Stop'
$account = "$env:COMPUTERNAME\$User"
$cred = Get-Credential -UserName $account -Message "Windows password for $User"

for ($i = 1; $i -le $WrongPasswords; $i++) {
    $bad = New-Object System.Management.Automation.PSCredential($account, (ConvertTo-SecureString "wrong-$i-$(Get-Random)" -AsPlainText -Force))
    try { Start-Process cmd.exe -Credential $bad -ArgumentList '/c', 'exit' -WindowStyle Hidden -Wait } catch { Write-Host "  wrong password $i rejected" }
    Start-Sleep -Milliseconds 700
}

# The employee cannot read files under ataur's profile, so the menu is copied to a shared folder first.
$menu = Join-Path $env:PUBLIC 'auditra_employee_menu.ps1'
Copy-Item (Join-Path $PSScriptRoot 'employee_menu.ps1') $menu -Force
Start-Process powershell.exe -Credential $cred -LoadUserProfile -WorkingDirectory 'C:\AuditraCompany' `
    -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', $menu
Write-Host "Opened a PowerShell window running as $account."
