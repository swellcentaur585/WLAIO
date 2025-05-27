# Wordlist Manager
A GUI application for managing and generating wordlists.

## Features
- Load and save wordlists from files
- Generate bruteforce wordlists based on character sets and lengths
- Apply hashcat-like rules to wordlists (e.g. append numbers, prepend special characters, leet speak)
- Combine multiple wordlists into one
- Estimate time to complete for large wordlist generation

## Requirements
- Python 3.x
- tkinter library (included with Python)

## Installation
1. Clone this repository or download the source code
2. Run the program using `python wordlist_manager.py`

## Usage
1. Launch the program and select a tab to perform an action:
    * Load/Save: Load a wordlist from a file or save the current wordlist to a file
    * Bruteforce Generator: Generate a wordlist based on character sets and lengths
    * Wordlist Manipulation: Apply hashcat-like rules to a wordlist
    * Wordlist Combiner: Combine multiple wordlists into one
2. Follow the prompts and instructions in each tab to complete the desired action

## Notes
- This program is designed for generating and managing wordlists, and should not be used for malicious purposes.
- Large wordlist generation can take a significant amount of time and system resources.
- Very Early work in progress plan on adding a ton more features and make it look somewhat better.
