#!/usr/bin/env python3

import collections
import hashlib
import json
import logging
import os
import re
import socket
import sys
import time

import tornado.gen
import tornado.ioloop
import tornado.options
import tornado.process
import tornado.web

# Constants

REGSERV_ADDRESS	 = '127.0.0.1'
REGSERV_PORT     = 9667
REGSERV_URL      = 'https://regserv.ndlug.org'

HASHCODE_TIMEOUT = 60 * 60 # 1 Hour

# Functions

def checksum(s):
    return hashlib.sha1(s.encode()).hexdigest()

def is_valid_email(e):
    return re.match(r'.+@.+', e)    # TODO: improve regex

# Handlers

class RegServHandler(tornado.web.RequestHandler):

    @tornado.gen.coroutine
    def get(self, hashcode=None):
        if not hashcode:
            return self.render('index.html')

        if hashcode not in self.application.hashes:
            return self.render('error.html',
                summary     = 'Invalid Registration Link',
                description = f'''
The link you used is invalid.  Please return to the registration page to send a new link.
''')

        timestamp = self.application.hashes[hashcode].get('timestamp', 0)
        if (time.time() - timestamp) >= HASHCODE_TIMEOUT:
            del self.application.hashes[hashcode]
            self.application.checkpoint()

            return self.render('error.html',
                summary     = 'Expired Registration Link',
                description = f'''
The link you used has expired.  Please return to the registration page to send a new link.
''')

        email = self.application.hashes[hashcode].get('email')
        if not email:
            del self.application.hashes[hashcode]
            self.application.checkpoint()

            return self.render('error.html',
                summary     = 'Invalid Registration Link',
                description = f'''
The link you used does not have an associated email.  Please return to the registration page to try again.
''')
        return self.render('register.html', email=email)

    @tornado.gen.coroutine
    def post(self, hashcode=None):
        if hashcode == 'email':
            email = self.get_argument('email', None)
            if not is_valid_email(email):
                return self.render('error.html',
                    summary     = 'Invalid Registration Email', 
                    description = f'''
The email you used is invalid.  Please return to the registration page to try again.
''')

            if email not in self.application.emails:
                self.application.emails[email] = {'last_emailed': 0, 'nicks': []}

            last_emailed = self.application.emails[email].get('last_emailed', 0)
            if (time.time() - last_emailed) < HASHCODE_TIMEOUT:
                return self.render('error.html',
                    summary     = 'Already Sent Registration Link',
                    description = f'''
A registration link has already been sent.  Please check your mailbox for the link.
''')

            hashcode = checksum(f'{email} + {str(time.time())}')
            stream    = tornado.process.Subprocess.STREAM
            command   = ['msmtp', '-C' 'configs/msmtprc', email]
            process   = tornado.process.Subprocess(command, stdin=stream)
            result    = yield tornado.gen.Task(process.stdin.write,
                # TODO: Give deadline in human readable format
                # TODO: Make this parameterizable
                f'''Subject: [RegServ] Registration Link for chat.ndlug.org

Use the following link to create or reset an IRC account on chat.ndlug.org:

    {REGSERV_URL}/{hashcode}

This link will be valid for 1 hour.
'''.encode())
            process.stdin.close()
            try:
                yield process.wait_for_exit()
            except tornado.process.CalledProcessError as e:
                self.application.logger.error(e)
                return self.render('error.html',
                    summary     = 'Unable to Send Registration Link',
                    description = f'''
We were unable to send a registration link to <a href="mailto:{ email }">{ email }</a>:

<pre>
{ e }
</pre>
''')

            self.application.emails[email]['last_emailed'] = time.time()
            self.application.hashes[hashcode]              = {'email': email, 'timestamp': time.time()}
            self.application.checkpoint()

            return self.render('success.html',
                summary     = 'Registration Link Sent',
                description = f'''
A registration link was sent to <a href="mailto:{ email }">{ email }</a>.  This
link will expire within <b>one hour</b>.
''')

        elif hashcode in self.application.hashes:
            email = self.application.hashes[hashcode].get('email')
            if not email:
                return self.render('error.html',
                    summary     = 'Invalid Registration Link',
                    description = f'''
The link you used does not have an associated email.  Please return to the registration page to try again.
''')

            timestamp = self.application.hashes[hashcode].get('timestamp', 0)
            if (time.time() - timestamp) >= HASHCODE_TIMEOUT:
                return self.render('error.html',
                    summary     = 'Expired Registration Link',
                    description = f'''
The link you used has expired.  Please return to the registration page to send a new link.
''')

            nickname = self.get_argument('nickname', None)
            password = self.get_argument('password', None)

            if not password:
                return self.render('error.html',
                    summary     = 'Invalid Registration Password',
                    description = f'''
You must enter in a valid password.  Please try again.
''')

            # TODO: Check if nickname belongs to email address
            unclaimed = any(nickname.lower() in d['nicks'] for e, d in self.application.emails.items() if email != e)
            if unclaimed:
                # TODO: delete old hash
                return self.render('error.html',
                    summary     = 'Claimed Account',
                    description = f'''
The nickname you are trying to register or update is associated with another
email address.  Please register another nickname or use the appropriate email
address.
''')

            stream  = tornado.process.Subprocess.STREAM
            environ = dict(os.environ, **{'USER_NICKNAME': nickname, 'USER_PASSWORD': password})

            command = './scripts/irc_account.py'
            process = tornado.process.Subprocess(command, stderr=stream, env=environ)
            result1 = yield tornado.gen.Task(process.stderr.read_until_close)

            try:
                yield process.wait_for_exit()
            except tornado.process.CalledProcessError as e:
                self.application.logger.error(e)
                return self.render('error.html',
                    summary     = 'Unable to Register or Update IRC Account',
                    description = f'''
There was a problem registering or updating the IRC account:
<pre>
{ e }
</pre>
''')
            command = './scripts/lounge_account.py'
            process = tornado.process.Subprocess(command, stderr=stream, env=environ)
            result2 = yield tornado.gen.Task(process.stderr.read_until_close)

            try:
                yield process.wait_for_exit()
            except tornado.process.CalledProcessError as e:
                self.application.logger.error(e)
                return self.render('error.html',
                    summary     = 'Unable to Register or Update Lounge Account',
                    description = f'''
There was a problem registering or updating the Lounge account:
<pre>
{ e }
</pre>
<pre>
{ result2 }
</pre>
''')

            del self.application.hashes[hashcode]
            if nickname.lower() not in self.application.emails[email]['nicks']:
                self.application.emails[email]['nicks'].append(nickname.lower())
            self.application.emails[email]['last_emailed'] = 0
            self.application.checkpoint()

            return self.render('success.html',
                summary     = 'Account Registered or Updated',
                description = f'''
Congratulations! We have updated the account information for { nickname }.
Feel free to login to <a href="https://chat.ndlug.org">chat.ndlug.org</a>.

</p>
</div>

<div>
<p>
If this is your first time logging into the server, then you will need to make
the following changes in the initial <b>Network Settings</b> page as shown below:
</p>

<ol>
<li>Replace the <b><tt>Nick</tt></b> and <tt>Username</tt> fields with <b>{ nickname }</b>.
<li>Replace the <b><tt>Password</tt></b> field with the registered <b>password</b>.</li>
</ol>

<p class="text-center">
<img class="img-fluid img-thumbnail rounded" src="https://yld.me/raw/VjT.png">
''')
        else:
            return self.render('error.html',
                summary     = 'Invalid Registration Link',
                description = f'''
The link you used is invalid.  Please return to the registration page to send a new link.
''')

# Application

class RegServApplication(tornado.web.Application):

    def __init__(self, **settings):
        tornado.web.Application.__init__(self, template_path='templates', **settings)

        self.logger   = logging.getLogger()
        self.address  = settings.get('address') or self.address
        self.port     = settings.get('port')    or self.port

        try:
            # TODO: parameterize
            json_data   = json.load(open('data/RegServ.json'))
            self.emails = json_data.get('emails', {})
            self.hashes = json_data.get('hashes', {})
        except IOError:
            self.emails = {}
            self.hashes = {}

        self.add_handlers('.*', [
            (r'.*/(.*)', RegServHandler),
        ])

    def run(self):
        try:
            self.listen(self.port, self.address)
        except socket.error as e:
            self.logger.fatal(f'Unable to listen on {self.address}:{self.port} = {e}')
            sys.exit(1)

        self.logger.info(f'Listening on {self.address}:{self.port}')
        tornado.ioloop.IOLoop.current().start()

    def checkpoint(self):
        # TODO: parameterize
        with open('data/RegServ.json', 'w') as stream:
            json.dump({
                'emails': self.emails,
                'hashes': self.hashes,
            }, stream)

# Main Execution

if __name__ == '__main__':
    tornado.options.define('address', default=REGSERV_ADDRESS, help='Address to listen on.')
    tornado.options.define('port'   , default=REGSERV_PORT   , help='Port to listen on.')
    tornado.options.define('debug'  , default=False          , help='Enable debugging mode.')
    tornado.options.parse_command_line()

    options = tornado.options.options.as_dict()
    RegServ = RegServApplication(**options)
    RegServ.run()
