#!/usr/bin/env python3
"""
Email Log Monitor Script
Monitor email sending logs from background tasks
"""

import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

def tail_file(file_path, lines=10):
    """Read the last N lines of a file"""
    try:
        with open(file_path, 'r') as f:
            return f.readlines()[-lines:]
    except FileNotFoundError:
        return [f"Log file not found: {file_path}\n"]
    except Exception as e:
        return [f"Error reading log file: {e}\n"]

def follow_file(file_path):
    """Follow a file like 'tail -f'"""
    try:
        with open(file_path, 'r') as f:
            # Go to the end of the file
            f.seek(0, 2)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                yield line
    except FileNotFoundError:
        print(f"Log file not found: {file_path}")
        return
    except KeyboardInterrupt:
        print("\nStopping log monitoring...")
        return

def filter_email_logs(lines, filter_term=None):
    """Filter log lines for email-related content"""
    email_keywords = ['email', 'smtp', 'mail', 'send', 'background']
    filtered_lines = []
    
    for line in lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in email_keywords):
            if not filter_term or filter_term.lower() in line_lower:
                filtered_lines.append(line)
    
    return filtered_lines

def print_colored_log(line):
    """Print log line with colors based on log level"""
    colors = {
        'ERROR': '\033[91m',    # Red
        'WARNING': '\033[93m',  # Yellow
        'INFO': '\033[92m',     # Green
        'DEBUG': '\033[94m',    # Blue
    }
    reset_color = '\033[0m'
    
    for level, color in colors.items():
        if level in line:
            print(f"{color}{line.strip()}{reset_color}")
            return
    
    print(line.strip())

def main():
    parser = argparse.ArgumentParser(description='Monitor email logs from background tasks')
    parser.add_argument('--follow', '-f', action='store_true', 
                       help='Follow log file (like tail -f)')
    parser.add_argument('--lines', '-n', type=int, default=20,
                       help='Number of lines to show (default: 20)')
    parser.add_argument('--filter', type=str,
                       help='Filter logs containing this term')
    parser.add_argument('--log-file', type=str,
                       help='Specific log file to monitor')
    parser.add_argument('--environment', '-e', type=str, default='local',
                       choices=['local', 'dev', 'development', 'prod', 'production'],
                       help='Environment to monitor (default: local)')
    
    args = parser.parse_args()
    
    # Determine log file path
    if args.log_file:
        log_file = args.log_file
    else:
        # Default email log file
        log_file = "logs/email_sender.log"
        
        # Check if we're in Docker environment
        if os.path.exists("/app/logs"):
            log_file = "/app/logs/email_sender.log"
    
    print(f"Monitoring email logs: {log_file}")
    print(f"Environment: {args.environment}")
    if args.filter:
        print(f"Filter: {args.filter}")
    print("-" * 60)
    
    if args.follow:
        print("Following log file (Press Ctrl+C to stop)...")
        for line in follow_file(log_file):
            if args.filter and args.filter.lower() not in line.lower():
                continue
            print_colored_log(line)
    else:
        lines = tail_file(log_file, args.lines)
        filtered_lines = filter_email_logs(lines, args.filter)
        
        if not filtered_lines:
            print("No email-related log entries found.")
            return
        
        print(f"Last {len(filtered_lines)} email log entries:")
        print("-" * 60)
        
        for line in filtered_lines:
            print_colored_log(line)

if __name__ == "__main__":
    main()
