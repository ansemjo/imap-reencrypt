#!/usr/bin/python

# commandline arguments
import argparse
args = argparse.ArgumentParser()

args.add_argument('--search', action='store_true', help='search for encrypted messages on server')
args.add_argument('--folder', help='selected mailbox folder', default='INBOX')
args.add_argument('--list', help='show mailbox folders', action='store_true')
args.add_argument('--account', help='override used account')
args.add_argument('--subject', help='set subject to given text')

args = args.parse_args()

# configuration
import configparser

conf = configparser.ConfigParser()
conf.read('config.ini')

account = conf.defaults()['account'] # if args.account == None else args.account
server   = conf[account]['server']
username = conf[account]['user']
password = conf[account]['pass']

# reinserted message through context libs
import contextlib
import imaplib
import email

@contextlib.contextmanager
def ReinsertableMessage(session, mailbox, message_id):

  # select mailbox
  ok, response = session.select(mailbox)
  if ok != 'OK': raise Exception(response)

  # fetch message and split response
  ok, response = session.fetch(str(message_id), '(FLAGS INTERNALDATE RFC822)')
  if ok != 'OK': raise Exception(response)
  metadata = response[0][0]
  rfcbody  = response[0][1]

  # parse flags, date and message body
  flags = ' '.join([f.decode() for f in imaplib.ParseFlags(metadata)])
  date = imaplib.Internaldate2tuple(metadata)
  mail = email.message_from_bytes(rfcbody)

  # yield mail for editing
  yield mail

  # append edited message to mailbox
  session.append(mailbox, flags, date, mail.as_bytes())

  # delete old message
  session.store(message_id, '+FLAGS', '\\DELETED')
  #session.expunge()

# GnuPG
import gnupg
gpg = gnupg.GPG(use_agent=True)

# pgp message tags
PGP_BEGIN = '-----BEGIN PGP MESSAGE-----\r\n'
PGP_END = '-----END PGP MESSAGE-----\r\n'

# split a message at PGP boundaries
def split_pgp_message(message):
  start = message.find(PGP_BEGIN)
  end = message.find(PGP_END) + len(PGP_END)
  return ((message[:start], message[end:]), message[start:end])

# open imap mailbox
with imaplib.IMAP4_SSL(server) as m:

  m.login(username, password)
  typ, messages = m.select(f'"{args.folder}"', readonly=True)
  if typ != 'OK':
    raise Exception(messages[0].decode())

  if args.list:
    folders = '\n'.join([f.decode() for f in m.list()[1]])
    print(f'Mailbox folders:\n{folders}')

  else:

    if args.search:

      print(f'Searching for encrypted messages in {args.folder} ...')

      ok, res = m.search(None, '(HEADER Content-Type "pgp-encrypted")')
      if ok == 'OK':
        mime = res[0].decode().split()
        print(mime)
        print('pgp/mime :', ', '.join(mime))

      ok, res = m.search(None, f'(BODY "-----BEGIN PGP MESSAGE-----")')
      if ok == 'OK':
        inline = res[0].decode().split()
        print(inline)
        print('inline   :', ', '.join(inline))

      def pgp_parts(payload):
        if PGP_BEGIN in payload:
          bounds, pgp = split_pgp_message(payload)
          decr = gpg.decrypt(pgp)
          if decr: print(decr.data)

      for msgid in mime + inline:

        with ReinsertableMessage(m, 'INBOX', msgid) as msg:
          payload = msg.get_payload()
          if isinstance(payload, list):
            for idx, pl in enumerate(payload):
              print(f'---------- PART {idx} ------------')
              pgp_parts(pl.get_payload())
          else:
            pgp_parts(payload)

      m.expunge()


    else:

      msgid = input('Enter message ID: ')
      ok, msg = m.fetch(msgid, '(RFC822)')

      if ok == 'OK':
        print(msg[0][1].decode())


    # append to subject line
    if args.subject:
      with ReinsertableMessage(m, 'INBOX', msgid) as msg:

        #subj = msg['Subject']
        del msg['Subject']
        msg['Subject'] = args.subject



