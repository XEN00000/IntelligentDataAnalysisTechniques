import re

STOP_WORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours",
    "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers",
    "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does",
    "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until",
    "while", "of", "at", "by", "for", "with", "about", "against", "between", "into",
    "through", "during", "before", "after", "above", "below", "to", "from", "up", "down",
    "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "any", "both", "each", "other", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "can", "will",
    "just", "don", "should", "now",

    # miejsca
    "house", "home", "kitchen", "fridge", "refrigerator", "freezer", "pantry", "cupboard",
    "shelf", "drawer", "cabinet", "table", "counter", "basement", "cellar", "room", "place",
    "inside", "outside", "top", "bottom", "back", "front",

    # opakowania
    "box", "bag", "bottle", "jar", "can", "tin", "packet", "package", "bowl", "plate",
    "cup", "glass", "container", "tupperware", "carton", "wrapper",

    # miary
    "lot", "lots", "plenty", "bunch", "little", "bit", "much", "many", "few", "some",
    "half", "quarter", "pound", "kilo", "kilogram", "gram", "liter", "millilitre",
    "ounce", "pinch", "dash", "piece", "pieces", "slice", "slices", "whole", "chunk",
    "handful", "more", "most", "less", "amount",

    # czasowniki
    "got", "keep", "keeps", "kept", "store", "stores", "stored", "put", "puts", "make",
    "makes", "making", "made", "cook", "cooks", "cooking", "cooked", "bake", "bakes",
    "baking", "baked", "fry", "fries", "frying", "fried", "boil", "boils", "boiling",
    "boiled", "eat", "eats", "eating", "ate", "eaten", "like", "likes", "liked", "love",
    "loves", "loved", "want", "wants", "wanted", "need", "needs", "needed", "find",
    "finds", "finding", "found", "look", "looks", "looking", "looked", "see", "sees",
    "seeing", "saw", "seen", "think", "thinks", "thinking", "thought", "know", "knows",
    "knowing", "knew", "known", "tell", "tells", "telling", "told", "say", "says", "saying",
    "said", "let", "lets", "help", "helps", "helping", "helped", "try", "tries", "trying",
    "tried", "use", "uses", "using", "used", "add", "adds", "adding", "added", "mix",
    "mixes", "mixing", "mixed", "chop", "chops", "chopping", "chopped", "cut", "cuts",
    "cutting", "pour", "pours", "pouring", "poured", "prepare", "prepares", "preparing",
    "prepared", "hold", "holds", "holding", "held", "buy", "bought", "bring", "brought",

    # słowa naturalne w komunikacji
    "well", "basically", "actually", "literally", "really", "maybe", "perhaps", "totally",
    "like", "um", "uh", "ah", "oh", "yeah", "yes", "ok", "okay", "please", "thanks",
    "thank", "hello", "hi", "hey", "today", "tomorrow", "yesterday", "right", "absolutely",
    "exactly", "example", "instance", "idea", "mind", "sure", "left", "leftover", "leftovers",

    "food", "meal", "dish", "dinner", "lunch", "breakfast", "supper", "snack", "dessert",
    "drink", "beverage", "stuff", "things", "thing", "something", "anything", "nothing",
    "everything", "ingredient", "ingredients", "grocery", "groceries", "product", "products",
    "item", "items", "fresh", "old", "new", "bad", "good", "rotten", "expired", "cold",
    "hot", "warm", "frozen", "raw", "hard", "soft", "big", "small", "large", "tasty",
    "delicious", "yummy", "sweet", "sour", "bitter", "spicy"
}


def extract_ingredients_local(self, text):
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)

    found = set()
    for word in words:
        if word not in STOP_WORDS and len(word) > 2:
            found.add(word)

    return list(found)
