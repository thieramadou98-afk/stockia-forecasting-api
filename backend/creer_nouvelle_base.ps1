# StockIA — nouvelle base SQLite sans toucher a stockia.db
# (utile si stockia.db est verrouille par uvicorn ou ouvert dans l'editeur.)
#
# Usage (PowerShell, depuis ce dossier backend) :
#   .\creer_nouvelle_base.ps1
#   uvicorn app.main:app --reload
#
$env:STOCKIA_DATABASE_URL = "sqlite:///./stockia_nouvelle.db"
Write-Host ""
Write-Host "STOCKIA_DATABASE_URL = $env:STOCKIA_DATABASE_URL"
Write-Host "Fichier cree au premier lancement : (dossier courant)\stockia_nouvelle.db"
Write-Host "Comptes : uniquement via inscription."
Write-Host ""
Write-Host "Prochaine etape : uvicorn app.main:app --reload"
Write-Host ""
