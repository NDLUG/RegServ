# RegServ - Registration Service

This is a simple registration service for the [NDLUG] IRC server at
[chat.ndlug.org](https://chat.ndlug.org).

## Requirements

- Python3.8+
- Tornado 5.1+

## Configuration

### Scripts

For `scripts/irc_account.py` to work, you will need to define the following
environmental variables:

- `OPER_NICKNAME`: This is the **nickname** of the operator account who has the
  ability to register new accounts.
  
- `OPER_PASSWORD`: This is the **password** of the operator account who has the
  ability to register new accounts.
  
    **Note**: This assumes the **password** of the operator's IRC account is
    the same as the `/oper` password (which doesn't necessary need to be true,
    but this is a simplification we have made).
    
### Mail

To email users a registration link, `RegServ.py` currently uses [msmtp] to send
email. It assumes a configuration file at `config/msmtprc`.  Here is an example
configuration that uses [Gmail] as the transport service:

```
account gmail
auth on
tls on
tls_nocertcheck
host smtp.gmail.com
port 587
from MyRegServ@gmail.com
user MyRegServ@gmail.com
password MyPaSsW0Rd

account default : gmail
```

**Note**: For [Gmail] mail transport, you must configure it to allow for [Less
Secure Apps](https://support.google.com/accounts/answer/6010255?hl=en).

## Todo

- [ ] Add service scripts to run registration service.

- [ ] Add more documenation.

- [ ] Fix hard-coded paths (a few).

[NDLUG]:            https://ndlug.org/
[Oragono]:          https://oragono.io/
[The Lounge]:       https://thelounge.chat/
[msmtp]:            https://marlam.de/msmtp/
[gmail]:            https://gmail.com
