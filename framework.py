# These are some imports that I found useful when implementing this project, you can use other libraries if you prefer.
# Note that you should only use standard python libraries. You should NOT use any existing testing framework libraries.

import time
import sys
import os

import argparse
import subprocess
import telnetlib


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="test cases for bftpd server")
    parser.add_argument('-p', action="store", dest="binary")
    parser.add_argument('-f', action="store", dest="file")  # if target test case is not provides, run all tests
    parser.add_argument('-v', action="store_true", dest="verbose")

    args = parser.parse_args()

    if not args.binary:
        print("Usage: python framework.py -p binary [-f input_file] [-v verbose]")
        # Exit with code 2, if it can't run the program with the given arguments
        sys.exit(2)

    # You implementation starts from here. You are free to change the structure of the code.
    # You can add new functions, classes, or python files. But, the behavior of your program should be consistent to the
    # requirements in the handout and what the skeleton code implies.
    if args.file:  # Run a single test case
        # TODO (1) Change the line below to get the conf file from the first line of the test case file
        configurationFile = "testing_environment/configurations/bftpd.conf"
        executeLine = './' + args.binary + ' -c ' + configurationFile + " -D"

        # Runs the BFTPD server as a subprocess.
        proc = subprocess.Popen(executeLine, shell=True)
        time.sleep(2)
        if proc.poll() != None:
            print("BFTPD failed to start, try changing your port")
            exit(2)

        # Your program can now communicate to the bftpd server.
        # You can use the telnetlib library to interact with it.
        # TODO (2) Run your test here and print the output based on the verbose level.

        # This kills the bftpd process, and all subprocesses that it created.
        # You must run this before you start another server on the same port
        os.system("ps -u $USER | grep bftpd | grep -v grep | awk '{print $1}' | xargs -r kill -9")
    else:  # Run all test cases under the testing_environment/testcases folder
        # TODO (3) Run all test cases
        pass

            

    




