import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os
import signal
import webbrowser
import threading
import time

class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Touch On Time Launcher")
        self.root.geometry("400x250")
        
        # Process Handle
        self.process = None
        self.server_url = "http://localhost:8501"
        
        # UI Components
        self.status_label = tk.Label(root, text="Status: Ready", fg="gray", font=("Helvetica", 12))
        self.status_label.pack(pady=20)
        
        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack(pady=10)
        
        # Button 1: Start Web UI
        self.start_btn = tk.Button(self.btn_frame, text="Start Web UI", command=self.start_server, width=15, bg="#e1f5fe")
        self.start_btn.pack(pady=5)
        
        # Button 2: Web Open
        self.browser_btn = tk.Button(self.btn_frame, text="Web Open", command=self.open_browser, state=tk.DISABLED, width=15)
        self.browser_btn.pack(pady=5)
        
        # Button 3: Stop
        self.stop_btn = tk.Button(self.btn_frame, text="Stop", command=self.stop_server, state=tk.DISABLED, width=15, bg="#ffcdd2")
        self.stop_btn.pack(pady=5)
        
        self.log_text = tk.Label(root, text="Waiting for action...", fg="gray", font=("Courier", 8))
        self.log_text.pack(side=tk.BOTTOM, pady=5)
        
        # Cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_server(self):
        if self.process:
            return
            
        self.update_status("Starting...", "orange")
        self.log_text.config(text="Initializing Streamlit...")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.browser_btn.config(state=tk.DISABLED) # Wait for ready
        
        # Run Streamlit in subprocess
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        
        # Headless mode is mandatory for the background process
        cmd = [sys.executable, "-m", "streamlit", "run", "src/web_ui.py", "--server.headless", "true"]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid # Create new process group
            )
            
            # Start monitoring thread
            threading.Thread(target=self.monitor_process, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {e}")
            self.stop_server() # Reset state

    def monitor_process(self):
        """Monitor stdout for readiness"""
        if not self.process:
            return

        while True:
            # Check if process is still alive
            if self.process is None or self.process.poll() is not None:
                # Process died unexpectedly
                if self.process: # If we didn't manually kill it
                    self.root.after(0, lambda: self.stop_server())
                break

            line = self.process.stdout.readline()
            if not line:
                break
            
            # Parse output for URL or Errors
            if "Local URL:" in line:
                # line example: "  Local URL: http://localhost:8501\n"
                parts = line.split("URL:")
                if len(parts) > 1:
                    new_url = parts[1].strip()
                    self.root.after(0, lambda url=new_url: self.on_server_ready(url))
            
            print(line.strip()) # Debug to terminal

    def on_server_ready(self, url):
        self.server_url = url
        self.update_status("Running", "green")
        self.log_text.config(text=f"Server Ready at {url}")
        self.browser_btn.config(state=tk.NORMAL)

    def open_browser(self):
        """Open browser in a way that respects the OS environment"""
        # Check if running in WSL (Microsoft kernel)
        try:
            with open("/proc/version", "r") as f:
                version_info = f.read().lower()
                is_wsl = "microsoft" in version_info
        except:
            is_wsl = False

        if is_wsl:
            # In WSL, use cmd.exe to launch the Windows default browser
            try:
                # cmd.exe /C start <url>
                subprocess.run(["cmd.exe", "/C", "start", self.server_url], check=False)
                return
            except Exception as e:
                print(f"Failed to launch via cmd.exe: {e}")
                # Fallback to standard webbrowser module

        # Standard Linux/Mac/Windows (Native)
        webbrowser.open(self.server_url)

    def stop_server(self):
        if self.process:
            self.update_status("Stopping...", "orange")
            self.log_text.config(text="Terminating process...")
            try:
                # Send SIGTERM to the process group
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # Force kill if not dead
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    self.process.wait(timeout=1)
            except Exception as e:
                print(f"Error killing process: {str(e)}")
            self.process = None
        
        # Reset UI (Only if window still exists)
        try:
            self.update_status("Stopped", "red")
            self.log_text.config(text="Server stopped.")
            self.start_btn.config(state=tk.NORMAL)
            self.browser_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
        except tk.TclError:
            pass # Window destroyed

    def update_status(self, text, color):
        try:
            self.status_label.config(text=f"Status: {text}", fg=color)
        except tk.TclError:
            pass

    def on_closing(self):
        """Handle window close event"""
        self.stop_server()
        self.root.destroy()
        sys.exit(0)

    def handle_signal(self, signum, frame):
        """Handle CLI signals (Ctrl+C)"""
        print("\nReceived signal. Cleaning up...")
        self.stop_server()
        if self.root:
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = LauncherApp(root)
    
    # Register Signal Handler for Ctrl+C
    signal.signal(signal.SIGINT, app.handle_signal)
    signal.signal(signal.SIGTERM, app.handle_signal)
    
    root.mainloop()
