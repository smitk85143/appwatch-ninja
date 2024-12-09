import yake

def extract_keywords(description: str, top_number: int):
    """
    Extracts keywords using YAKE. This function will run synchronously.
    """
    extractor = yake.KeywordExtractor(lan='en', n=3, dedupLim=0.9, features=None, top=top_number)
    keys = extractor.extract_keywords(description)
    
    # Prepare the list of keywords
    keywords = [{'keyword': k[0], 'number': k[1] * 1000} for k in keys]
    
    return keywords