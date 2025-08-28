# Copyright (c) 2025 Pentastic Security Limited. All rights reserved.

from typing import Callable # for type hints for callbacks
from typing import Literal

import tkinter as tk
from tkinter import filedialog as fd
from tkinter import ttk

from model import Table as TableModel
from model import Entry as EntryModel
from model import CSV_to_table
from model import table_to_CSV

class Table:
    def __init__(self, parent: tk.Widget, table_model: TableModel, *, editable: bool = False, cell_bar_visible = False):
        self.__editable: bool = False
        self.__cell_bar_visible: bool = cell_bar_visible
        self.__selected_row_index: int = -1
        self.__selected_column_index: int = -1
        self.__selected_textbox: tk.Text | None = None

        self.__default_font = ('Arial', 10)

        self.__table_model: TableModel = table_model
        column_names: tuple[str] = self.__table_model.get_column_names()

        # create a frame to wrap everything in this object
        self.__frame = ttk.Frame(parent, padding=5)
        self.__frame.pack(fill=tk.BOTH, expand=True)

        self.__cell_bar: tk.Text | None = None
        treeview_grid_row = 0
        if (self.is_cell_bar_visible()):
            # create cell bar
            cell_bar = tk.Text(self.__frame, font=self.__default_font, wrap=tk.WORD, height=5, state=self.__get_editor_state())
            self.__cell_bar = cell_bar
            cell_bar.grid(row=0, column=0, sticky="ew")
            
            # create vertical scrollbar
            table_vert_scrollbar: ttk.Scrollbar = ttk.Scrollbar(self.__frame, orient=tk.VERTICAL, command=cell_bar.yview)
            # link the cell bar to the scrollbar
            cell_bar.configure(yscrollcommand=table_vert_scrollbar.set)
            # put vertical scrollbar right of the cell bar
            table_vert_scrollbar.grid(row=0, column=1, sticky="ns")

            def save_edit(event):
                cell_bar_string: str = cell_bar.get("1.0", tk.END)
                cell_indices: tuple[int, int] = (self.__selected_row_index, self.__selected_column_index)
                self.__set_cell_value(cell_indices, cell_bar_string)
                cell_bar.edit_modified(False)

            cell_bar.edit_modified(False)
            # update the cell when cell bar loses focus
            cell_bar.bind("<<Modified>>", save_edit)

            # ask treeview table to be placed under cell bar
            treeview_grid_row = 1

        # create treeview to render the table
        self.__tree: ttk.Treeview = ttk.Treeview(self.__frame, columns=column_names, show="headings")
        # place table heading into the treeview
        for column_name in column_names:
            self.__tree.heading(column_name, text=column_name)

        # place table entries into the treeview
        entry_models: list[EntryModel] = self.__table_model.get_entries()
        row_index: int = 0
        for entry_model in entry_models:
            value_strings: list[str] = entry_model.get_value_str_from_columns()
            self.__tree.insert("", tk.END, text="", values=value_strings, iid=row_index)
            row_index += 1
        # put table at the middle left
        self.__tree.grid(row=treeview_grid_row, column=0, sticky="nsew")

        # create horizontal scrollbar
        table_hori_scrollbar: ttk.Scrollbar = ttk.Scrollbar(self.__frame, orient=tk.HORIZONTAL, command=self.__tree.xview)
        # link the table to the scrollbar
        self.__tree.configure(xscrollcommand=table_hori_scrollbar.set)
        # put horizontal scrollbar below the table
        table_hori_scrollbar.grid(row=treeview_grid_row + 1, column=0, sticky="ew")

        # create vertical scrollbar
        table_vert_scrollbar: ttk.Scrollbar = ttk.Scrollbar(self.__frame, orient=tk.VERTICAL, command=self.__tree.yview)
        # link the table to the scrollbar
        self.__tree.configure(yscrollcommand=table_vert_scrollbar.set)
        # put vertical scrollbar right of the table
        table_vert_scrollbar.grid(row=treeview_grid_row, column=1, sticky="ns")

        # Configure grid weights to allow table resizing
        self.__frame.grid_rowconfigure(treeview_grid_row, weight=1)
        self.__frame.grid_columnconfigure(0, weight=1)

        # configure whether the cells in this table are editable or not
        self.set_editable(editable)

        # bind user inputs to callbacks
        self.__tree.bind("<Left>", self.__on_left_arrow_key_clicked)
        self.__tree.bind("<Right>", self.__on_right_arrow_key_clicked)
        self.__tree.bind("<Up>", self.__on_up_arrow_key_clicked)
        self.__tree.bind("<Down>", self.__on_down_arrow_key_clicked)
        self.__tree.bind("<Button-1>", self.__on_single_click)
        self.__tree.bind("<Double-1>", self.__on_double_click)

    def get_table_model(self) -> TableModel:
        return self.__table_model

    def get_gui_node(self) -> tk.Widget:
        return self.__frame
    
    def set_editable(self, editable: bool) -> None:
        self.__editable = editable
        if (self.__cell_bar != None):
            self.__cell_bar.config(state=self.__get_editor_state())
        if (self.__selected_textbox != None):
            self.__selected_textbox.config(state=self.__get_editor_state())

    def is_editable(self) -> bool:
        return self.__editable

    def __get_editor_state(self) -> Literal['normal', 'disabled']:
        return tk.NORMAL if self.is_editable() else tk.DISABLED
    
    def is_cell_bar_visible(self) -> bool:
        return self.__cell_bar_visible

    def __render_cell_bar(self, cell_position: tuple[str, str] | tuple[int, int]) -> None:
        if ((not self.is_cell_bar_visible()) or (self.__cell_bar == None)):
            return
        cell_values = self.__get_cell_value(cell_position)
        if (cell_values == None):
            return
        row_values, column_index, cell_value = cell_values
        self.__cell_bar.config(state=tk.NORMAL)
        self.__cell_bar.delete("1.0", tk.END)
        self.__cell_bar.insert("1.0", cell_value)
        self.__cell_bar.config(state=self.__get_editor_state())
    
    def __get_cell_ids(self, event) -> tuple[str, str]:
        item_id = self.__tree.identify_row(event.y)
        column_id = self.__tree.identify_column(event.x)
        return (item_id, column_id)

    def __get_cell_indices(self, cell_ids: tuple[str, str]) -> tuple[int, int] | None:
        item_id, column_id = cell_ids
        if item_id and column_id:
            row_index: int = int(item_id)
            # Get column index (e.g., '#0' for first column, '#1' for second)
            column_index: int = int(column_id.replace('#', '')) - 1 if column_id != '#0' else 0
            return (row_index, column_index)
        else:
            return None
    
    def __get_cell_item_id(self, cell_row_index: int) -> str:
        return str(cell_row_index)
    
    def __get_cell_column_id(self, cell_column_index: int) -> str:
        return "#" + str(cell_column_index + 1)

    def __get_cell_value(self, cell_position: tuple[str, str] | tuple[int, int]) -> tuple[list[str], int, str] | None:
        row_position, column_position = cell_position
        if (isinstance(row_position, int) and isinstance(column_position, int)):
            row_index: int = row_position
            column_index: int = column_position
            entry: EntryModel = self.__table_model.get_entry(row_index)
            row_values: list[str] = entry.get_value_str_from_columns()
            cell_value: str = entry.get_value_str_from_column(column_index)
            return (row_values, column_index, cell_value)
        elif (isinstance(row_position, str) and isinstance(column_position, str)):
            cell_ids: tuple[str, str] = (row_position, column_position)
            cell_indices: tuple[int, int] | None = self.__get_cell_indices(cell_ids)
            if (cell_indices == None):
                return None
            return self.__get_cell_value(cell_indices)
        else:
            return None # compiler type-checking failed...

    def __set_cell_value(self, cell_position: tuple[str, str] | tuple[int, int], cell_value: str) -> None:
        row_position, column_position = cell_position
        if (isinstance(row_position, int) and isinstance(column_position, int)):
            # update the data model
            row_index: int = row_position
            column_index: int = column_position
            entry: EntryModel = self.__table_model.get_entry(row_index)
            entry.set_value_at_column(column_index, cell_value)

            # update the GUI table
            row_values: list[str] = entry.get_value_str_from_columns()
            row_values[column_index] = cell_value
            item_id: str = self.__get_cell_item_id(row_index)
            self.__tree.item(item_id, values=tuple(row_values))
        elif (isinstance(row_position, str) and isinstance(column_position, str)):
            cell_ids: tuple[str, str] = (row_position, column_position)
            cell_indices: tuple[int, int] | None = self.__get_cell_indices(cell_ids)
            if (cell_indices == None):
                return None
            return self.__set_cell_value(cell_indices, cell_value)
        else:
            return None # compiler type-checking failed...

    def __update_cell_indices(self, cell_indices: tuple[int, int]) -> None:
        row_index, column_index = cell_indices
        if (self.__selected_row_index == row_index and self.__selected_column_index == column_index):
            return
        self.__selected_row_index = row_index
        self.__selected_column_index = column_index
        if self.is_cell_bar_visible():
            self.__render_cell_bar(cell_indices)
        
        cell_values = self.__get_cell_value(cell_indices)
        if (cell_values == None):
            return

        # destroy previous selected textbox
        if (self.__selected_textbox != None):
            self.__selected_textbox.destroy()
            self.__selected_textbox = None

        item_id: str = self.__get_cell_item_id(row_index)
        column_id: str = self.__get_cell_column_id(column_index)
        # Get cell bounding box
        x, y, width, height = self.__tree.bbox(item_id, column_id)
        cell_value = cell_values[2]
        # Create and position Entry widget
        textbox: tk.Text = tk.Text(self.__tree, font=self.__default_font)
        textbox.insert("1.0", cell_value)
        textbox.place(x=x, y=y, width=width, height=height)
        textbox.config(state=self.__get_editor_state())

        def save_edit(event=None):
            new_text = textbox.get("1.0", tk.END)
            self.__set_cell_value(cell_indices, new_text)

        # textbox.bind("<FocusOut>", lambda e: entry.destroy())
        textbox.bind("<FocusOut>", save_edit)
        self.__selected_textbox = textbox

    def __on_up_arrow_key_clicked(self, event) -> None:
        if (self.__selected_row_index > 0):
            self.__update_cell_indices((self.__selected_row_index - 1, self.__selected_column_index))

    def __on_down_arrow_key_clicked(self, event) -> None:
        if (self.__selected_row_index + 1 < self.__table_model.get_entry_count()):
            self.__update_cell_indices((self.__selected_row_index + 1, self.__selected_column_index))

    def __on_left_arrow_key_clicked(self, event) -> None:
        if (self.__selected_column_index > 0):
            self.__update_cell_indices((self.__selected_row_index, self.__selected_column_index - 1))

    def __on_right_arrow_key_clicked(self, event) -> None:
        if (self.__selected_column_index + 1 < self.__table_model.get_column_count()):
            self.__update_cell_indices((self.__selected_row_index, self.__selected_column_index + 1))

    def __on_single_click(self, event) -> None:
        cell_ids = self.__get_cell_ids(event)
        cell_indices = self.__get_cell_indices(cell_ids)
        if (cell_indices == None):
            return
        self.__update_cell_indices(cell_indices)

    def __on_double_click(self, event) -> None:
        cell_ids = self.__get_cell_ids(event)
        cell_indices = self.__get_cell_indices(cell_ids)
        if (cell_indices == None):
            return
        self.__update_cell_indices(cell_indices)

        if (not self.is_editable()):
            return

        item_id, column_id = cell_ids
        if item_id and column_id:
            if (self.is_cell_bar_visible()):
                # tamper the cell bar instead
                if (self.__cell_bar != None):
                    self.__cell_bar.focus_set()
            else:
                # Get cell bounding box
                x, y, width, height = self.__tree.bbox(item_id, column_id)

                # tk.Entry and ttk.Entry do not support multi-line values
                # don't use them
                # # Create and position Entry widget
                # entry: ttk.Entry = ttk.Entry(self.__tree, font=('Arial', 10))
                # entry.insert(0, current_text)
                # entry.place(x=x, y=y, width=width, height=height)
                # entry.focus_set()

                # def save_edit(event=None):
                #     new_text = entry.get()
                #     current_values[col_index] = new_text
                #     self.__tree.item(item_id, values=tuple(current_values))
                #     entry.destroy()

                # entry.bind("<Return>", save_edit)
                # # entry.bind("<FocusOut>", lambda e: entry.destroy())
                # entry.bind("<FocusOut>", save_edit)

                # cell_values = self.__get_cell_value(cell_indices)
                # if (cell_values == None):
                #     return
                # cell_value = cell_values[2]
                # # Create and position Entry widget
                # textbox: tk.Text = tk.Text(self.__tree, font=self.__default_font)
                # textbox.insert("1.0", cell_value)
                # textbox.place(x=x, y=y, width=width, height=height * 5)
                # textbox.focus_set()

                # def save_edit(event=None):
                #     new_text = textbox.get("1.0", tk.END)
                #     self.__set_cell_value(cell_ids, new_text)
                #     textbox.destroy()

                # # textbox.bind("<FocusOut>", lambda e: entry.destroy())
                # textbox.bind("<FocusOut>", save_edit)


class Window:
    def __init__(self):
        self.__root = tk.Tk()
        self.__root.title("Remove CSV Duplicates App")
        self.__root.minsize(400, 100)
        self.__root.geometry("500x200")
        self.__frame: ttk.Frame = ttk.Frame(self.__root, padding=10)
        self.__frame.pack(fill=tk.BOTH, expand=True)

        self.__menubar = self.__create_menubar(self.__root)

        self.__mainframe_component: tk.Widget | None = self.__create_landing_label(self.__frame)

        self.__current_table_model: TableModel | None = None

        # start looping
        self.__root.mainloop()
    
    def __open(self, event=None):
        print("open")
        filepath = fd.askopenfilename(title="Select The CSV File to be DeDuped", filetypes=[("CSV files", "*.csv")])
        if (filepath == ""):
            print("no file is selected")
            return

        print(filepath)

        # destroy the previous component in mainframe
        # before adding the new one to the mainframe
        if (self.__mainframe_component != None):
            self.__mainframe_component.destroy()
            self.__mainframe_component = None
        
        # convert the csv file to a table model
        table_model: TableModel = CSV_to_table(filepath)
        self.__current_table_model = table_model
        table: Table = Table(self.__frame, table_model, editable=True, cell_bar_visible=True)
        self.__mainframe_component = table.get_gui_node()
    
    def __save(self, event=None):
        print("save")
        if (self.__current_table_model == None):
            print("no table is rendered")
            return
    
        filepath = fd.asksaveasfilename(title="Save File As", defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if (filepath == ""):
            print("no file is selected")
            return

        print(filepath)
    
    # closes the current rendered table
    def __close(self, event=None):
        if (self.__current_table_model == None):
            # no tables are opened
            return

        self.__current_table_model = None

        if (self.__mainframe_component != None):
            self.__mainframe_component.destroy()
            self.__mainframe_component = None
        
        landing_label: tk.Widget = self.__create_landing_label(self.__frame)
        self.__mainframe_component = landing_label

    def __exit(self, event=None):
        self.__root.destroy()
    
    def __get_accel_name(self, *names: str):
        accel_name = "Ctrl"
        # accel_name = "Command"
        for name in names:
            accel_name += "+" + name
        return accel_name
    
    def __get_accel_seq(self, *seqs: str):
        accel_seq = "Control"
        # accel_name = "Command"
        for seq in seqs:
            accel_seq += "-" + seq
        accel_seq = "<" + accel_seq + ">"
        return accel_seq

    def __create_landing_label(self, parent: tk.Widget) -> tk.Widget:
        no_csv_label: ttk.Label = ttk.Label(parent, text="Open a CSV file to continue.")
        no_csv_label.pack(fill=tk.BOTH, expand=True)
        return no_csv_label
    
    def __create_filemenu(self, menubar: tk.Menu) -> tk.Menu:
        filemenu = tk.Menu(menubar, tearoff=False)

        # create open menu
        filemenu.add_command(label="Open" , accelerator=self.__get_accel_name("O"), command=self.__open)
        filemenu.bind_all(self.__get_accel_seq("o"), self.__open)

        # create save menu
        filemenu.add_command(label="Save" , accelerator=self.__get_accel_name("S"), command=self.__save)
        filemenu.bind_all(self.__get_accel_seq("s"), self.__save)

        # create close menu
        filemenu.add_command(label="Close", accelerator=self.__get_accel_name("W"), command=self.__close)
        filemenu.bind_all(self.__get_accel_seq("w"), self.__close)

        # add a separator
        filemenu.add_separator()

        # create exit menu
        filemenu.add_command(label="Exit" , accelerator=self.__get_accel_name("Shift", "W"), command=self.__exit)
        filemenu.bind_all(self.__get_accel_seq("W"), self.__exit)

        # add filemenu to menubar
        menubar.add_cascade(label="File", menu=filemenu)
        return filemenu
    
    def __create_menubar(self, root: tk.Tk) -> tk.Menu:
        menubar = tk.Menu(root, tearoff=False)
        filemenu = self.__create_filemenu(menubar)
        root.config(menu=menubar)
        return menubar

def main():
    window = Window()

if __name__ == "__main__":
    main()