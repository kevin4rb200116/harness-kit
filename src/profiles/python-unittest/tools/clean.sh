#!/usr/bin/env bash
# Limpia contenedores, imágenes locales y caché de Python del proyecto.
set -u

docker compose down --rmi local --volumes --remove-orphans
status=$?

find . -name __pycache__ -type d -prune -exec rm -rf {} +

exit $status
