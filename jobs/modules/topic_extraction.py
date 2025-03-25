
import re
from keybert import KeyBERT
from rake_nltk import Rake
import nltk
from nltk.corpus import stopwords
import spacy

from ..utils import strip_emojis, strip_special_chars, strip_links

nlp = spacy.load("en_core_web_sm")
stop_words = set(stopwords.words('english'))
nltk.download('stopwords')
nltk.download('punkt_tab')

MAX_NGRAM = 2
RAKE_THRESHOLD = 2.5
KEY_BERT_THRESHOLD = 2.0
rake = Rake()
kw_model = KeyBERT(
    # model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

def title_case(text: str) -> str:
    """Custom title casing logic"""
    # Words to keep lowercase
    lowercase_words = {'a', 'an', 'the', 'and', 'or', 'but', 'for', 'of', 'at', 'by', 'in', 'on', 'to'}
    
    # Split into words and apply casing rules
    words = text.split()
    for i, word in enumerate(words):
        if i == 0 or word.lower() not in lowercase_words:
            words[i] = word.capitalize()
        else:
            words[i] = word.lower()
    return ' '.join(words)

def correct_casing(phrase: str) -> str:
    """Convert lowercase phrases to properly cased versions"""

    # Step 1: Basic title casing with smart apostrophe handling
    phrase = title_case(phrase.lower())
    
    # Step 2: Process with spaCy for entity-aware casing
    doc = nlp(phrase)
    
    processed = []
    for token in doc:
        # Preserve entity casing
        if token.ent_type_:
            processed.append(token.text_with_ws)
        # Handle special cases
        elif token.text.lower() in {'ai', 'ml'}:
            processed.append(token.text.upper())
        # Fix apostrophe cases (e.g., "Patrick'S" -> "Patrick's")
        elif "'" in token.text:
            processed.append(re.sub(r"([a-zA-Z])'([A-Z])", 
                                lambda m: f"{m.group(1)}'{m.group(2).lower()}", 
                                token.text))
        else:
            processed.append(token.text_with_ws)
    
    # Combine tokens and final cleanup
    result = "".join(processed).strip()
    return re.sub(r'\s{2,}', ' ', result) # Fix multiple spaces

def is_valid_topic(phrase):
    if len(phrase) < 2:
        return False
    doc = nlp(phrase)
    has_noun = any(tok.pos_ in ['NOUN', 'PROPN'] for tok in doc)
    adj_adv_ratio = sum(1 for tok in doc if tok.pos_ in ['ADJ', 'ADV'])/len(doc)
    return has_noun and (adj_adv_ratio < 0.5)

def get_topics(text: str, language: str):
    text = strip_emojis(text)
    text = strip_links(text)
    text = strip_special_chars(text)
    

    rake.extract_keywords_from_text(text)

    topics = []
    for score, candidate in rake.get_ranked_phrases_with_scores():
        if score < RAKE_THRESHOLD:
            continue
        if len(candidate.split()) > MAX_NGRAM:
            continue
        if not is_valid_topic(candidate):
            continue
        topics.append(candidate)
        
    for candidate, score in kw_model.extract_keywords(
        text, 
        keyphrase_ngram_range=(1, 2), 
        stop_words='english', 
        top_n=10, 
        use_mmr=True, 
        diversity=0.6):
        if score < RAKE_THRESHOLD:
            continue
        if not is_valid_topic(candidate):
            continue
        topics.append(candidate)

    return {topic: correct_casing(topic) for topic in set(topics)}
        

if __name__ == "__main__":
    text = "For Saint Patrick's day, and #mosstodon Monday, some greenery on the rocks from Beacon Rock, and more greenery on Wind Mountain. I recently read Gathering Moss by Robin Wall Kimmerer, author of Braiding Sweetgrass, which was really interesting. I had no idea that moss reproduced with sperm, one of the first organisms on earth to do so! Also had no idea how dependent on very specific local conditions each moss is."

    print(get_topics(text, 'en'))