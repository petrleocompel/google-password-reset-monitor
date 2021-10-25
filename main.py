import imapclient
from imapclient.exceptions import LoginError
from discord_webhook import DiscordWebhook, DiscordEmbed
import os
import os.path as path
import sys
import traceback
import logging
from logging.handlers import RotatingFileHandler
import configparser
import email
from time import sleep
from datetime import datetime, time

log = logging.getLogger('imap_monitor')
log.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
handler_stdout = logging.StreamHandler(sys.stdout)
handler_stdout.setLevel(logging.DEBUG)
handler_stdout.setFormatter(formatter)
log.addHandler(handler_stdout)

class GooglePassMonitor:
    def __init__(self):
        # Retrieve IMAP host - halt script if section 'imap' or value
        self.host = os.getenv('MAIL_HOST', None)
        if self.host is None:
            log.critical('no IMAP host specified in configuration file')
            exit(1)

        self.username = os.getenv('MAIL_LOGIN', None)
        if self.username is None:
            log.critical('no IMAP login specified in configuration file')
            exit(1)

        # Retrieve IMAP password - halt script if missing
        self.password = os.getenv('MAIL_PASS', None)
        if self.password is None:
            log.critical('no IMAP password specified in configuration file')
            exit(1)

        # Retrieve IMAP SSL setting - warn if missing, halt if not boolean
        self.ssl = bool(os.getenv('MAIL_SSL', True))
        # Retrieve IMAP folder to monitor - warn if missing
        self.folder = os.getenv('MAIL_FOLDER', 'INBOX')

        # Retrieve Webhook url
        self.webhook_url = os.getenv('WEBHOOK', None)
        if self.webhook_url is None:
            log.critical('no "discord" section in configuration')
            exit(1)

    def run(self):
        log.debug('... script started')
        while True:
            while True:
                # Attempt connection to IMAP server
                log.debug('connecting to IMAP server - {0}'.format(self.host))
                try:
                    imap = imapclient.IMAPClient(self.host, use_uid=True, ssl=self.ssl)
                except Exception:
                    # If connection attempt to IMAP server fails, retry
                    etype, evalue = sys.exc_info()[:2]
                    estr = traceback.format_exception_only(etype, evalue)
                    logstr = 'failed to connect to IMAP server - '
                    for each in estr:
                        logstr += '{0}; '.format(each.strip('\n'))
                    log.error(logstr)
                    sleep(10)
                    continue
                log.debug('server connection established')

                # Attempt login to IMAP server
                log.debug('logging in to IMAP server - {0}'.format(self.username))
                try:
                    result = imap.login(self.username, self.password)
                    log.info('login successful - {0}'.format(result))
                    webhook = DiscordWebhook(
                        url=self.webhook_url,
                        content='Grandpa password watch started\n' + str(datetime.now())
                    )
                    webhook.execute()
                except LoginError as e:
                    if "Invalid credentials" in str(e):
                        log.critical("Password was changed")
                        webhook = DiscordWebhook(url=self.webhook_url, content='Grandpa change password')
                        # create embed object for webhook
                        embed = DiscordEmbed(
                            title='Grandpa change password',
                            description='Gmail password changed',
                            color=770000
                        )

                        # add embed object to webhook
                        webhook.add_embed(embed)
                        webhook.execute()
                    break
                except Exception:
                    # Halt script when login fails
                    etype, evalue = sys.exc_info()[:2]
                    estr = traceback.format_exception_only(etype, evalue)
                    logstr = 'failed to login to IMAP server - '
                    for each in estr:
                        logstr += '{0}; '.format(each.strip('\n'))
                    log.critical(logstr)
                    break

                # Select IMAP folder to monitor
                log.debug('selecting IMAP folder - {0}'.format(self.folder))
                try:
                    result = imap.select_folder(self.folder)
                    log.debug('folder selected')
                except Exception:
                    # Halt script when folder selection fails
                    etype, evalue = sys.exc_info()[:2]
                    estr = traceback.format_exception_only(etype, evalue)
                    logstr = 'failed to select IMAP folder - '
                    for each in estr:
                        logstr += '{0}; '.format(each.strip('\n'))
                    log.critical(logstr)
                    break

                # Retrieve and process all unread messages. Should errors occur due
                # to loss of connection, attempt restablishing connection
                try:
                    result = imap.search('UNSEEN')
                except Exception:
                    continue

                log.debug('{0} unread messages seen - {1}'.format(len(result), result))
                
                while True:
                    # <--- Start of mail monitoring loop

                    # After all unread emails are cleared on initial login, start
                    # monitoring the folder for new email arrivals and process
                    # accordingly. Use the IDLE check combined with occassional NOOP
                    # to refresh. Should errors occur in this loop (due to loss of
                    # connection), return control to IMAP server connection loop to
                    # attempt restablishing connection instead of halting script.
                    imap.idle()
                    # TODO: Remove hard-coded IDLE timeout; place in config file
                    # current check = 5 minutes
                    result = imap.idle_check(5 * 60)
                    if result:
                        imap.idle_done()
                        result = imap.search('UNSEEN')
                        log.debug('{0} new unread messages - {1}'.format(len(result), result))
                    else:
                        imap.idle_done()
                        imap.noop()
                        log.debug('no new messages seen')
                    # End of mail monitoring loop --->
                    continue
                # End of IMAP server connection loop --->
            # End of configuration section --->
            break
        log.warn('script stopped ...')
        webhook = DiscordWebhook(url=self.webhook_url, content='End password check' + str(datetime.now()))
        webhook.execute()


if __name__ == '__main__':
    GooglePassMonitor().run()