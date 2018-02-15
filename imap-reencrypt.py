#!/usr/bin/python

# local library
from lib.config import get_imap_configuration as config
from lib import imap

# system imports
import imaplib
import argparse
import gnupg

# parse commandline arguments
args = argparse.ArgumentParser()

args.add_argument('--dry-run', action='store_true', help='Perform a dry-run. Do not change mails on server.')
args.add_argument('--mailbox', help='Select Mailbox folder.', default='INBOX')
args.add_argument('--account', help='Select account from config.ini file.')

grp_mode = args.add_argument_group('tasks')
grp_mode.add_argument('--single', help='Show a single message.', type=int)
grp_mode.add_argument('--search', help='Search for encrypted messages on server.', action='store_true')
grp_mode.add_argument('--repack', help='Re-encrypt messages after searching or single selection.', action='store_true')
grp_mode.add_argument('--list', help='List Mailbox folders.', action='store_true')

grp_gpg = args.add_argument_group('gpg key selection')
grp_gpg.add_argument('--delkey', action='append', help='Remove keys from recipient list. (multi)', default=[])
grp_gpg.add_argument('--addkey', action='append', help='Add keys to recipient list. (multi)', default=[])
grp_gpg.add_argument('--only-for', help='Only repack messages encrypted to this key.')

args = args.parse_args()

# get configuration
server, username, password = config('config.ini', args.account)

# initialize gpg
gpg = gnupg.GPG(use_agent=True)

print(args)

# open imap mailbox
with imap.session(server, username, password) as session:

  # test opening mailbox
  mailbox = imap.escape_mailbox(args.mailbox)
  imap.cd(session, mailbox)

  # LIST ALL FOLDERS
  if args.list:
    print(imap.ls(session))

  # SEARCH AND DISPLAY ENCRYPTED MESSAGES
  elif args.search:
    
    print(f'Searching for encrypted messages in {mailbox} ...')
    mime, inline = imap.search_encrypted(session, mailbox)
    msglist = mime + inline

    print('pgp/mime :', ', '.join(mime))
    print('inline   :', ', '.join(inline))

    # ALSO RE-ENCRYPT MESSAGES
    if args.repack:

      imap.repack_pgp(session, gpg, mailbox, msglist,
        args.delkey, args.addkey, args.only_for, args.dry_run)

  # SHOW A SINGLE MESSAGE
  else:
    print(imap.fetch(session))
