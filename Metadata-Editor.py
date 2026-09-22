import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import os
import mutagen
from mutagen.easyid3 import EasyID3

# --- File Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILES_FILE = os.path.join(SCRIPT_DIR, "profiles.json")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

AVAILABLE_KEYS = sorted(list(EasyID3.valid_keys.keys()))

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.title("Settings - Hide Fields")
        self.geometry("350x500")
        self.main_app = main_app
        
        self.check_vars = {}

        tk.Label(self, text="Select fields to HIDE from the main interface:", pady=10).pack()

        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        current_hidden = self.main_app.app_config.get("hidden_fields", [])
        
        for key in AVAILABLE_KEYS:
            var = tk.BooleanVar(value=(key in current_hidden))
            self.check_vars[key] = var
            chk = tk.Checkbutton(self.scroll_frame, text=key, variable=var)
            chk.pack(anchor="w", padx=10)

        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=10)
        tk.Button(btn_frame, text="Save Settings", command=self.save_settings, bg="lightblue").pack()

    def save_settings(self):
        hidden_fields = [key for key, var in self.check_vars.items() if var.get()]
        self.main_app.app_config["hidden_fields"] = hidden_fields
        self.main_app.save_app_config()
        
        if self.main_app.filepath:
            self.main_app.load_metadata()
            
        self.destroy()

class ProfileEditorWindow(tk.Toplevel):
    def __init__(self, parent, main_app, profile_name=None):
        super().__init__(parent)
        self.title("Profile Editor")
        self.geometry("500x400")
        self.main_app = main_app
        
        self.profile_name = tk.StringVar(value=profile_name if profile_name else "New Profile")
        self.profile_data = self.main_app.profiles.get(profile_name, {}) if profile_name else {}
        self.row_widgets = {}

        top_frame = tk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(top_frame, text="Profile Name:").pack(side=tk.LEFT)
        tk.Entry(top_frame, textvariable=self.profile_name).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", width=480)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.scroll_frame.columnconfigure(1, weight=1)

        bottom_frame = tk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)

        self.key_combobox = ttk.Combobox(bottom_frame, values=AVAILABLE_KEYS, state="readonly", width=15)
        self.key_combobox.pack(side=tk.LEFT, padx=5)
        if AVAILABLE_KEYS:
            self.key_combobox.set(AVAILABLE_KEYS[0])

        tk.Button(bottom_frame, text="Add Line", command=self.add_line).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(self, text="Save Profile", command=self.save_profile, bg="lightgreen").pack(pady=10)

        self.render_all_lines()

    def render_all_lines(self):
        for widget_tuple in self.row_widgets.values():
            for w in widget_tuple:
                w.destroy()
        self.row_widgets.clear()

        row = 0
        for key, value in self.profile_data.items():
            self._create_row_ui(row, key, value)
            row += 1

    def _create_row_ui(self, row_index, key, value=""):
        lbl = tk.Label(self.scroll_frame, text=f"{key}:", width=15, anchor='e')
        lbl.grid(row=row_index, column=0, padx=5, pady=2, sticky="e")

        entry = tk.Entry(self.scroll_frame)
        entry.insert(0, value)
        entry.grid(row=row_index, column=1, padx=5, pady=2, sticky="ew")

        del_btn = tk.Button(self.scroll_frame, text="Delete", command=lambda k=key: self.delete_line(k))
        del_btn.grid(row=row_index, column=2, padx=5, pady=2)

        self.row_widgets[key] = (lbl, entry, del_btn)

    def add_line(self):
        key = self.key_combobox.get()
        if not key or key in self.row_widgets:
            return 
        self.profile_data[key] = ""
        self.render_all_lines()
        self.canvas.yview_moveto(1.0)

    def delete_line(self, key):
        if key in self.profile_data:
            del self.profile_data[key]
        self.render_all_lines()

    def save_profile(self):
        name = self.profile_name.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Profile name cannot be empty.", parent=self)
            return

        updated_data = {}
        for key, widgets in self.row_widgets.items():
            updated_data[key] = widgets[1].get().strip()

        self.main_app.profiles[name] = updated_data
        self.main_app.save_profiles()
        self.main_app.refresh_profile_list()
        self.destroy()

class MetadataEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Music Metadata Editor Pro")
        self.root.geometry("850x600")
        
        self.audio_file = None
        self.filepath = ""
        self.entries = {}
        
        # Folder state tracking
        self.folder_files = []
        self.current_file_index = -1
        
        self.profiles = self.load_json(PROFILES_FILE, default_type={})
        self.app_config = self.load_json(CONFIG_FILE, default_type={"hidden_fields": []})

        self._setup_menu()

        self.paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.left_pane = tk.Frame(self.paned_window, width=250)
        self.paned_window.add(self.left_pane, weight=1)

        self.right_pane = tk.Frame(self.paned_window)
        self.paned_window.add(self.right_pane, weight=3)

        self._setup_left_pane()
        self._setup_right_pane()

    def _setup_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Settings", command=self.open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menubar)

    def _setup_left_pane(self):
        tk.Label(self.left_pane, text="Artist Profiles", font=("Arial", 12, "bold")).pack(pady=5)
        
        list_frame = tk.Frame(self.left_pane)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.profile_listbox = tk.Listbox(list_frame, exportselection=False)
        list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.profile_listbox.yview)
        self.profile_listbox.configure(yscrollcommand=list_scroll.set)
        
        self.profile_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.profile_listbox.bind('<<ListboxSelect>>', self.apply_profile)

        btn_frame = tk.Frame(self.left_pane)
        btn_frame.pack(fill=tk.X, pady=10)
        tk.Button(btn_frame, text="New Profile", command=self.open_profile_editor).pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="Edit Selected", command=self.edit_selected_profile).pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="Delete Selected", command=self.delete_selected_profile).pack(fill=tk.X, pady=2)

        self.refresh_profile_list()

    def _setup_right_pane(self):
        top_frame = tk.Frame(self.right_pane)
        top_frame.pack(fill=tk.X, pady=5)
        
        # --- Row 1: Primary Controls ---
        controls_frame = tk.Frame(top_frame)
        controls_frame.pack(fill=tk.X)

        self.browse_btn = tk.Button(controls_frame, text="Browse File", command=self.browse_file)
        self.browse_btn.pack(side=tk.LEFT, padx=5)

        self.browse_folder_btn = tk.Button(controls_frame, text="Browse Folder", command=self.browse_folder)
        self.browse_folder_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = tk.Button(controls_frame, text="Save Metadata", command=self.save_metadata, state=tk.DISABLED, bg="lightblue")
        self.save_btn.pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(controls_frame, text="", font=("Arial", 10, "bold"))
        self.status_label.pack(side=tk.LEFT, padx=10)

        # --- Row 2: Folder Navigation ---
        nav_frame = tk.Frame(top_frame)
        nav_frame.pack(fill=tk.X, pady=5)
        
        self.prev_btn = tk.Button(nav_frame, text="Previous File", command=self.prev_file, state=tk.DISABLED)
        self.prev_btn.pack(side=tk.LEFT, padx=5)

        self.next_btn = tk.Button(nav_frame, text="Next File", command=self.next_file, state=tk.DISABLED)
        self.next_btn.pack(side=tk.RIGHT, padx=5)

        # --- Row 3: File Path Label ---
        # Note: height=1 ensures this label truncates horizontally instead of expanding down
        self.file_label = tk.Label(top_frame, text="No file selected", anchor="w", justify=tk.LEFT, height=1)
        self.file_label.pack(fill=tk.X, padx=5, pady=(0, 5))

        # --- Metadata Canvas ---
        self.canvas = tk.Canvas(self.right_pane)
        self.scrollbar = ttk.Scrollbar(self.right_pane, orient="vertical", command=self.canvas.yview)
        self.fields_frame = tk.Frame(self.canvas)

        self.fields_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.fields_frame, anchor="nw")
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.fields_frame.columnconfigure(1, weight=1)

    # --- Config & File Management ---
    def load_json(self, filepath, default_type):
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return default_type

    def save_profiles(self):
        try:
            with open(PROFILES_FILE, 'w') as f:
                json.dump(self.profiles, f, indent=4)
        except PermissionError:
            messagebox.showerror("Error", "Permission Denied. Cannot save profiles.json.")

    def save_app_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.app_config, f, indent=4)
        except PermissionError:
            messagebox.showerror("Error", "Permission Denied. Cannot save config.json.")

    # --- App Logic Methods ---
    def open_settings(self):
        SettingsWindow(self.root, self)

    def refresh_profile_list(self):
        self.profile_listbox.delete(0, tk.END)
        for profile_name in sorted(self.profiles.keys()):
            self.profile_listbox.insert(tk.END, profile_name)

    def open_profile_editor(self):
        ProfileEditorWindow(self.root, self)

    def edit_selected_profile(self):
        selection = self.profile_listbox.curselection()
        if selection:
            ProfileEditorWindow(self.root, self, self.profile_listbox.get(selection[0]))

    def delete_selected_profile(self):
        selection = self.profile_listbox.curselection()
        if selection:
            profile_name = self.profile_listbox.get(selection[0])
            if messagebox.askyesno("Confirm", f"Delete profile '{profile_name}'?"):
                del self.profiles[profile_name]
                self.save_profiles()
                self.refresh_profile_list()

    def mark_unsaved(self, event=None):
        if self.audio_file:
            self.status_label.config(text="EDITS", fg="red")

    def apply_profile(self, event):
        selection = self.profile_listbox.curselection()
        if not selection or not self.audio_file: return
        profile_data = self.profiles.get(self.profile_listbox.get(selection[0]), {})
        
        changes_made = False
        for key, value in profile_data.items():
            if key in self.entries:
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, value)
                changes_made = True
                
        if changes_made:
            self.mark_unsaved()

    # --- File & Folder Browsing ---
    def browse_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.flac *.ogg *.m4a"), ("All Files", "*.*")])
        if filepath:
            self.folder_files = [] # Clear folder state
            self.current_file_index = -1
            self.toggle_nav_buttons()
            
            self.filepath = filepath
            self.load_metadata()

    def browse_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            valid_exts = ('.mp3', '.flac', '.ogg', '.m4a')
            self.folder_files = [
                os.path.join(folder_path, f) 
                for f in os.listdir(folder_path) 
                if f.lower().endswith(valid_exts)
            ]
            
            if self.folder_files:
                self.folder_files.sort() # Alphabetical order
                self.current_file_index = 0
                self.filepath = self.folder_files[self.current_file_index]
                self.toggle_nav_buttons()
                self.load_metadata()
            else:
                messagebox.showinfo("Info", "No supported audio files found in this folder.")
                self.folder_files = []
                self.current_file_index = -1
                self.toggle_nav_buttons()

    def toggle_nav_buttons(self):
        """Enables or disables navigation buttons based on the folder state."""
        if len(self.folder_files) > 1:
            self.prev_btn.config(state=tk.NORMAL)
            self.next_btn.config(state=tk.NORMAL)
        else:
            self.prev_btn.config(state=tk.DISABLED)
            self.next_btn.config(state=tk.DISABLED)

    def next_file(self):
        if self.folder_files:
            # Move to next index and wrap around to the start if at the end
            self.current_file_index = (self.current_file_index + 1) % len(self.folder_files)
            self.filepath = self.folder_files[self.current_file_index]
            self.load_metadata()

    def prev_file(self):
        if self.folder_files:
            # Move to previous index and wrap around to the end if at the start
            self.current_file_index = (self.current_file_index - 1) % len(self.folder_files)
            self.filepath = self.folder_files[self.current_file_index]
            self.load_metadata()

    # --- Loading & Saving Metadata ---
    def load_metadata(self):
        for widget in self.fields_frame.winfo_children():
            widget.destroy()
        self.entries.clear()
        
        # Display current file name (or path)
        self.file_label.config(text=f"{self.current_file_index + 1}/{len(self.folder_files)} - {self.filepath}" if self.folder_files else self.filepath)
        self.status_label.config(text="")

        try:
            if self.filepath.lower().endswith('.mp3'):
                try: self.audio_file = EasyID3(self.filepath)
                except mutagen.id3.ID3NoHeaderError:
                    self.audio_file = mutagen.File(self.filepath, easy=True)
                    self.audio_file.add_tags()
                keys_to_display = AVAILABLE_KEYS
            else:
                self.audio_file = mutagen.File(self.filepath)
                if self.audio_file is None: return
                keys_to_display = sorted(list(set(list(self.audio_file.keys()) + ['title', 'artist', 'album', 'date', 'genre', 'tracknumber'])))

            hidden_fields = self.app_config.get("hidden_fields", [])
            keys_to_display = [key for key in keys_to_display if key not in hidden_fields]

            row = 0
            for key in keys_to_display:
                tk.Label(self.fields_frame, text=f"{key}:", width=15, anchor='e').grid(row=row, column=0, padx=5, pady=2, sticky="e")
                entry = tk.Entry(self.fields_frame)
                entry.grid(row=row, column=1, padx=5, pady=2, sticky="ew")
                
                if key in self.audio_file:
                    entry.insert(0, self.audio_file[key][0])
                
                entry.bind("<KeyRelease>", self.mark_unsaved)
                
                self.entries[key] = entry
                row += 1

            self.save_btn.config(state=tk.NORMAL)
            self.canvas.yview_moveto(0)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{e}")

    def save_metadata(self):
        if not self.audio_file: return
        try:
            for key, entry_widget in self.entries.items():
                new_value = entry_widget.get().strip()
                if new_value: self.audio_file[key] = [new_value]
                elif key in self.audio_file: del self.audio_file[key]

            self.audio_file.save()
            self.status_label.config(text="SAVED", fg="green")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save metadata:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MetadataEditorApp(root)
    root.mainloop()