import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import itertools
import os
import time
import threading
import subprocess
import re
import select
from collections import OrderedDict
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import queue

class WordlistGenerator:
    """Handles wordlist generation logic"""
    
    CHARACTER_SETS = {
        'uppercase': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        'lowercase': 'abcdefghijklmnopqrstuvwxyz',
        'numbers': '0123456789',
        'special_characters': '!@#$%^&*()_+-={}:<>?,./'
    }
    
    LEET_MAP = {'e': '3', 'a': '4', 'i': '1', 'o': '0', 's': '5', 't': '7', 'l': '1'}
    DEFAULT_NUMBERS = ['1', '2', '3', '123', '2023', '2024']
    DEFAULT_SPECIAL_CHARS = ['!', '@', '#', '$', '!@#']
    
    @staticmethod
    def generate_brute_force(character_sets, length, progress_callback=None):
        """Generate brute force wordlist with progress tracking"""
        charset = ''.join(WordlistGenerator.CHARACTER_SETS[cs] for cs in character_sets if cs in WordlistGenerator.CHARACTER_SETS)
        if not charset:
            return []
        
        total = len(charset) ** length
        if total > 1000000:  # 1M limit for GUI display
            raise ValueError(f"Too many combinations ({total:,}). Consider using file output directly.")
        
        wordlist = []
        for i, combo in enumerate(itertools.product(charset, repeat=length)):
            if progress_callback and i % 1000 == 0:
                progress_callback(i / total * 100)
            wordlist.append(''.join(combo))
        
        return wordlist
    
    @staticmethod
    def apply_leet_speak(word):
        """Apply leet speak transformations"""
        leet_word = word.lower()
        for char, replacement in WordlistGenerator.LEET_MAP.items():
            leet_word = leet_word.replace(char, replacement)
        return leet_word
    
    @staticmethod
    def apply_rules_to_word(word, rules):
        """Apply transformation rules to a single word"""
        variations = [word]
        
        if rules.get('leet_speak'):
            variations.append(WordlistGenerator.apply_leet_speak(word))
        
        if rules.get('case_variations'):
            variations.extend([word.upper(), word.lower(), word.capitalize()])
        
        # Apply number/special char rules to all variations
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
        
        return list(OrderedDict.fromkeys(final_variations))  # Remove duplicates while preserving order


class WordlistFileManager:
    """Handles file I/O operations"""
    
    @staticmethod
    def load_wordlist(filename):
        """Load wordlist from file with proper error handling"""
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as file:
                return [line.strip() for line in file if line.strip()]
        except Exception as e:
            raise Exception(f"Failed to load file: {str(e)}")
    
    @staticmethod
    def save_wordlist(filename, wordlist, chunk_size=10000):
        """Save wordlist to file with chunking for large lists"""
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                for i, word in enumerate(wordlist):
                    file.write(word + '\n')
                    if i % chunk_size == 0:
                        file.flush()  # Flush periodically for large files
        except Exception as e:
            raise Exception(f"Failed to save file: {str(e)}")


class WebScraper:
    """Scrapes words from websites like CeWL"""
    
    @staticmethod
    def scrape_website(url, depth=1, include_external=False, progress_callback=None):
        """Scrape words from a website with depth control"""
        try:
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme:
                url = "http://" + url
                parsed_url = urlparse(url)
            
            base_domain = parsed_url.netloc
            visited = set()
            words = set()
            to_visit = queue.Queue()
            to_visit.put((url, 0))
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            while not to_visit.empty():
                current_url, current_depth = to_visit.get()
                
                if current_url in visited:
                    continue
                
                visited.add(current_url)
                
                try:
                    response = requests.get(current_url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    # Extract words from page content
                    soup = BeautifulSoup(response.content, 'html.parser')
                    text = soup.get_text()
                    page_words = re.findall(r'\b[a-zA-Z]{4,}\b', text)  # Words with 4+ letters
                    words.update(page_words)
                    
                    # Update progress
                    if progress_callback:
                        progress_callback(len(visited))
                    
                    # Add links to queue if we haven't reached depth limit
                    if current_depth < depth:
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            next_url = urljoin(current_url, href)
                            parsed_next = urlparse(next_url)
                            
                            # Filter links
                            if not include_external and parsed_next.netloc != base_domain:
                                continue
                            
                            if next_url not in visited:
                                to_visit.put((next_url, current_depth + 1))
                
                except Exception as e:
                    print(f"Error scraping {current_url}: {str(e)}")
            
            return list(words)
        
        except Exception as e:
            raise Exception(f"Scraping failed: {str(e)}")


class HashcatManager:
    """Manages Hashcat integration"""
    
    COMMON_MODES = {
        "MD5": 0,
        "SHA1": 100,
        "SHA256": 1400,
        "NTLM": 1000,
        "LM": 3000,
        "WPA/WPA2": 22000,
        "Kerberos": 13100,
        "NetNTLMv1": 5500,
        "NetNTLMv2": 5600,
        "bcrypt": 3200,
        "scrypt": 8900,
        "Wordpress": 400,
        "JWT": 16500
    }
    
    @staticmethod
    def run_hashcat(hash_file, wordlist_file, hash_mode, extra_args="", progress_callback=None, status_callback=None):
        """Run hashcat with the specified parameters"""
        try:
            # Check if hashcat is available
            result = subprocess.run(['hashcat', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("Hashcat not found. Make sure it's installed and in your PATH.")
            
            # Build command
            cmd = [
                'hashcat',
                '-m', str(hash_mode),
                '-a', '0',  # Dictionary attack
                '--potfile-disable',  # Don't use potfile
                '-o', 'cracked.txt',  # Output file
                '--status',  # Enable status updates
                '--status-timer=60',  # Update every minute
                hash_file,
                wordlist_file
            ]
            
            # Add extra arguments if provided
            if extra_args:
                cmd.extend(extra_args.split())
            
            # Run hashcat
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,  # Add stdin for sending 's' key
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Store the process for later interaction
            if status_callback:
                status_callback(process)
            
            # Read output line by line
            output_lines = []
            while True:
                # Use select to check if there's data to read
                rlist, _, _ = select.select([process.stdout], [], [], 0.1)
                if process.stdout in rlist:
                    line = process.stdout.readline()
                    if not line:
                        break
                    output_lines.append(line)
                    if progress_callback:
                        progress_callback(line.strip())
                
                # Check if process has finished
                if process.poll() is not None:
                    break
            
            process.wait()
            
            # Read cracked hashes if any
            cracked = []
            if os.path.exists('cracked.txt'):
                with open('cracked.txt', 'r') as f:
                    cracked = [line.strip() for line in f if line.strip()]
            
            return {
                "success": process.returncode == 0,
                "returncode": process.returncode,
                "output": "\n".join(output_lines),
                "cracked": cracked
            }
            
        except Exception as e:
            raise Exception(f"Hashcat execution failed: {str(e)}")


class WordlistManagerGUI:
    """Main GUI application"""
    
    # Constants
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
        self.combiner_wordlist1 = []
        self.combiner_wordlist2 = []
        self.scraped_words = []
        self.hashcat_process = None
    
    def setup_window(self):
        """Initialize main window"""
        self.window = tk.Tk()
        self.window.title("WLAIO - Advanced Wordlist Manager")
        self.window.minsize(self.WINDOW_MIN_WIDTH, self.WINDOW_MIN_HEIGHT)
        self.window.geometry("900x750")
    
    def create_notebook(self):
        """Create tabbed interface"""
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
    
    def setup_all_tabs(self):
        """Setup all application tabs"""
        self.tabs = {}
        tab_configs = [
            ("Load/Save", self.setup_load_save_tab),
            ("Brute Force", self.setup_brute_force_tab),
            ("Word Rules", self.setup_rules_tab),
            ("Combiner", self.setup_combiner_tab),
            ("Web Scraper", self.setup_web_scraper_tab),
            ("Hashcat", self.setup_hashcat_tab)
        ]
        
        for name, setup_func in tab_configs:
            frame = ttk.Frame(self.notebook)
            self.tabs[name.lower().replace('/', '_').replace(' ', '_')] = frame
            self.notebook.add(frame, text=name)
            setup_func(frame)
    
    def setup_load_save_tab(self, parent):
        """Setup load/save functionality tab"""
        # File operations frame
        file_frame = ttk.LabelFrame(parent, text="File Operations", padding=10)
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(file_frame, text="📁 Load Wordlist", command=self.load_wordlist).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="💾 Save Wordlist", command=self.save_wordlist).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="🗑️ Clear", command=self.clear_load_save_area).pack(side=tk.LEFT, padx=5)
        
        # Stats frame
        stats_frame = ttk.Frame(file_frame)
        stats_frame.pack(side=tk.RIGHT)
        self.word_count_label = ttk.Label(stats_frame, text="Words: 0")
        self.word_count_label.pack()
        
        # Text area with scrollbar
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_area_load_save = tk.Text(text_frame, height=self.TEXT_AREA_HEIGHT, 
                                          width=self.TEXT_AREA_WIDTH, wrap=tk.WORD)
        scrollbar1 = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_area_load_save.yview)
        self.text_area_load_save.configure(yscrollcommand=scrollbar1.set)
        
        self.text_area_load_save.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar1.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind text change event
        self.text_area_load_save.bind('<KeyRelease>', self.update_word_count)
    
    def setup_brute_force_tab(self, parent):
        """Setup brute force generation tab"""
        # Options frame
        options_frame = ttk.LabelFrame(parent, text="Character Sets", padding=10)
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.brute_force_vars = {}
        brute_force_options = ['uppercase', 'lowercase', 'numbers', 'special_characters']
        
        for i, option in enumerate(brute_force_options):
            var = tk.IntVar()
            self.brute_force_vars[option] = var
            cb = ttk.Checkbutton(options_frame, text=option.replace('_', ' ').title(), variable=var)
            cb.grid(row=i//2, column=i%2, sticky=tk.W, padx=10, pady=2)
        
        # Length frame
        length_frame = ttk.LabelFrame(parent, text="Configuration", padding=10)
        length_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(length_frame, text="Length:").pack(side=tk.LEFT)
        self.length_entry = ttk.Entry(length_frame, width=10)
        self.length_entry.pack(side=tk.LEFT, padx=5)
        self.length_entry.insert(0, "4")
        
        # Store button references for safe access
        self.generate_brute_force_button = ttk.Button(
            length_frame, 
            text="🔢 Generate", 
            command=self.generate_brute_force
        )
        self.generate_brute_force_button.pack(side=tk.LEFT, padx=10)
        
        self.save_brute_force_button = ttk.Button(
            length_frame, 
            text="💾 Save to File", 
            command=self.save_brute_force_to_file
        )
        self.save_brute_force_button.pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.brute_force_progress = ttk.Progressbar(length_frame, mode='determinate')
        self.brute_force_progress.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)
        
        # Warning label
        self.brute_force_warning = ttk.Label(parent, text="", foreground="red")
        self.brute_force_warning.pack(padx=5)
        
        # Text area
        text_frame2 = ttk.Frame(parent)
        text_frame2.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_area_brute_force = tk.Text(text_frame2, height=self.TEXT_AREA_HEIGHT, 
                                           width=self.TEXT_AREA_WIDTH)
        scrollbar2 = ttk.Scrollbar(text_frame2, orient=tk.VERTICAL, command=self.text_area_brute_force.yview)
        self.text_area_brute_force.configure(yscrollcommand=scrollbar2.set)
        
        self.text_area_brute_force.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind length entry to show estimates
        self.length_entry.bind('<KeyRelease>', self.update_brute_force_estimate)
    
    def setup_rules_tab(self, parent):
        """Setup word rules transformation tab"""
        # Input frame
        input_frame = ttk.LabelFrame(parent, text="Input Words", padding=10)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(input_frame, text="Words (comma-separated):").pack(anchor=tk.W)
        self.rules_entry = ttk.Entry(input_frame, width=60)
        self.rules_entry.pack(fill=tk.X, pady=5)
        
        # Rules frame
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
        
        # Action buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="⚡ Apply Rules", command=self.apply_rules).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🗑️ Clear", command=self.clear_rules_area).pack(side=tk.LEFT, padx=5)
        
        # Text area
        text_frame3 = ttk.Frame(parent)
        text_frame3.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_area_rules = tk.Text(text_frame3, height=self.TEXT_AREA_HEIGHT, 
                                     width=self.TEXT_AREA_WIDTH)
        scrollbar3 = ttk.Scrollbar(text_frame3, orient=tk.VERTICAL, command=self.text_area_rules.yview)
        self.text_area_rules.configure(yscrollcommand=scrollbar3.set)
        
        self.text_area_rules.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar3.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_combiner_tab(self, parent):
        """Setup word combiner tab with two wordlist inputs"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Wordlist 1 Section
        wl1_frame = ttk.LabelFrame(main_frame, text="Wordlist 1", padding=10)
        wl1_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.wl1_btn = ttk.Button(wl1_frame, 
                                text="📁 Load Wordlist 1", 
                                command=lambda: self.load_combiner_wordlist(1))
        self.wl1_btn.pack(side=tk.LEFT, padx=5)
        self.wl1_label = ttk.Label(wl1_frame, text="0 words loaded")
        self.wl1_label.pack(side=tk.LEFT)

        # Wordlist 2 Section
        wl2_frame = ttk.LabelFrame(main_frame, text="Wordlist 2", padding=10)
        wl2_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.wl2_btn = ttk.Button(wl2_frame,
                                text="📁 Load Wordlist 2",
                                command=lambda: self.load_combiner_wordlist(2))
        self.wl2_btn.pack(side=tk.LEFT, padx=5)
        self.wl2_label = ttk.Label(wl2_frame, text="0 words loaded")
        self.wl2_label.pack(side=tk.LEFT)

        # Transformation Options
        options_frame = ttk.LabelFrame(main_frame, 
                                     text="Combination Options", 
                                     padding=10)
        options_frame.pack(fill=tk.X, padx=5, pady=5)

        self.combiner_vars = {
            'case_variations': tk.IntVar(),
            'leet_speak': tk.IntVar(),
            'append_numbers': tk.IntVar(),
            'prepend_numbers': tk.IntVar(),
            'append_special_characters': tk.IntVar(),
            'prepend_special_characters': tk.IntVar()
        }

        for i, (opt, var) in enumerate(self.combiner_vars.items()):
            cb = ttk.Checkbutton(options_frame, 
                               text=opt.replace('_', ' ').title(),
                               variable=var)
            cb.grid(row=i//3, column=i%3, sticky=tk.W, padx=10, pady=2)

        # Stats and Actions
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.combiner_size_label = ttk.Label(stats_frame, 
                                          text="Estimated combinations: 0")
        self.combiner_size_label.pack(side=tk.LEFT)
        
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.generate_combiner_btn = ttk.Button(action_frame, 
                                             text="🚀 Combine Wordlists",
                                             command=self.generate_combined_wordlist)
        self.generate_combiner_btn.pack(side=tk.LEFT)
        
        # Use determinate progress bar for combiner
        self.combiner_progress = ttk.Progressbar(action_frame, mode='determinate')
        self.combiner_progress.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # Results Display
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_area_combiner = tk.Text(text_frame, 
                                        height=self.TEXT_AREA_HEIGHT,
                                        width=self.TEXT_AREA_WIDTH, 
                                        wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, 
                                command=self.text_area_combiner.yview)
        self.text_area_combiner.configure(yscrollcommand=scrollbar.set)
        self.text_area_combiner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_web_scraper_tab(self, parent):
        """Setup web scraper tab (CeWL-like functionality)"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # URL Input
        url_frame = ttk.Frame(frame)
        url_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(url_frame, text="Website URL:").pack(side=tk.LEFT)
        self.scrape_url = ttk.Entry(url_frame, width=50)
        self.scrape_url.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.scrape_url.insert(0, "http://example.com")
        
        # Options
        options_frame = ttk.LabelFrame(frame, text="Scraping Options", padding=10)
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(options_frame, text="Depth:").pack(side=tk.LEFT)
        self.scrape_depth = ttk.Spinbox(options_frame, from_=1, to=5, width=5)
        self.scrape_depth.set(1)
        self.scrape_depth.pack(side=tk.LEFT, padx=5)
        
        self.include_external = tk.IntVar()
        ttk.Checkbutton(
            options_frame, 
            text="Include External Links", 
            variable=self.include_external
        ).pack(side=tk.LEFT, padx=10)
        
        # Action buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            btn_frame, 
            text="🌐 Scrape Website", 
            command=self.scrape_website
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            btn_frame, 
            text="💾 Save Scraped Words", 
            command=self.save_scraped_words
        ).pack(side=tk.LEFT, padx=10)
        
        # Progress
        self.scrape_progress = ttk.Progressbar(btn_frame, mode='determinate')
        self.scrape_progress.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # Stats
        self.scrape_stats = ttk.Label(frame, text="0 words scraped")
        self.scrape_stats.pack(anchor=tk.W, padx=5)
        
        # Results
        results_frame = ttk.LabelFrame(frame, text="Scraped Words", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_area_scraper = tk.Text(results_frame, height=15)
        scrollbar = ttk.Scrollbar(results_frame, command=self.text_area_scraper.yview)
        self.text_area_scraper.configure(yscrollcommand=scrollbar.set)
        self.text_area_scraper.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_hashcat_tab(self, parent):
        """Setup Hashcat integration tab"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # File selection
        file_frame = ttk.Frame(frame)
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(file_frame, text="Hash File:").pack(side=tk.LEFT)
        self.hash_file_entry = ttk.Entry(file_frame, width=40)
        self.hash_file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(
            file_frame, 
            text="Browse", 
            command=lambda: self.browse_file(self.hash_file_entry)
        ).pack(side=tk.LEFT)
        
        file_frame2 = ttk.Frame(frame)
        file_frame2.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(file_frame2, text="Wordlist File:").pack(side=tk.LEFT)
        self.wordlist_file_entry = ttk.Entry(file_frame2, width=40)
        self.wordlist_file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(
            file_frame2, 
            text="Browse", 
            command=lambda: self.browse_file(self.wordlist_file_entry)
        ).pack(side=tk.LEFT)
        
        # Hash mode selection
        mode_frame = ttk.Frame(frame)
        mode_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(mode_frame, text="Hash Mode:").pack(side=tk.LEFT)
        self.hash_mode = ttk.Combobox(mode_frame, width=25)
        self.hash_mode['values'] = list(HashcatManager.COMMON_MODES.keys())
        self.hash_mode.set("MD5")
        self.hash_mode.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(mode_frame, text="Mode ID:").pack(side=tk.LEFT, padx=(20, 0))
        self.mode_id_var = tk.StringVar(value="0")
        ttk.Label(mode_frame, textvariable=self.mode_id_var).pack(side=tk.LEFT, padx=5)
        
        # Bind mode selection to update mode ID
        self.hash_mode.bind("<<ComboboxSelected>>", self.update_hash_mode_id)
        
        # Extra arguments
        arg_frame = ttk.Frame(frame)
        arg_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(arg_frame, text="Extra Arguments:").pack(side=tk.LEFT)
        self.extra_args = ttk.Entry(arg_frame, width=40)
        self.extra_args.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.extra_args.insert(0, "--force -O")  # Common options
        
        # Action buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.run_hashcat_btn = ttk.Button(
            btn_frame, 
            text="🔓 Run Hashcat Attack", 
            command=self.run_hashcat_attack
        )
        self.run_hashcat_btn.pack(side=tk.LEFT)
        
        self.status_hashcat_btn = ttk.Button(
            btn_frame, 
            text="🔄 Get Status", 
            command=self.request_hashcat_status,
            state=tk.DISABLED
        )
        self.status_hashcat_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_hashcat_btn = ttk.Button(
            btn_frame, 
            text="⏹ Stop", 
            command=self.stop_hashcat_attack,
            state=tk.DISABLED
        )
        self.stop_hashcat_btn.pack(side=tk.LEFT)
        
        self.hashcat_progress = ttk.Progressbar(btn_frame, mode='indeterminate')
        self.hashcat_progress.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # Output area
        output_frame = ttk.LabelFrame(frame, text="Hashcat Output", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_area_hashcat = tk.Text(output_frame, height=15)
        scrollbar = ttk.Scrollbar(output_frame, command=self.text_area_hashcat.yview)
        self.text_area_hashcat.configure(yscrollcommand=scrollbar.set)
        self.text_area_hashcat.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Cracked results
        cracked_frame = ttk.LabelFrame(frame, text="Cracked Hashes", padding=10)
        cracked_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_area_cracked = tk.Text(cracked_frame, height=5)
        scrollbar2 = ttk.Scrollbar(cracked_frame, command=self.text_area_cracked.yview)
        self.text_area_cracked.configure(yscrollcommand=scrollbar2.set)
        self.text_area_cracked.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)

    def update_hash_mode_id(self, event=None):
        """Update mode ID when hash mode selection changes"""
        mode_name = self.hash_mode.get()
        if mode_name in HashcatManager.COMMON_MODES:
            self.mode_id_var.set(str(HashcatManager.COMMON_MODES[mode_name]))

    def browse_file(self, entry_widget):
        """Open file dialog and set entry text"""
        filename = filedialog.askopenfilename()
        if filename:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, filename)

    def scrape_website(self):
        """Scrape words from a website"""
        url = self.scrape_url.get().strip()
        if not url:
            messagebox.showerror("Error", "Enter a valid URL")
            return
        
        try:
            depth = int(self.scrape_depth.get())
        except ValueError:
            depth = 1
        
        include_external = bool(self.include_external.get())
        
        # Reset UI
        self.scraped_words = []
        self.text_area_scraper.delete(1.0, tk.END)
        self.scrape_progress['value'] = 0
        self.scrape_stats.config(text="Starting scraping...")
        self.update_status(f"Scraping {url} (depth={depth})...")
        
        def scrape_thread():
            try:
                def progress_callback(pages_done):
                    self.window.after(0, lambda: 
                        self.scrape_progress.config(value=pages_done * 10))
                    self.window.after(0, lambda: 
                        self.scrape_stats.config(text=f"Scraped {pages_done} pages"))
                
                words = WebScraper.scrape_website(
                    url, 
                    depth=depth, 
                    include_external=include_external,
                    progress_callback=progress_callback
                )
                
                self.scraped_words = words
                self.window.after(0, lambda: self.display_scraped_results(words))
                
            except Exception as e:
                self.window.after(0, lambda: 
                    messagebox.showerror("Scraping Error", str(e)))
            finally:
                self.window.after(0, self.reset_scraper_ui)
        
        threading.Thread(target=scrape_thread, daemon=True).start()

    def display_scraped_results(self, wordlist):
        """Display scraped words in the text area"""
        self.text_area_scraper.delete(1.0, tk.END)
        
        if wordlist:
            # Display only unique words, sorted alphabetically
            unique_words = sorted(set(wordlist))
            self.text_area_scraper.insert(tk.END, '\n'.join(unique_words))
            self.scrape_stats.config(text=f"Scraped {len(unique_words)} unique words")
            self.update_status(f"Scraped {len(unique_words)} words from website")
        else:
            self.scrape_stats.config(text="No words scraped")
            self.update_status("No words scraped from website")

    def reset_scraper_ui(self):
        """Reset scraper UI elements"""
        self.scrape_progress.config(value=0)

    def save_scraped_words(self):
        """Save scraped words to a file"""
        if not self.scraped_words:
            messagebox.showinfo("Info", "No words to save. Scrape a website first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt", 
            filetypes=[("Text files", "*.txt")]
        )
        if filename:
            try:
                WordlistFileManager.save_wordlist(filename, self.scraped_words)
                self.update_status(f"Saved {len(self.scraped_words)} scraped words to file")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")

    def run_hashcat_attack(self):
        """Run hashcat attack using the specified parameters"""
        hash_file = self.hash_file_entry.get().strip()
        wordlist_file = self.wordlist_file_entry.get().strip()
        hash_mode = self.mode_id_var.get()
        extra_args = self.extra_args.get().strip()
        
        if not hash_file or not os.path.exists(hash_file):
            messagebox.showerror("Error", "Select a valid hash file")
            return
        
        if not wordlist_file or not os.path.exists(wordlist_file):
            messagebox.showerror("Error", "Select a valid wordlist file")
            return
        
        if not hash_mode.isdigit():
            messagebox.showerror("Error", "Select a valid hash mode")
            return
        
        # Reset UI
        self.text_area_hashcat.delete(1.0, tk.END)
        self.text_area_cracked.delete(1.0, tk.END)
        self.hashcat_progress.start()
        self.run_hashcat_btn.config(state=tk.DISABLED)
        self.status_hashcat_btn.config(state=tk.NORMAL)
        self.stop_hashcat_btn.config(state=tk.NORMAL)
        self.update_status("Starting Hashcat attack...")
        
        # Store the process reference
        self.hashcat_process = None
        
        def status_callback(process):
            """Callback to store the hashcat process"""
            self.hashcat_process = process
        
        def hashcat_thread():
            try:
                def progress_callback(line):
                    self.window.after(0, lambda: 
                        self.text_area_hashcat.insert(tk.END, line + "\n"))
                    self.window.after(0, lambda: 
                        self.text_area_hashcat.see(tk.END))
                
                result = HashcatManager.run_hashcat(
                    hash_file,
                    wordlist_file,
                    int(hash_mode),
                    extra_args,
                    progress_callback,
                    status_callback
                )
                
                self.window.after(0, lambda: self.display_hashcat_results(result))
                
            except Exception as e:
                self.window.after(0, lambda: 
                    messagebox.showerror("Hashcat Error", str(e)))
            finally:
                self.window.after(0, self.reset_hashcat_ui)

        threading.Thread(target=hashcat_thread, daemon=True).start()

    def request_hashcat_status(self):
        """Send 's' key to Hashcat process to request status update"""
        if self.hashcat_process:
            try:
                # Send 's' followed by newline to request status
                self.hashcat_process.stdin.write('s\n')
                self.hashcat_process.stdin.flush()
                self.update_status("Requested status update from Hashcat...")
            except Exception as e:
                self.text_area_hashcat.insert(tk.END, f"\nFailed to request status: {str(e)}\n")
        else:
            self.text_area_hashcat.insert(tk.END, "\nNo active Hashcat process to request status from\n")

    def stop_hashcat_attack(self):
        """Stop the running Hashcat attack"""
        if self.hashcat_process:
            try:
                self.hashcat_process.terminate()
                self.text_area_hashcat.insert(tk.END, "\n\nHashcat attack stopped by user\n")
                self.update_status("Hashcat attack stopped")
            except Exception as e:
                self.text_area_hashcat.insert(tk.END, f"\nFailed to stop Hashcat: {str(e)}\n")
            finally:
                self.reset_hashcat_ui()
        else:
            self.text_area_hashcat.insert(tk.END, "\nNo active Hashcat process to stop\n")

    def display_hashcat_results(self, result):
        """Display hashcat results in the UI"""
        self.hashcat_progress.stop()
        
        if result['success']:
            self.text_area_hashcat.insert(tk.END, "\n\nHashcat completed successfully!\n")
            if result['cracked']:
                self.text_area_cracked.insert(tk.END, "\n".join(result['cracked']))
                self.update_status(f"Hashcat cracked {len(result['cracked'])} hashes!")
            else:
                self.text_area_cracked.insert(tk.END, "No hashes cracked")
                self.update_status("Hashcat completed but no hashes cracked")
        else:
            self.text_area_hashcat.insert(tk.END, f"\n\nHashcat failed with exit code {result['returncode']}\n")
            self.update_status("Hashcat attack failed")

    def reset_hashcat_ui(self):
        """Reset hashcat UI elements"""
        self.hashcat_progress.stop()
        self.run_hashcat_btn.config(state=tk.NORMAL)
        self.status_hashcat_btn.config(state=tk.DISABLED)
        self.stop_hashcat_btn.config(state=tk.DISABLED)
        self.hashcat_process = None

    def load_combiner_wordlist(self, list_num):
        """Load wordlist for combiner tab"""
        filename = filedialog.askopenfilename(
            title=f"Select Wordlist {list_num}",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                words = WordlistFileManager.load_wordlist(filename)
                if list_num == 1:
                    self.combiner_wordlist1 = words
                    self.wl1_label.config(text=f"{len(words):,} words loaded")
                else:
                    self.combiner_wordlist2 = words
                    self.wl2_label.config(text=f"{len(words):,} words loaded")
                self.update_combiner_estimate()
            except Exception as e:
                messagebox.showerror("Loading Error", f"Failed to load wordlist: {str(e)}")

    def update_combiner_estimate(self, event=None):
        """Update combination estimates"""
        len1 = len(self.combiner_wordlist1)
        len2 = len(self.combiner_wordlist2)
        
        if len1 == 0 or len2 == 0:
            self.combiner_size_label.config(text="Estimated combinations: 0")
            return
        
        base_combinations = len1 * len2
        multiplier = 1
        
        # Calculate transformation multiplier
        if self.combiner_vars['case_variations'].get():
            multiplier *= 3  # Upper, lower, capitalize
        if self.combiner_vars['leet_speak'].get():
            multiplier *= 2
        if self.combiner_vars['append_numbers'].get():
            multiplier *= len(WordlistGenerator.DEFAULT_NUMBERS) + 1
        if self.combiner_vars['prepend_numbers'].get():
            multiplier *= len(WordlistGenerator.DEFAULT_NUMBERS) + 1
        if self.combiner_vars['append_special_characters'].get():
            multiplier *= len(WordlistGenerator.DEFAULT_SPECIAL_CHARS) + 1
        if self.combiner_vars['prepend_special_characters'].get():
            multiplier *= len(WordlistGenerator.DEFAULT_SPECIAL_CHARS) + 1
        
        estimated = base_combinations * multiplier
        self.combiner_size_label.config(text=f"Estimated combinations: {estimated:,}")

    def generate_combined_wordlist(self):
        """Generate combinations from two loaded wordlists"""
        if not self.combiner_wordlist1 or not self.combiner_wordlist2:
            messagebox.showerror("Error", "Load both wordlists first")
            return

        # Get selected options
        options = {name: var.get() for name, var in self.combiner_vars.items()}
        
        # UI Setup
        self.generate_combiner_btn.config(state='disabled', text="Generating...")
        self.combiner_progress['value'] = 0
        self.update_status("Combining wordlists...")

        def generation_thread():
            try:
                unique_combinations = OrderedDict()
                total_pairs = len(self.combiner_wordlist1) * len(self.combiner_wordlist2)
                processed = 0
                
                for w1, w2 in itertools.product(self.combiner_wordlist1, self.combiner_wordlist2):
                    base = f"{w1}{w2}"
                    variations = [base]
                    
                    # Case variations
                    if options['case_variations']:
                        variations.extend([
                            base.upper(),
                            base.lower(),
                            base.capitalize()
                        ])
                    
                    # Leet speak transformations
                    if options['leet_speak']:
                        for var in variations.copy():
                            leet_version = WordlistGenerator.apply_leet_speak(var)
                            if leet_version not in variations:
                                variations.append(leet_version)
                    
                    # Number/Special character transformations
                    final_variants = []
                    for variant in variations:
                        final_variants.append(variant)
                        
                        # Append numbers
                        if options['append_numbers']:
                            final_variants.extend(
                                [f"{variant}{num}" for num in WordlistGenerator.DEFAULT_NUMBERS]
                            )
                        
                        # Prepend numbers
                        if options['prepend_numbers']:
                            final_variants.extend(
                                [f"{num}{variant}" for num in WordlistGenerator.DEFAULT_NUMBERS]
                            )
                        
                        # Append special characters
                        if options['append_special_characters']:
                            final_variants.extend(
                                [f"{variant}{sc}" for sc in WordlistGenerator.DEFAULT_SPECIAL_CHARS]
                            )
                        
                        # Prepend special characters
                        if options['prepend_special_characters']:
                            final_variants.extend(
                                [f"{sc}{variant}" for sc in WordlistGenerator.DEFAULT_SPECIAL_CHARS]
                            )
                    
                    # Add to unique combinations
                    for variant in final_variants:
                        unique_combinations[variant] = None
                    
                    # Update progress
                    processed += 1
                    if processed % 100 == 0 or processed == total_pairs:
                        progress = (processed / total_pairs) * 100
                        self.window.after(0, lambda: 
                            self.combiner_progress.config(value=progress))
                        self.window.after(0, lambda: 
                            self.update_status(f"Processed {processed:,} of {total_pairs:,} pairs"))

                # Convert to list
                final_list = list(unique_combinations.keys())
                
                # Update UI
                self.window.after(0, lambda: self.display_combined_results(final_list))
                
            except Exception as e:
                self.window.after(0, lambda: 
                    messagebox.showerror("Generation Error", str(e)))
            finally:
                self.window.after(0, self.reset_combiner_ui)

        threading.Thread(target=generation_thread, daemon=True).start()

    def display_combined_results(self, wordlist):
        """Display combined wordlist results"""
        self.text_area_combiner.delete(1.0, tk.END)
        
        if len(wordlist) > 5000:  # Limit GUI display for performance
            self.text_area_combiner.insert(tk.END, '\n'.join(wordlist[:5000]))
            self.text_area_combiner.insert(tk.END, f"\n\n... and {len(wordlist)-5000:,} more words")
            
            # Offer to save large wordlists
            if messagebox.askyesno("Large Wordlist", 
                f"Generated {len(wordlist):,} words. Would you like to save to file?"):
                self.save_large_wordlist(wordlist)
        else:
            self.text_area_combiner.insert(tk.END, '\n'.join(wordlist))
        
        self.reset_combiner_ui()
        self.update_status(f"Generated {len(wordlist):,} combined words")

    def reset_combiner_ui(self):
        """Reset combiner UI elements"""
        self.generate_combiner_btn.config(state='normal', text="🚀 Combine Wordlists")
        self.combiner_progress.config(value=0)
    
    def setup_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.window)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.window.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Remove Duplicates", command=self.remove_duplicates)
        edit_menu.add_command(label="Sort Alphabetically", command=self.sort_wordlist)
        edit_menu.add_command(label="Show Statistics", command=self.show_statistics)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        self.window.config(menu=menubar)
    
    def setup_status_bar(self):
        """Create status bar"""
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.window, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_keyboard_shortcuts(self):
        """Configure keyboard shortcuts"""
        self.window.bind('<Control-o>', lambda event: self.load_wordlist())
        self.window.bind('<Control-s>', lambda event: self.save_wordlist())
    
    def update_status(self, message):
        """Update status bar message"""
        self.status_var.set(message)
        self.window.update_idletasks()
    
    def update_word_count(self, event=None):
        """Update word count display"""
        text = self.text_area_load_save.get("1.0", tk.END)
        words = [w for w in text.split() if w.strip()]
        self.word_count_label.config(text=f"Words: {len(words)}")
    
    def load_wordlist(self):
        """Load wordlist from file"""
        filename = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filename:
            try:
                words = WordlistFileManager.load_wordlist(filename)
                self.current_wordlist = words
                self.text_area_load_save.delete(1.0, tk.END)
                self.text_area_load_save.insert(tk.END, '\n'.join(words))
                self.update_word_count()
                self.update_status(f"Loaded {len(words)} words from {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")
    
    def save_wordlist(self):
        """Save wordlist to file"""
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if filename:
            try:
                text = self.text_area_load_save.get(1.0, tk.END)
                words = [word.strip() for word in text.splitlines() if word.strip()]
                WordlistFileManager.save_wordlist(filename, words)
                self.update_status(f"Saved {len(words)} words to {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
    
    def clear_load_save_area(self):
        """Clear load/save text area"""
        self.text_area_load_save.delete(1.0, tk.END)
        self.current_wordlist = []
        self.update_word_count()
        self.update_status("Cleared wordlist")
    
    def clear_rules_area(self):
        """Clear rules text area"""
        self.text_area_rules.delete(1.0, tk.END)
        self.update_status("Cleared rules output")
    
    def update_brute_force_estimate(self, event=None):
        """Update brute force combination estimate"""
        try:
            length = int(self.length_entry.get())
        except ValueError:
            self.brute_force_warning.config(text="Invalid length")
            return
        
        charsets = [key for key, var in self.brute_force_vars.items() if var.get() == 1]
        charset = ''.join(WordlistGenerator.CHARACTER_SETS[cs] for cs in charsets)
        
        if not charset:
            self.brute_force_warning.config(text="Select at least one character set")
            return
        
        total = len(charset) ** length
        self.brute_force_warning.config(text=f"Total combinations: {total:,}")
        if total > 1000000:
            self.brute_force_warning.config(foreground="red")
        else:
            self.brute_force_warning.config(foreground="black")
    
    def generate_brute_force(self):
        """Generate brute force wordlist"""
        try:
            length = int(self.length_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid length")
            return
        
        charsets = [key for key, var in self.brute_force_vars.items() if var.get() == 1]
        if not charsets:
            messagebox.showerror("Error", "Select at least one character set")
            return
        
        # Disable generate button during generation
        self.generate_brute_force_button.config(state='disabled')
        self.brute_force_progress['value'] = 0
        
        try:
            def generate_thread():
                try:
                    wordlist = WordlistGenerator.generate_brute_force(
                        charsets, 
                        length,
                        progress_callback=lambda p: self.window.after(0, lambda: self.brute_force_progress.config(value=p))
                    )
                    self.window.after(0, lambda: self.display_brute_force_results(wordlist))
                except Exception as e:
                    self.window.after(0, lambda: messagebox.showerror("Error", str(e)))
                finally:
                    self.window.after(0, lambda: self.generate_brute_force_button.config(state='normal'))
            
            threading.Thread(target=generate_thread, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.generate_brute_force_button.config(state='normal')
    
    def display_brute_force_results(self, wordlist):
        """Display brute force results"""
        self.text_area_brute_force.delete(1.0, tk.END)
        if wordlist:
            self.text_area_brute_force.insert(tk.END, '\n'.join(wordlist))
            self.update_status(f"Generated {len(wordlist)} brute-force words")
        else:
            self.update_status("No words generated")
    
    def save_brute_force_to_file(self):
        """Save brute force wordlist directly to file"""
        try:
            length = int(self.length_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid length")
            return
        
        charsets = [key for key, var in self.brute_force_vars.items() if var.get() == 1]
        if not charsets:
            messagebox.showerror("Error", "Select at least one character set")
            return
        
        charset = ''.join(WordlistGenerator.CHARACTER_SETS[cs] for cs in charsets)
        total = len(charset) ** length
        
        if total > 100000000:  # 100 million
            if not messagebox.askyesno("Confirm", f"Generating {total:,} words may take significant time. Continue?"):
                return
        
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if not filename:
            return
        
        # Disable button during save
        self.save_brute_force_button.config(state='disabled')
        self.brute_force_progress['value'] = 0
        
        def save_thread():
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    # Generate and write in chunks
                    for i, combo in enumerate(itertools.product(charset, repeat=length)):
                        f.write(''.join(combo) + '\n')
                        if i % 10000 == 0:
                            progress = (i / total) * 100
                            self.window.after(0, lambda: self.brute_force_progress.config(value=progress))
                self.window.after(0, lambda: self.update_status(f"Saved {total} words to {os.path.basename(filename)}"))
            except Exception as e:
                self.window.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.window.after(0, lambda: self.save_brute_force_button.config(state='normal'))
        
        threading.Thread(target=save_thread, daemon=True).start()
    
    def apply_rules(self):
        """Apply transformation rules to words"""
        input_text = self.rules_entry.get()
        words = [word.strip() for word in input_text.split(',') if word.strip()]
        if not words:
            messagebox.showinfo("Info", "Enter some words first")
            return
        
        rules = {rule: var.get() for rule, var in self.rules_vars.items()}
        
        result_words = []
        for word in words:
            result_words.extend(WordlistGenerator.apply_rules_to_word(word, rules))
        
        self.text_area_rules.delete(1.0, tk.END)
        self.text_area_rules.insert(tk.END, '\n'.join(result_words))
        self.update_status(f"Generated {len(result_words)} variations from {len(words)} words")
    
    def remove_duplicates(self):
        """Remove duplicate words"""
        text = self.text_area_load_save.get(1.0, tk.END)
        words = text.splitlines()
        
        # Remove empty lines and duplicates while preserving order
        seen = set()
        unique_words = []
        for word in words:
            if word.strip() and word not in seen:
                seen.add(word)
                unique_words.append(word)
        
        self.text_area_load_save.delete(1.0, tk.END)
        self.text_area_load_save.insert(tk.END, '\n'.join(unique_words))
        self.update_word_count()
        self.update_status(f"Removed duplicates. Now {len(unique_words)} unique words.")
    
    def sort_wordlist(self):
        """Sort wordlist alphabetically"""
        text = self.text_area_load_save.get(1.0, tk.END)
        words = [word.strip() for word in text.splitlines() if word.strip()]
        words.sort()
        
        self.text_area_load_save.delete(1.0, tk.END)
        self.text_area_load_save.insert(tk.END, '\n'.join(words))
        self.update_status("Wordlist sorted alphabetically")
    
    def show_statistics(self):
        """Show wordlist statistics"""
        text = self.text_area_load_save.get(1.0, tk.END)
        words = [word.strip() for word in text.splitlines() if word.strip()]
        
        if not words:
            messagebox.showinfo("Statistics", "No words in wordlist")
            return
        
        total_words = len(words)
        unique_words = len(set(words))
        avg_length = sum(len(word) for word in words) / total_words
        
        char_distribution = {}
        for word in words:
            for char in word:
                char_distribution[char] = char_distribution.get(char, 0) + 1
        
        # Get top 10 most common characters
        sorted_chars = sorted(char_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
        char_report = "\n".join([f"{char}: {count}" for char, count in sorted_chars])
        
        stats = (
            f"Total words: {total_words}\n"
            f"Unique words: {unique_words}\n"
            f"Average word length: {avg_length:.2f}\n"
            f"Top 10 characters:\n{char_report}"
        )
        messagebox.showinfo("Wordlist Statistics", stats)
    
    def save_large_wordlist(self, wordlist):
        """Save large wordlist to file"""
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if filename:
            try:
                WordlistFileManager.save_wordlist(filename, wordlist)
                self.update_status(f"Saved {len(wordlist)} words to {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {str(e)}")
    
    def run(self):
        """Start the application"""
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
