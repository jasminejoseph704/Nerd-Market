from flask import Flask, request, render_template, jsonify, redirect, url_for, session
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import requests
import os
import time
import shelve
import re
from functools import wraps
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for session management

# Hard-coded password
PASSWORD = "goggs"

# Check if running on Heroku
HEROKU = os.getenv('HEROKU')

if not HEROKU:
    # Set the Tesseract executable path if running locally and not in PATH
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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
    return text.strip()

def preprocess_for_small_cards(image):
    # Convert to grayscale
    image = image.convert('L')

    # Resize to make the card larger in the image
    image = image.resize((image.width * 2, image.height * 2), Image.LANCZOS)

    # Apply sharpening
    image = image.filter(ImageFilter.SHARPEN)

    return image

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def clean_ocr_text(text):
    # Basic cleanup: remove non-alphanumeric characters except for punctuation
    text = re.sub(r'[^a-zA-Z0-9,\.\s]', '', text)

    # Replace periods followed by a space with commas (common OCR mistake)
    text = text.replace(". ", ", ")

    # Fix common missing space issues (e.g., "Firstof" -> "First of")
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)  # Add space between lowercase and uppercase letters

    # Specifically target and fix "Firstof" pattern into "First of"
    text = text.replace("Firstof", "First of")

    # Remove any trailing characters that don't belong
    # Assume Magic: The Gathering card titles don't have trailing 2-character artifacts
    text = re.sub(r'\s\w{1,2}$', '', text)

    # Remove any extra spaces
    text = text.strip()

    return text

def extract_card_title(image):
    # Convert to grayscale if not already
    image = image.convert('L')

    # Apply thresholding to convert the image to pure black and white
    image = image.point(lambda p: p > 128 and 255)  # Simple binary thresholding

    # Log the size of the image
    print(f"Image size: {image.size}")

    # Save the thresholded image for inspection
    image.save("thresholded_title_region.jpg")
    print("Thresholded title region saved as 'thresholded_title_region.jpg'")

    # Use Tesseract with different page segmentation mode
    custom_config = r'--oem 3 --psm 6'  # Try PSM 6 for better block text recognition
    text = pytesseract.image_to_string(image, config=custom_config)

    # Log the raw text extracted
    print(f"Raw extracted text: {text}")

    # Clean the OCR text using custom cleanup
    cleaned_text = clean_ocr_text(text)

    # Log the cleaned title
    print(f"Cleaned card title: {cleaned_text}")

    # Return the first cleaned line (assumed to be the title)
    card_title = cleaned_text.splitlines()[0] if cleaned_text else ""
    return card_title


def manual_crop_title_region(image):
    # Convert the OpenCV image to PIL
    pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    # Define the manual crop coordinates based on standard Magic: The Gathering card layout
    width, height = pil_image.size
    title_region_height = int(height * 0.1)  # The title typically takes up about 10% of the card height
    title_region = pil_image.crop((0, 0, width, title_region_height))

    # Resize to make the text larger for OCR
    title_region = title_region.resize((title_region.width * 2, title_region.height * 2), Image.LANCZOS)
    
    # Apply sharpening and contrast enhancement
    title_region = title_region.filter(ImageFilter.SHARPEN)
    enhancer = ImageEnhance.Contrast(title_region)
    title_region = enhancer.enhance(2)

    # Save the title region for inspection
    title_region.save("manual_cropped_title_region.jpg")
    print("Manual cropped title region saved as 'manual_cropped_title_region.jpg'")

    return title_region


@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return "Incorrect password", 403
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

def detect_card_and_crop(image_path):
    # Load the image using OpenCV
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply edge detection to find the card
    edges = cv2.Canny(gray, 50, 150)
    
    # Find contours based on the edges
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Find the largest contour which should correspond to the card
    largest_contour = max(contours, key=cv2.contourArea)

    # Get the bounding box for the largest contour
    x, y, w, h = cv2.boundingRect(largest_contour)

    # Crop the image to the bounding box
    cropped_image = image[y:y+h, x:x+w]
    
    # Convert the cropped image back to PIL for further processing
    cropped_pil_image = Image.fromarray(cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB))

    # Save the full cropped card for inspection
    cropped_pil_image.save("full_cropped_card.jpg")
    print("Full cropped card saved as 'full_cropped_card.jpg'")

    # Manually crop the top portion where the title is located
    cropped_width, cropped_height = cropped_pil_image.size
    title_region = cropped_pil_image.crop((0, 0, cropped_width, int(cropped_height * 0.25)))  # Increase to 25%

    # Resize to make the text larger for OCR
    title_region = title_region.resize((title_region.width * 2, title_region.height * 2), Image.LANCZOS)
    
    # Apply sharpening and contrast enhancement
    title_region = title_region.filter(ImageFilter.SHARPEN)
    enhancer = ImageEnhance.Contrast(title_region)
    title_region = enhancer.enhance(2)

    # Save the updated title region for inspection
    title_region.save("updated_title_region.jpg")
    print("Updated title region saved as 'updated_title_region.jpg'")

    return title_region


@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    if file:
        # Save the file locally for OpenCV processing
        image_path = 'temp_card_image.jpg'
        file.save(image_path)
        
        # Load the image using OpenCV
        image = cv2.imread(image_path)

        # Manually crop the title region based on a fixed percentage of the card's height
        title_region = manual_crop_title_region(image)

        # Extract the card title from the cropped image
        card_title = extract_card_title(title_region)
        
        # Log the extracted title
        print(f"Extracted card title: {card_title}")
        
        if card_title:
            # Fetch all versions of the card using the extracted title
            best_card = find_best_match(file, card_title)
            
            if best_card:
                # Log the matched card information in the console
                print(f"Best matched card: {best_card['name']}")
                print(f"USD price: {best_card['prices']['usd']}")
                print(f"Foil USD price: {best_card['prices']['usd_foil']}")
                print(f"Similarity score: {best_card['similarity_score']}")

                return jsonify({
                    'extracted_text': card_title,
                    'best_match': best_card['name'],
                    'card_value': best_card['prices']
                })
            else:
                print("No matching card found")
                return jsonify({'error': 'No matching card found'})
        else:
            print("No card title found")
            return jsonify({'error': 'No card title found'})


def fetch_card_images(card_name):
    api_url = "https://api.scryfall.com/cards/search"
    params = {'q': f'{card_name}', 'unique': 'prints', 'order': 'usd'}
    response = requests.get(api_url, params=params)
    card_images = []
    if response.status_code == 200:
        data = response.json()
        for card in data['data']:
            if 'image_uris' in card:  # Check if the image_uris field exists
                card_images.append({
                    'image_url': card['image_uris']['normal'],
                    'prices': card['prices'],
                    'name': card['name']
                })
            else:
                print(f"Skipping card {card['name']} due to missing image_uris")
    return card_images

def download_image(image_url):
    response = requests.get(image_url, stream=True)
    img = Image.open(response.raw)
    return np.array(img)

def compare_images(image1, image2):
    # Resize images to the same size
    image1 = cv2.resize(image1, (250, 350))
    image2 = cv2.resize(image2, (250, 350))

    # Convert images to grayscale for better comparison
    gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)

    # Compare using Structural Similarity Index (SSIM)
    score, _ = ssim(gray1, gray2, full=True)
    return score

def find_best_match(uploaded_image, card_name):
    print(f"Fetching card images for: {card_name}")
    
    # Fetch all versions of the card
    card_versions = fetch_card_images(card_name)
    
    if not card_versions:
        print("No card versions found from API")
        return None
    
    best_match = None
    highest_similarity = 0
    
    for version in card_versions:
        card_image = download_image(version['image_url'])
        similarity_score = compare_images(np.array(Image.open(uploaded_image)), card_image)
        
        # Log each comparison score
        print(f"Comparing with card: {version['name']}, similarity score: {similarity_score}")
        
        if similarity_score > highest_similarity:
            highest_similarity = similarity_score
            best_match = version
    
    if best_match:
        print(f"Best match: {best_match['name']} with score: {highest_similarity}")

        # Save the best-matched card's image locally for verification
        best_image_url = best_match['image_url']
        response = requests.get(best_image_url, stream=True)
        best_image = Image.open(response.raw)

        best_image_path = f"best_matched_card_{best_match['name'].replace(' ', '_')}.jpg"
        best_image.save(best_image_path)
        print(f"Best matched card image saved as '{best_image_path}'")

        return {
            'name': best_match['name'],
            'prices': best_match['prices'],
            'similarity_score': highest_similarity,
            'image_path': best_image_path  # Add image path to the result
        }
    
    return None


if __name__ == '__main__':
    print("Running the Flask app...")
    app.run(debug=True)
