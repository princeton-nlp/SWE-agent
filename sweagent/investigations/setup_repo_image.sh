set -e
set -x

container_name=$1

if [[ -z $container_name ]]; then
  echo "ERROR: \$1=container_name missing."
  exit 1
fi

echo -e "Installing VSCode server..."
# Install code-server.
# Also fix bind-addr. See: https://github.com/coder/code-server/discussions/5208
docker exec $container_name /bin/sh -c '
apt-get update && 
apt-get install -y curl sudo && 
(curl -fsSL https://code-server.dev/install.sh | sh) &&
mkdir -p ~/.config/code-server && echo "bind-addr: 0.0.0.0:8080" > ~/.config/code-server/config.yaml
'

