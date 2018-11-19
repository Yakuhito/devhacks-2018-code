import json
import hashlib
import hmac
import pyg2fa
import sys
import random
import time
import string

random.seed(time.time())

def gethash(key, message):
	return hmac.new(str(key), str(message), hashlib.sha256).hexdigest()

def getRandomStr(N):
	return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase) for _ in range(N))

if len(sys.argv) != 3:
	print("Usage: python adduser.py [user] [pass]")
	exit(1)

usr = sys.argv[1]
pswd = sys.argv[2]

obj = json.loads(open("config.json", "r").read())
for u in obj["users"]:
	if usr == u["username"]:
		print("User already exists!")
		exit(1)
	
psalt = getRandomStr(16)
otp_seed = getRandomStr(16)

phash = gethash(psalt, pswd)

obj["users"].append({"username": usr, "otp_seed": otp_seed, "password_salt": psalt, "password_hash": phash})
open('config.json', 'w').write(json.dumps(obj))
print(pyg2fa.qrCodeURL(usr + "@devhacks", otp_seed))




