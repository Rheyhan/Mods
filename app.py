import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import os
import shutil
from google.cloud import storage
from datetime import datetime

hidden_key = {
    "DELETED FOR PRIVACY, ASK RHEY IF YOU NEED IT!"
}

storage_client = storage.Client.from_service_account_info(hidden_key)
bucket = storage_client.get_bucket("rheyminecraft-mods") 

minecraft_dir = ""

class ToolTip:
    """Creates a tooltip for a given widget"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)

    def on_enter(self, event=None):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.geometry(f"+{x}+{y}")
        
        label = tk.Label(
            self.tooltip,
            text=self.text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("Arial", 9),
            wraplength=300
        )
        label.pack()

    def on_leave(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

def format_bytes(bytes):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"

def get_timestamp():
    """Get current timestamp for logging"""
    return datetime.now().strftime("%H:%M:%S")

def select_minecraft_directory():
    """Allow user to select the Minecraft directory"""
    global minecraft_dir
    selected_dir = filedialog.askdirectory(title="Select Minecraft Directory")
    if selected_dir:
        # Validate if it's a valid Minecraft directory
        if os.path.exists(os.path.join(selected_dir, "versions")):
            minecraft_dir = selected_dir
            dir_label.config(text=f"Directory: {os.path.basename(minecraft_dir)}", foreground="#2e7d32")
            log_message(f"✓ Minecraft directory set to: {minecraft_dir}", "success")
            # Enable buttons once directory is selected
            btn_fresh_install.config(state="normal")
            btn_update.config(state="normal")
            btn_get_options.config(state="normal")
        else:
            messagebox.showerror("Invalid Directory", "Selected directory doesn't appear to be a valid Minecraft directory (missing 'versions' folder)")
            log_message("✗ Invalid Minecraft directory selected", "error")

def log_message(message, level="info"):
    """Add a message to the log area with timestamp and color coding"""
    timestamp = get_timestamp()
    log_text.config(state="normal")
    
    # Color coding based on level
    if level == "error":
        color = "#d32f2f"
        prefix = "ERROR"
    elif level == "warning":
        color = "#f57c00"
        prefix = "WARN"
    elif level == "success":
        color = "#2e7d32"
        prefix = "SUCCESS"
    elif level == "download":
        color = "#1976d2"
        prefix = "DOWNLOAD"
    else:
        color = "#424242"
        prefix = "INFO"
    
    # Insert timestamp
    log_text.insert(tk.END, f"[{timestamp}] ", ("timestamp",))
    # Insert level prefix
    log_text.insert(tk.END, f"[{prefix}] ", (level,))
    # Insert message
    log_text.insert(tk.END, f"{message}\n")
    
    # Configure tags for colors
    log_text.tag_config("timestamp", foreground="#666666")
    log_text.tag_config("error", foreground="#d32f2f")
    log_text.tag_config("warning", foreground="#f57c00")
    log_text.tag_config("success", foreground="#2e7d32")
    log_text.tag_config("download", foreground="#1976d2")
    log_text.tag_config("info", foreground="#424242")
    
    log_text.config(state="disabled")
    log_text.see(tk.END)  # Scroll to bottom

def update_progress(current, total, operation="Processing", details=""):
    """Update progress bar and label with enhanced information"""
    if total > 0:
        progress = (current / total) * 100
        progress_var.set(progress)
        status_text = f"{operation}: {current}/{total} ({progress:.1f}%)"
        if details:
            # Truncate details if too long to prevent sidebar resizing
            max_details_length = 10
            if len(details) > max_details_length:
                details = details[:max_details_length-3] + "..."
            status_text += f" - {details}"
        progress_label.config(text=status_text, font=("Arial", 8))
    else:
        progress_var.set(0)
        progress_label.config(text=f"{operation}...", font=("Arial", 8))
    root.update_idletasks()

def reset_progress():
    """Reset progress bar"""
    progress_var.set(0)
    progress_label.config(text="Ready")

# Function for GOOGLE CLOUD STORAGE!
def get_all_blobs():
    """Returns a list of all blob names in the bucket."""
    log_message("Fetching file list from cloud storage...", "info")
    filename = list(bucket.list_blobs())
    files = [blob.name for blob in filename]
    log_message(f"Found {len(files)} files in cloud storage", "info")
    return files

def get_blob_size(blob_name):
    """Get the size of a blob in bytes"""
    blob = bucket.blob(blob_name)
    blob.reload()
    return blob.size

def download_single_blob(blob_name, local_path):
    """Downloads a single blob from the bucket with detailed logging."""
    try:
        blob = bucket.blob(blob_name)
        blob.reload()  # Get metadata including size
        file_size = blob.size
        file_size_str = format_bytes(file_size)
        
        log_message(f"Downloading: {os.path.basename(blob_name)} ({file_size_str})", "download")
        blob.download_to_filename(local_path)
        log_message(f"✓ Downloaded: {os.path.basename(blob_name)}", "success")
        
    except Exception as e:
        log_message(f"✗ Failed to download {os.path.basename(blob_name)}: {str(e)}", "error")
        raise

def get_tacz():
    """Keeps the local tacz folder in sync with the GCS bucket."""
    log_message("Starting TACZ synchronization...", "info")
    tacz_dir = os.path.join(minecraft_dir, "tacz")
    os.makedirs(tacz_dir, exist_ok=True)
    
    zip_files = [f for f in os.listdir(tacz_dir) if f.endswith('.zip')]
    gcs_files = [blob for blob in get_all_blobs() if blob.startswith('tacz/')]
    gcs_zip_files = [os.path.basename(f) for f in gcs_files]

    log_message(f"Local TACZ files: {len(zip_files)}, Cloud TACZ files: {len(gcs_zip_files)}", "info")

    total_operations = len(gcs_zip_files) + len([f for f in zip_files if f not in gcs_zip_files])
    current_op = 0

    # Download new or updated files
    downloads = 0
    for gcs_file in gcs_zip_files:
        current_op += 1
        local_path = os.path.join(tacz_dir, gcs_file)
        if gcs_file not in zip_files:
            update_progress(current_op, total_operations, "Downloading TACZ", gcs_file)
            download_single_blob(f'tacz/{gcs_file}', local_path)
            downloads += 1
        else:
            update_progress(current_op, total_operations, "Checking TACZ", gcs_file)
    
    # Delete obsolete local files
    deletions = 0
    for zip_file in zip_files:
        if zip_file not in gcs_zip_files:
            current_op += 1
            update_progress(current_op, total_operations, "Cleaning TACZ", zip_file)
            local_path = os.path.join(tacz_dir, zip_file)
            os.remove(local_path)
            log_message(f"✗ Removed obsolete file: {zip_file}", "warning")
            deletions += 1
    
    log_message(f"TACZ sync complete - Downloaded: {downloads}, Removed: {deletions}", "success")

def get_mods():
    """Keeps the mods folder in sync with the GCS bucket."""
    log_message("Starting mods synchronization...", "info")
    mods_dir = os.path.join(minecraft_dir, "mods")
    os.makedirs(mods_dir, exist_ok=True)
    
    mod_files = [f for f in os.listdir(mods_dir) if f.endswith('.jar')]
    gcs_files = [blob for blob in get_all_blobs() if blob.startswith('mods/')]
    gcs_mod_files = [os.path.basename(f) for f in gcs_files]

    log_message(f"Local mod files: {len(mod_files)}, Cloud mod files: {len(gcs_mod_files)}", "info")

    total_operations = len(gcs_mod_files) + len([f for f in mod_files if f not in gcs_mod_files])
    current_op = 0

    # Download new or updated files
    downloads = 0
    for gcs_file in gcs_mod_files:
        current_op += 1
        local_path = os.path.join(mods_dir, gcs_file)
        if gcs_file not in mod_files:
            update_progress(current_op, total_operations, "Downloading mods", gcs_file)
            download_single_blob(f'mods/{gcs_file}', local_path)
            downloads += 1
        else:
            update_progress(current_op, total_operations, "Checking mods", gcs_file)
    
    # Delete obsolete local files
    deletions = 0
    for mod_file in mod_files:
        if mod_file not in gcs_mod_files:
            current_op += 1
            update_progress(current_op, total_operations, "Cleaning mods", mod_file)
            local_path = os.path.join(mods_dir, mod_file)
            os.remove(local_path)
            log_message(f"✗ Removed obsolete mod: {mod_file}", "warning")
            deletions += 1
    
    log_message(f"Mods sync complete - Downloaded: {downloads}, Removed: {deletions}", "success")

def get_options():
    """Gets options.txt from GCS and saves it to the minecraft directory."""
    log_message("Starting options.txt download...", "info")
    update_progress(0, 3, "Preparing options")
    
    if os.path.exists(os.path.join(minecraft_dir, "options.txt")):
        os.remove(os.path.join(minecraft_dir, "options.txt"))
        log_message("Removed existing options.txt", "info")
    
    update_progress(1, 3, "Downloading options.txt")
    
    try:
        options_blob = bucket.blob('options.txt')
        options_blob.reload()
        file_size = format_bytes(options_blob.size)
        
        local_path = os.path.join(minecraft_dir, "options.txt")
        log_message(f"Downloading options.txt ({file_size})...", "download")
        options_blob.download_to_filename(local_path)
        
        update_progress(3, 3, "Options downloaded")
        log_message("✓ Options.txt downloaded successfully", "success")
        
    except Exception as e:
        log_message(f"✗ Failed to download options.txt: {str(e)}", "error")
        raise

def fresh_install():
    """Deletes the mods and tacz folders and re-downloads everything from GCS."""
    log_message("=" * 50, "info")
    log_message("STARTING FRESH INSTALL", "info")
    log_message("=" * 50, "info")
    
    mods_dir = os.path.join(minecraft_dir, "mods")
    tacz_dir = os.path.join(minecraft_dir, "tacz")
    
    update_progress(0, 6, "Starting fresh install")
    
    # Delete existing directories
    for dir_path, dir_name in [(mods_dir, "mods"), (tacz_dir, "tacz")]:
        try:
            if os.path.exists(dir_path):
                file_count = len([f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))])
                shutil.rmtree(dir_path)
                log_message(f"✗ Removed existing {dir_name} directory ({file_count} files)", "warning")
            else:
                log_message(f"No existing {dir_name} directory found", "info")
        except Exception as e:
            log_message(f"✗ Error removing {dir_name} directory: {str(e)}", "error")

    update_progress(2, 6, "Creating directories")
    
    # Recreate directories
    os.makedirs(tacz_dir, exist_ok=True)
    os.makedirs(mods_dir, exist_ok=True)
    log_message("✓ Created fresh mods and tacz directories", "success")
    
    update_progress(3, 6, "Downloading TACZ files")
    get_tacz()
    
    update_progress(4, 6, "Downloading mod files")
    get_mods()
    
    update_progress(5, 6, "Downloading options")
    get_options()
    
    update_progress(6, 6, "Fresh install complete")
    log_message("=" * 50, "success")
    log_message("FRESH INSTALL COMPLETED SUCCESSFULLY", "success")
    log_message("=" * 50, "success")

def update():
    """Updates the mods and tacz folders by syncing with GCS."""
    log_message("=" * 40, "info")
    log_message("STARTING UPDATE", "info")
    log_message("=" * 40, "info")
    
    update_progress(0, 2, "Starting update")
    get_tacz()
    update_progress(1, 2, "Updating mods")
    get_mods()
    update_progress(2, 2, "Update complete")
    
    log_message("=" * 40, "success")
    log_message("UPDATE COMPLETED SUCCESSFULLY", "success")
    log_message("=" * 40, "success")

# Enhanced Tkinter GUI functions
def run_fresh_install():
    result = messagebox.askyesno(
        "Confirm Fresh Install", 
        "⚠️ WARNING: This will DELETE all existing mods and TACZ files!\n\n"
        "• All current mods will be removed\n"
        "• All current TACZ files will be removed\n"
        "• Fresh copies will be downloaded from the server\n\n"
        "Are you sure you want to continue?",
        icon="warning"
    )
    
    if not result:
        log_message("Fresh install cancelled by user", "info")
        return
    
    def task():
        try:
            fresh_install()
            messagebox.showinfo("Success", "✅ Fresh install completed successfully!\n\nAll mods and files have been updated.")
        except Exception as e:
            log_message(f"✗ Fresh install failed: {str(e)}", "error")
            messagebox.showerror("Error", f"❌ Fresh install failed:\n\n{str(e)}")
        finally:
            btn_fresh_install.config(state="normal")
            reset_progress()
    
    btn_fresh_install.config(state="disabled")
    threading.Thread(target=task, daemon=True).start()

def run_update():
    def task():
        try:
            update()
            messagebox.showinfo("Success", "✅ Update completed successfully!\n\nAll files are now synchronized.")
        except Exception as e:
            log_message(f"✗ Update failed: {str(e)}", "error")
            messagebox.showerror("Error", f"❌ Update failed:\n\n{str(e)}")
        finally:
            btn_update.config(state="normal")
            reset_progress()
    
    btn_update.config(state="disabled")
    threading.Thread(target=task, daemon=True).start()

def run_get_options():
    result = messagebox.askyesno(
        "Confirm Options Download", 
        "⚠️ This will REPLACE your current options.txt file!\n\n"
        "• Your current game settings will be overwritten\n"
        "• Server-optimized settings will be applied\n\n"
        "Are you sure you want to continue?",
        icon="warning"
    )
    
    if not result:
        log_message("Options download cancelled by user", "info")
        return
    
    def task():
        try:
            get_options()
            messagebox.showinfo("Success", "✅ Options.txt downloaded successfully!\n\nGame settings have been updated.")
        except Exception as e:
            log_message(f"✗ Download options failed: {str(e)}", "error")
            messagebox.showerror("Error", f"❌ Download options failed:\n\n{str(e)}")
        finally:
            btn_get_options.config(state="normal")
            reset_progress()
    
    btn_get_options.config(state="disabled")
    threading.Thread(target=task, daemon=True).start()

def clear_logs():
    """Clear the log area"""
    log_text.config(state="normal")
    log_text.delete(1.0, tk.END)
    log_text.config(state="disabled")
    log_message("Log area cleared", "info")

# Create main window with enhanced styling
root = tk.Tk()
root.title("🎮 Mod Manager Thing")
root.geometry("1000x700")
root.resizable(True, True)
root.configure(bg="#f5f5f5")

# Configure style
style = ttk.Style()
style.theme_use('clam')

# Configure custom styles
style.configure("Title.TLabel", font=("Arial", 16, "bold"), background="#f5f5f5")
style.configure("Header.TLabelframe.Label", font=("Arial", 10, "bold"))
style.configure("Success.TButton", foreground="white")

# Create main frame
main_frame = ttk.Frame(root, padding="15")
main_frame.pack(fill=tk.BOTH, expand=True)

# Left panel for controls (enhanced)
left_frame = ttk.LabelFrame(main_frame, text="🎛️ Control Panel", padding="15", style="Header.TLabelframe")
left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

# Right panel for logs (enhanced)
right_frame = ttk.LabelFrame(main_frame, text="📋 Activity Logs", padding="15", style="Header.TLabelframe")
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

# Enhanced title with icon
title_label = ttk.Label(left_frame, text="🎮 Minecraft Mod Manager", style="Title.TLabel")
title_label.pack(pady=(0, 25))

# Directory selection section
dir_frame = ttk.LabelFrame(left_frame, text="📁 Directory Setup", padding="10")
dir_frame.pack(fill=tk.X, pady=(0, 20))

btn_select_dir = ttk.Button(dir_frame, text="📂 Select Minecraft Directory", command=select_minecraft_directory, width=28)
btn_select_dir.pack(pady=(0, 10))

# Create tooltip for select directory button
ToolTip(btn_select_dir, "Select your Minecraft installation directory\n(Usually in %appdata%/.minecraft)")

dir_label = ttk.Label(dir_frame, text="No directory selected", font=("Arial", 9), foreground="gray", wraplength=250)
dir_label.pack()

# Enhanced progress frame
progress_frame = ttk.LabelFrame(left_frame, text="📊 Progress", padding="15")
progress_frame.pack(fill=tk.X, pady=(0, 20))

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100, length=250)
progress_bar.pack(fill=tk.X, pady=(0, 8))

progress_label = ttk.Label(progress_frame, text="Ready", font=("Arial", 9))
progress_label.pack()

# Action buttons section
action_frame = ttk.LabelFrame(left_frame, text="🚀 Actions", padding="15")
action_frame.pack(fill=tk.X, pady=(0, 15))

# Fresh Install button with enhanced styling
btn_fresh_install = ttk.Button(action_frame, text="🔄 Fresh Install", command=run_fresh_install, width=28, state="disabled")
btn_fresh_install.pack(pady=(0, 8))
ToolTip(btn_fresh_install, "Completely removes all existing mods and TACZ files,\nthen downloads fresh copies from the server.\n\n⚠️ This will delete all current mod files!")

# Update button
btn_update = ttk.Button(action_frame, text="⬇️ Update", command=run_update, width=28, state="disabled")
btn_update.pack(pady=(0, 8))
ToolTip(btn_update, "Synchronizes your mods and TACZ files with the server.\nOnly downloads new or changed files.\n\n✅ Safe operation - keeps existing files if unchanged")

# Get Options button
btn_get_options = ttk.Button(action_frame, text="⚙️ Get Options", command=run_get_options, width=28, state="disabled")
btn_get_options.pack()
ToolTip(btn_get_options, "Downloads the server's optimized options.txt file.\nThis will replace your current game settings.\n\n⚠️ Your current settings will be overwritten!")

# Log controls frame
log_controls_frame = ttk.Frame(right_frame)
log_controls_frame.pack(fill=tk.X, pady=(0, 10))

# Clear logs button
btn_clear_logs = ttk.Button(log_controls_frame, text="🗑️ Clear Logs", command=clear_logs)
btn_clear_logs.pack(side=tk.RIGHT)
ToolTip(btn_clear_logs, "Clear all messages from the log area")

# Enhanced log text area
log_frame = ttk.Frame(right_frame)
log_frame.pack(fill=tk.BOTH, expand=True)

log_text = scrolledtext.ScrolledText(
    log_frame, 
    state="disabled", 
    wrap=tk.WORD, 
    width=60, 
    height=35,
    font=("Consolas", 9),
    bg="#1e1e1e",
    fg="#ffffff",
    selectbackground="#404040"
)
log_text.pack(fill=tk.BOTH, expand=True)

# Initial enhanced log message
log_message("🎮 Minecraft Mod Manager started", "success")
log_message("Please select your Minecraft directory to begin", "info")

# Start the GUI
root.mainloop()