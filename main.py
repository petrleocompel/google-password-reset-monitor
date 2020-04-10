#import eventlet

#imapclient = eventlet.import_patched('imapclient')
import imapclient
from imapclient.exceptions import LoginError

import os
#import discord
#from discord.ext import commands
from discord_webhook import DiscordWebhook, DiscordEmbed

import os.path as path
import sys
import traceback
import logging
from logging.handlers import RotatingFileHandler
import configparser
import email
from time import sleep
from datetime import datetime, time
#description = 'GrandPaPassBot'
#bot = commands.Bot(command_prefix='!pw', description=description)

# Setup the log handlers to stdout and file.
log = logging.getLogger('imap_monitor')
log.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
handler_stdout = logging.StreamHandler(sys.stdout)
handler_stdout.setLevel(logging.DEBUG)
handler_stdout.setFormatter(formatter)
log.addHandler(handler_stdout)


# TODO: Support SMTP log handling for CRITICAL errors.
def process_email(mail_, log_):
    """Email processing to be done here. mail_ is the Mail object passed to this
    function. download_ is the path where attachments may be downloaded to.
    log_ is the logger object.

    """
    log_.info(mail_['subject'])
    if 'accounts.google.com' in mail_['From']:
        return 'changed pass'
    return 'return meaningful result here'


def main():
    log.info('... script started')
    while True:
        # <--- Start of configuration section

        # Retrieve IMAP host - halt script if section 'imap' or value
        host = os.getenv('MAIL_HOST', None)
        if host is None:
            log.critical('no IMAP host specified in configuration file')
            exit(1)

        username = os.getenv('MAIL_LOGIN', None)
        if username is None:
            log.critical('no IMAP login specified in configuration file')
            exit(1)

        # Retrieve IMAP password - halt script if missing
        password = os.getenv('MAIL_PASS', None)
        if password is None:
            log.critical('no IMAP password specified in configuration file')
            exit(1)

        # Retrieve IMAP SSL setting - warn if missing, halt if not boolean
        ssl = bool(os.getenv('MAIL_SSL', True))
        # Retrieve IMAP folder to monitor - warn if missing
        folder = os.getenv('MAIL_FOLDER', 'INBOX')

        # Retrieve Webhook url
        webhook_url = os.getenv('WEBHOOK', None)
        if webhook_url is None:
            log.critical('no "discord" section in configuration')
            exit(1)

        while True:
            # <--- Start of IMAP server connection loop

            # Attempt connection to IMAP server
            log.info('connecting to IMAP server - {0}'.format(host))
            try:
                imap = imapclient.IMAPClient(host, use_uid=True, ssl=ssl)
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
            log.info('server connection established')

            # Attempt login to IMAP server
            log.info('logging in to IMAP server - {0}'.format(username))
            try:
                result = imap.login(username, password)
                log.info('login successful - {0}'.format(result))
                webhook = DiscordWebhook(
                    url=webhook_url,
                    content='Grandpa password watch started\n' + str(datetime.now())
                )
                webhook.execute()
            except LoginError as e:
                if "Invalid credentials" in str(e):
                    log.critical("Password was changed")
                    webhook = DiscordWebhook(url=webhook_url, content='Grandpa change password')
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
            log.info('selecting IMAP folder - {0}'.format(folder))
            try:
                result = imap.select_folder(folder)
                log.info('folder selected')
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
            log.info('{0} unread messages seen - {1}'.format(
                len(result), result
            ))
            for each in result:
                try:
                    result = imap.fetch(each, ['RFC822'])
                except Exception:
                    log.error('failed to fetch email - {0}'.format(each))
                    continue
                mail = email.message_from_string(result[each][b'RFC822'].decode("utf-8"))
                try:
                    process_email(mail, log)
                    log.info('processing email {0} - {1}'.format(
                        each, mail['subject']
                    ))
                except Exception:
                    log.error('failed to process email {0}'.format(each))
                    raise
                    continue

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
                result = imap.idle_check(5 * 60)
                if result:
                    imap.idle_done()
                    result = imap.search('UNSEEN')
                    log.info('{0} new unread messages - {1}'.format(
                        len(result), result
                    ))
                    for each in result:
                        fetch = imap.fetch(each, ['RFC822'])
                        mail = email.message_from_string(
                            fetch[each]['RFC822']
                        )
                        try:
                            process_email(mail, log)
                            log.info('processing email {0} - {1}'.format(
                                each, mail['subject']
                            ))
                        except Exception:
                            log.error(
                                'failed to process email {0}'.format(each))
                            raise
                            continue
                else:
                    imap.idle_done()
                    imap.noop()
                    log.info('no new messages seen')
                # End of mail monitoring loop --->
                continue

            # End of IMAP server connection loop --->
            break

        # End of configuration section --->
        break
    log.info('script stopped ...')
    webhook = DiscordWebhook(url=webhook_url, content='End password check' + str(datetime.now()))
    webhook.execute()


if __name__ == '__main__':
    main()