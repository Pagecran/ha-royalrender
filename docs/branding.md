# Royal Render branding in Home Assistant

The integration includes `brand/icon.png`, `brand/dark_icon.png`, `brand/logo.png`
and `brand/dark_logo.png`. Home Assistant 2026.3+ supports these local brand images;
our supported version is 2026.9+. No external brands-catalog registration is needed.
Update the integration through HACS and restart Home Assistant to load them.
The frontend selects the light/dark variant for the integration automatically.

## Utiliser le logo dans votre dashboard

Après mise à jour HACS vers **v0.1.2** et redémarrage de HA, le logo est disponible
sur la fiche Royal Render. Pour une carte de dashboard, copier les fichiers dans
le dossier `www` de Home Assistant (avec File editor, Studio Code Server ou Terminal).
Exemple dans le terminal **HA**, et non dans PowerShell sur le serveur RR :

```sh
mkdir -p /config/www/royalrender
cp /config/custom_components/royalrender/brand/*.png /config/www/royalrender/
```

Si vous venez de créer le dossier `www` pour la première fois, redémarrer HA.
Ajouter ensuite une carte manuelle avec le contenu de
[`examples/logo-card.yaml`](../examples/logo-card.yaml) :

```yaml
type: picture
image: /local/royalrender/logo.png
tap_action:
  action: none
hold_action:
  action: none
```

Pour un dashboard sombre, utiliser `/local/royalrender/dark_logo.png`.
L'icône carrée est disponible dans `icon.png` / `dark_icon.png`.
La carte Picture utilise le fichier choisi ; elle ne change pas automatiquement
de variante avec le thème. Ces images ne constituent pas un nouvel identifiant
`mdi:` : les utiliser dans les cartes qui acceptent une image.

Les fichiers sous `/local/` sont des visuels publics et ne nécessitent aucune clé.
Ne copier que les PNG, jamais `config.json`. L'API native `/api/brands/` utilise
une authentification gérée par le frontend ; ne coller aucun token dans le YAML.

## Sources and attribution

Official Royal Render website assets, retrieved 29 September 2026:

- https://www.royalrender.de/wp-content/uploads/2026/05/RoyalRender_Logo_invert_small.png
- https://www.royalrender.de/wp-content/uploads/2026/05/RoyalRender_Logo_white.png
- https://www.royalrender.de/wp-content/uploads/2026/05/cropped-R_black-192x192.png

Logos are resized proportionally to 221×128. The square icon is resized to
256×256; its white background is converted to transparency, with a white-mark
variant for dark themes. No additional image detail is claimed by resizing.

Royal Render names and artwork belong to their respective owners, are used for
product identification and do not imply endorsement. These third-party assets
are not covered by this repository's MIT code license.
