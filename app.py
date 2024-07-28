from flask import Flask, request, render_template, jsonify
from PIL import Image
import pytesseract
import requests
import os
import time
import shelve
import re

# Set the Tesseract executable path if it's not in PATH
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = Flask(__name__)

# Initialize the cache (using shelve for simplicity)
CACHE_FILE = "card_cache.db"

def get_cached_card_value(card_text):
    with shelve.open(CACHE_FILE) as cache:
        if card_text in cache:
            return cache[card_text]
        return None

def cache_card_value(card_text, value):
    with shelve.open(CACHE_FILE) as cache:
        cache[card_text] = value

def clean_text(text):
    # Remove newlines and extra spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove unwanted characters
    text = re.sub(r'[^a-zA-Z0-9,\'".:;()\-\s]', '', text)
    
    # Attempt to extract Oracle text portion (simplified logic)
    # Assume the Oracle text starts after the first period and ends before the last period
    oracle_text_match = re.search(r'\.\s+(.*?)\.\s', text)
    if oracle_text_match:
        text = oracle_text_match.group(1)
    
    # Additional cleaning steps can be added here
    return text.strip()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    if file:
        image = Image.open(file)
        text = pytesseract.image_to_string(image)
        cleaned_text = clean_text(text)
        card_text = f'"{cleaned_text}"'  # Quote the text for Scryfall query
        cached_value = get_cached_card_value(card_text)
        if cached_value:
            return jsonify({'extracted_text': cleaned_text, 'card_value': cached_value})
        else:
            card_value = search_card_value(card_text)
            if card_value:
                cache_card_value(card_text, card_value)
            return jsonify({'extracted_text': cleaned_text, 'card_value': card_value})

def search_card_value(card_text):
    print(f"Searching for card value: {card_text}")
    api_url = "https://api.scryfall.com/cards/search"
    params = {'q': f'o:{card_text}', 'unique': 'prints', 'order': 'usd'}
    response = requests.get(api_url, params=params)
    time.sleep(0.1)  # Delay to respect Scryfall API rate limits
    if response.status_code == 200:
        data = response.json()
        if data['data']:
            # Get the first matching card's price
            card = data['data'][0]
            if 'prices' in card:
                usd_price = card['prices'].get('usd', 'N/A')
                usd_foil_price = card['prices'].get('usd_foil', 'N/A')
                return {
                    'name': card['name'],
                    'usd': usd_price,
                    'usd_foil': usd_foil_price
                }
            return 'Price not available'
        return 'Card not found'
    elif response.status_code == 404:
        return 'Card not found'
    else:
        return 'Error fetching card data'

if __name__ == '__main__':
    print("Running the Flask app...")
    app.run(debug=True)
