import tkinter as tk
from tkinter import messagebox, ttk
import database

class PasswordManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Desktop Password Manager")
        self.root.geometry("620x520")
        self.root.resizable(False, False)

        self.cipher = None
        database.init_db()
        self.show_login_screen()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    # --- Screen 1: Login & Master Password Setup ---
    def show_login_screen(self):
        self.clear_screen()
        self.cipher = None

        frame = tk.Frame(self.root, padx=30, pady=30)
        frame.pack(expand=True)

        is_setup = not database.is_master_set()
        title_text = "Set Up Master Password" if is_setup else "Master Password Login"
        btn_text = "Create Vault" if is_setup else "Unlock Vault"

        tk.Label(frame, text=title_text, font=("Arial", 16, "bold")).pack(pady=10)

        self.password_entry = tk.Entry(frame, show="*", width=30, font=("Arial", 12))
        self.password_entry.pack(pady=10)
        self.password_entry.focus()

        action = self.handle_setup if is_setup else self.handle_login
        tk.Button(frame, text=btn_text, command=action, width=15, height=2, bg="#007acc", fg="white").pack(pady=10)
        self.root.bind("<Return>", lambda event: action())

    def handle_setup(self):
        pwd = self.password_entry.get().strip()
        if not pwd:
            messagebox.showwarning("Warning", "Password cannot be empty.")
            return
        database.setup_master_password(pwd)
        messagebox.showinfo("Success", "Master password set successfully! Please log in.")
        self.show_login_screen()

    def handle_login(self):
        pwd = self.password_entry.get().strip()
        valid, cipher = database.verify_master_password(pwd)
        if valid:
            self.cipher = cipher
            self.show_vault_screen()
        else:
            messagebox.showerror("Error", "Invalid master password.")
            self.password_entry.delete(0, tk.END)

    # --- Screen 2: Vault Dashboard ---
    def show_vault_screen(self):
        self.clear_screen()
        self.root.unbind("<Return>")

        # Top Bar
        top_bar = tk.Frame(self.root, pady=10, padx=15)
        top_bar.pack(fill="x")
        tk.Label(top_bar, text="Password Vault", font=("Arial", 14, "bold")).pack(side="left")
        tk.Button(top_bar, text="Logout", command=self.show_login_screen, bg="#d9534f", fg="white").pack(side="right")

        # Entry Form
        form_frame = tk.LabelFrame(self.root, text="Add New Credential", padx=10, pady=10)
        form_frame.pack(fill="x", padx=15, pady=5)

        tk.Label(form_frame, text="Service:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.service_entry = tk.Entry(form_frame, width=18)
        self.service_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Username:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.user_entry = tk.Entry(form_frame, width=18)
        self.user_entry.grid(row=0, column=3, padx=5, pady=5)

        tk.Label(form_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.pass_entry = tk.Entry(form_frame, width=18, show="*")
        self.pass_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Button(form_frame, text="Save", command=self.handle_add_entry, bg="#5cb85c", fg="white", width=12).grid(row=1, column=3, padx=5, pady=5)

        # Table View
        table_frame = tk.Frame(self.root, padx=15, pady=10)
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "service", "username", "password")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
        self.tree.heading("id", text="ID")
        self.tree.heading("service", text="Service")
        self.tree.heading("username", text="Username / Email")
        self.tree.heading("password", text="Password")

        self.tree.column("id", width=35, anchor="center")
        self.tree.column("service", width=150)
        self.tree.column("username", width=180)
        self.tree.column("password", width=160)
        self.tree.pack(fill="both", expand=True)

        # Bottom Actions
        bottom_frame = tk.Frame(self.root, pady=10)
        bottom_frame.pack(fill="x", padx=15)
        tk.Button(bottom_frame, text="Copy Selected Password", command=self.handle_copy_password).pack(side="left", padx=5)
        tk.Button(bottom_frame, text="Delete Selected", command=self.handle_delete_entry, bg="#f0ad4e").pack(side="right", padx=5)

        self.refresh_table()

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in database.get_all_credentials(self.cipher):
            self.tree.insert("", "end", values=item)

    def handle_add_entry(self):
        service = self.service_entry.get().strip()
        user = self.user_entry.get().strip()
        pwd = self.pass_entry.get().strip()

        if not (service and user and pwd):
            messagebox.showwarning("Incomplete", "Please fill in all three fields.")
            return

        database.add_credential(self.cipher, service, user, pwd)
        self.service_entry.delete(0, tk.END)
        self.user_entry.delete(0, tk.END)
        self.pass_entry.delete(0, tk.END)
        self.refresh_table()

    def handle_delete_entry(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Row", "Please select an entry to delete.")
            return
        item_id = self.tree.item(selected[0])["values"][0]
        database.delete_credential(item_id)
        self.refresh_table()

    def handle_copy_password(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Row", "Please select an entry to copy its password.")
            return
        password = self.tree.item(selected[0])["values"][3]
        self.root.clipboard_clear()
        self.root.clipboard_append(password)
        messagebox.showinfo("Copied", "Password copied to clipboard.")

if __name__ == "__main__":
    root = tk.Tk()
    app = PasswordManagerApp(root)
    root.mainloop()