# Nerd Market

Nerd Market is a web application for checking the value of Magic: The Gathering cards using image recognition. Upload a card image, and the app extracts the text and fetches the card's value from the Scryfall API.

## Installation

### Prerequisites

- Python 3.11 or later
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed and configured (required for local development)
- [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) installed (required for deployment to Heroku)

### Clone the Repository

```git clone https://github.com/yourusername/nerd-market.git```

```cd nerd-market```


### Create and Activate a Virtual Environment

```python -m venv venv```

```venv\Scripts\activate ```  # On Windows
```source venv/bin/activate```  # On MacOS/Linux

### Install Dependencies

```pip install -r requirements.txt```

### Set Up Environment Variables
Create a .env file in the project root and add any necessary environment variables.

For local development, you can set the Tesseract executable path in app.py:

``if not HEROKU:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'``

## Usage
### Run the Application Locally

``python app.py``

Open your browser and go to http://127.0.0.1:5000/ to see the application.

### Login
Use the hardcoded password 'goggs' to log in.

Upload a Card Image
Click "Choose File" and select an image of a Magic: The Gathering card.
Click "Upload" to process the image and fetch the card value.

## Deployment

1. Log in to Heroku

``heroku login``

2. Add the Heroku remote (if not already added)

``git remote add heroku https://git.heroku.com/nerd-market.git``

3. Set the TESSDATA_PREFIX environment variable (if not already set)

``heroku config:set TESSDATA_PREFIX=/app/.apt/usr/share/tesseract-ocr/4.00/tessdata --app nerd-market``

4. Push changes to Heroku

``git push heroku main``

5. Open the application

``heroku open``

Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. Please make sure to update tests as appropriate.


### MIT License

Copyright (c) [2024] [Jasmine Joseph]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Project Status
The project is actively maintained and under development. Contributions are welcome.