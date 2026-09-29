# Installation pilote et dépannage

État au 29 septembre 2026 : service Windows démarré, API locale authentifiée
fonctionnelle et clients affichés dans Home Assistant. Les commandes réelles sur
les machines ne sont pas encore validées. Une [base de dashboard utilisateur](dashboard.md)
est maintenant disponible ; `examples/dashboard.yaml` reste un exemple minimal.

Les chemins ci-dessous sont des exemples d'installation standard. Adaptez-les si
vous avez choisi d'autres dossiers. Les adresses et les clés sont propres à votre
installation : aucune valeur réelle n'est fournie dans ce document.

## Ordre d'installation

1. Installer Python 3.13 **64 bits**, compatible avec le SDK RR utilisé.
   Les alias `WindowsApps/python.exe` ne prouvent pas que Python est installé.
2. Extraire le projet et lancer `scripts/install.ps1` en PowerShell administrateur
   avec les chemins Python/RR et l'adresse du serveur RR (voir le README).
3. Pour la v0.1.1, appliquer les deux corrections décrites ci-dessous.
4. Vérifier la réponse locale de l'API, puis autoriser HA dans le pare-feu.
5. Télécharger l'intégration dans HACS, redémarrer Home Assistant, puis ajouter
   Royal Render dans **Paramètres → Appareils et services**.

Le bouton « Ajouter l'intégration » ne télécharge pas son code. Si HA annonce
qu'elle ne prend pas en charge la configuration graphique, vérifier d'abord le
téléchargement HACS et le redémarrage de HA.

## Correction HTTP 500 de la v0.1.1

Symptôme dans `bridge.log` :
`TypeError: Object of type method is not JSON serializable`.
Le SDK expose `sceneDisplayName()` comme méthode. Le correctif `9679c6a` appelle
cette méthode avant de construire la réponse JSON. Il est publié sur `main`,
mais n'est pas dans l'archive taguée v0.1.1.

Dans PowerShell administrateur, arrêter la passerelle puis installer ce correctif :

```powershell
$ErrorActionPreference = 'Stop'
$Dossier = 'C:\ProgramData\RoyalRenderHABridge'
Stop-Service RoyalRenderHABridge
& "$Dossier\venv\Scripts\python.exe" -m pip install --force-reinstall --no-deps `
    'https://github.com/Pagecran/ha-royalrender/archive/9679c6a.zip'
if ($LASTEXITCODE -ne 0) { throw 'Installation du correctif échouée.' }
```

Redémarrer avec `Start-Service RoyalRenderHABridge` si le lanceur fonctionne déjà.
Sinon, appliquer la correction suivante. La configuration et la clé sont conservées.

## Service Windows : délai de démarrage ou DLL manquante

Symptômes observés : service arrêté, délai de 30 secondes, aucun `bridge.log`.
Le lancement direct de `pythonservice.exe` renvoyait `-1073741515` (`0xC0000135`,
DLL manquante). Avec le dossier Python dans le PATH, il échouait ensuite avec
`PythonService was unable to locate the service manager`.

Le lancement direct de la passerelle permet de distinguer ce problème d'une
erreur du SDK. Exécuter seulement quand le service est arrêté :

```powershell
& 'C:\ProgramData\RoyalRenderHABridge\venv\Scripts\python.exe' `
    -m rr_ha_bridge.server `
    --config 'C:\ProgramData\RoyalRenderHABridge\config.json'
```

Arrêter ce diagnostic avec **Ctrl+C** avant de démarrer le service : les deux
processus utilisent le même port.

### Lanceur validé pour le pilote

Le service utilise explicitement le Python de son environnement virtuel.
Ce contournement doit encore être intégré à l'installateur ; exécuter en
PowerShell administrateur, service arrêté :

```powershell
$ErrorActionPreference = 'Stop'
$Dossier = 'C:\ProgramData\RoyalRenderHABridge'
$Service = Get-CimInstance Win32_Service -Filter "Name='RoyalRenderHABridge'"
if (-not $Service) { throw 'Service non installé.' }
if ($Service.State -ne 'Stopped') { throw 'Arrêter le service avant cette opération.' }
$Sauvegarde = Join-Path $Dossier ("service-path-{0}.txt" -f (Get-Date -Format yyyyMMdd-HHmmss))
$Service.PathName | Set-Content $Sauvegarde -Encoding UTF8

@'
import servicemanager
from rr_ha_bridge.windows_service import RoyalRenderBridgeService

if __name__ == "__main__":
    servicemanager.Initialize()
    servicemanager.PrepareToHostSingle(RoyalRenderBridgeService)
    servicemanager.StartServiceCtrlDispatcher()
'@ | Set-Content "$Dossier\service_host.py" -Encoding UTF8

$Commande = "`"$Dossier\venv\Scripts\python.exe`" `"$Dossier\service_host.py`""
$Resultat = Invoke-CimMethod -InputObject $Service -MethodName Change `
    -Arguments @{ PathName = $Commande }
if ($Resultat.ReturnValue -ne 0) { throw "Erreur Windows : $($Resultat.ReturnValue)" }

Start-Service RoyalRenderHABridge
Start-Sleep -Seconds 15
Get-Service RoyalRenderHABridge
Get-Content "$Dossier\bridge.log" -Tail 30
```

Le chemin précédent est sauvegardé localement pour permettre son rétablissement
via la même méthode `Change`, service arrêté. Ne pas supprimer `service_host.py`
tant que le service l'utilise. Une mise à jour du paquet par pip le conserve.

## Vérifier l'API sans afficher de secret

```powershell
$Config = Get-Content 'C:\ProgramData\RoyalRenderHABridge\config.json' -Raw |
    ConvertFrom-Json
$Etat = Invoke-RestMethod -Uri 'http://127.0.0.1:8787/api/v1/snapshot' `
    -Headers @{ Authorization = "Bearer $($Config.api_key)" }
$Etat.summary
```

La réponse doit afficher les compteurs. Ces compteurs décrivent la ferme ; le
filtre des 10 derniers jours est appliqué ensuite par l'intégration HA.
En cas d'erreur, consulter `bridge.log` :

- **401** : clé absente ou incorrecte ; normal pour un navigateur sans authentification.
- **503** : données RR indisponibles ou périmées ; vérifier la connexion RR.
- **500** : erreur interne ; examiner le traceback (correctif JSON ci-dessus).
- Connexion refusée/délai dépassé : vérifier service, adresse d'écoute et pare-feu.

## Connexion depuis Home Assistant

Si aucune règle équivalente n'existe, autoriser uniquement l'adresse HA choisie :

```powershell
$IPHomeAssistant = Read-Host 'Adresse IP de Home Assistant'
New-NetFirewallRule -DisplayName 'Royal Render HA Bridge' `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8787 `
    -RemoteAddress $IPHomeAssistant
```

Dans le formulaire HA, renseigner séparément :

- **URL** : `http://ADRESSE_DU_SERVEUR_RR:8787`, en remplaçant le texte par
  l'adresse réseau du serveur ; `127.0.0.1` dans HA désignerait HA lui-même.
- **Clé API** : valeur du champ `api_key` du fichier local, sans `Bearer`,
  guillemets ou espaces supplémentaires. Ce n'est pas le mot de passe RR.

Copier la clé localement vers le formulaire ; ne pas la transmettre dans une
issue, un message, une capture ou un dashboard. `config.json` et ses sauvegardes
restent dans le dossier protégé du serveur. Les journaux peuvent contenir des
noms internes : les anonymiser avant partage.

## Activer les boutons

L'installation sans `-EnableCommands` configure `allow_commands=false`.
Les capteurs fonctionnent alors, mais les boutons restent indisponibles.
Pour autoriser les commandes, en PowerShell administrateur :

```powershell
$ErrorActionPreference = 'Stop'
$Chemin = 'C:\ProgramData\RoyalRenderHABridge\config.json'
Copy-Item $Chemin "$Chemin.bak-$(Get-Date -Format yyyyMMdd-HHmmss)"
$Config = Get-Content $Chemin -Raw | ConvertFrom-Json
$Config.allow_commands = $true
$Config | ConvertTo-Json | Set-Content $Chemin -Encoding UTF8
Restart-Service RoyalRenderHABridge
```

Attendre environ 30 secondes avec les intervalles par défaut. Pour revenir à la
supervision seule, utiliser `$false` puis redémarrer le service. Si les boutons
restent indisponibles, vérifier aussi la disponibilité des capteurs et du service.

**Disable** peut interrompre un rendu ; **Disable after frame** demande un arrêt
après la frame. **Working Hours** applique le planning RR existant, sans le modifier.
Les affectations de groupes concernent les membres au moment de la commande.
L'activation et les actions réelles restent à confirmer sur le pilote.

## Affichage et dashboard

Dans les options de l'intégration, **10 jours** conserve les jobs actifs et ceux
soumis récemment ; **0** ne conserve que les actifs. Les jobs en attente et
bloqués après erreurs restent visibles même s'ils sont anciens.

La [base Renderfarm](dashboard.md) fournie par l'utilisateur est publiée avec
une machine fictive. Adapter les identifiants à votre installation ; les détails
de mise en page et les commandes restent à valider dans votre interface.
