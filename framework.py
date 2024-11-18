import time
import sys
import os
import glob
import argparse
import subprocess
import telnetlib
import socket
import signal

def cleanup_existing_processes():
    """Kill any existing BFTPD processes"""
    try:
        os.system("ps -u $USER | grep bftpd | grep -v grep | awk '{print $1}' | xargs -r kill -9")
        time.sleep(1)  # Give processes time to clean up
    except Exception as e:
        print(f"Warning: Error while cleaning up processes: {str(e)}")

def wait_for_server(timeout=10):
    """Wait for server to start accepting connections"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                if sock.connect_ex(('127.0.0.1', 10566)) == 0:
                    return True
        except:
            pass
        time.sleep(0.5)
    return False

def run_test(binary, config_file, test_commands, verbose=False):
    if verbose:
        print(f"Running test with:")
        print(f"Binary: {binary}")
        print(f"Config file: {config_file}")
        print(f"Test commands: {test_commands}")
    
    # Clean up any existing processes first
    if verbose:
        print("Cleaning up any existing BFTPD processes...")
    cleanup_existing_processes()
    
    executeLine = f'{binary} -c {config_file} -D'
    if verbose:
        print(f"Executing command: {executeLine}")
        
    # Start the server with full output capture
    proc = subprocess.Popen(
        executeLine,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid  # Create new process group
    )
    
    # Wait for server to start
    if verbose:
        print("Waiting for server to start...")
    if not wait_for_server():
        _, stderr = proc.communicate()
        print("Error: Server failed to start within timeout period")
        print("Server error output:")
        print(stderr.decode())
        cleanup_existing_processes()
        sys.exit(2)

    # Try to connect multiple times
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if verbose and attempt > 0:
                print(f"Connection attempt {attempt + 1}...")
            telnet = telnetlib.Telnet("localhost", 10566)
            break
        except ConnectionRefusedError:
            if attempt == max_retries - 1:
                print("Could not connect to BFTPD server after multiple attempts.")
                cleanup_existing_processes()
                sys.exit(2)
            time.sleep(2)
        except Exception as e:
            print(f"Error connecting to server: {str(e)}")
            cleanup_existing_processes()
            sys.exit(2)

    output_log = []
    try:
        # Read initial banner
        initial_response = telnet.read_until(b"\n").decode('ascii').strip()
        output_log.append(initial_response)
        if verbose:
            print(f"Server banner: {initial_response}")

        for command in test_commands:
            if verbose:
                print(f"Sending command: {command}")
            telnet.write((command + "\r\n").encode('ascii'))
            print(f"Sending raw command: {repr(command)}")
            response = telnet.read_until(b"\n", timeout=20).decode('ascii').strip()
            output_log.append(response)
            if verbose:
                print(f"Received response: {response}")
    except Exception as e:
        print(f"Error during communication: {str(e)}")
    finally:
        telnet.close()
        # Kill the entire process group
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except:
            pass
        cleanup_existing_processes()
    
    return output_log

def get_config_path(config_file):
    """Get the full path to the configuration file"""
    config_path = os.path.join(os.getcwd(), "testing_environment", "configurations", config_file)
    print(f"config path: {config_path}")
    if os.path.exists(config_path):
        return config_path
    
    print(f"Error: Configuration file '{config_file}' not found in testing_environment/configurations/")
    print(f"Looked in: {config_path}")
    sys.exit(2)

def read_test(file_path):
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()
            if not lines:
                print(f"Error: Test file '{file_path}' is empty")
                sys.exit(2)
                
            config_file = lines[0].strip()
            print(f"Config file curr: {config_file}")
            config_file = get_config_path(config_file)
                
            test_commands = []
            for line in lines:
                if line.startswith("1:"):
                    cmd = line.split(":", 1)[1].strip()
                    if cmd:
                        test_commands.append(cmd)
            
            if not test_commands:
                print(f"Error: No test commands found in '{file_path}'")
                sys.exit(2)
                
            return config_file, test_commands
    except Exception as e:
        print(f"Error reading test file '{file_path}': {str(e)}")
        sys.exit(2)

def read_expected(file_path):
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()
            if len(lines) > 0 and not lines[0].startswith("220"):
                lines = lines[1:]
            return [line.strip() for line in lines if line.strip()]
    except Exception as e:
        print(f"Error reading expected output file '{file_path}': {str(e)}")
        sys.exit(2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="test cases for bftpd server")
    parser.add_argument('-p', action="store", dest="binary")
    parser.add_argument('-f', action="store", dest="file")
    parser.add_argument('-v', action="store_true", dest="verbose")

    args = parser.parse_args()

    if not args.binary:
        print("Usage: python framework.py -p binary [-f input_file] [-v verbose]")
        sys.exit(2)

    if not os.path.isabs(args.binary):
        args.binary = os.path.abspath(args.binary)
    
    if not os.path.exists(args.binary):
        print(f"Error: Binary '{args.binary}' not found")
        sys.exit(2)
    if not os.access(args.binary, os.X_OK):
        print(f"Error: Binary '{args.binary}' is not executable")
        sys.exit(2)

    if args.file:  # Run a single test case
        config_file, test_commands = read_test(args.file)
        print("CONFIG:", config_file)
        print("COMMAND:", test_commands)
        output = run_test(args.binary, config_file, test_commands, args.verbose)

        expected_output_file = args.file.replace("input", "output")
        expected_output = read_expected(expected_output_file)

        if output == expected_output:
            print("Test passed")
        else:
            print("Test failed")
            if args.verbose:
                print("Expected:", expected_output)
                print("Actual:", output)
    else:  # Run all test cases
        test_files = glob.glob("testing_environment/testcases/test_input_*.txt")
        test_files.sort()

        for test_file in test_files:
            config_file, test_commands = read_test(test_file)
            output = run_test(args.binary, config_file, test_commands, args.verbose)

            expected_output_file = test_file.replace("input", "output")
            expected_output = read_expected(expected_output_file)

            test_name = os.path.basename(test_file)
            print(f"Running {test_name}... ", end="")

            if output == expected_output:
                print("Passed")
            else:
                print("Failed")
                if args.verbose:
                    print("Expected:", expected_output)
                    print("Actual:", output)