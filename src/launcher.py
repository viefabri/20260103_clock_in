import customtkinter as ctk
from tkinter import messagebox
import subprocess
import sys
import os
import signal
import webbrowser
import threading
import time
from PIL import Image, ImageTk
import ctypes
from ctypes import c_long, c_ulong

# Set Appearance Mode
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

import customtkinter as ctk
from tkinter import messagebox
import subprocess
import sys
import os
import signal
import webbrowser
import threading
import time
from PIL import Image, ImageTk

# Set Appearance Mode
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

import customtkinter as ctk
from tkinter import messagebox
import subprocess
import sys
import os
import signal
import webbrowser
import threading
import time
from PIL import Image, ImageTk
import ctypes
from ctypes import c_long, c_ulong, c_int, c_char_p, POINTER, byref

# Set Appearance Mode
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

import customtkinter as ctk
from tkinter import messagebox
import subprocess
import sys
import os
import signal
import webbrowser
import threading
import time
from PIL import Image, ImageTk

# Set Appearance Mode
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class LauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window Setup
        self.title("Touch On Time Launcher")
        self.geometry("400x350")
        
        # Standard Window (Managed by OS/WSLg)
        # No extra hacks needed.
        
        # Center Window
        self.center_window()
        
        # Grid Layout
        self.grid_columnconfigure(0, weight=1)
        # Row 0 was Title Bar, now removed.
        self.grid_rowconfigure(0, weight=1) # Status
        self.grid_rowconfigure(1, weight=2) # Buttons
        self.grid_rowconfigure(2, weight=1) # Log

        # Process Handle
        self.process = None
        self.server_url = "http://localhost:8501"
        
        # Icon Setup
        self.setup_icon()
        
        # === 1. Status Section ===
        self.status_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1a1a1a")
        self.status_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        self.status_label = ctk.CTkLabel(
            self.status_frame, 
            text="Status: Ready", 
            font=("Roboto Medium", 16)
        )
        self.status_label.pack(pady=10)
        
        # === 2. Controls Section ===
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=1, column=0, padx=20, pady=10)
        
        # Start Button
        self.start_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Start Web UI", 
            command=self.start_server, 
            width=200, 
            height=40,
            fg_color="#1f6aa5",
            hover_color="#144870"
        )
        self.start_btn.pack(pady=6)
        
        # Open Browser Button
        self.browser_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Open Browser", 
            command=self.open_browser, 
            state="disabled",
            width=200, 
            height=40,
            fg_color="transparent", 
            border_width=2,
            border_color="#3E454A",
            text_color=("gray90", "#DCE4EE")  
        )
        self.browser_btn.pack(pady=6)
        
        # Stop Button
        self.stop_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Stop Server", 
            command=self.stop_server, 
            state="disabled",
            width=200, 
            height=40,
            fg_color="#b71c1c",
            hover_color="#7f0000"
        )
        self.stop_btn.pack(pady=6)
        
        # === 3. Log Section ===
        self.log_text = ctk.CTkLabel(
            self, 
            text="Waiting for user action...", 
            font=("Consolas", 11),
            text_color="gray"
        )
        self.log_text.grid(row=2, column=0, pady=(0, 20))
        
        # Cleanup logic
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_icon(self):
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "assets", "icon.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                photo_icon = ImageTk.PhotoImage(img)
                self.wm_iconphoto(True, photo_icon) # Set for OS Taskbar & Title Bar
            else:
                print(f"Icon not found at: {icon_path}")
        except Exception as e:
            print(f"Failed to load icon: {e}")

    def center_window(self):
        self.update_idletasks()
        width = 400
        height = 350
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{int(x)}+{int(y)}')

    def start_server(self):
        if self.process:
            return
            
        self.update_status("Starting...", "orange")
        self.log_text.configure(text="Initializing Streamlit...")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cmd = [sys.executable, "-m", "streamlit", "run", "src/web_ui.py", "--server.headless", "true"]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid
            )
            threading.Thread(target=self.monitor_process, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {e}")
            self.stop_server()

    def monitor_process(self):
        if not self.process:
            return
        while True:
            if self.process is None or self.process.poll() is not None:
                if self.process:
                    self.after(0, lambda: self.stop_server())
                break
            line = self.process.stdout.readline()
            if not line:
                break
            if "Local URL:" in line:
                parts = line.split("URL:")
                if len(parts) > 1:
                    new_url = parts[1].strip()
                    self.after(0, lambda url=new_url: self.on_server_ready(url))
            print(line.strip())

    def on_server_ready(self, url):
        self.server_url = url
        self.update_status("Running", "#2e7d32")
        self.log_text.configure(text=f"Server Ready at {url}")
        self.browser_btn.configure(state="normal")

    def open_browser(self):
        try:
            with open("/proc/version", "r") as f:
                version_info = f.read().lower()
                is_wsl = "microsoft" in version_info
        except:
            is_wsl = False

        if is_wsl:
            try:
                subprocess.run(["cmd.exe", "/C", "start", self.server_url], check=False)
                return
            except Exception as e:
                print(f"Failed to launch via cmd.exe: {e}")
        webbrowser.open(self.server_url)

    def stop_server(self):
        if self.process:
            self.update_status("Stopping...", "orange")
            self.log_text.configure(text="Terminating process...")
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    self.process.wait(timeout=1)
            except Exception as e:
                print(f"Error killing process: {str(e)}")
            self.process = None
        
        try:
            self.update_status("Stopped", "#c62828")
            self.log_text.configure(text="Server stopped.")
            self.start_btn.configure(state="normal")
            self.browser_btn.configure(state="disabled")
            self.stop_btn.configure(state="disabled")
        except Exception:
            pass 

    def update_status(self, text, color):
        try:
            self.status_label.configure(text=f"Status: {text}", text_color=color)
        except Exception:
            pass

    def on_closing(self):
        self.stop_server()
        self.destroy()
        sys.exit(0)

    def handle_signal(self, signum, frame):
        print("\nReceived signal. Cleaning up...")
        self.stop_server()
        if self:
            try:
                self.quit()
                self.destroy()
            except:
                pass
        sys.exit(0)

if __name__ == "__main__":
    app = LauncherApp()
    signal.signal(signal.SIGINT, app.handle_signal)
    signal.signal(signal.SIGTERM, app.handle_signal)
    app.mainloop()
