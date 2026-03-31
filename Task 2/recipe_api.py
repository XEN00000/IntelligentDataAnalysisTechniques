import requests
import os
from dotenv import load_dotenv

load_dotenv()

SPOONACULAR_API_KEY = os.getenv('SPOONACULAR_API_KEY')
SPOONACULAR_URL = os.getenv('SPOONACULAR_URL')


def get_recipes_by_ingredients(ingredients_list, limit=5):
    """
    Wysyła zapytanie do Spoonacular API, szukając przepisów zawierających podane składniki.

    :param ingredients_list: Lista składników po angielsku, np. ['apple', 'flour', 'sugar']
    :param limit: Maksymalna liczba przepisów do zwrócenia
    :return: Lista słowników z przepisami dopasowanymi do logiki aplikacji
    """

    if not ingredients_list:
        return []

    params = {
        "apiKey": SPOONACULAR_API_KEY,
        "ingredients": ",".join(ingredients_list),
        "number": limit,
        "ranking": 1,
        "ignorePantry": True
    }

    try:
        response = requests.get(SPOONACULAR_URL, params=params)
        response.raise_for_status()

        data = response.json()

        formatted_recipes = []
        for item in data:
            all_ingredients = [ing["name"]
                               for ing in item.get("usedIngredients", [])]
            all_ingredients += [ing["name"]
                                for ing in item.get("missedIngredients", [])]

            recipe_obj = {
                "name": item.get("title", "Nieznany przepis"),
                "ingredients": all_ingredients,
                # tudo: wysweitlac zdj w gui
                "image_url": item.get("image", "")
            }
            formatted_recipes.append(recipe_obj)

        return formatted_recipes

    except requests.exceptions.RequestException as e:
        print(f"Błąd połączenia z API: {e}")
        return []


if __name__ == "__main__":
    test_ingredients = ["chicken", "rice", "garlic"]
    print(f"Szukam przepisów dla: {test_ingredients}\n")

    results = get_recipes_by_ingredients(test_ingredients, limit=2)

    for r in results:
        print(f"Przepis: {r['name']}")
        print(f"Składniki: {', '.join(r['ingredients'])}\n")
