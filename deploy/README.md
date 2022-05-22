# Deployment Scripts
TBD

## Certbot
Certbot allows us to specify hooks by placing files in subdirectories which are then run as pre-, deploy- and post-hooks when any certificates are renewed with the `renew` command. This will work with automatic renewal.

Hooks should be placed in the following folders:
```
/etc/letsencrypt/renewal-hooks
├── pre
    └── nginx-pre-renewal.sh
├── deploy
└── post
    └── nginx-pre-renewal.sh
```

There are also deploy-hook shell scripts, but these are currently **not** used.