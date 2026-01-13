import os

def load_prompt(filename: str) -> str:
    """Load prompt from text file in the same directory"""
    prompt_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(prompt_dir, filename)
    if not os.path.exists(file_path):
        # Fallback for common filenames without extension
        if not filename.endswith('.txt'):
            file_path += '.txt'
            
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return ""
