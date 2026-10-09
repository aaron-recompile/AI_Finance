# Usage: source alpaca_env.sh
# Pull the Alpaca PAPER key out of the macOS keychain into this terminal's environment
# (only affects the current terminal).
# First time, store them (each prompts for input, no echo, not saved to shell history):
#   security add-generic-password -U -a "$USER" -s alpaca-paper-key-id -w
#   security add-generic-password -U -a "$USER" -s alpaca-paper-secret -w

_ap_get() { security find-generic-password -a "$USER" -s "$1" -w 2>/dev/null; }

export APCA_API_KEY_ID="$(_ap_get alpaca-paper-key-id)"
export APCA_API_SECRET_KEY="$(_ap_get alpaca-paper-secret)"
export APCA_API_BASE_URL="https://paper-api.alpaca.markets"   # paper = a different domain, not an extra header

for v in APCA_API_KEY_ID APCA_API_SECRET_KEY; do
  if [ -n "$(eval echo \$$v)" ]; then echo "OK $v imported"; else echo "MISSING $v is empty -- not stored in the keychain yet"; fi
done
case "$APCA_API_KEY_ID" in
  PK*) echo "OK Key ID starts with PK = paper key" ;;
  "")  ;;
  *)   echo "WARNING Key ID does not start with PK -- may be a live key, stop and check!" ;;
esac
unset -f _ap_get
