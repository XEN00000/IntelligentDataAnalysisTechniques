# Baza przepisów w języku angielskim
RECIPES = [
    {"name": "Spaghetti Bolognese", "ingredients": [
        "pasta", "minced meat", "tomato", "onion", "garlic", "olive oil"]},
    {"name": "Scrambled Eggs", "ingredients": [
        "egg", "butter", "salt", "pepper"]},
    {"name": "Caprese Salad", "ingredients": [
        "tomato", "mozzarella", "basil", "olive oil"]},
    {"name": "Tomato Soup", "ingredients": [
        "tomato", "broth", "cream", "pasta", "carrot"]},
    {"name": "Pancakes", "ingredients": [
        "flour", "egg", "milk", "sugar", "butter", "baking powder"]},
    {"name": "Margherita Pizza", "ingredients": [
        "flour", "yeast", "water", "salt", "tomato", "mozzarella", "basil"]},
    {"name": "Chicken Curry", "ingredients": [
        "chicken", "coconut milk", "curry powder", "onion", "garlic", "rice"]},
    {"name": "Guacamole", "ingredients": [
        "avocado", "lime", "garlic", "onion", "cilantro", "salt"]},
    {"name": "Mushroom Risotto", "ingredients": [
        "rice", "mushroom", "broth", "onion", "wine", "parmesan", "butter"]},
    {"name": "Beef Stew", "ingredients": [
        "beef", "potato", "carrot", "onion", "beef broth", "garlic"]},
    {"name": "Caesar Salad", "ingredients": [
        "romaine lettuce", "croutons", "parmesan", "chicken", "caesar dressing"]},
    {"name": "Mac and Cheese", "ingredients": [
        "macaroni", "cheddar cheese", "milk", "butter", "flour"]},
    {"name": "Greek Salad", "ingredients": [
        "cucumber", "tomato", "red onion", "feta cheese", "olives", "olive oil"]},
    {"name": "Veggie Stir Fry", "ingredients": [
        "broccoli", "bell pepper", "carrot", "soy sauce", "ginger", "garlic"]},
    {"name": "French Toast", "ingredients": [
        "bread", "egg", "milk", "cinnamon", "butter", "maple syrup"]}
]

KNOWN_INGREDIENTS = set(
    ing for recipe in RECIPES for ing in recipe["ingredients"])

SYNONYMS = {
    "tomatoes": "tomato",
    "eggs": "egg",
    "potatoes": "potato",
    "carrots": "carrot",
    "onions": "onion",
    "mushrooms": "mushroom",
    "apples": "apple",
    "peppers": "bell pepper",
    "macaroni": "pasta",
    "chicken breast": "chicken"
}
