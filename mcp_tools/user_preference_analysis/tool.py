import json
from bs4 import BeautifulSoup
from textblob import TextBlob
import requests

def user_preference_analysis(user_data: str, context: str) -> str:
    """
    Analyzes user preferences based on provided data to determine capabilities and limitations.
    """
    try:
        # Parse user_data as HTML
        soup = BeautifulSoup(user_data, 'html.parser')
        
        # Extract text from the HTML
        text = soup.get_text()
        
        # Analyze sentiment of the text
        blob = TextBlob(text)
        sentiment = blob.sentiment
        
        # Extract noun phrases
        noun_phrases = blob.noun_phrases
        
        # Prepare the result
        result = {
            "sentiment": {
                "polarity": sentiment.polarity,
                "subjectivity": sentiment.subjectivity
            },
            "noun_phrases": list(noun_phrases)
        }
        
        return json.dumps(result)
    
    except Exception as e:
        return json.dumps({"error": str(e)})