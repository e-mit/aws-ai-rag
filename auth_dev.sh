# Create test credentials for development use only.

TEMP_PWORD=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 7; echo)
BCRYPT_HASH=$(echo $TEMP_PWORD | python3 -c \
"import sys
import bcrypt
pword_bytes = sys.stdin.read().strip().encode('utf-8')
print(bcrypt.hashpw(pword_bytes, bcrypt.gensalt()).decode('utf-8'))")
export AUTH_SECRET_KEY=$(openssl rand -hex 32)
export AUTH_TOKEN_EXPIRE_MINS=2
export AUTH_USER_PASSWORD_HASH=$BCRYPT_HASH
export AUTH_ADMIN_PASSWORD_HASH=$BCRYPT_HASH
