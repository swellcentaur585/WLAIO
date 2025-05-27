
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import itertools
import os
import time
import threading
from collections import OrderedDict


class WordlistGenerator:
    CHARACTER_SETS = {
        'uppercase': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'lowercase': 'abcdefghijklmnopqrstuvwxyz',
        'numbers': '0123456789',
        'pecial_characters': '!@#$%^&*()_+-={}:<>?,./'
    }

    LEET_MAP = {'e': '3', 'a': '4', 'i': '1', 'o': '0', '': '5', 't': '7', 'l': '1'}
    DEFAULT_NUMBERS = ['1', '2', '3', '123', '2023', '2024']
    DEFAULT_SPECIAL_CHARS = ['!', '@', '#', '$', '!@#']

    @staticmethod
    def generate_brute_force(character_sets, length, progress_callback=None):
        charset = ''.join(WordlistGenerator.CHARACTER_SETS[cs] for cs in character_sets if cs in WordlistGenerator.CHARACTER_SETS)
        if not charset:
            return []

        total = len(charset) ** length
        if total > 1000000:
            raise ValueError(f"Too many combinations ({total:,}). Consider using file output directly.")

        wordlist = []
        for i, combo in enumerate(itertools.product(charset, repeat=length)):
            if progress_callback and i % 1000 == 0:
                progress_callback(i / total * 100)
            wordlist.append(''.join(combo))

        return wordlist

    @staticmethod
    def apply_leet_speak(word):
        leet_word = word.lower()
        for char, replacement in WordlistGenerator.LEET_MAP.items():
            leet_word = leet_word.replace(char, replacement)
        return leet_word

    @staticmethod
    def apply_rules_to_word(word, rules):
        variations = [word]

        if rules.get('leet_speak'):
            variations.append(WordlistGenerator.apply_leet_speak(word))

        if rules.get('case_variations'):
            variations.extend([word.upper(), word.lower(), word.capitalize()])

        final_variations = []
        for var in variations:
            final_variations.append(var)

            if rules.get('append_numbers'):
                final_variations.extend([var + num for num in WordlistGenerator.DEFAULT_NUMBERS])

            if rules.get('prepend_numbers'):
                final_variations.extend([num + var for num in WordlistGenerator.DEFAULT_NUMBERS])

            if rules.get('append_special_characters'):
                final_variations.extend([var + char for char in WordlistGenerator.DEFAULT_SPECIAL_CHARS])

            if rules.get('prepend_special_characters'):
                final_variations.extend([char + var for char in WordlistGenerator.DEFAULT_SPECIAL_CHARS])

        return list(OrderedDict.fromkeys(final_variations))


class WordlistFileManager:
    @staticmethod
    def load_wordlist(filename):
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as file:
                return [line.strip() for line in file if line.strip()]
        except Exception as e:
            raise Exception(f"Failed to load file: {str(e)}")

    @staticmethod
    def save_wordlist(filename, wordlist, chunk_size=10000):
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                for i, word in enumerate(wordlist):
                    file.write(word + '\n')
                    if i % chunk_size == 0:
                        file.flush()
        except Exception as e:
            raise Exception(f"Failed to save file: {str(e)}")


class WordlistManagerGUI:
    MAX_SAFE_BRUTE_LENGTH = 6
    TEXT_AREA_HEIGHT = 12
    TEXT_AREA_WIDTH = 50
    WINDOW_MIN_WIDTH = 700
    WINDOW_MIN_HEIGHT = 600

    def __init__(self):
        self.current_wordlist = []
        self.setup_window()
        self.create_notebook()
        self.setup_all_tabs()
        self.setup_menu()
        self.setup_status_bar()
        self.setup_keyboard_shortcuts()

    def setup_window(self):
        self.window = tk.Tk()
        self.window.title("WLAIO - Wordlist Manager")
        self.window.minsize(self.WINDOW_MIN_WIDTH, self.WINDOW_MIN_HEIGHT)
        self.window.geometry("800x700")

    def create_notebook(self):
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

    def setup_all_tabs(self):
        self.tabs = {}
        tab_configs = [
            ("Load/Save", self.setup_load_save_tab),
            ("Brute Force", self.setup_brute_force_tab),
            ("Word Rules", self.setup_rules_tab),
            ("List Combiner", self.setup_combiner_tab)
        ]

        for name, setup_func in tab_configs:
            frame = ttk.Frame(self.notebook)
            self.tabs[name.lower().replace('/', '_').replace(' ', '_')] = frame
            self.notebook.add(frame, text=name)
            setup_func(frame)

    def setup_load_save_tab(self, parent):
        file_frame = ttk.LabelFrame(parent, text="File Operations", padding=10)
        file_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(file_frame, text=" Load Wordlist", command=self.load_wordlist).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text=" Save Wordlist", command=self.save_wordlist).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text=" Clear", command=self.clear_load_save_area).pack(side=tk.LEFT, padx=5)

        stats_frame = ttk.Frame(file_frame)
        stats_frame.pack(side=tk.RIGHT)
        self.word_count_label = ttk.Label(stats_frame, text="Words: 0")
        self.word_count_label.pack()

        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.text_area_load_save = tk.Text(text_frame, height=self.TEXT_AREA_HEIGHT, 
                                          width=self.TEXT_AREA_WIDTH, wrap=tk.WORD)
        scrollbar1 = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_area_load_save.yview)
        self.text_area_load_save.configure(yscrollcommand=scrollbar1.set)

        self.text_area_load_save.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar1.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_area_load_save.bind('<KeyRelease>', self.update_word_count)

    def setup_brute_force_tab(self, parent):
        options_frame = ttk.LabelFrame(parent, text="Character Sets", padding=10)
        options_frame.pack(fill=tk.X, padx=5, pady=5)

        self.brute_force_vars = {}
        brute_force_options = ['uppercase', 'lowercase', 'numbers', 'pecial_characters']

        for i, option in enumerate(brute_force_options):
            var = tk.IntVar()
            self.brute_force_vars[option] = var
            cb = ttk.Checkbutton(options_frame, text=option.replace('_', ' ').title(), variable=var)
            cb.grid(row=i//2, column=i%2, sticky=tk.W, padx=10, pady=2)

        length_frame = ttk.LabelFrame(parent, text="Configuration", padding=10)
        length_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(length_frame, text="Length:").pack(side=tk.LEFT)
        self.length_entry = ttk.Entry(length_frame, width=10)
        self.length_entry.pack(side=tk.LEFT, padx=5)
        self.length_entry.insert(0, "4")

        ttk.Button(length_frame, text=" Generate", command=self.generate_brute_force).pack(side=tk.LEFT, padx=10)
        ttk.Button(length_frame, text=" Save to File", command=self.save_brute_force_to_file).pack(side=tk.LEFT, padx=5)

        self.brute_force_progress = ttk.Progressbar(length_frame, mode='determinate')
        self.brute_force_progress.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)

        self.brute_force_warning = ttk.Label(parent, text="", foreground="red")
        self.brute_force_warning.pack(padx=5)

        text_frame2 = ttk.Frame(parent)
        text_frame2.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.text_area_brute_force = tk.Text(text_frame2, height=self.TEXT_AREA_HEIGHT, 
                                           width=self.TEXT_AREA_WIDTH)
        scrollbar2 = ttk.Scrollbar(text_frame2, orient=tk.VERTICAL, command=self.text_area_brute_force.yview)
        self.text_area_brute_force.configure(yscrollcommand=scrollbar2.set)

        self.text_area_brute_force.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)

        self.length_entry.bind('<KeyRelease>', self.update_brute_force_estimate)

    def setup_rules_tab(self, parent):
        input_frame = ttk.LabelFrame(parent, text="Input Words", padding=10)
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(input_frame, text="Words (comma-separated):").pack(anchor=tk.W)
        self.rules_entry = ttk.Entry(input_frame, width=60)
        self.rules_entry.pack(fill=tk.X, pady=5)

        rules_frame = ttk.LabelFrame(parent, text="Transformation Rules", padding=10)
        rules_frame.pack(fill=tk.X, padx=5, pady=5)

        self.rules_vars = {}
        rules_options = [
            'leet_speak', 'case_variations', 'append_numbers', 
            'prepend_numbers', 'append_special_characters', 'prepend_special_characters'
        ]

        for i, option in enumerate(rules_options):
            var = tk.IntVar()
            self.rules_vars[option] = var
            cb = ttk.Checkbutton(rules_frame, text=option.replace('_', ' ').title(), variable=var)
            cb.grid(row=i//2, column=i%2, sticky=tk.W, padx=10, pady=2)

        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(button_frame, text=" Apply Rules", command=self.apply_rules).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text=" Clear", command=self.clear_rules_area).pack(side=tk.LEFT, padx=5)

        text_frame3 = ttk.Frame(parent)
        text_frame3.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.text_area_rules = tk.Text(text_frame3, height=self.TEXT_AREA_HEIGHT, 
                                     width=self.TEXT_AREA_WIDTH)
        scrollbar3 = ttk.Scrollbar(text_frame3, orient=tk.VERTICAL, command=self.text_area_rules.yview)
        self.text_area_rules.configure(yscrollcommand=scrollbar3.set)

        self.text_area_rules.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar3.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_combiner_tab(self, parent):
        input_frame = ttk.LabelFrame(parent, text="Input Wordlists", padding=10)
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.combiner_list1_label = ttk.Label(input_frame, text="Wordlist 1:")
        self.combiner_list1_label.pack()
        self.combiner_list1_entry = tk.Text(input_frame, height=5, width=40)
        self.combiner_list1_entry.pack()
        self.load_list1_button = ttk.Button(input_frame, text="Load List 1", command=lambda: self.load_list(1))
        self.load_list1_button.pack()

        self.combiner_list2_label = ttk.Label(input_frame, text="Wordlist 2:")
        self.combiner_list2_label.pack()
        self.combiner_list2_entry = tk.Text(input_frame, height=5, width=40)
        self.combiner_list2_entry.pack()
        self.load_list2_button = ttk.Button(input_frame, text="Load List 2", command=lambda: self.load_list(2))
        self.load_list2_button.pack()

        options_frame = ttk.Frame(parent)
        options_frame.pack(fill=tk.X, padx=5, pady=5)

        self.combiner_vars = {}
        combiner_options = [
            'concatenate', 'preload_list1', 'preload_list2'
        ]

        for i, option in enumerate(combiner_options):
            var = tk.IntVar()
            self.combiner_vars[option] = var
            cb = ttk.Checkbutton(options_frame, text=option.replace('_', ' ').title(), variable=var)
            cb.pack(side=tk.LEFT)

        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, padx=5, pady=5)

        self.generate_combiner_btn = ttk.Button(action_frame, text=" Generate Combined List", 
                                              command=self.generate_combined_wordlist)
        self.generate_combiner_btn.pack(side=tk.LEFT, padx=5)

        self.clear_combiner_area_button = ttk.Button(action_frame, text=" Clear", command=self.clear_combiner_area)
        self.clear_combiner_area_button.pack(side=tk.LEFT, padx=5)

        self.combiner_progress = ttk.Progressbar(action_frame, mode='indeterminate')
        self.combiner_progress.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)

        text_frame4 = ttk.Frame(parent)
        text_frame4.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.text_area_combiner = tk.Text(text_frame4, height=self.TEXT_AREA_HEIGHT, 
                                        width=self.TEXT_AREA_WIDTH)
        scrollbar4 = ttk.Scrollbar(text_frame4, orient=tk.VERTICAL, command=self.text_area_combiner.yview)
        self.text_area_combiner.configure(yscrollcommand=scrollbar4.set)

        self.text_area_combiner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar4.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_menu(self):
        menubar = tk.Menu(self.window)
        self.window.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Wordlist", command=self.load_wordlist, accelerator="Ctrl+O")
        file_menu.add_command(label="Save Wordlist", command=self.save_wordlist, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.window.quit, accelerator="Ctrl+Q")

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Remove Duplicates", command=self.remove_duplicates)
        tools_menu.add_command(label="Sort Wordlist", command=self.sort_wordlist)
        tools_menu.add_command(label="Statistics", command=self.show_statistics)

    def setup_status_bar(self):
        self.status_bar = ttk.Label(self.window, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_keyboard_shortcuts(self):
        self.window.bind('<Control-o>', lambda e: self.load_wordlist())
        self.window.bind('<Control-s>', lambda e: self.save_wordlist())
        self.window.bind('<Control-q>', lambda e: self.window.quit())

    def update_status(self, message):
        self.status_bar.config(text=message)
        self.window.update_idletasks()

    def update_word_count(self, event=None):
        content = self.text_area_load_save.get(1.0, tk.END).strip()
        word_count = len([line for line in content.split('\n') if line.strip()]) if content else 0
        self.word_count_label.config(text=f"Words: {word_count:,}")

    def load_wordlist(self):
        filename = filedialog.askopenfilename(
            title="Select wordlist file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                self.update_status("Loading wordlist...")
                wordlist = WordlistFileManager.load_wordlist(filename)
                self.text_area_load_save.delete(1.0, tk.END)
                self.text_area_load_save.insert(tk.END, '\n'.join(wordlist))
                self.update_word_count()
                self.update_status(f"Loaded {len(wordlist):,} words from {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", str(e))
                self.update_status("Ready")

    def save_wordlist(self):
        filename = filedialog.asksaveasfilename(
            title="Save wordlist file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            defaultextension=".txt"
        )
        if filename:
            try:
                content = self.text_area_load_save.get(1.0, tk.END).strip()
                wordlist = [line.strip() for line in content.split('\n') if line.strip()]
                self.update_status("Saving wordlist...")
                WordlistFileManager.save_wordlist(filename, wordlist)
                self.update_status(f"Saved {len(wordlist):,} words to {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", str(e))
                self.update_status("Ready")

    def generate_brute_force(self):
        try:
            length = int(self.length_entry.get())
            if length <= 0 or length > 10:
                messagebox.showerror("Error", "Length must be between 1 and 10")
                return

            selected_sets = [key for key, var in self.brute_force_vars.items() if var.get()]
            if not selected_sets:
                messagebox.showerror("Error", "Select at least one character set")
                return

            total_combinations = sum(len(WordlistGenerator.CHARACTER_SETS[cs]) for cs in selected_sets) ** length

            if total_combinations > 1000000:
                if not messagebox.askyesno("Warning", 
                    f"This will generate {total_combinations:,} combinations. This may take a long time and use lots of memory. Continue?"):
                    return

            self.update_status("Generating brute force wordlist...")
            self.brute_force_progress.config(mode='determinate', value=0)

            def progress_callback(percent):
                self.brute_force_progress.config(value=percent)
                self.window.update_idletasks()

            def generate_thread():
                try:
                    wordlist = WordlistGenerator.generate_brute_force(selected_sets, length, progress_callback)

                    self.window.after(0, lambda: self.display_brute_force_results(wordlist))
                except Exception as e:
                    self.window.after(0, lambda: messagebox.showerror("Error", str(e)))
                    self.window.after(0, lambda: self.update_status("Ready"))

            threading.Thread(target=generate_thread, daemon=True).start()

        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number for length")

    def load_list(self, num):
        filename = filedialog.askopenfilename(
            title=f"Select wordlist {num} file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                wordlist = WordlistFileManager.load_wordlist(filename)
                if num == 1:
                    self.combiner_list1_entry.delete(1.0, tk.END)
                    self.combiner_list1_entry.insert(tk.END, '\n'.join(wordlist))
                elif num == 2:
                    self.combiner_list2_entry.delete(1.0, tk.END)
                    self.combiner_list2_entry.insert(tk.END, '\n'.join(wordlist))
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def generate_combined_wordlist(self):
        wordlist1 = self.combiner_list1_entry.get(1.0, tk.END).strip().split('\n')
        wordlist2 = self.combiner_list2_entry.get(1.0, tk.END).strip().split('\n')
        wordlist1 = [word for word in wordlist1 if word]
        wordlist2 = [word for word in wordlist2 if word]
        if not wordlist1 or not wordlist2:
            messagebox.showerror("Error", "Please load both wordlists")
            return

        self.generate_combiner_btn.config(state='disabled', text="Generating...")
        self.combiner_progress.config(mode='indeterminate')
        self.combiner_progress.start()
        self.update_status("Generating combined wordlist...")

        def generate_thread():
            try:
                all_combinations = []
                for word1 in wordlist1:
                    for word2 in wordlist2:
                        if self.combiner_vars.get('concatenate'):
                            all_combinations.append(word1 + word2)
                            all_combinations.append(word2 + word1)
                self.window.after(0, lambda: self.display_combined_results(all_combinations))
            except Exception as e:
                self.window.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.window.after(0, lambda: self.update_status("Ready"))

        threading.Thread(target=generate_thread, daemon=True).start()

    def display_brute_force_results(self, wordlist):
        self.text_area_brute_force.delete(1.0, tk.END)
        if len(wordlist) > 10000:
            self.text_area_brute_force.insert(tk.END, '\n'.join(wordlist[:10000]))
            self.text_area_brute_force.insert(tk.END, f"\n\n... and {len(wordlist)-10000:,} more words")
        else:
            self.text_area_brute_force.insert(tk.END, '\n'.join(wordlist))

        self.brute_force_progress.config(value=0, mode='determinate')
        self.update_status(f"Generated {len(wordlist):,} brute force combinations")

    def apply_rules(self):
        words_text = self.rules_entry.get().strip()
        if not words_text:
            messagebox.showerror("Error", "Please enter some words")
            return

        words = [word.strip() for word in words_text.split(',') if word.strip()]
        rules = {key: var.get() for key, var in self.rules_vars.items()}

        if not any(rules.values()):
            messagebox.showerror("Error", "Please select at least one rule")
            return

        self.update_status("Applying transformation rules...")

        all_variations = []
        for word in words:
            variations = WordlistGenerator.apply_rules_to_word(word, rules)
            all_variations.extend(variations)

        unique_variations = list(OrderedDict.fromkeys(all_variations))

        self.text_area_rules.delete(1.0, tk.END)
        self.text_area_rules.insert(tk.END, '\n'.join(unique_variations))

        self.update_status(f"Generated {len(unique_variations):,} word variations")

    def clear_load_save_area(self):
        self.text_area_load_save.delete(1.0, tk.END)
        self.update_word_count()

    def clear_rules_area(self):
        self.text_area_rules.delete(1.0, tk.END)

    def clear_combiner_area(self):
        self.text_area_combiner.delete(1.0, tk.END)

    def remove_duplicates(self):
        content = self.text_area_load_save.get(1.0, tk.END).strip()
        if not content:
            messagebox.showinfo("Info", "No wordlist loaded")
            return

        words = [line.strip() for line in content.split('\n') if line.strip()]
        original_count = len(words)
        unique_words = list(OrderedDict.fromkeys(words))

        self.text_area_load_save.delete(1.0, tk.END)
        self.text_area_load_save.insert(tk.END, '\n'.join(unique_words))
        self.update_word_count()

        removed = original_count - len(unique_words)
        messagebox.showinfo("Duplicates Removed", f"Removed {removed:,} duplicate words")

    def sort_wordlist(self):
        content = self.text_area_load_save.get(1.0, tk.END).strip()
        if not content:
            messagebox.showinfo("Info", "No wordlist loaded")
            return

        words = [line.strip() for line in content.split('\n') if line.strip()]
        sorted_words = sorted(words, key=lambda x: (len(x), x.lower()))

        self.text_area_load_save.delete(1.0, tk.END)
        self.text_area_load_save.insert(tk.END, '\n'.join(sorted_words))

        messagebox.showinfo("Sorted", f"Sorted {len(sorted_words):,} words by length and alphabetically")

    def create_stats_window(self, stats_text):
        stats_window = tk.Toplevel(self.window)
        stats_window.title("Wordlist Statistics")
        stats_window.geometry("400x350")
        stats_window.resizable(False, False)

        text_widget = tk.Text(stats_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, stats_text)
        text_widget.config(state=tk.DISABLED)

        ttk.Button(stats_window, text="Close", command=stats_window.destroy).pack(pady=10)

    def show_statistics(self):
        content = self.text_area_load_save.get(1.0, tk.END).strip()
        if not content:
            messagebox.showinfo("Info", "No wordlist loaded")
            return

        words = [line.strip() for line in content.split('\n') if line.strip()]
        if not words:
            messagebox.showinfo("Info", "No words found")
            return

        total_words = len(words)
        unique_words = len(set(words))
        duplicates = total_words - unique_words

        lengths = [len(word) for word in words]
        min_length = min(lengths)
        max_length = max(lengths)
        avg_length = sum(lengths) / len(lengths)

        has_upper = sum(1 for word in words if any(c.isupper() for c in word))
        has_lower = sum(1 for word in words if any(c.islower() for c in word))
        has_digits = sum(1 for word in words if any(c.isdigit() for c in word))
        has_special = sum(1 for word in words if any(not c.isalnum() for c in word))

        stats_text = f"""Wordlist Statistics:
        Total words: {total_words:,}
        Unique words: {unique_words:,}
        Duplicates: {duplicates:,}
        
        Length Statistics:
        - Minimum length: {min_length}
        - Maximum length: {max_length}
        - Average length: {avg_length:.1f}
        
        Character Analysis:
        - Contains uppercase: {has_upper:,} words ({has_upper/total_words*100:.1f}%)
        - Contains lowercase: {has_lower:,} words ({has_lower/total_words*100:.1f}%)
        - Contains digits: {has_digits:,} words ({has_digits/total_words*100:.1f}%)
        - Contains special chars: {has_special:,} words ({has_special/total_words*100:.1f}%)
        """
    def save_brute_force_to_file(self):
    try:
        length = int(self.length_entry.get())
        selected_sets = [key for key, var in self.brute_force_vars.items() if var.get()]

        if not selected_sets:
            messagebox.showerror("Error", "Select at least one character set")
            return

        charset = ''.join(WordlistGenerator.CHARACTER_SETS[cs] for cs in selected_sets)
        total = len(charset) ** length

        filename = filedialog.asksaveasfilename(
            title="Save brute force wordlist",
            filetypes=[("Text files", "*.txt")],
            defaultextension=".txt"
        )

        if filename:
            self.update_status(f"Saving {total:,} combinations to file...")

            def save_thread():
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        for i, combo in enumerate(itertools.product(charset, repeat=length)):
                            f.write(''.join(combo) + '\n')
                            if i % 10000 == 0:
                                progress = (i / total) * 100
                                self.window.after(0, lambda p=progress: self.brute_force_progress.config(value=p))

                    self.window.after(0, lambda: self.update_status(f"Saved {total:,} combinations to file"))
                    self.window.after(0, lambda: self.brute_force_progress.config(value=0))
                except Exception as e:
                    self.window.after(0, lambda: messagebox.showerror("Error", str(e)))
                    self.window.after(0, lambda: self.update_status("Ready"))

            threading.Thread(target=save_thread, daemon=True).start()

    except ValueError:
        messagebox.showerror("Error", "Please enter a valid number for length")

Total words: {total_words:,}
Unique words: {unique_words:,}
Duplicates: {duplicates:,}

Length Statistics:
- Minimum length: {min_length}
- Maximum length: {max_length}
- Average length: {avg_length:.1f}

Character Analysis:
- Contains uppercase: {has_upper:,} words ({has_upper/total_words*100:.1f}%)
- Contains lowercase: {has_lower:,} words ({has_lower/total_words*100:.1f}%)
- Contains digits: {has_digits:,} words ({has_digits/total_words*100:.1f}%)
- Contains special chars: {has_special:,} words ({has_special/total_words*100:.1f}%)"".format(
            total_words=total_words,
            unique_words=unique_words,
            duplicates=duplicates,
            min_length=min_length,
            max_length=max_length,
            avg_length=avg_length,
            has_upper=has_upper,
            has_lower=has_lower,
            has_digits=has_digits,
            has_special=has_special
        )

        self.create_stats_window(stats_text)

    def display_combined_results(self, wordlist):
        self.text_area_combiner.delete(1.0, tk.END)

        if len(wordlist) > 5000:
            self.text_area_combiner.insert(tk.END, '\n'.join(wordlist[:5000]))
            self.text_area_combiner.insert(tk.END, f"\n\n... and {len(wordlist)-5000:,} more words")

            if messagebox.askyesno("Large Wordlist", 
                f"Generated {len(wordlist):,} words. Would you like to save to file?"):
                self.save_large_wordlist(wordlist)
        else:
            self.text_area_combiner.insert(tk.END, '\n'.join(wordlist))

        self.generate_combiner_btn.config(state='normal', text=" Generate Combined List")
        self.combiner_progress.stop()
        self.combiner_progress.config(mode='determinate', value=0)
        self.update_status(f"Generated {len(wordlist):,} combined words")

    def save_large_wordlist(self, wordlist):
        filename = filedialog.asksaveasfilename(
            title="Save combined wordlist",
            filetypes=[("Text files", "*.txt")],
            defaultextension=".txt"
        )
        if filename:
            try:
                WordlistFileManager.save_wordlist(filename, wordlist)
                messagebox.showinfo("Success", f"Saved {len(wordlist):,} words to {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {str(e)}")

    def run(self):
        self.update_status("Ready")
        self.window.mainloop()


if __name__ == "__main__":
    try:
        app = WordlistManagerGUI()
        app.run()
    except Exception as e:
        messagebox.showerror("Fatal Error", f"Application failed to start: {str(e)}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()