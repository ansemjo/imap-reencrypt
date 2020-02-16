# Copyright 2018 Anton Semjonov
# SPDX-License-Identiter: MIT

import gnupg
import re
import sys
from lib.consolecolor import color, COLOR

# constants
TAG_BEGIN = "-----BEGIN PGP MESSAGE-----\r\n"
TAG_END = "-----END PGP MESSAGE-----\r\n"
NO_SECKEY = "decryption failed: No secret key"

# custom exceptions
sys.tracebacklimit = 0
class DecryptionError(Exception): pass
class NoSecretKeyError(Exception): pass
class EncryptionError(Exception): pass
class RecipientError(Exception): pass


# split a message at PGP boundaries [mail --> pgppart, (header, trailing)]
def message_split(message):
    start = message.find(TAG_BEGIN)
    end = message.find(TAG_END) + len(TAG_END)
    return (message[start:end], (message[:start], message[end:]))


# splice parts back together [pgppart, (header, trailing) --> mail]
def message_splice(inner, outer):
    return "".join([outer[0], inner, outer[1]])


# decrypt a message and parse recipient keys
def decrypt(gpg, message):
    d = gpg.decrypt(message)

    # if decryption successful
    if (d.ok or (d.status == "signature valid" and d.valid)) and d.data != "":
        d.recipients = set(re.findall(r"KEY_CONSIDERED ([A-F0-9]+)", d.stderr))

        # output original recipients
        with color(COLOR.TEAL):
            print("Old Recipients:", "\n".join(d.recipients))

        # return crypto object
        return d

    # if unsuccessful, raise exception
    else:
        if NO_SECKEY in d.stderr:
            raise NoSecretKeyError("No secret key available.")
        else:
            raise DecryptionError(f'Could not decrypt message. GPG exited with message "{d.status}". STDERR:\n{d.stderr}')


# encrypt a message for an augmented recipient list
def reencrypt(gpg, decr, delkeys, newkeys, del_all_keys, always_trust):

    # save original recipients
    orig = decr.recipients.copy()

    # remove from / add keys to recipient set
    recp = decr.recipients if not del_all_keys else set([])
    recp -= set(delkeys)
    recp |= set(newkeys)

    # check if recipient sets are identical
    if orig == recp:
        raise RecipientError("Recipient sets are identical. Skip.")

    # output new set
    with color(COLOR.YELLOW):
        print("New Recipients:", "\n".join(recp))

    # encrypt
    encr = gpg.encrypt(str(decr), recp, always_trust=always_trust)

    # return object or raise error
    if encr.ok:
        return encr
    else:
        print(encr.stderr)
        raise EncryptionError(encr.status)


# combine the above two functions
def repack(gpg, message, delkeys, newkeys, del_all_keys=False, only_for=None, always_trust=False):

    # check for PGP tags
    if TAG_BEGIN in message and TAG_END in message:

        # split message
        inner, outer = message_split(message)

        # dirty hacks ..
        # if 'Charset: windows-1252' in inner or '(MingW32)' in inner:
        inner = inner.replace("=3D", "=")
        inner = inner.replace("=20\r\n", "\r\n")

        # decrypt, optionally check if we are a recipient and reecnrypt
        crypt = decrypt(gpg, inner)
        if only_for != None and only_for not in crypt.recipients:
            raise RecipientError("Not for the intended recipient. Skip.")
        crypt = reencrypt(gpg, crypt, delkeys, newkeys, del_all_keys, always_trust)

        # return respliced message
        return message_splice(str(crypt), outer)

    # just return input if tags not found
    else:
        return message


# further notes
#
# CHECK VALIDITY
# import time
# now = int(time.time())
# exp = gpg.search_keys(fingerprint)[0].get('expires')
# now < int(exp)
