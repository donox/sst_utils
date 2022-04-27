#!/usr/bin/env python3
import shlex
import logging
import subprocess


class OvernightLogger(object):
    def __init__(self, log_name, log_directory):
        self.logger = logging.getLogger(log_name)
        self.logger.setLevel(logging.INFO)
        # create file handler which logs even debug messages
        fh = logging.FileHandler(log_directory + log_name + '.log', mode='w')
        fh.setLevel(logging.INFO)
        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        # add the handlers to the logger
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def make_info_entry(self, entry):
        self.logger.info(entry)

    def make_error_entry(self, entry):
        self.logger.error(entry)

    def close_logger(self):
        self.logger = None


def run_shell_command(command_line, logger, outfile=False, result_as_string=False, ignore=None):
    command_line_plus = command_line
    if ignore:
        command_line_plus += " --exclude=" + ignore
    command_line_args = shlex.split(command_line_plus)
    cmd = command_line_args[0]

    logger.make_info_entry('Subprocess: {}'.format(command_line_plus))

    try:
        command_line_process = subprocess.Popen(
            command_line_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        process_output, process_error = command_line_process.communicate()
        if process_error:
            logger.make_error_entry(f"Error returned from subprocess with command line:\n\t\t{command_line_plus}" +
                                    f"\n\nError:\n\t\t{process_error}")
        logger.make_info_entry(f"Command output (first 1000 chars):\n\n{process_output[:1000]}")
        if outfile:
            with open(outfile, 'wb') as fl:
                fl.write(process_output)

        # logger.make_info_entry(process_output)
        # logger.make_info_entry(process_error)
    except (OSError, subprocess.CalledProcessError) as exception:
        logger.make_error_entry('Exception occurred in {}: {}'.format(cmd, exception))
        logger.make_error_entry('Subprocess {} failed'.format(cmd))
        return False
    else:
        # no exception was raised
        # logger.make_info_entry('Subprocess {} completed'.format(cmd))
        if result_as_string:
            return process_output
    return True


