# Copyright 2018 Anton Semjonov
# SPDX-License-Identiter: MIT

import contextlib
import imaplib
import email

from lib.consolecolor import color, COLOR


@contextlib.contextmanager
def Mail(session, mailbox, message_uid, expunge=False):

    # select mailbox
    ok, response = session.select(mailbox)
    if ok != "OK":
        raise Exception(response)

    # fetch message and split response
    ok, response = session.uid('fetch', str(message_uid), "(FLAGS INTERNALDATE RFC822)")
    if ok != "OK":
        raise Exception(response)

    metadata = response[0][0]
    rfcbody = response[0][1]

    # parse flags, date and message body
    flags = " ".join([f.decode() for f in imaplib.ParseFlags(metadata)])
    date = imaplib.Internaldate2tuple(metadata)
    mail = email.message_from_bytes(rfcbody)

    # debug
    with color(COLOR.BLUE):
        print("Message UID:", mailbox, f"({message_uid})")
        print("From    :", mail["From"])
        print("Date    :", mail["Date"])
        print("Subject :", mail["Subject"])

    # yield mail for editing
    state = {"mail": mail, "dirty": False}
    yield state

    # if message was edited, append to mailbox and
    # set deletion flag on old message
    if state["dirty"] == True:
        with color(COLOR.RED):
            print("Message modified. Reuploading ..")
        session.append(mailbox, flags, date, mail.as_bytes())
        session.uid('store', message_uid, "+FLAGS", "\\DELETED")

        # optionally directly expunge
        if expunge:
            session.expunge()

