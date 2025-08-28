# Copyright (c) 2025 Pentastic Security Limited. All rights reserved.

# @brief An immutable header.
class Header:
    def __init__(self, column_names: tuple[str]):
        self.__column_names: tuple[str] = column_names

    def get_column_names(self) -> tuple[str]:
        return self.__column_names

    def get_column_count(self) -> int:
        return len(self.__column_names)

    def get_copy(self) -> 'Header':
        return Header(self.__column_names)

# An entry is a row.
# Every entry has a fixed amount of columns, thus is a fixed-length horizontal list.
# In an entry, multiple unique values exist in every cell.
class Entry:
    def __init__(self, *, length: int = 0, values: list[str] = []):
        if (values == None or len(values) == 0):
            values = [""] * length
        self.__column_count: int = len(values)
        self.__cell_values: list[dict[str, object]] = []
        for column_value in values:
            if (column_value != ""):
                self.__cell_values.append({column_value: None})
            else:
                self.__cell_values.append({})
    
    def append_value_to_column(self, column_index: int, value: str) -> None:
        if (column_index < 0 or column_index >= self.__column_count):
            # return if index out of bounds
            return
        if (value == ""):
            # empty string
            return
        # append the value into the dictionary as a key
        self.__cell_values[column_index].update({value: None})
    
    def set_value_at_column(self, column_index: int, value: str) -> None:
        if (column_index < 0 or column_index >= self.__column_count):
            # return if index out of bounds
            return
        if (value == ""):
            # empty string
            return
        # remove all key-value pairs from the dictionary
        self.__cell_values[column_index].clear()
        # append the value into the dictionary as a key
        self.__cell_values[column_index].update({value: None})
    
    def get_values_from_column(self, column_index: int) -> list[str]:
        return list(self.__cell_values[column_index].keys())

    def get_value_str_from_column(self, column_index: int, separator: str = ", ") -> str:
        if (column_index < 0 or column_index >= self.__column_count):
            # return if index out of bounds
            return ""
        return separator.join(self.get_values_from_column(column_index))

    def get_value_str_from_columns(self, separator: str = ", ") -> list[str]:
        value_strings: list[str] = []
        for column_index in range(self.__column_count):
            value_string: str = self.get_value_str_from_column(column_index, separator)
            value_strings.append(value_string)
        return value_strings
    
    # @return the number of columns in this entry
    def get_column_count(self) -> int:
        return self.__column_count

    # @return a new Entry object, which is a deep copy of this entry
    def get_deep_copy(self) -> 'Entry':
        deep_copy: 'Entry' = Entry(length = self.__column_count)
        for column_index in range(self.__column_count):
            column_values: list[str] = self.get_values_from_column(column_index)
            for value in column_values:
                deep_copy.append_value_to_column(column_index, value)
        return deep_copy

    # @param entries the other entries to be merged, no need to include this entry
    # @return a new Entry object, which is a deep copy of this entry and all other entries
    def merge_entries(self, entries: list['Entry']) -> 'Entry':
        merged_entry: 'Entry' = self.get_deep_copy()
        if (entries == None or len(entries) == 0):
            return merged_entry
        for entry in entries:
            for column_index in range(min(self.__column_count, entry.__column_count)):
                column_values: list[str] = entry.get_values_from_column(column_index)
                for value in column_values:
                    merged_entry.append_value_to_column(column_index, value)
        return merged_entry

class Table:
    def __init__(self, header: Header, entries: list[Entry] | None = None):
        self.__header: Header = header
        self.__entries: list[Entry] = []
        if (entries != None):
            for entry in entries:
                self.__entries.append(entry.get_deep_copy())

    def get_header(self) -> Header:
        return self.__header

    def get_column_names(self) -> tuple[str]:
        return self.__header.get_column_names()
    
    def get_column_count(self) -> int:
        return self.__header.get_column_count()

    def get_entries(self) -> list[Entry]:
        return self.__entries

    def get_entry_count(self) -> int:
        return len(self.__entries)

    def get_entry(self, index: int) -> Entry:
        return self.__entries[index]

    def append_entry(self, entry: Entry) -> None:
        self.__entries.append(entry)

    def insert_entry(self, index: int, entry: Entry) -> None:
        self.__entries.insert(index, entry)

    def pop_entry(self, index: int) -> Entry:
        return self.__entries.pop(index)

    def remove_entry(self, entry: Entry) -> Entry:
        self.__entries.remove(entry)
        return entry

    def get_deep_copy(self) -> 'Table':
        return Table(self.__header, self.__entries)

import csv

def CSV_to_table(csv_filepath: str, *, encoding="utf-8") -> Table:
    with open(csv_filepath, 'r', encoding=encoding) as csv_file:
        # create CSV reader
        csv_reader = csv.reader(csv_file)

        # get the table header
        header_list: list = next(csv_reader)
        header_tuple: tuple[str] = tuple(header_list)
        header: Header = Header(header_tuple)

        # get the table entries
        entries: list[Entry] = []
        for row in csv_reader:
            entry: Entry = Entry(values=row)
            entries.append(entry)

        # create a table from the header and the entries
        return Table(header, entries)

def table_to_CSV(table: Table, csv_filepath: str, *, encoding="utf-8") -> None:
    with open(csv_filepath, mode="w+t", encoding=encoding, newline='') as csv_file:
        # create CSV writer
        csv_writer = csv.writer(csv_file)

        # writes the table header
        csv_writer.writerow(table.get_column_names())

        # writes the table entries
        for entry in table.get_entries():
            csv_writer.writerow(entry.get_value_str_from_columns())