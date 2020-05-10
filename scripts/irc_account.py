#!/usr/bin/env python3

''' irc_account - IRC Account Registration

This script will login as the specified IRC operator in order to do the
following:

    1. Create a new IRC account (if it doesn't exist).

    2. Update the password for this account.

The script looks for the following environmental variables:

    USER_NICKNAME   This is the nickname for the IRC account.
    USER_PASSWORD   This is the password for the IRC account.

    OPER_NICKNAME   This is the nickname for the IRC operator account.
    OPER_PASSWORD   This is the nickname for the IRC operator account.

The USER_NICKNAME and USER_PASSWORD may be set via command line arguments:

    $ ./irc_account.py --nickname ExampleNick --password ExamplePassword

That said, it is recommended that you pass the parameters via the process
environment (so that noone can snoop passwords via the process table).

Note, the operator must have "accreg" capabilities (ie. it must be able to
execute /NS SAREGISTER).
'''

import asyncio
import argparse
import logging
import os
import sys

# Globals

IRC_HOST = 'localhost'
IRC_PORT = 6667

USER_NICKNAME = os.environ.get('USER_NICKNAME')
USER_PASSWORD = os.environ.get('USER_PASSWORD')

OPER_NICKNAME = os.environ.get('OPER_NICKNAME')
OPER_PASSWORD = os.environ.get('OPER_PASSWORD')

# Functions

async def register_account(nickname, password, host=IRC_HOST, port=IRC_PORT):
    # Connect to IRC Host and Port
    logging.info(f'Connecting to {host}:{port}')
    reader, writer = await asyncio.open_connection(host, port)
    
    # Authorization
    logging.info(f'Authorizing as {OPER_NICKNAME}')
    writer.write(f'USER {OPER_NICKNAME} 0 * :{OPER_NICKNAME}\r\n'.encode())
    writer.write(f'NICK {OPER_NICKNAME}\r\n'.encode())
    await writer.drain()

    authorized = False
    while not authorized and (data := await reader.readline()):
        authorized = '376' in data.decode()
    
    if not authorized:
        sys.exit(1)
    
    # Authentication
    logging.info(f'Authenticating with NickServ')
    writer.write(f'PRIVMSG NickServ :IDENTIFY {OPER_PASSWORD}\r\n'.encode())
    await writer.drain()

    authenticated = False
    while not authenticated and (data := await reader.readline()):
        authenticated = f'now logged in as {OPER_NICKNAME}' in data.decode()

    if not authenticated:
        sys.exit(2)
    
    # Privilege Elevation
    logging.info(f'Elevating Privilege')
    writer.write(f'OPER {OPER_NICKNAME} {OPER_PASSWORD}\r\n'.encode())
    await writer.drain()
    
    elevated = False
    while not elevated and (data := await reader.readline()):
        elevated = f'now an IRC operator' in data.decode()

    if not elevated:
        sys.exit(3)

    # Registration
    logging.info(f'Registering {nickname}')
    writer.write(f'PRIVMSG NickServ :SAREGISTER {nickname} {password}\r\n'.encode())
    writer.write(f'PRIVMSG NickServ :PASSWD {nickname} {password}\r\n'.encode())
    await writer.drain()
    
    registered = False
    exists     = False
    changed    = False
    while not registered and (data := await reader.readline()):
        exists     = exists  or f'Account already exists' in data.decode() \
                             or f'Successfully registered account' in data.decode()
        changed    = changed or f'Password changed' in data.decode()
        registered = exists and changed

    if not registered:
        sys.exit(4)

    logging.info(f'Disconnecting from {host}:{port}')
    writer.close()
    await writer.wait_closed()

    sys.exit(0)

# Main Execution

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description = 'Register IRC Nick and Password.',
        epilog      = 'Be sure to set the OPER_NICK and OPER_PASS environment variables.'
    )
    parser.add_argument('--host'    , default=IRC_HOST     , help='IRC Hostname')
    parser.add_argument('--port'    , default=IRC_PORT     , help='IRC Port', type=int)
    parser.add_argument('--nickname', default=USER_NICKNAME, help='User Nickname')
    parser.add_argument('--password', default=USER_PASSWORD, help='User Password')

    args = parser.parse_args()

    if not all([args.nickname, args.password, OPER_NICKNAME, OPER_PASSWORD]):
        parser.print_help()
        sys.exit(1)

    logging.basicConfig(
        format  = "[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d] %(message)s",
        datefmt = "%y%m%d %H:%M:%S",
        level   = logging.INFO,
    )

    try:
        asyncio.run(register_account(args.nickname, args.password, args.host, args.port))
    except KeyboardInterrupt:
        sys.exit(9)
