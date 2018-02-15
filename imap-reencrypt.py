#!/usr/bin/python

# local library
from lib.config import get_imap_configuration
from lib.mail import Mail
import lib.gpg as gpg

# system imports
import imaplib
import argparse

# parse commandline arguments
args = argparse.ArgumentParser()
args.add_argument('--search', action='store_true', help='search for encrypted messages on server')
args.add_argument('--folder', help='selected mailbox folder', default='INBOX')
args.add_argument('--list', help='show mailbox folders', action='store_true')
args.add_argument('--account', help='override used account')
args = args.parse_args()

# get configuration
server, username, password = get_imap_configuration('config.ini', args.account)

# open imap mailbox
with imaplib.IMAP4_SSL(server) as session:

  # login
  session.login(username, password)

  # test opening mailbox
  mailbox = f'"{args.folder}"'
  typ, messages = session.select(mailbox, readonly=True)
  if typ != 'OK': raise Exception(messages[0].decode())

  # LIST ALL FOLDERS
  if args.list:
    folders = '\n'.join([f.decode() for f in session.list()[1]])
    print(f'Mailbox folders:\n{folders}')

  # SEARCH AND DISPLAY ENCRYPTED MESSAGES
  elif args.search:
    print(f'Searching for encrypted messages in {args.folder} ...')
    mime = inline = []

    # search for PGP/MIME messages
    ok, res = session.search(None, '(HEADER Content-Type "pgp-encrypted")')
    if ok == 'OK': mime = res[0].decode().split()

    # search for inline messages (boundaries in body)
    ok, res = session.search(None, f'(BODY "-----BEGIN PGP MESSAGE-----")')
    if ok == 'OK': inline = res[0].decode().split()
    
    print('pgp/mime :', ', '.join(mime))
    print('inline   :', ', '.join(inline))

    oldkey, newkey = (
      'B9F738A13373DB0D6CF5AA04BEBED18385323A4B',
      '16FF4A61A3E4E52F1A1D42903CEAD59D197D19A7',
    )

    def repack(message):
      payload = message.get_payload()
      if isinstance(payload, list):
        for p in payload:
          repack(p)
      else:
        n = gpg.repack(payload, [oldkey], [newkey])
        message.set_payload(n)

    # iterate over all found messages
    for msgid in mime + inline:

      with Mail(session, mailbox, msgid) as mail:
        email = mail['mail']
        repack(email)
        print(mail['mail'])
        mail['dirty'] = True

    session.expunge()

  # SHOW A SINGLE MESSAGE
  else:

    msgid = input('Enter message ID: ')
    ok, msg = session.fetch(msgid, '(RFC822)')

    if ok == 'OK':
      print(msg[0][1].decode())



