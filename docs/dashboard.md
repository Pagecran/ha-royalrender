# Base de dashboard Renderfarm

[Télécharger le YAML](../examples/renderfarm-dashboard.yaml) — base fournie par
l'utilisateur, avec entités génériques **Machine Lambda**.

Cette vue Sections comprend deux tableaux (jobs en cours et en attente), une
carte machine et un exemple de popup avec commandes RR. Elle est publiée comme
point de départ à adapter, pas comme dashboard entièrement validé sur toutes
les versions des cartes personnalisées.

## Dépendances

- L'intégration Royal Render configurée et ses capteurs disponibles.
- [Bubble Card](https://github.com/Clooos/Bubble-Card), installé via HACS.
- [card-mod](https://github.com/thomasloven/lovelace-card-mod), installé via HACS.
- `allow_commands=true` dans la passerelle pour utiliser les boutons (voir
  [activation des commandes](installation-fr.md#activer-les-boutons)).

## Importer la vue

Le fichier décrit **une vue**, pas une carte individuelle ni un dashboard complet.
Dans l'éditeur de configuration brute d'un dashboard, ajouter son contenu comme
un élément de la liste `views:`. Par exemple :

```yaml
views:
  - title: Renderfarm
    path: renderfarm
    icon: mdi:render
    type: sections
    max_columns: 4
    sections:
      # Insérer ici les sections du fichier fourni.
```

Conserver l'ancre `&jobs_table_style` et sa référence `*jobs_table_style` ensemble
lors de l'import. Si l'éditeur ne conserve pas les ancres, recopier le bloc CSS
dans la deuxième carte.

## Adapter à votre installation

1. Vérifier les identifiants des capteurs `sensor.royal_render_queue`,
   `sensor.royal_render_rendering_jobs` et `sensor.royal_render_waiting_jobs`.
2. Remplacer **toutes** les occurrences de `machine_lambda` par vos entités réelles,
   y compris dans les templates et les actions. Les noms peuvent différer de
   ceux générés automatiquement par HA.
3. Dupliquer les cartes/popups pour les autres machines, avec un `hash` unique
   et un `navigation_path` correspondant pour chacune.
4. Ajouter éventuellement le [logo Royal Render](branding.md).

## Points à finaliser

- Les styles dynamiques de la carte machine fournie contiennent du Jinja dans
  `styles`. Bubble Card utilise habituellement des templates JavaScript pour
  ses styles : adapter ces expressions à la version installée si les couleurs
  ne changent pas. Les templates des cartes Markdown sont, eux, traités par HA.
- La structure du popup (`cards` imbriquées) est à vérifier avec votre version
  de Bubble Card ; suivre sa documentation si elle attend les cartes après
  la carte `pop-up` dans une pile verticale.
- Le champ App est déduit du nom/layer (dont la convention `03-3d`), pas d'un
  champ officiel de logiciel RR. Adapter cette heuristique à vos noms de jobs.
  Les logos applicatifs utilisent des URL externes ; leurs propriétaires
  respectifs conservent leurs droits.
- Le tableau d'attente exclut les jobs signalés en problème. Ajouter une carte
  d'incidents (voir `examples/dashboard.yaml`) pour garder ces jobs visibles.
- Une liste vide ne prouve pas que RR est disponible : vérifier les états
  `unavailable` des capteurs, que cette base ne traite pas séparément.
- Les actions Enable + Working Hours/Ignore Working Hours ciblent deux boutons.
  Leur exécution n'est pas une transaction et l'ordre n'est pas garanti ; utiliser
  un script HA séquentiel si un ordre précis est nécessaire.
- Le temps par frame n'est pas encore fourni par l'intégration.

Le fichier contient des noms fictifs, aucune clé et aucune adresse interne.
Les données réelles des jobs et utilisateurs seront affichées localement par HA.
