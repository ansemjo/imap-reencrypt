import gnupg
import re

from lib.consolecolor import color, COLOR

# initialize
gpg = gnupg.GPG(use_agent=True)

# constants
TAG_BEGIN = '-----BEGIN PGP MESSAGE-----\r\n'
TAG_END   = '-----END PGP MESSAGE-----\r\n'

# split a message at PGP boundaries
def split_pgp_message(message):
  start = message.find(TAG_BEGIN)
  end = message.find(TAG_END) + len(TAG_END)
  return (message[start:end], (message[:start], message[end:]))

# splice parts back together
def splice_pgp_message(inner, outer):
  return ''.join([outer[0], inner, outer[1]])

# decrypt a message and parse recipient keys
def decrypt(message):

  decrypted = gpg.decrypt(message)

  # if decryption successful
  if decrypted:
    decrypted.recipients = \
      set(re.findall(r'KEY_CONSIDERED ([A-F0-9]+)', decrypted.stderr))

    # output original recipients
    with color(COLOR.TEAL):
      print('Old Recipients:', '\n'.join(decrypted.recipients))

    # return crypt object
    return decrypted

  # otherwise show reason, if not successful
  else: print(decrypted.status)


# check if it was in fact encrypted for us and re-encrypt
# delete del_keyid from recipients and add
def reencrypt(crypt, del_keyids, new_keyids):

  # remove from / add keys to recipient list
  r = crypt.recipients
  r -= set(del_keyids)
  r |= set(new_keyids)
  r -= set(['80615870F5BAD690333686D0F2AD85AC1E42B367']) # Werner Koch
  recipients = list(r)
  
  with color(COLOR.YELLOW):
    print('New Recipients:', '\n'.join(recipients))

  encr = gpg.encrypt(str(crypt), recipients)
  if not encr.ok: raise ValueError(encr.status)
  
  return encr

# combine the above two functions
def repack(payload, delkeys, newkeys):

  # if pgp tag found, split message and reencrypt
  if TAG_BEGIN in payload:

    inner, outer = split_pgp_message(payload)

    crypt = decrypt(inner)
    crypt = reencrypt(crypt, delkeys, newkeys)

    return splice_pgp_message(str(crypt), outer)

  # otherwise just return payload
  else: return payload

