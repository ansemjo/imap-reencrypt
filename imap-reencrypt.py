#!/usr/bin/env python

# Copyright 2018 Anton Semjonov
# SPDX-License-Identiter: MIT

# local library
from lib.config import get_imap_configuration as config
from lib import imap

# system imports
import imaplib
import argparse
import gnupg

# parse commandline arguments
args = argparse.ArgumentParser()

args.add_argument('--config', help='Configuration file.', type=argparse.FileType('r'), default='config.ini')
args.add_argument('--dry-run', action='store_true', help='Perform a dry-run. Do not change mails on server.')
args.add_argument('--mailbox', help='Select Mailbox folder.', default='INBOX')
args.add_argument('--account', help='Select account from config.ini file.')

grp_mode = args.add_argument_group('tasks')
exl_mode = grp_mode.add_mutually_exclusive_group(required=True)
exl_mode.add_argument('--single', help='Show a single message.', metavar='MSGNUM', type=int)
exl_mode.add_argument('--search', help='Search for encrypted messages on server.', action='store_true')
grp_mode.add_argument('--repack', help='Re-encrypt messages after searching or single selection.', action='store_true')
exl_mode.add_argument('--list', help='List Mailbox folders.', action='store_true')

grp_gpg = args.add_argument_group('gpg key selection')
grp_gpg.add_argument('--delkey', metavar='FNGPRNT', action='append', help='Remove keys from recipient list. (multi)', default=[])
grp_gpg.add_argument('--addkey', metavar='FNGPRNT', action='append', help='Add keys to recipient list. (multi)', default=[])
grp_gpg.add_argument('--del-all-keys', action='store_true', help='Clear recipient list before adding with --addkey.')
grp_gpg.add_argument('--only-for', metavar='FNGPRNT', help='Only repack messages that were encrypted to this key.')
grp_gpg.add_argument('--always-trust', action='store_true', help='Always trust the recipient keys and skip trust validation.')


args = args.parse_args()

# get configuration and initialize gpg
server, username, password = config(args.config, args.account)
gpg = gnupg.GPG(use_agent=True)
mailbox = imap.quoted_mailbox(args.mailbox)

# open imap mailbox
with imap.session(server, username, password) as session:

  # LIST ALL FOLDERS
  if args.list:
    print(imap.ls(session))

  # SEARCH AND DISPLAY ENCRYPTED MESSAGES
  if args.search:
    
    print(f'Searching for encrypted messages in {mailbox} ...')
    mime, inline = imap.search_encrypted(session, mailbox)
    msglist = mime + inline

    print('pgp/mime :', ', '.join(mime))
    print('inline   :', ', '.join(inline))

  # SHOW A SINGLE MESSAGE
  if args.single:
    if not args.repack:
      print(imap.fetch(session, mailbox, str(args.single)))
    msglist = [str(args.single)]

  # ALSO RE-ENCRYPT MESSAGES
  if args.repack:
    imap.repack_pgp(session, gpg, mailbox, msglist,
      args.delkey, args.addkey, args.del_all_keys, args.only_for, args.dry_run,
      args.always_trust)

