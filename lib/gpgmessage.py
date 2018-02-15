import gnupg
import re
import sys
from lib.consolecolor import color, COLOR

# constants
TAG_BEGIN = '-----BEGIN PGP MESSAGE-----\r\n'
TAG_END   = '-----END PGP MESSAGE-----\r\n'
NO_SECKEY = 'decryption failed: No secret key'

# custom exceptions
#sys.tracebacklimit = 0
class DecryptionError(Exception): pass
class NoSecretKeyError(Exception): pass
class EncryptionError(Exception): pass
class RecipientError(Exception): pass

# split a message at PGP boundaries
def message_split(message):
  start = message.find(TAG_BEGIN)
  end = message.find(TAG_END) + len(TAG_END)
  return (message[start:end], (message[:start], message[end:]))

# splice parts back together
def message_splice(inner, outer):
  return ''.join([outer[0], inner, outer[1]])

# decrypt a message and parse recipient keys
def decrypt(gpg, message):
  d = gpg.decrypt(message)

  # if decryption successful
  if d.ok:
    d.recipients = set(re.findall(r'KEY_CONSIDERED ([A-F0-9]+)', d.stderr))

    # output original recipients
    with color(COLOR.TEAL):
      print('Old Recipients:', '\n'.join(d.recipients))

    # return crypto object
    return d

  # if unsuccessful, raise exception
  else:
    if NO_SECKEY in d.stderr:
      key = re.search(r'gpg: encrypted with [^\n]*', d.stderr)
      raise NoSecretKeyError(key[0] if key else None)
    else:
      raise DecryptionError(d.status)


# encrypt a message for an augmented recipient list
def reencrypt(gpg, decr, delkeys, newkeys):

  # remove from / add keys to recipient set
  r = decr.recipients
  r -= set(delkeys)
  r |= set(newkeys)
  
  # output new set
  with color(COLOR.YELLOW):
    print('New Recipients:', '\n'.join(r))

  # encrypt
  encr = gpg.encrypt(str(decr), r)

  # return object or raise error
  if encr.ok:
    return encr
  else:
    raise EncryptionError(encr.status)
  

# combine the above two functions
def repack(gpg, message, delkeys, newkeys, onlyfor=None):

  # check for PGP tags
  if TAG_BEGIN in message and TAG_END in message:

    # split message
    inner, outer = message_split(message)

    # decrypt, optionally check if we are a recipient and reecnrypt
    crypt = decrypt(gpg, inner)
    if onlyfor != None and onlyfor not in crypt.recipients:
      raise RecipientError('not for intended recipient')
    crypt = reencrypt(gpg, crypt, delkeys, newkeys)

    # return respliced message
    return message_splice(str(crypt), outer)

  # just return input if tags not found
  else:
    return message
