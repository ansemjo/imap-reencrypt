# imap-reencrypt.py

Assume that you want to reencrypt all E-Mail in your IMAP mailbox for another key, because ...

- you are rotating keys but do not want to lose access to old messages
- you've lost your offline master and the keys stored on your YubiKey expired
- for whatever other reason you cannot recertify an expired key
- have a group mailbox which multiple persons should be able to read but you do not want to share a
  key

This script goes through an entire mailbox folder, searching for signs that a message is PGP
encrypted. It decrypts each message and then stores a new copy - encrypted to your chosen set of
keys - with the exact same metadata as the original one.

## requirements

Python modules:

- [`python-gnupg`](https://pypi.python.org/pypi/python-gnupg/0.4.1) (not the `isislovecruft` fork)
- various built-in modules in Python 3.5+

## WARNING

I have written this script solely for my own, personal use. I shall _not_ be liable for any damage
done to your email! The error handling is probably flaky at best ..

If in doubt, always use `--dry-run` and make sure you do not hit any exceptions. Then rerun without
that flag.

## usage

### configuration

First of all the script needs some information how to connect to your IMAP server. This is done in a
file `config.ini` next to the script (you can also specify a different path with the `--config`
flag):

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

You can enter multiple accounts and the `account` variable in the DEFAULT section shall point to
your preferred one. Otherwise you can chose the account to be used by passing a `--account SECTION`
flag to the script, where `SECTION` is the corresponding section name in the configuration file.

### Mailbox

Next you need to find the correct mailbox name, which you want to use. Use the `--list` flag to
display all mailbox names:

```
$ ./imap-reencrypt.py --list
Mailbox folders:
INBOX
INBOX.Trash
INBOX.Sent
INBOX.Junk
INBOX.Drafts
```

If you want to use something other than `INBOX` you need to pass the `--mailbox MAILBOX` flag to the
script later.

### Searching messages

Now you can search for encrypted messages in your mailbox with the `--search` flag:

```
$ ./imap-reencrypt.py [...] --search
Searching for encrypted messages in "INBOX" ...
pgp/mime : 4, 5
inline   : 6, 7
```

_Note:_ Replace `[...]` with your appropriate mailbox and account flags, if required.

This searches for encrypted messages on the server by looking for messages with the
`Content-Type: pgp-encrypted` header (`mime`) or the PGP message begin tag in its body (`inline`).

If you want to verify, you can show a single message by using
`$ ./imap-reencrypt.py [...] --single UID`, where `UID` is the message uid in this mailbox.

### Re-encrypt

To actually perform decryption and re-encryption, you need to pass the `--repack` flag. The GnuPG
library tries to use a running agent and uses the default gnupghome, which is usually `~/.gnupg/`.

Make sure that all keys to which you want to encrypt are trusted. Otherwise an unhandled exception
is thrown. Or use `--always-trust` to blindly trust all recipient keys.

You can configure the new recipients by using `--delkey`, `--addkey`, `--del-all-keys` and
`--only-for`. The former two can be used multiple times to add or remove multiple keys. By default,
the script tries to encrypt to all the original recipients of a message. If you want to exclude a
certain key (e.g. because that key is expired), then blacklist it with `--delkey`. You can also skip
the default list and completely clear the recipients with `--del-all-keys`. You then need to add
recipient keys with `--addkey` manually.

The `--only-for` flag compares the original recipient list after decryption and only takes any
further steps if the given fingerprint was part of the original recipient list. It does not mean,
that the message will be re-encrypted to this key!

**Note:** if the original and the newly constructed recipient sets are identical for a message it is
skipped and will not be re-encrypted.

All flags expecting a `FNGPRNT` require a full-length fingerprint with no spaces. For example, for
my YubiKey key that would be `B1046F23C2742782DF1C7B27CE47E7C938D5209D`:

```
$ gpg --list-secret-keys
/home/ansemjo/.gnupg/pubring.kbx
--------------------------------
sec#  rsa3808 2015-11-21 [SC] [expires: 2020-01-01]
      B1046F23C2742782DF1C7B27CE47E7C938D5209D
uid           [ultimate] Anton Semjonov (main) <redacted>
uid           [ultimate] Anton Semjonov (university) <redacted>
```

You always need to combine `--repack` with either `--search` or `--single`. After a search, it loops
over all the messages that it found automatically. And if you give a single message ID, then only
that message is re-encrypted.

### Example

An example with which I reencrypted one of my mailboxes:

```
$ ./imap-reencrypt.py [...] --search --repack \
  --delkey $my_yubi \
  --delkey $my_smart \
  --addkey $my_rsa \
  --only-for $my_yubi
```

Where `$my_yubi`, `$my_smart` and `$my_rsa` are fingerprints for three of my keys. It operated only
on messages that were encrypted to my YubiKey, deleted my YubiKey and an old Smartcard from the
recipients and added my default RSA key to the recipient list, while keeping all the other original
recipients as well.

### help

You can always run `./imap-reencrypt.py --help` for a full and up-to-date argument help.

## LICENSE

This project is licensed under the MIT license.
