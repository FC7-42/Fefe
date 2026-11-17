$ErrorActionPreference = "Stop"
Set-Location $HOME\Downloads\Fefe-main

$files = "planning.py","planner.py","app.py","banister.py","README.md",".env.example"
foreach ($f in $files) {
  Invoke-WebRequest -Uri "https://raw.githubusercontent.com/FC7-42/Fefe/main/$f" -OutFile $f
}
foreach ($f in "dashboard.html","base.html","index.html") {
  Invoke-WebRequest -Uri "https://raw.githubusercontent.com/FC7-42/Fefe/main/templates/$f" -OutFile "templates\$f"
}
if (-not (Select-String -Path .env -Pattern "EVENT_DATE" -Quiet)) {
  Add-Content .env "`nEVENT_NAME=Marathon des Blessees des Armees`nEVENT_DATE=2027-05-23`nEVENT_DISTANCE=marathon`nEVENT_GOAL_TIME=3:00:00"
}
Write-Host ""
Write-Host "MISE A JOUR TERMINEE" -ForegroundColor Green
Write-Host "Relance maintenant l'application avec :" -ForegroundColor Green
Write-Host "    & .venv\Scripts\python.exe app.py" -ForegroundColor Yellow
