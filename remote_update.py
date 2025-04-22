import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, filedialog
import sqlite3
import os
import tempfile
import requests
import re
import json
import time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

class PokemonAliasManager:
    def __init__(self, root, drive_url, credentials_file=None):
        self.root = root
        self.drive_url = drive_url
        self.credentials_file = credentials_file
        self.service = None
        
        # Extract file ID from the URL
        file_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', self.drive_url)
        if file_id_match:
            self.file_id = file_id_match.group(1)
        else:
            raise ValueError("Invalid Google Drive URL. Could not extract file ID.")
        
        # Create a temporary file to store the database
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Setup Google Drive service if credentials file is provided
        if credentials_file and os.path.exists(credentials_file):
            self.setup_drive_service(credentials_file)
        
        # Download the database from Google Drive
        self.download_db()
        
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.selected_pokemon = None
        self.selected_alias = None
        
        # Add a status bar to show sync status
        self.status_var = tk.StringVar()
        self.status_var.set("データベースが正常にダウンロードされました")
        
        self.setup_ui()
    
    def setup_drive_service(self, credentials_file):
        """Setup Google Drive API service."""
        try:
            # Load credentials from the service account file
            scopes = ['https://www.googleapis.com/auth/drive']
            credentials = Credentials.from_service_account_file(credentials_file, scopes=scopes)
            
            # Build the Drive API service
            self.service = build('drive', 'v3', credentials=credentials)
            return True
        except Exception as e:
            messagebox.showerror("API認証エラー", f"Google Drive APIの認証に失敗しました: {str(e)}")
            return False

    def setup_ui(self):
        self.root.title("エイリアスの更新 (Google Drive)")
        self.root.geometry("500x450")  # ウィンドウサイズを少し大きく

        # Pokemon selection with autocomplete
        tk.Label(self.root, text="ポケモンを選択").grid(row=0, column=0, padx=5, pady=5)
        self.pokemon_var = tk.StringVar()
        self.pokemon_entry = ttk.Combobox(self.root, textvariable=self.pokemon_var, width=30)
        self.pokemon_entry.grid(row=0, column=1, padx=5, pady=5)
        self.pokemon_entry.bind("<KeyRelease>", self.suggest_pokemon)
        self.pokemon_entry.bind("<<ComboboxSelected>>", self.select_pokemon)

        # Alias display
        tk.Label(self.root, text="すがた:").grid(row=2, column=0, padx=5, pady=5)
        self.form_var = tk.StringVar()
        self.form_var.trace('w', self.update_alias_list)
        self.form_option = tk.OptionMenu(self.root, self.form_var, "")
        self.form_option.grid(row=2, column=1, padx=5, pady=5)

        self.alias_listbox = tk.Listbox(self.root, width=40, height=10)
        self.alias_listbox.grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        self.alias_listbox.bind("<Button-3>", self.show_alias_options)

        # Buttons
        button_frame = tk.Frame(self.root)
        button_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5)
        
        tk.Button(button_frame, text="別名の追加", command=self.add_alias).grid(row=0, column=0, padx=5, pady=5)
        tk.Button(button_frame, text="別名の削除", command=self.delete_alias).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(button_frame, text="ローカルに保存", command=self.save_local).grid(row=0, column=2, padx=5, pady=5)
        
        # Google Drive sync buttons
        drive_frame = tk.Frame(self.root)
        drive_frame.grid(row=5, column=0, columnspan=2, padx=5, pady=5)
        
        # Only show upload button if API is configured
        if self.service:
            tk.Button(drive_frame, text="Google Driveに保存", command=self.upload_to_drive).grid(row=0, column=0, padx=5, pady=5)
            tk.Button(drive_frame, text="最新版を取得", command=self.refresh_from_drive).grid(row=0, column=1, padx=5, pady=5)
        else:
            tk.Label(drive_frame, text="Google Drive APIが設定されていません。認証情報が必要です。").grid(row=0, column=0, columnspan=2, padx=5, pady=5)
            tk.Button(drive_frame, text="認証情報を設定", command=self.set_credentials).grid(row=1, column=0, columnspan=2, padx=5, pady=5)
        
        # Status bar
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=6, column=0, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=5)

    def download_db(self):
        """Download the database from Google Drive."""
        try:
            if self.service:
                # Download using Google Drive API
                request = self.service.files().get_media(fileId=self.file_id)
                fh = io.FileIO(self.db_path, 'wb')
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                fh.close()
                self.status_var.set("データベースが正常にダウンロードされました")
            else:
                # Fallback to direct download link
                download_url = f"https://drive.google.com/uc?id={self.file_id}&export=download"
                
                # Download the file
                response = requests.get(download_url)
                
                if response.status_code == 200:
                    with open(self.db_path, 'wb') as f:
                        f.write(response.content)
                    self.status_var.set("データベースが正常にダウンロードされました (API未使用)")
                else:
                    raise Exception(f"ダウンロードエラー: {response.status_code}")
                
        except Exception as e:
            self.status_var.set(f"エラー: {str(e)}")
            messagebox.showerror("ダウンロードエラー", f"データベースのダウンロードに失敗しました: {str(e)}")

    def save_local(self):
        """Save the database to a local file."""
        # Commit any pending transactions
        self.conn.commit()
        
        # Ask for a location to save
        file_path = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
            title="データベースを保存"
        )
        
        if file_path:
            try:
                # Copy the database to the selected location
                with open(self.db_path, 'rb') as src, open(file_path, 'wb') as dst:
                    dst.write(src.read())
                
                self.status_var.set(f"データベースが {file_path} に保存されました")
                messagebox.showinfo("成功", f"データベースが {file_path} に正常に保存されました")
            except Exception as e:
                self.status_var.set(f"エラー: {str(e)}")
                messagebox.showerror("保存エラー", f"データベースの保存に失敗しました: {str(e)}")
                
    def set_credentials(self):
        """Allow the user to select a credentials file."""
        credentials_path = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Google DriveのAPI認証情報を選択"
        )
        
        if credentials_path and os.path.exists(credentials_path):
            if self.setup_drive_service(credentials_path):
                self.credentials_file = credentials_path
                messagebox.showinfo("成功", "Google Drive APIの認証に成功しました。アプリを再起動してください。")
                self.root.destroy()  # Restart the app to apply changes
            
    def upload_to_drive(self):
        """Upload the database to Google Drive."""
        if not self.service:
            messagebox.showerror("APIエラー", "Google Drive APIが設定されていません。")
            return
            
        try:
            # Commit any pending transactions
            self.conn.commit()
            
            # Create file metadata
            file_metadata = {
                'name': f'pokemons_{time.strftime("%Y%m%d_%H%M%S")}.db',  # Create version with timestamp
            }
            
            # Create media
            media = MediaFileUpload(self.db_path, mimetype='application/x-sqlite3')
            
            # Check if we should create a new file or update existing one
            update_existing = messagebox.askyesno("アップロード方法", 
                                                "既存のファイルを上書きしますか？\nはい: 既存ファイルを上書き\nいいえ: 新しいバージョンを作成")
            
            if update_existing:
                # Update the existing file
                file = self.service.files().update(
                    fileId=self.file_id,
                    media_body=media,
                    fields='id'
                ).execute()
                self.status_var.set(f"Google Driveのファイルが更新されました")
            else:
                # Create a new file
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                self.file_id = file.get('id')
                self.status_var.set(f"新しいバージョンがGoogle Driveに保存されました (ID: {self.file_id})")
            
            messagebox.showinfo("成功", "データベースがGoogle Driveに正常に保存されました")
            
        except Exception as e:
            self.status_var.set(f"エラー: {str(e)}")
            messagebox.showerror("アップロードエラー", f"Google Driveへのアップロードに失敗しました: {str(e)}")
    
    def refresh_from_drive(self):
        """Refresh the database from Google Drive."""
        if not self.service:
            messagebox.showerror("APIエラー", "Google Drive APIが設定されていません。")
            return
            
        # Check if there are unsaved changes
        confirm = messagebox.askokcancel("更新確認", 
                                       "Google Driveから最新のデータベースを取得します。\n未保存の変更は失われます。続行しますか？")
        if not confirm:
            return
            
        # Close current connection
        self.conn.close()
        
        # Download fresh copy
        self.download_db()
        
        # Reopen connection
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Reset UI
        self.pokemon_var.set("")
        self.form_var.set("")
        self.alias_listbox.delete(0, tk.END)
        self.selected_pokemon = None
        self.selected_alias = None
        
        self.status_var.set("Google Driveから最新のデータベースを取得しました")

    def suggest_pokemon(self, event):
        typed = self.pokemon_var.get()
        self.cursor.execute("SELECT NAME FROM POKEMON_NAME WHERE NAME LIKE ?", ('%' + typed + '%',))
        suggestions = [row[0] for row in self.cursor.fetchall()]
        self.pokemon_entry['values'] = suggestions

    def select_pokemon(self, event=None):
        self.selected_pokemon = self.pokemon_var.get()
        self.update_forms_and_aliases()

    def update_forms_and_aliases(self):
        self.cursor.execute("SELECT NDEX_NUMBER FROM POKEMON_NAME WHERE NAME = ?", (self.selected_pokemon,))
        result = self.cursor.fetchone()
        if result:
            self.ndex_number = result[0]
            self.cursor.execute("SELECT FORM_ID, FORM_NAME, GENDER FROM POKEMON_NAME_FORM WHERE NDEX_NUMBER = ?", (self.ndex_number,))
            forms = []
            form_exists = False

            for form_id, form_name, gender in self.cursor.fetchall():
                if form_id == 0:
                    form_exists = True
                    if form_name is None and gender is None:
                        forms.append("基本")
                    elif form_name is not None:
                        forms.append(form_name)
                    elif gender is not None:
                        forms.append(gender)
                else:
                    if form_name is not None:
                        forms.append(form_name)
                    if gender is not None:
                        forms.append(gender)

            if not form_exists:
                forms.append("基本")

            forms = list(set(forms))  # Remove duplicates

            self.form_option['menu'].delete(0, 'end')
            self.form_var.set(forms[0] if forms else "")
            for form in forms:
                self.form_option['menu'].add_command(label=form, command=tk._setit(self.form_var, form))

            self.update_alias_list()

    def update_alias_list(self, *args):
        if self.form_var.get():
            self.alias_listbox.delete(0, tk.END)
            form_name = self.form_var.get()
            if form_name == "基本":
                self.cursor.execute("SELECT NAME_ALIAS FROM POKEMON_NAME_ALIAS WHERE NDEX_NUMBER = ? AND FORM_ID = 0", (self.ndex_number,))
            else:
                self.cursor.execute("""
                    SELECT NAME_ALIAS FROM POKEMON_NAME_ALIAS 
                    WHERE NDEX_NUMBER = ? AND FORM_ID = 
                    (SELECT FORM_ID FROM POKEMON_NAME_FORM 
                     WHERE (FORM_NAME = ? OR GENDER = ?) AND NDEX_NUMBER = ?)""", 
                    (self.ndex_number, form_name, form_name, self.ndex_number))
            aliases = [alias[0] for alias in self.cursor.fetchall()]
            for alias in aliases:
                self.alias_listbox.insert(tk.END, alias)

    def show_alias_options(self, event):
        selection = self.alias_listbox.curselection()
        if selection:
            self.selected_alias = self.alias_listbox.get(selection[0])
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="編集", command=self.edit_alias)
            menu.add_command(label="削除", command=self.delete_alias)
            menu.post(event.x_root, event.y_root)

    def add_alias(self):
        new_alias = simpledialog.askstring("別名の追加", "新しい別名を入力")
        if new_alias:
            form_name = self.form_var.get()
            if form_name == "基本":
                form_id = 0
            else:
                self.cursor.execute("""
                    SELECT FORM_ID FROM POKEMON_NAME_FORM 
                    WHERE (FORM_NAME = ? OR GENDER = ?) AND NDEX_NUMBER = ?""", 
                    (form_name, form_name, self.ndex_number))
                form_id = self.cursor.fetchone()
                form_id = form_id[0] if form_id else 0

            self.cursor.execute("INSERT INTO POKEMON_NAME_ALIAS (NAME_ALIAS, NDEX_NUMBER, FORM_ID) VALUES (?, ?, ?)", (new_alias, self.ndex_number, form_id))
            self.conn.commit()
            self.update_alias_list()
            self.status_var.set("別名が追加されました (ローカルのみ)")

    def edit_alias(self):
        new_alias = simpledialog.askstring("別名の編集", "新しい別名を入力", initialvalue=self.selected_alias)
        if new_alias:
            form_name = self.form_var.get()
            if form_name == "基本":
                form_id = 0
            else:
                self.cursor.execute("""
                    SELECT FORM_ID FROM POKEMON_NAME_FORM 
                    WHERE (FORM_NAME = ? OR GENDER = ?) AND NDEX_NUMBER = ?""", 
                    (form_name, form_name, self.ndex_number))
                form_id = self.cursor.fetchone()
                form_id = form_id[0] if form_id else 0

            self.cursor.execute("UPDATE POKEMON_NAME_ALIAS SET NAME_ALIAS = ? WHERE NAME_ALIAS = ? AND NDEX_NUMBER = ? AND FORM_ID = ?", (new_alias, self.selected_alias, self.ndex_number, form_id))
            self.conn.commit()
            self.update_alias_list()
            self.status_var.set("別名が編集されました (ローカルのみ)")

    def delete_alias(self):
        if self.selected_alias:
            confirm = messagebox.askokcancel("別名の削除", f"本当に '{self.selected_alias}' を削除しますか？")
            if confirm:
                form_name = self.form_var.get()
                if form_name == "基本":
                    form_id = 0
                else:
                    self.cursor.execute("""
                        SELECT FORM_ID FROM POKEMON_NAME_FORM 
                        WHERE (FORM_NAME = ? OR GENDER = ?) AND NDEX_NUMBER = ?""", 
                        (form_name, form_name, self.ndex_number))
                    form_id = self.cursor.fetchone()
                    form_id = form_id[0] if form_id else 0

                self.cursor.execute("DELETE FROM POKEMON_NAME_ALIAS WHERE NAME_ALIAS = ? AND NDEX_NUMBER = ? AND FORM_ID = ?", (self.selected_alias, self.ndex_number, form_id))
                self.conn.commit()
                self.update_alias_list()
                self.selected_alias = None
                self.status_var.set("別名が削除されました (ローカルのみ)")

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def on_close(self):
        """Handle window close event - ask to save changes."""
        confirm = messagebox.askyesnocancel("終了", "変更をローカルに保存しますか？")
        if confirm is None:  # Cancel was clicked
            return
        elif confirm:  # Yes was clicked
            self.save_local()
        
        # Clean up temporary file
        self.conn.close()
        try:
            os.remove(self.db_path)
        except:
            pass
        self.root.destroy()

    def __del__(self):
        try:
            self.conn.close()
        except:
            pass
        try:
            os.remove(self.db_path)
        except:
            pass

if __name__ == "__main__":
    # Google Drive file URL
    drive_url = "https://drive.google.com/file/d/1X1GQ_TSW8PTsSG1ZtMkzpPuddezsHcA9/view?usp=drive_link"
    
    # Check for a credentials file in the same directory
    credentials_file = None
    if os.path.exists('credentials.json'):
        credentials_file = 'credentials.json'
    
    root = tk.Tk()
    app = PokemonAliasManager(root, drive_url, credentials_file)
    app.run()