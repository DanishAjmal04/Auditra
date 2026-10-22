# Runs inside the window opened by act_as.ps1, as the employee. Each choice does a real action on real files.
$Root = 'C:\AuditraCompany'
function Open-File($relative) {
    $path = Join-Path $Root $relative
    Write-Host "`n--- $path ---" -ForegroundColor Cyan
    Get-Content $path -TotalCount 5
}
function Usb-Drive {
    $drive = Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=2' | Select-Object -First 1
    if (-not $drive) { Write-Host 'Plug in a USB stick first.' -ForegroundColor Red; return $null }
    return "$($drive.DeviceID)\"
}
function Copy-ToUsb($relative) {
    $usb = Usb-Drive; if (-not $usb) { return }
    Copy-Item (Join-Path $Root $relative) $usb -Force
    Write-Host "Copied $relative to $usb" -ForegroundColor Yellow
}

$items = [ordered]@{
    '1'  = @('Open Finance\invoices_2026.csv (allowed for Bilal)', { Open-File 'Finance\invoices_2026.csv' })
    '2'  = @('Open Payroll\salaries_2026.csv', { Open-File 'Payroll\salaries_2026.csv' })
    '3'  = @('Open Medical\patient_records.csv', { Open-File 'Medical\patient_records.csv' })
    '4'  = @('Open Legal\criminal_record_checks.csv', { Open-File 'Legal\criminal_record_checks.csv' })
    '5'  = @('Open Biometrics\fingerprint_enrolment.csv', { Open-File 'Biometrics\fingerprint_enrolment.csv' })
    '6'  = @('Open HR\employees_cnic.csv (allowed for Sara)', { Open-File 'HR\employees_cnic.csv' })
    '7'  = @('Open HR\performance_reviews.csv (allowed for Sara)', { Open-File 'HR\performance_reviews.csv' })
    '8'  = @('Open Customers\fatima_noor_profile.csv', { Open-File 'Customers\fatima_noor_profile.csv' })
    '9'  = @('Open Customers\ali_khan_profile.csv', { Open-File 'Customers\ali_khan_profile.csv' })
    '10' = @('Copy HR\employees_cnic.csv to USB', { Copy-ToUsb 'HR\employees_cnic.csv' })
    '11' = @('Copy Payroll + Medical files to USB (bulk export)', { Copy-ToUsb 'Payroll\salaries_2026.csv'; Copy-ToUsb 'Medical\patient_records.csv' })
    '12' = @('Delete Customers\leads_1..3.csv', { 1..3 | ForEach-Object { Remove-Item (Join-Path $Root "Customers\leads_$_.csv") -ErrorAction SilentlyContinue }; Write-Host 'Deleted 3 lead files' -ForegroundColor Yellow })
    '13' = @('Visit wetransfer.com in Edge', { Start-Process msedge.exe 'https://wetransfer.com' })
    '14' = @('Visit facebook.com in Edge', { Start-Process msedge.exe 'https://facebook.com' })
    '15' = @('Print Customers\fatima_noor_profile.csv to PDF', { Start-Process notepad.exe -ArgumentList '/pt', (Join-Path $Root 'Customers\fatima_noor_profile.csv'), 'Microsoft Print to PDF' })
}

while ($true) {
    Write-Host "`nAuditra employee actions - running as $(whoami)" -ForegroundColor Green
    foreach ($key in $items.Keys) { Write-Host ("  {0,2}  {1}" -f $key, $items[$key][0]) }
    Write-Host '   0  Exit'
    $choice = Read-Host 'Choose'
    if ($choice -eq '0') { break }
    if ($items.Contains($choice)) { & $items[$choice][1] } else { Write-Host 'Unknown choice' }
}
