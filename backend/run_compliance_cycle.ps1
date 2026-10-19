$ErrorActionPreference = 'Stop'

Set-Location -LiteralPath 'D:\Auditra\backend'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = 'D:\Auditra\backend\venv\Lib\site-packages'

py manage.py run_compliance_cycle --trigger scheduled
exit $LASTEXITCODE
