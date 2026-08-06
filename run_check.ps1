$ErrorActionPreference = 'Stop'
Set-Location 'D:\gitcangku\deepassetlens'
& .\check_health.ps1
Write-Output ""
& .\check_ports.ps1