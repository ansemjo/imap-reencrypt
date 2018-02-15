# reinserted message through context libs
import contextlib
import imaplib
import email

from lib.consolecolor import color

@contextlib.contextmanager
def Mail(session, mailbox, message_id, expunge=False):

  # select mailbox
  ok, response = session.select(mailbox)
  if ok != 'OK': raise Exception(response)

  # fetch message and split response
  ok, response = session.fetch(str(message_id),
    '(FLAGS INTERNALDATE RFC822)')
  if ok != 'OK': raise Exception(response)

  metadata = response[0][0]
  rfcbody  = response[0][1]

  # parse flags, date and message body
  flags = ' '.join([f.decode() for f in imaplib.ParseFlags(metadata)])
  date = imaplib.Internaldate2tuple(metadata)
  mail = email.message_from_bytes(rfcbody)

  # debug
  with color('34'):
    print('From    :', mail['From'])
    print('Subject :', mail['Subject'])

  # yield mail for editing
  state = { 'mail': mail, 'dirty': False }
  yield state

    # if message was edited, append to mailbox and
  # set deletion flag on old message
  if state['dirty'] == True:
    print('Message dirty. Reuploading ..')
    session.append(mailbox, flags, date, mail.as_bytes())
    session.store(message_id, '+FLAGS', '\\DELETED')

    # optionally directly expunge
    if expunge: session.expunge()


# USAGE:
# # append to subject line
# if args.subject:
#   with ReinsertableMessage(m, 'INBOX', msgid) as msg:
#     del msg['Subject']
#     msg['Subject'] = args.subject
