#!/usr/bin/env bash
# EXPERIMENTAL, Nov 1, 2026. Still being tested in real codespaces.
# Starts Studio from RasaHQ/studio-docker-compose. That compose file hardcodes localhost for the Studio API,
# the web client and the model-service chat address. In a browser codespace those must be the forwarded
# addresses. The Keycloak address is NOT handled here because no setting for it was found. Expect login problems
# and report the exact error.
set -euo pipefail
: "${RASA_LICENSE:?Save RASA_LICENSE as a Codespaces secret scoped to this repository, then restart the codespace}"
# Mantle reads RASA_LICENSE. The Studio compose file reads RASA_PRO_LICENSE. Same key, mapped here.
: "${CODESPACE_NAME:?This script is for a codespace}"
DOMAIN="${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
dir="$HOME/studio-docker-compose"
# Pinned to the commit tested in a first run (Studio 1.15.2 and rasa/rasa-pro 3.15.8 from its .env), so a run is repeatable.
STUDIO_COMPOSE_COMMIT=deb6b8fa0dac6991fdb3584ab3143a04b5de3b6c
[ -d "$dir" ] || git clone --quiet https://github.com/RasaHQ/studio-docker-compose "$dir"
git -C "$dir" checkout --quiet "$STUDIO_COMPOSE_COMMIT"
git -C "$dir" rev-parse HEAD
url() { echo "https://${CODESPACE_NAME}-$1.${DOMAIN}"; }
# The upstream database command starts postgres in the background, sleeps 5 seconds, then runs psql. On a first boot the
# official entrypoint's temporary init server shuts down during that window and psql fails ("database system is shutting
# down"), so the container exits 2. Run postgres in the foreground and let the official init directory create the
# keycloak database (POSTGRES_DB already creates studio). This only helps a FIRST boot with a fresh volume: an already
# initialized volume skips the init directory.
mkdir -p "$dir/initdb"
printf 'CREATE DATABASE keycloak;\n' > "$dir/initdb/10-keycloak.sql"
cat > "$dir/docker-compose.override.yml" <<YAML
services:
  database:
    command: ["postgres"]
    volumes:
      - ./initdb:/docker-entrypoint-initdb.d:ro
  studio-keycloak:
    environment:
      # Keycloak 26 (hostname v2): the browser-facing issuer and endpoints must be the forwarded address, not localhost.
      # Backchannel requests from the Studio containers (http://keycloak:8080/auth) keep resolving from their own host header.
      # Candidate from Keycloak's hostname and reverse-proxy docs. NOT run. Whether Studio's backend accepts a token whose
      # issuer is the public address while it talks to the internal one is unknown.
      KC_HOSTNAME: $(url 8081)/auth
      KC_HOSTNAME_BACKCHANNEL_DYNAMIC: "true"
      KC_PROXY_HEADERS: xforwarded
      KC_HTTP_ENABLED: "true"
    # The upstream health probe fetches /auth/, which now redirects to the forwarded HTTPS address, so the helper exits 1
    # and Studio's dependent services never start. Same helper and timing, pointed at the master realm discovery document,
    # which answers 200 without a redirect and exists before the backend runs. The rasa-studio realm does not: the backend
    # creates it, so probing it would deadlock a first boot. The health gate is kept, not disabled.
    healthcheck:
      test:
        [
          "CMD-SHELL",
          '[ -f /tmp/HealthCheck.java ] || echo "public class HealthCheck { public static void main(String[] args) throws java.lang.Throwable { System.exit(java.net.HttpURLConnection.HTTP_OK == ((java.net.HttpURLConnection)new java.net.URL(args[0]).openConnection()).getResponseCode() ? 0 : 1); } }" > /tmp/HealthCheck.java && java /tmp/HealthCheck.java http://localhost:8080/auth/realms/master/.well-known/openid-configuration',
        ]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 60s
  studio-backend:
    environment:
      API_URL: $(url 4000)/api
      WEB_CLIENT_URL: $(url 8080)
  model-service:
    environment:
      RASA_MODEL_SERVER_BASE_URL: $(url 8000)/talk
YAML
cd "$dir"
export RASA_PRO_LICENSE="$RASA_LICENSE"
docker compose up -d
echo "Follow startup with: docker compose -f $dir/docker-compose.yml logs -f startup-helper"
echo "Studio: $(url 8080)   Login (Keycloak): $(url 8081)/auth/"
