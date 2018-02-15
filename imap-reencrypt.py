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
args.add_argument('--search', action='store_true', help='search for encrypted messages on server')
args.add_argument('--repack', action='store_true', help='reencrypt messages after search')
args.add_argument('--dry-run', action='store_true', help='dry-run, do not change mails on server')
args.add_argument('--folder', help='selected mailbox folder', default='INBOX')
args.add_argument('--list', help='show mailbox folders', action='store_true')
args.add_argument('--account', help='override used account')
args = args.parse_args()

# get configuration
server, username, password = config('config.ini', args.account)

# initialize gpg
gpg = gnupg.GPG(use_agent=True)

# open imap mailbox
with imap.session(server, username, password) as session:

  # test opening mailbox
  mailbox = imap.escape_mailbox(args.folder)
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

      delkey, addkey = (
        '16FF4A61A3E4E52F1A1D42903CEAD59D197D19A7', # testing
        'B9F738A13373DB0D6CF5AA04BEBED18385323A4B', # another
      )

      imap.repack_pgp(session, gpg, mailbox, msglist,
        [delkey], [addkey], dryrun=args.dry_run)

  # SHOW A SINGLE MESSAGE
  else:
    print(imap.fetch(session))
