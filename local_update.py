import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import sqlite3

class PokemonAliasManager:
    def __init__(self, root, db_path):
        self.root = root
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.selected_pokemon = None
        self.selected_alias = None

        self.setup_ui()

    def setup_ui(self):
        self.root.title("エイリアスの更新")

        # Pokemon selection with autocomplete
        tk.Label(self.root, text="ポケモンを選択").grid(row=0, column=0, padx=5, pady=5)
        self.pokemon_var = tk.StringVar()
        self.pokemon_entry = ttk.Combobox(self.root, textvariable=self.pokemon_var)
        self.pokemon_entry.grid(row=0, column=1, padx=5, pady=5)
        self.pokemon_entry.bind("<KeyRelease>", self.suggest_pokemon)
        self.pokemon_entry.bind("<<ComboboxSelected>>", self.select_pokemon)

        # Alias display
        tk.Label(self.root, text="すがた:").grid(row=2, column=0, padx=5, pady=5)
        self.form_var = tk.StringVar()
        self.form_var.trace('w', self.update_alias_list)
        self.form_option = tk.OptionMenu(self.root, self.form_var, "")
        self.form_option.grid(row=2, column=1, padx=5, pady=5)

        self.alias_listbox = tk.Listbox(self.root)
        self.alias_listbox.grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        self.alias_listbox.bind("<Button-3>", self.show_alias_options)

        tk.Button(self.root, text="別名の追加", command=self.add_alias).grid(row=4, column=0, padx=5, pady=5)
        tk.Button(self.root, text="別名の削除", command=self.delete_alias).grid(row=4, column=1, padx=5, pady=5)

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

    def run(self):
        self.root.mainloop()

    def __del__(self):
        self.conn.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = PokemonAliasManager(root, "pokemons.db")
    app.run()
