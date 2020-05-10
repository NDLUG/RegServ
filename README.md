# RegServ - Registration Service

This is a simple registration service for the [NDLUG] IRC server at
[chat.ndlug.org](chat.ndlug.org).

## Requirements

- Python3.8+
- Tornado 5.1+

## Configuration

For `scripts/irc_account.py` to work, you will need to define the following
environmental variables:

- `OPER_NICKNAME`: This is the **nickname** of the operator account who has the
  ability to register new accounts.
  
- `OPER_PASSWORD`: This is the **password** of the operator account who has the
  ability to register new accounts.
  
    **Note**: This assumes the **password** of the operator's IRC account is
    the same as the `/oper` password (which doesn't necessary need to be true,
    but this is a simplification we have made).

## Todo

- [ ] Add default [NDLUG] network to new [The Lounge] accounts.
    - [ ] Save password to configuration.
    
- [ ] Add service scripts to run registration service.

- [ ] Add more documenation.

- [ ] Fix hard-coded paths (a few).

[NDLUG]:            https://ndlug.org
[Oragono]:          https://oragono.io
[The Lounge]:       https://thelounge.chat
