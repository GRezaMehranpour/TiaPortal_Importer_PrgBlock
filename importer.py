import os
import sys
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue

# --- Setup TIA Scripting API ---
try:
    import siemens_tia_scripting as ts
except ImportError:
    logging.critical("siemens_tia_scripting could not be found.")
    messagebox.showerror("Fatal Error", "Could not import the TIA Scripting library.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(threadName)s - %(message)s",
    handlers=[
        logging.FileHandler("importer.log", mode='w'),
        logging.StreamHandler()
    ]
)

class TIA_ImporterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TIA Portal Project Importer")
        self.root.geometry("800x300")

        # --- GUI Layout ---
        path_frame = ttk.LabelFrame(root, text="Project and Source Settings")
        path_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        path_frame.grid_columnconfigure(1, weight=1)

        tk.Label(path_frame, text="Target TIA Project:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.path_entry = tk.Entry(path_frame, width=70)
        self.path_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.browse_project_btn = tk.Button(path_frame, text="Browse...", command=self.select_project_file)
        self.browse_project_btn.grid(row=0, column=2, padx=5, pady=5)

        tk.Label(path_frame, text="Source Export Folder:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.import_dir_entry = tk.Entry(path_frame, width=70)
        self.import_dir_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.browse_import_btn = tk.Button(path_frame, text="Browse...", command=self.select_import_dir)
        self.browse_import_btn.grid(row=1, column=2, padx=5, pady=5)
        
        control_frame = ttk.Frame(root)
        control_frame.grid(row=2, column=0, pady=20)
        
        self.run_btn = tk.Button(control_frame, text="Import All Blocks from Source Folder", command=self.start_import_thread, font=("Segoe UI", 10, "bold"))
        self.run_btn.pack()
        
        status_frame = ttk.Frame(root)
        status_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        self.status_label = tk.Label(status_frame, text="Status: Ready", wraplength=780, justify=tk.LEFT)
        self.status_label.pack(fill=tk.X)
        self.progress_bar = ttk.Progressbar(status_frame, length=780, mode="indeterminate")
        
        self.version = "17.0"
        self.queue = queue.Queue()
        self.is_running = False

    def select_project_file(self):
        file_path = filedialog.askopenfilename(title="Select Target TIA Portal Project File", filetypes=[("TIA Portal Project", "*.ap*")])
        if file_path: self.path_entry.delete(0, tk.END); self.path_entry.insert(0, file_path)

    def select_import_dir(self):
        dir_path = filedialog.askdirectory(title="Select Source Folder Containing Exported Blocks")
        if dir_path: self.import_dir_entry.delete(0, tk.END); self.import_dir_entry.insert(0, dir_path)

    def set_ui_state(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.run_btn.config(state=state)
        self.browse_project_btn.config(state=state)
        self.browse_import_btn.config(state=state)

    def start_import_thread(self):
        if self.is_running: return
        project_file_path = self.path_entry.get()
        import_root_dir = self.import_dir_entry.get()

        if not project_file_path or not os.path.isfile(project_file_path):
            messagebox.showerror("Error", "Please provide a valid TIA Portal project file.")
            return
        if not import_root_dir or not os.path.isdir(import_root_dir):
            messagebox.showerror("Error", "Please provide a valid source directory for import.")
            return

        self.is_running = True
        self.set_ui_state(False)
        self.status_label.config(text="Status: Starting import process...")
        self.progress_bar.pack(fill=tk.X, pady=5)
        self.progress_bar.start(10)
        
        thread = threading.Thread(target=self._import_worker, args=(project_file_path, import_root_dir), daemon=True)
        thread.start()
        self.process_queue()

    def _import_worker(self, project_file_path, import_root_dir):
        portal = None
        try:
            self.queue.put(('status', f"Connecting to TIA Portal V{self.version}..."))
            portal = ts.open_portal(ts.Enums.PortalMode.WithGraphicalUserInterface, version=self.version)
            
            self.queue.put(('status', f"Opening project: {os.path.basename(project_file_path)}..."))
            project = portal.open_project(project_file_path=project_file_path)
            
            plcs = project.get_plcs()
            if not plcs:
                self.queue.put(('error', "No PLCs found in the target project."))
                return
            
            target_plc = plcs[0]
            self.queue.put(('status', f"Preparing to import into PLC: {target_plc.get_name()}..."))

            # --- REVISED AND CORRECTED IMPORT LOGIC ---

            # 1. Get the PlcSoftware object from the PLC
            plc_software = target_plc.get_plc_software()
            if not plc_software:
                 self.queue.put(('error', f"Could not access the software container for PLC {target_plc.get_name()}."))
                 return
                 
            # 2. Get the main "Program blocks" group from the PlcSoftware object
            program_blocks_group = plc_software.get_block_group()
            if not program_blocks_group:
                self.queue.put(('error', f"Could not find the 'Program blocks' folder in PLC {target_plc.get_name()}."))
                return

            # 3. Find all XML files to be imported
            xml_files_to_import = []
            for root, _, files in os.walk(import_root_dir):
                for file in files:
                    if file.lower().endswith('.xml'):
                        xml_files_to_import.append(os.path.join(root, file))
            
            if not xml_files_to_import:
                self.queue.put(('error', "No .xml files found in the source directory."))
                return
            
            # 4. Process each file individually
            self.queue.put(('status', f"Importing {len(xml_files_to_import)} blocks..."))
            for xml_file_path in xml_files_to_import:
                # 5. Determine the target group path within TIA
                relative_path = os.path.relpath(os.path.dirname(xml_file_path), import_root_dir)
                target_group_path = ""
                if relative_path and relative_path != '.':
                     target_group_path = relative_path.replace(os.path.sep, '\\')

                target_group = program_blocks_group
                # If the block was in a subfolder, create that group structure
                if target_group_path:
                    logging.info(f"Creating/getting group: '{target_group_path}'")
                    target_group = program_blocks_group.create_group(group_name=target_group_path)

                # 6. Import the block into the correct target group
                logging.info(f"Importing '{os.path.basename(xml_file_path)}' into group '{target_group.get_name()}'")
                target_group.import_block(source_file_path=xml_file_path)

            # -------------------------------------------
            
            self.queue.put(('finished', "Import process completed successfully. Please check TIA Portal for results."))

        except Exception as e:
            self.queue.put(('error', f"An error occurred: {str(e)}"))
        finally:
            # We leave the portal open for the user to inspect the results
            pass

    def process_queue(self):
        try:
            while True:
                msg_type, data = self.queue.get_nowait()
                if msg_type == 'status': self.status_label.config(text=f"Status: {data}")
                elif msg_type == 'finished':
                    self.progress_bar.stop()
                    self.progress_bar.pack_forget()
                    self.status_label.config(text=f"Status: {data}")
                    messagebox.showinfo("Success", data)
                    self.is_running = False
                    self.set_ui_state(True)
                elif msg_type == 'error':
                    self.progress_bar.stop()
                    self.progress_bar.pack_forget()
                    self.status_label.config(text=f"Status: Error - {data}")
                    messagebox.showerror("Error", data)
                    self.is_running = False
                    self.set_ui_state(True)
        except queue.Empty:
            pass
        finally:
            if self.is_running: self.root.after(100, self.process_queue)

def main():
    root = tk.Tk()
    app = TIA_ImporterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()