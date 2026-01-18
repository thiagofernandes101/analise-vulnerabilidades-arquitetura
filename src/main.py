import sys
import os
import time

def main():
    env = os.environ.get('APP_ENV', 'unknown')
    print(f"Starting Vulnerability Analysis Tool in {env} mode...")
    
    # Simulate some work or loop
    print("Running analysis loop. Press Ctrl+C to exit.")
    counter = 0
    try:
        while True:
            counter += 1
            # In debug mode, you can set a breakpoint here
            print(f"Processing chunk {counter}...")
            time.sleep(2)
    except KeyboardInterrupt:
        print("Stopping analysis.")

if __name__ == "__main__":
    main()
