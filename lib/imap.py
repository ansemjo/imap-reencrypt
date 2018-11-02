# Copyright 2018 Anton Semjonov
# SPDX-License-Identiter: MIT

import imaplib
import contextlib
import re
from lib.mail import Mail
from lib import gpgmessage
from lib.consolecolor import color, COLOR

# imap session context
@contextlib.contextmanager
def session(server, username, password):
    with imaplib.IMAP4_SSL(server) as connection:
        connection.login(username, password)
        yield connection


# quote mailbox string
quoted_mailbox = lambda m: f'"{m}"' if m[0] != '"' or m[-1] != '"' else m

# change / select mailbox
def cd(session, mailbox):
    ok, response = session.select(mailbox)
    if ok != "OK":
        raise Exception(response[0].decode())


# list all folders
def ls(session):
    folders = session.list()[1]
    folders = '\n'.join((re.sub(r"^\([^)]+\)\s\".\"\s", "", f.decode()) for f in folders))
    return f"Mailbox folders:\n{folders}"


# fetch a single message
def fetch(session, mailbox, uid):
    cd(session, mailbox)
    ok, response = session.uid('fetch', uid, "(RFC822)")
    if ok == "OK":
        return response[0][1].decode()


# search for encrypted messages
def search_encrypted(session, mailbox):

    cd(session, mailbox)

    # empty fallback
    mime = inline = []

    # search for PGP/MIME messages
    ok, res = session.uid('search', None, '(HEADER Content-Type "pgp-encrypted")')
    if ok == "OK":
        mime = res[0].decode().split()

    # search for inline messages (boundaries in body)
    ok, res = session.uid('search', None, f'(BODY "-----BEGIN PGP MESSAGE-----")')
    if ok == "OK":
        inline = res[0].decode().split()

    return (mime, inline)


# reencrypt messages for a new key and reupload
def repack_pgp(
    session, gpg, mailbox, msglist, delkeys, addkeys, del_all_keys, only=None, dryrun=True, always_trust=False
):

    # recursive repack for plaintext or pgp/mime payloads
    def repack(message):
        payload = message.get_payload()
        if isinstance(payload, list):
            for p in payload:
                repack(p)
        else:
            newp = gpgmessage.repack(gpg, payload, delkeys, addkeys, del_all_keys, only, always_trust)
            message.set_payload(newp)

    try:
        # iterate over all messages
        for msgid in msglist:

            with Mail(session, mailbox, msgid) as mail:
                try:
                    email = mail["mail"]
                    repack(email)
                    if dryrun:
                        print(mail["mail"])
                    if not dryrun:
                        mail["dirty"] = True
                    with color(COLOR.GREEN):
                        print("Repack OK.")
                except gpgmessage.NoSecretKeyError:
                    with color(COLOR.RED):
                        print("No matching secret key. Skip.")
                    mail["dirty"] = False
                except gpgmessage.RecipientError:
                    with color(COLOR.YELLOW):
                        print("Given key was not a recipient. Skip.")
                    mail["dirty"] = False

    finally:
        if not dryrun:
            session.expunge()
