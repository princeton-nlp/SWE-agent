set -euo pipefail
set -x

image_id=$1

if [[ -z $image_id ]]; then
  echo "ERROR: \$1=image_id missing."
  exit 1
fi
echo -e "Installing VSCode server..."
# Install code-server.
# Also fix bind-addr. See: https://github.com/coder/code-server/discussions/5208
docker exec $image_id /bin/sh -c '
apt-get update && 
apt-get install -y curl sudo && 
(curl -fsSL https://code-server.dev/install.sh | sh) &&
mkdir -p ~/.config/code-server && echo "bind-addr: 0.0.0.0:8080" > ~/.config/code-server/config.yaml
'

