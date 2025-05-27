import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import itertools
import os
import time

class WordlistManager:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Wordlist Manager")

        # Create notebook
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(pady=10, expand=True)

        # Create tabs
        self.tab1 = tk.Frame(self.notebook)
        self.tab2 = tk.Frame(self.notebook)
        self.tab3 = tk.Frame(self.notebook)
        self.tab4 = tk.Frame(self.notebook)

        self.notebook.add(self.tab1, text="Load/Save")
        self.notebook.add(self.tab2, text="Bruteforce Generator")
        self.notebook.add(self.tab3, text="Wordlist Manipulation")
        self.notebook.add(self.tab4, text="Wordlist Combiner")

        # Tab 1: Load/Save
        self.label1 = tk.Label(self.tab1, text="Load wordlist from file:")
        self.label1.pack()
        self.button1 = tk.Button(self.tab1, text="Browse", command=self.load_wordlist)
        self.button1.pack()
        self.label2 = tk.Label(self.tab1, text="Save wordlist to file:")
        self.label2.pack()
        self.button2 = tk.Button(self.tab1, text="Browse", command=self.save_wordlist)
        self.button2.pack()
        self.text_area1 = tk.Text(self.tab1, height=10, width=40)
        self.text_area1.pack()

        # Tab 2: Bruteforce Generator
        self.label3 = tk.Label(self.tab2, text="Bruteforce generator options:")
        self.label3.pack()
        self.variables = {
            "uppercase": tk.IntVar(),
            "lowercase": tk.IntVar(),
            "numbers": tk.IntVar(),
            "special_characters": tk.IntVar(),
        }
        self.checkboxes = [
            tk.Checkbutton(self.tab2, text="Uppercase", variable=self.variables["uppercase"]),
            tk.Checkbutton(self.tab2, text="Lowercase", variable=self.variables["lowercase"]),
            tk.Checkbutton(self.tab2, text="Numbers", variable=self.variables["numbers"]),
            tk.Checkbutton(self.tab2, text="Special characters", variable=self.variables["special_characters"]),
        ]
        for checkbox in self.checkboxes:
            checkbox.pack()
        self.label4 = tk.Label(self.tab2, text="Length of words:")
        self.label4.pack()
        self.entry1 = tk.Entry(self.tab2, width=10)
        self.entry1.pack()
        self.button3 = tk.Button(self.tab2, text="Generate", command=self.generate_bruteforce)
        self.button3.pack()
        self.text_area2 = tk.Text(self.tab2, height=10, width=40)
        self.text_area2.pack()

        # Tab 3: Wordlist Manipulation
        self.label5 = tk.Label(self.tab3, text="Enter group of words (separated by commas):")
        self.label5.pack()
        self.entry2 = tk.Entry(self.tab3, width=40)
        self.entry2.pack()
        self.label6 = tk.Label(self.tab3, text="Apply hashcat-like rules:")
        self.label6.pack()
        self.variables2 = {
            "append_numbers": tk.IntVar(),
            "prepend_numbers": tk.IntVar(),
            "append_special_characters": tk.IntVar(),
            "prepend_special_characters": tk.IntVar(),
            "leet_speak": tk.IntVar(),
        }
        self.checkboxes2 = [
            tk.Checkbutton(self.tab3, text="Append numbers", variable=self.variables2["append_numbers"]),
            tk.Checkbutton(self.tab3, text="Prepend numbers", variable=self.variables2["prepend_numbers"]),
            tk.Checkbutton(self.tab3, text="Append special characters", variable=self.variables2["append_special_characters"]),
            tk.Checkbutton(self.tab3, text="Prepend special characters", variable=self.variables2["prepend_special_characters"]),
            tk.Checkbutton(self.tab3, text="Leet speak", variable=self.variables2["leet_speak"]),
        ]
        for checkbox in self.checkboxes2:
            checkbox.pack()
        self.button4 = tk.Button(self.tab3, text="Apply rules", command=self.apply_rules)
        self.button4.pack()
        self.text_area3 = tk.Text(self.tab3, height=10, width=40)
        self.text_area3.pack()

        # Tab 4: Wordlist Combiner
        self.label7 = tk.Label(self.tab4, text="Enter words to combine (separated by commas):")
        self.label7.pack()
        self.entry3 = tk.Entry(self.tab4, width=40)
        self.entry3.pack()
        self.label8 = tk.Label(self.tab4, text="Estimated wordlist size: ")
        self.label8.pack()
        self.label9 = tk.Label(self.tab4, text="Estimated time to complete: ")
        self.label9.pack()

        # Options frame
        self.options_frame = tk.Frame(self.tab4)
        self.options_frame.pack()
        self.variables3 = {
            "combine_words": tk.IntVar(),
            "case_words": tk.IntVar(),
            "leet_speak": tk.IntVar(),
            "append_numbers": tk.IntVar(),
            "prepend_numbers": tk.IntVar(),
            "append_special_characters": tk.IntVar(),
            "prepend_special_characters": tk.IntVar(),
        }
        self.checkboxes3 = [
            tk.Checkbutton(self.options_frame, text="Combine words", variable=self.variables3["combine_words"]),
            tk.Checkbutton(self.options_frame, text="Case words", variable=self.variables3["case_words"]),
            tk.Checkbutton(self.options_frame, text="Leet speak", variable=self.variables3["leet_speak"]),
            tk.Checkbutton(self.options_frame, text="Append numbers", variable=self.variables3["append_numbers"]),
            tk.Checkbutton(self.options_frame, text="Prepend numbers", variable=self.variables3["prepend_numbers"]),
            tk.Checkbutton(self.options_frame, text="Append special characters", variable=self.variables3["append_special_characters"]),
            tk.Checkbutton(self.options_frame, text="Prepend special characters", variable=self.variables3["prepend_special_characters"]),
        ]
        for i, checkbox in enumerate(self.checkboxes3):
            checkbox.grid(row=i // 2, column=i % 2)

        self.button5 = tk.Button(self.tab4, text="Generate wordlist", command=self.generate_combined_wordlist)
        self.button5.pack()
        self.text_area4 = tk.Text(self.tab4, height=10, width=40)
        self.text_area4.pack()

    def load_wordlist(self):
        filename = filedialog.askopenfilename(title="Select wordlist file", filetypes=[("Text files", "*.txt")])
        if filename:
            with open(filename, "r") as file:
                wordlist = [line.strip() for line in file.readlines()]
            self.text_area1.delete(1.0, tk.END)
            for word in wordlist:
                self.text_area1.insert(tk.END, word + "\n")

    def save_wordlist(self):
        filename = filedialog.asksaveasfilename(title="Save wordlist file", filetypes=[("Text files", "*.txt")], defaultextension=".txt")
        if filename:
            wordlist = self.text_area1.get(1.0, tk.END).splitlines()
            with open(filename, "w") as file:
                for word in wordlist:
                    file.write(word + "\n")

    def generate_bruteforce(self):
        length = int(self.entry1.get())
        character_set = ""
        if self.variables["uppercase"].get():
            character_set += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if self.variables["lowercase"].get():
            character_set += "abcdefghijklmnopqrstuvwxyz"
        if self.variables["numbers"].get():
            character_set += "0123456789"
        if self.variables["special_characters"].get():
            character_set += "!@#$%^&*()_+-={}:<>?,./"
        wordlist = [''.join(p) for p in itertools.product(character_set, repeat=length)]
        self.text_area2.delete(1.0, tk.END)
        for word in wordlist:
            self.text_area2.insert(tk.END, word + "\n")

    def apply_rules(self):
        words = self.entry2.get().split(",")
        wordlist = []
        for word in words:
            word = word.strip()
            if self.variables2["append_numbers"].get():
                wordlist.append(word + "1")
                wordlist.append(word + "2")
                wordlist.append(word + "3")
            if self.variables2["prepend_numbers"].get():
                wordlist.append("1" + word)
                wordlist.append("2" + word)
                wordlist.append("3" + word)
            if self.variables2["append_special_characters"].get():
                wordlist.append(word + "!")
                wordlist.append(word + "@")
                wordlist.append(word + "#")
            if self.variables2["prepend_special_characters"].get():
                wordlist.append("!" + word)
                wordlist.append("@ " + word)
                wordlist.append("#" + word)
            if self.variables2["leet_speak"].get():
                wordlist.append(word.replace("e", "3"))
                wordlist.append(word.replace("a", "4"))
                wordlist.append(word.replace("i", "1"))
                wordlist.append(word.replace("o", "0"))
                wordlist.append(word.replace("s", "5"))
            wordlist.append(word)
        self.text_area3.delete(1.0, tk.END)
        for word in wordlist:
            self.text_area3.insert(tk.END, word + "\n")

    def estimate_time(self, words):
        wordlist_size = 0
        for r in range(1, len(words) + 1):
            wordlist_size += len(list(itertools.permutations(words, r))) * 4
        if wordlist_size < 1000:
            return "Less than 1 second"
        elif wordlist_size < 10000:
            return "1-5 seconds"
        elif wordlist_size < 100000:
            return "5-30 seconds"
        elif wordlist_size < 1000000:
            return "30 seconds to 1 minute"
        elif wordlist_size < 10000000:
            return "1-5 minutes"
        else:
            return "More than 5 minutes"

    def generate_combined_wordlist(self):
        words = self.entry3.get().split(",")
        words = [word.strip() for word in words]
        wordlist_size = 0
        for r in range(1, len(words) + 1):
            wordlist_size += len(list(itertools.permutations(words, r))) * 4
        self.label8['text'] = f"Estimated wordlist size: {wordlist_size} words"
        self.label9['text'] = f"Estimated time to complete: {self.estimate_time(words)}"
        self.button5.config(text="Generating...", state="disabled")
        generated_wordlist = []
        for r in range(1, len(words) + 1):
            for combo in itertools.permutations(words, r):
                word = ''.join(combo)
                if self.variables3["case_words"].get():
                    generated_wordlist.append(word)
                    generated_wordlist.append(word.upper())
                    generated_wordlist.append(word.lower())
                    generated_wordlist.append(word.capitalize())
                else:
                    generated_wordlist.append(word)
                if self.variables3["leet_speak"].get():
                    leet_word = word.replace("e", "3").replace("a", "4").replace("i", "1").replace("o", "0").replace("s", "5")
                    generated_wordlist.append(leet_word)
                if self.variables3["append_numbers"].get():
                    generated_wordlist.append(word + "1")
                    generated_wordlist.append(word + "2")
                    generated_wordlist.append(word + "3")
                if self.variables3["prepend_numbers"].get():
                    generated_wordlist.append("1" + word)
                    generated_wordlist.append("2" + word)
                    generated_wordlist.append("3" + word)
                if self.variables3["append_special_characters"].get():
                    generated_wordlist.append(word + "!")
                    generated_wordlist.append(word + "@")
                    generated_wordlist.append(word + "#")
                if self.variables3["prepend_special_characters"].get():
                    generated_wordlist.append("!" + word)
                    generated_wordlist.append("@ " + word)
                    generated_wordlist.append("#" + word)
                if self.variables3["combine_words"].get():
                    for other_word in words:
                        if other_word!= word:
                            generated_wordlist.append(word + other_word)
                            generated_wordlist.append(other_word + word)
        self.text_area4.delete(1.0, tk.END)
        for word in generated_wordlist:
            self.text_area4.insert(tk.END, word + "\n")
        filename = filedialog.asksaveasfilename(title="Save wordlist file", filetypes=[("Text files", "*.txt")], defaultextension=".txt")
        if filename:
            with open(filename, "w") as file:
                for word in generated_wordlist:
                    file.write(word + "\n")
        self.button5.config(text="Generate wordlist", state="normal")

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = WordlistManager()
    app.run()