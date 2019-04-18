"""
Copyright (c) 2014 Wind River Systems, Inc.

SPDX-License-Identifier: Apache-2.0

"""

###################
# IMPORTS
###################
from __future__ import absolute_import
import logging
import logging.handlers
import time
import os
import subprocess
import glob
import re
import sys

from daemon import runner

from logmgmt import prepostrotate

###################
# CONSTANTS
###################
LOG_DIR = '/var/lib/logmgmt'
LOG_FILE = LOG_DIR + '/logmgmt.log'
PID_FILE = '/var/run/logmgmt.pid'
LOG_FILE_MAX_BYTES = 1024 * 1024
LOG_FILE_BACKUP_COUNT = 5

PERCENT_FREE_CRITICAL = 10
PERCENT_FREE_MAJOR = 20

LOGROTATE_PERIOD = 600  # Every ten minutes


###################
# METHODS
###################
def start_polling():
    logmgmt_daemon = LogMgmtDaemon()
    logmgmt_runner = runner.DaemonRunner(logmgmt_daemon)
    logmgmt_runner.daemon_context.umask = 0o022
    logmgmt_runner.do_action()


def handle_exception(exc_type, exc_value, exc_traceback):
    """Exception handler to log any uncaught exceptions"""
    logging.error("Uncaught exception",
                  exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


###################
# CLASSES
###################
class LogMgmtDaemon():
    """Daemon process representation of the /var/log monitoring program"""
    def __init__(self):
        # Daemon-specific init
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/null'
        self.stderr_path = '/dev/null'
        self.pidfile_path = PID_FILE
        self.pidfile_timeout = 5

        self.monitored_files = []
        self.unmonitored_files = []

        self.last_logrotate = 0
        self.last_check = 0

    def configure_logging(self, level=logging.DEBUG):
        my_exec = os.path.basename(sys.argv[0])

        if not os.path.exists(LOG_DIR):
            os.mkdir(LOG_DIR, 0o755)

        log_format = '%(asctime)s: ' \
                     + my_exec + '[%(process)s]: ' \
                     + '%(filename)s(%(lineno)s): ' \
                     + '%(levelname)s: %(message)s'

        fmt = logging.Formatter(fmt=log_format)

        # Use python's log rotation, rather than logrotate
        handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_FILE_BACKUP_COUNT)

        my_logger = logging.getLogger()
        my_logger.setLevel(level)

        handler.setFormatter(fmt)
        handler.setLevel(level)
        my_logger.addHandler(handler)

        # Log uncaught exceptions to file
        sys.excepthook = handle_exception

    def run(self):
        self.configure_logging()

        while True:
            self.check_var_log()

            # run/poll every 1 min
            time.sleep(60)

    def get_percent_free(self):
        usage = os.statvfs('/var/log')
        return ((usage.f_bavail * 100) / usage.f_blocks)

    def get_monitored_files(self):
        self.monitored_files = []

        try:
            output = subprocess.check_output(['/usr/sbin/logrotate', '-d', '/etc/logrotate.conf'],
                                             stderr=subprocess.STDOUT)

            for line in output.split('\n'):
                fields = line.split()
                if len(fields) > 0 and fields[0] == "considering":
                    self.monitored_files.extend(glob.glob(fields[2]))
                    self.monitored_files.extend(glob.glob(fields[2] + '.[0-9].gz'))
                    self.monitored_files.extend(glob.glob(fields[2] + '.[0-9][0-9].gz'))
                    self.monitored_files.extend(glob.glob(fields[2] + '.[0-9]'))
                    self.monitored_files.extend(glob.glob(fields[2] + '.[0-9][0-9]'))
        except:
            logging.error('Failed to determine monitored files')
            raise

    def get_unmonitored_files(self):
        self.unmonitored_files = []

        try:
            output = subprocess.check_output(['find', '/var/log', '-type', 'f'])

            for fname in output.split('\n'):
                if fname in self.monitored_files:
                    continue

                # Ignore some files
                if ('/var/log/puppet' in fname
                        or '/var/log/dmesg' in fname
                        or '/var/log/rabbitmq' in fname
                        or '/var/log/lastlog' in fname):
                    continue

                if os.path.exists(fname):
                    self.unmonitored_files.append(fname)

        except:
            logging.error('Failed to determine unmonitored files')

    def purge_files(self, index):
        pattern = re.compile('.*\.([0-9]*)\.gz')
        for fname in sorted(self.monitored_files):
            result = pattern.match(fname)
            if result:
                if int(result.group(1)) >= index:
                    logging.info("Purging file: %s" % fname)
                    try:
                        os.remove(fname)
                    except OSError as e:
                        logging.error('Failed to remove file: %s', e)

    def run_logrotate(self):
        self.last_logrotate = int(time.time())
        try:
            subprocess.check_call(['/usr/sbin/logrotate', '/etc/logrotate.conf'])
        except:
            logging.error('Failed logrotate')

    def run_logrotate_forced(self):
        self.last_logrotate = int(time.time())
        try:
            subprocess.check_call(['/usr/sbin/logrotate', '-f', '/etc/logrotate.conf'])
        except:
            logging.error('Failed logrotate -f')

    def timecheck(self):
        # If we're more than a couple of mins since the last timecheck,
        # there could have been a large time correction, which would skew
        # our timing. Reset the logrotate timestamp to ensure we don't miss anything
        now = int(time.time())

        if self.last_check > now or (now - self.last_check) > 120:
            self.last_logrotate = 0

        self.last_check = now

    def check_var_log(self):
        self.timecheck()

        try:
            prepostrotate.ensure_bash_log_locked_down()
        except Exception as e:
            logging.exception('Failed to ensure bash.log locked', e)

        pf = self.get_percent_free()

        if pf > PERCENT_FREE_CRITICAL:
            # We've got more than 10% free space, so just run logrotate every ten minutes
            now = int(time.time())
            if self.last_logrotate > now or (now - self.last_logrotate) > LOGROTATE_PERIOD:
                logging.info("Running logrotate")
                self.run_logrotate()

            return

        logging.warning("Reached critical disk usage for /var/log: %d%% free" % pf)

        # We're running out of disk space, so we need to start deleting files
        try:
            for index in range(20, 11, -1):
                logging.info("/var/log is %d%% free. Purging rotated .%d.gz files to free space" % (pf, index))
                self.get_monitored_files()
                self.purge_files(index)
                pf = self.get_percent_free()

                if pf >= PERCENT_FREE_MAJOR:
                    # We've freed up enough space. Do a logrotate and leave
                    logging.info("/var/log is %d%% free. Running logrotate" % pf)
                    self.run_logrotate()
                    return
        except Exception as e:
            logging.exception('Failed purging rotated files', e)

        # We still haven't freed up enough space, so try a logrotate
        logging.info("/var/log is %d%% free. Running logrotate" % pf)
        self.run_logrotate()

        pf = self.get_percent_free()
        if pf >= PERCENT_FREE_MAJOR:
            return

        # Try a forced rotate
        logging.info("/var/log is %d%% free. Running forced logrotate" % pf)
        self.run_logrotate_forced()

        pf = self.get_percent_free()
        if pf >= PERCENT_FREE_MAJOR:
            return

        # Start deleting unmonitored files
        try:
            self.get_monitored_files()
            self.get_unmonitored_files()
            logging.info("/var/log is %d%% free. Deleting unmonitored files to free space" % pf)
            for fname in sorted(self.unmonitored_files, key=os.path.getsize, reverse=True):
                logging.info("Deleting unmonitored file: %s" % fname)
                try:
                    os.remove(fname)
                except OSError as e:
                    logging.error('Failed to remove file: %s', e)
                pf = self.get_percent_free()
                if pf >= PERCENT_FREE_MAJOR:
                    logging.info("/var/log is %d%% free." % pf)
                    return
        except Exception as e:
            logging.exception('Failed checking unmonitored files', e)

        # Nothing else to be done
        logging.info("/var/log is %d%% free." % pf)
        return

