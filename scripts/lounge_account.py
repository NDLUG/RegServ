#!/usr/bin/env python3

''' lounge_account - Lounge Account Registration

This script will do the following

    1. Create a new Lounge account (if it doesn't exist).

    2. Update the password for this account.

The script looks for the following environmental variables:

    USER_NICKNAME   This is the nickname for the IRC account.
    USER_PASSWORD   This is the password for the IRC account.

The USER_NICKNAME and USER_PASSWORD may be set via command line arguments:

    $ ./LougeServ.py --nickname ExampleNick --password ExamplePassword

That said, it is recommended that you pass the parameters via the process
environment (so that noone can snoop passwords via the process table).

Note, the script requires permissions to the Lounge data.
'''

import argparse
import logging
import os
import sys

import pexpect

# Globals

USER_NICKNAME  = os.environ.get('USER_NICKNAME')
USER_PASSWORD  = os.environ.get('USER_PASSWORD')
LOUNGE_UID     = os.environ.get('LOUNGE_UID', 'node')
LOUNGE_GID     = os.environ.get('LOUNGE_GID', 'node')
LOUNGE_COMMAND = f'docker exec --user {LOUNGE_UID}:{LOUNGE_GID} -it thelounge thelounge'
LOUNGE_DATADIR = '/data/thelounge'

# Functions

def register_account(nickname, password):
    json_path = os.path.join(LOUNGE_DATADIR, 'users', f'{nickname}.json')

    # Create account if it doesn't exist yet
    if not os.path.exists(json_path):
        logging.info(f'Creating the lounge account for {nickname}')
        process = pexpect.spawn(f'{LOUNGE_COMMAND} add {nickname}')
        process.expect('.*Enter password:.*')
        process.sendline(password)
        process.expect('.*Save logs to disk.*')
        process.sendline('yes')
        process.wait()

    if not os.path.exists(json_path):
        sys.exit(1)

    # Update password
    logging.info(f'Updating the lounge password for {nickname}')
    process = pexpect.spawn(f'{LOUNGE_COMMAND} reset {nickname}')
    process.expect('.*Enter new password:.*')
    process.sendline(password)
    process.wait()

    sys.exit(0)

# Main Execution

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description = 'Register IRC Nick and Password.'
    )
    parser.add_argument('--nickname', default=USER_NICKNAME, help='User Nickname')
    parser.add_argument('--password', default=USER_PASSWORD, help='User Password')

    args = parser.parse_args()

    if not all([args.nickname, args.password]):
        parser.print_help()
        sys.exit(1)

    logging.basicConfig(
        format  = "[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d] %(message)s",
        datefmt = "%y%m%d %H:%M:%S",
        level   = logging.INFO,
    )

    try:
        register_account(args.nickname, args.password)
    except KeyboardInterrupt:
        sys.exit(9)
