import imaplib
import contextlib
from lib.mail import Mail
from lib import gpgmessage

# imap session context
@contextlib.contextmanager
def session(server, username, password):
  with imaplib.IMAP4_SSL(server) as connection:
    connection.login(username, password)
    yield connection

# escape mailbox string
escape_mailbox = lambda mailbox: f'"{mailbox}"'

# change / select mailbox
def cd(session, mailbox):
  ok, response = session.select(mailbox)
  if ok != 'OK':
    raise Exception(response[0].decode())

# list all folders
def ls(session):
  folders = [f.decode() for f in session.list()[1]]
  folders = [' '.join([p.strip() for p in reversed(f.split('"."'))]) for f in folders]
  folders = '\n'.join(folders)
  return f'Mailbox folders:\n{folders}'

# fetch a single message
def fetch(session, msgid=None):
  if msgid == None:
    msgid = input('Enter message ID: ')
  ok, response = session.fetch(msgid, '(RFC822)')
  if ok == 'OK':
    return(response[0][1].decode())

# search for encrypted messages
def search_encrypted(session, mailbox):
  
  cd(session, mailbox)
  
  # empty fallback
  mime = inline = []

  # search for PGP/MIME messages
  ok, res = session.search(None, '(HEADER Content-Type "pgp-encrypted")')
  if ok == 'OK': mime = res[0].decode().split()

  # search for inline messages (boundaries in body)
  ok, res = session.search(None, f'(BODY "-----BEGIN PGP MESSAGE-----")')
  if ok == 'OK': inline = res[0].decode().split()

  return (mime, inline)

# reencrypt messages for a new key and reupload
def repack_pgp(session, gpg, mailbox, msglist,
  delkeys, addkeys, only=None, dryrun=True):

  # recursive repack for plaintext or pgp/mime payloads
  def repack(message):
    payload = message.get_payload()
    if isinstance(payload, list):
      for p in payload: repack(p)
    else:
      newp = gpgmessage.repack(gpg, payload, delkeys, addkeys, only)
      message.set_payload(newp)

  # iterate over all messages
  for msgid in msglist:

    with Mail(session, mailbox, msgid) as mail:
      email = mail['mail']
      repack(email)
      if dryrun: print(mail['mail'])
      if not dryrun: mail['dirty'] = True

  if not dryrun: session.expunge()