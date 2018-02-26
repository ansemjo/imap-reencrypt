# imap-reencrypt.py

Assume that you want to reencrypt all E-Mail in your IMAP mailbox
for another key because you are rotating keys but do not want to lose
access to old messages .. or because you've lost your offline master
and the keys stored on your YubiKey expired. :P

This script goes through an entire mailbox folder, searching for some
signs that a message is PGP encrypted, decrypts it and then stores a
new copy, encrypted to your chosen new key online with the exact
same metadata as the original one.

## Requirements

Python modules:
- [`python-gnupg`](https://pypi.python.org/pypi/python-gnupg/0.4.1) (Not the `isislovecruft` fork.)
- various built-in modules in Python 3.5+

## WARNING

I have written this script solely for my own, personal use. I shall _not_
be liable for any damage done to your email! The error handling is
probably flaky at best ..

If in doubt, always use `--dry-run` and make sure you do not hit any
exceptions. Then rerun without that flag.

## License

This project is licensed under the MIT license.

## Usage

### Configuration

First of all the script needs some information how to connect to your
IMAP server. This is done in a file `config.ini` next to the script:

```
$ cat config.ini 
[DEFAULT]
account = myaccount

[myaccount]
server = mail.yourdomain.com
username = info@yourdomain.com
password = mySuperSecurePassword

[myotheraccount]
server = mail.yourotherdomain.com
username = info@yourotherdomain.com
password = myOtherSuperSecurePassword
```

You can enter multiple accounts and the `account` variable in the
DEFAULT section shall point to your preferred one. Otherwise you
can chose the account to be used by passing a `--account SECTION`
flag to the script, where `SECTION` is the corresponding section
name in the configuration file.

### Mailbox

Next you need to find the correct mailbox name, which you want to
use. Use the `--list` flag to display all mailbox names:

```
$ ./imap-reencrypt.py --list
Mailbox folders:
INBOX (\HasChildren)
INBOX.Trash (\HasNoChildren \Trash)
INBOX.Sent (\HasNoChildren \Sent)
INBOX.Junk (\HasNoChildren)
INBOX.Drafts (\HasNoChildren \Drafts)
```
If you want to use something other than `INBOX` you need to pass
the `--mailbox MAILBOX` flag to the script later.

### Searching messages

Now you can search for encrypted messages in your mailbox with the
`--search` flag:

```
$ ./imap-reencrypt.py [...] --search
Searching for encrypted messages in "INBOX" ...
pgp/mime : 4, 5
inline   : 6, 7
```

_Note:_ Replace `[...]` with your appropriate mailbox and account
flags, if required.

This searches for encrypted messages on the server by looking for
messages with the `Content-Type: pgp-encrypted` header (`mime`) or
the PGP message begin tag in its body (`inline`).

If you want to verify, you can show a single message by using
`$ ./imap-reencrypt.py [...] --single MSGNUM`, where `MSGNUM` is the
message number in this mailbox.

### Re-encrypt

To actually perform decryption and re-encryption, you need to pass
the `--repack` flag. The GnuPG library tries to use a running agent
and uses the default gnupghome, which is usually `~/.gnupg/`.

Make sure that all keys to which you want to encrypt are trusted.
Otherwise an unhandled exception is thrown. Or use `--always-trust`
to blindly trust all recipient keys.

You can configure the new recipients by using `--delkey`, `--addkey`,
`--del-all-keys` and `--only-for`. The former two can be used multiple
times to add or remove multiple keys. By default, the script tries to
encrypt to all the original recipients of a message. If you want to
exclude a certain key (e.g. because that key is expired), then
blacklist it with `--delkey`. You can also skip the default list and
completely clear the recipients with `--del-all-keys`. You then need
to add recipient keys with `--addkey` manually.

The `--only-for` flag compares the original recipient list after
decryption and only takes any further steps if the given keygrip was
part of the original recipient list. It does not mean, that the
message will be re-encrypted to this key!

All flags expecting a `KEYGRIP` require a full-length fingerprint
with no spaces. For example, for my YubiKey key that would be
`B1046F23C2742782DF1C7B27CE47E7C938D5209D`:

```
$ gpg --list-secret-keys 
/home/ansemjo/.gnupg/pubring.kbx
--------------------------------
sec#  rsa3808 2015-11-21 [SC] [expires: 2020-01-01]
      B1046F23C2742782DF1C7B27CE47E7C938D5209D
uid           [ultimate] Anton Semjonov (main) <redacted>
uid           [ultimate] Anton Semjonov (university) <redacted>
```

You always need to combine `--repack` with either `--search` or
`--single`. After a search, it loops over all the messages that
it found automatically. And if you give a single message ID, then
only that message is re-encrypted.

### Example

An example with which I reencrypted one of my mailboxes:

```
$ ./imap-reencrypt.py [...] --search --repack --delkey $my_yubi --delkey $my_smart --addkey $my_rsa --only-for $my_yubi
```

Where `$my_yubi`, `$my_smart` and `$my_rsa` are fingerprints for
three of my keys. It operated only on messages that were encrypted
to my YubiKey, deleted my YubiKey and an old Smartcard from the
recipients and added my default RSA key to the recipient list,
while keeping all the other original recipients as well.

### Help

You can always run `--help` for a full and up-to-date help,
generated by `argparse`:

```
$ date --utc --iso=seconds
2018-02-26T13:39:04+00:00
$ ./imap-reencrypt.py --help
usage: imap-reencrypt.py [-h] [--dry-run] [--mailbox MAILBOX]
                         [--account ACCOUNT] [--single MSGNUM] [--search]
                         [--repack] [--list] [--delkey KEYGRIP]
                         [--addkey KEYGRIP] [--del-all-keys]
                         [--only-for KEYGRIP] [--always-trust]

optional arguments:
  -h, --help          show this help message and exit
  --dry-run           Perform a dry-run. Do not change mails on server.
  --mailbox MAILBOX   Select Mailbox folder.
  --account ACCOUNT   Select account from config.ini file.

tasks:
  --single MSGNUM     Show a single message.
  --search            Search for encrypted messages on server.
  --repack            Re-encrypt messages after searching or single selection.
  --list              List Mailbox folders.

gpg key selection:
  --delkey KEYGRIP    Remove keys from recipient list. (multi)
  --addkey KEYGRIP    Add keys to recipient list. (multi)
  --del-all-keys      Clear recipient list before adding with --addkey.
  --only-for KEYGRIP  Only repack messages that were encrypted to this key.
  --always-trust      Always trust the recipient keys and skip trust
                      validation.
```
