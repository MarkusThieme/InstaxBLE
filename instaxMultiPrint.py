# path_watcher.py
#
# A Python script for Windows that monitors a given path.
# It ensures 'printed' and 'error' sub-folders exist
# and then enters an endless loop processing image files.

import sys
import os
import time
import shutil



def main(args):
    """
    Main function to process command-line arguments, create folders,
    and enter a monitoring loop.

    Args:
        args (list): The list of command-line arguments, including the
                     script name (e.g., sys.argv).

    Returns:
        int: 0 on successful termination (Ctrl-C), 1 on any error.
    """

    # --- 1. Argument Handling ---

    # Check if at least one argument (besides the script name) is provided
    if len(args) < 2:
        # Print error message to standard error
        print("Error: No path argument provided.", file=sys.stderr)
        print("Usage: python path_watcher.py <path_to_file_or_directory>", file=sys.stderr)
        return 1  # Return error code

    input_path = args[1]

    # --- 2. Path Validation ---

    # Check if the provided path exists
    if not os.path.exists(input_path):
        print(f"Error: Path '{input_path}' does not exist.", file=sys.stderr)
        return 1

    # --- 3. Path Resolution ---

    # Get the absolute path from the input
    try:
        abs_path = os.path.abspath(input_path)
    except Exception as e:
        print(f"Error resolving absolute path: {e}", file=sys.stderr)
        return 1

    # Determine the target directory.
    # If input is a file, use its parent directory.
    # If input is a directory, use the directory itself.
    if os.path.isdir(abs_path):
        target_dir = abs_path
    elif os.path.isfile(abs_path):
        target_dir = os.path.dirname(abs_path)
    else:
        # This handles edge cases like broken symlinks (if os.path.exists was true)
        print(f"Error: Path '{abs_path}' is not a valid file or directory.", file=sys.stderr)
        return 1

    print(f"Target directory set to: {target_dir}")

    # --- 4. Sub-folder Creation ---

    printed_dir = os.path.join(target_dir, "printed")
    error_dir = os.path.join(target_dir, "error")

    try:
        # os.makedirs with exist_ok=True is idempotent.
        # It creates the directory if it doesn't exist.
        # It does nothing if it already exists.
        # It will only raise an error for other issues (e.g., permissions).

        os.makedirs(printed_dir, exist_ok=True)
        print(f"Successfully ensured 'printed' folder exists at: {printed_dir}")

        os.makedirs(error_dir, exist_ok=True)
        print(f"Successfully ensured 'error' folder exists at: {error_dir}")

    except OSError as e:
        # This catches errors like "Permission denied"
        print(f"Error: Failed to create directories.", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred during directory creation: {e}", file=sys.stderr)
        return 1

    # --- 5. Endless Loop ---

    instax = None  # Initialize instax outside the try block
    try:
        instax = InstaxBLE(print_enabled=True, quiet=True)
        instax.connect()
        instax.send_led_pattern(LedPatterns.rainbow, when=1)
        instax.send_led_pattern(LedPatterns.pulseGreen, when=2)
    except Exception as e:
        print(f"Error initializing InstaxBLE or connecting: {e}", file=sys.stderr)
        if instax:
            instax.disconnect()
        return 1


    print("\nSetup complete. Entering processing loop.")
    print("Press Ctrl-C to terminate the script...")



    IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')

    try:
        while True:

            # --- 1. Read the directory ---
            files_with_mtime = []
            try:
                for f in os.listdir(target_dir):
                    file_path = os.path.join(target_dir, f)
                    try:
                        # Only consider files, not sub-directories
                        if os.path.isfile(file_path):
                            mtime = os.path.getmtime(file_path)
                            files_with_mtime.append((file_path, mtime))
                    except (OSError, FileNotFoundError):
                        # File might have been moved/deleted just as we check it
                        continue
            except Exception as e:
                print(f"Error reading directory '{target_dir}': {e}", file=sys.stderr)
                # Wait before retrying to avoid spamming errors
                time.sleep(5)
                continue

            # --- 2. Sort the list by modification date (oldest first) ---
            files_with_mtime.sort(key=lambda x: x[1])
            sorted_files = [f[0] for f in files_with_mtime]

            # --- 3. Filter for image files ---
            image_files = [f for f in sorted_files if f.lower().endswith(IMAGE_EXTENSIONS)]

            if image_files:
                print(f"Found {len(image_files)} image(s) to process...")

            # --- 4. Iterate over the list of files ---
            for file_path in image_files:

                # Check if file is not being used
                in_use = True
                try:
                    # On Windows, trying to rename a file to itself will
                    # raise PermissionError if the file is locked.
                    os.rename(file_path, file_path)
                    in_use = False
                except PermissionError:
                    print(f"Skipping '{os.path.basename(file_path)}': File is in use.")
                except FileNotFoundError:
                    print(f"Skipping '{os.path.basename(file_path)}': File was moved or deleted.")
                    continue  # File is gone, move to the next
                except OSError as e:
                    print(f"Skipping '{os.path.basename(file_path)}': OS error ({e}).")

                # If it is not in use, process it
                if not in_use:
                    basename = os.path.basename(file_path)
                    print(f"Processing: {basename}")

                    # Ensure a unique name is assigned upon moving
                    base, ext = os.path.splitext(basename)
                    counter = 1
                    dest_path = os.path.join(printed_dir, basename)

                    while os.path.exists(dest_path):
                        # If "image.jpg" exists, try "image_1.jpg", then "image_2.jpg"
                        dest_path = os.path.join(printed_dir, f"{base}_{counter}{ext}")
                        counter += 1

                    # Move the file
                    try:
                        shutil.move(file_path, dest_path)
                        print(f"Moved to: {os.path.basename(dest_path)}")
                    except Exception as e:
                        print(f"Error moving '{basename}': {e}", file=sys.stderr)
                        # If moving fails, we'll just skip it for this iteration.
                        # We could move it to 'error_dir' here if needed.

                # Wait 1 sec and continue the iteration
                time.sleep(1)

            # After processing all files, wait 1 second before scanning again
            # This is the main polling interval.
            time.sleep(1)

    except KeyboardInterrupt:
        # This block executes when the user presses Ctrl-C
        print("\nTermination signal (Ctrl-C) received. Exiting gracefully.")
        return 0  # Return success code


# --- Script Entry Point ---

if __name__ == "__main__":
    # Call the main function with the command-line arguments
    # sys.exit() ensures that the return value from main()
    # is used as the process's exit code.
    # 0 indicates success, non-zero indicates an error.
    sys.exit(main(sys.argv))

