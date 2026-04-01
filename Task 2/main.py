from recipe_api import get_recipes_by_ingredients
import customtkinter as ctk
import speech_recognition as sr
import threading
import re
import os
import tempfile
from tkinter import filedialog, messagebox
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator
from dotenv import load_dotenv

from PIL import Image
from io import BytesIO
import requests

# Importy dla Gemini
import google.generativeai as genai

# Wczytanie kluczy z pliku .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Konfiguracja Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


class RecipeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Smart Recipe - AI Audio Filter (Whisper & Gemini)")
        self.geometry("1100x750")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.recognizer = sr.Recognizer()

        self.build_ui()

    def build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- PANEL BOCZNY ---
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(self.sidebar, text="KONTROLKI AUDIO", font=ctk.CTkFont(
            size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))

        # --- NOWOŚĆ: WYBÓR SILNIKA AI ---
        ctk.CTkLabel(self.sidebar, text="Silnik analizy:").grid(
            row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.engine_var = ctk.StringVar(value="Gemini API (Chmura)")
        self.engine_dropdown = ctk.CTkComboBox(self.sidebar, values=[
                                               "Gemini API (Chmura)", "Whisper (Lokalnie)"], variable=self.engine_var)
        self.engine_dropdown.grid(row=2, column=0, padx=20, pady=(0, 20))

        self.record_btn = ctk.CTkButton(
            self.sidebar, text="🎤 Nagraj z mikrofonu", command=self.start_recording)
        self.record_btn.grid(row=3, column=0, padx=20, pady=10)

        self.file_btn = ctk.CTkButton(
            self.sidebar, text="📁 Wczytaj plik audio", command=self.load_audio_file)
        self.file_btn.grid(row=4, column=0, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(
            self.sidebar, text="Status: Oczekuję...", text_color="gray")
        self.status_label.grid(row=5, column=0, padx=20, pady=20, sticky="s")

        # --- PANEL GŁÓWNY ---
        self.main_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.main_panel.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_panel.grid_columnconfigure(0, weight=1)

        self.text_frame = ctk.CTkFrame(self.main_panel)
        self.text_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))

        ctk.CTkLabel(self.text_frame, text="Logi analizy (Tekst/Prompt):",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 0))
        self.transcript_box = ctk.CTkTextbox(self.text_frame, height=80)
        self.transcript_box.pack(fill="x", padx=10, pady=10)

        self.ing_frame = ctk.CTkFrame(self.main_panel)
        self.ing_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        ctk.CTkLabel(self.ing_frame, text="Zrozumiane składniki (EN):", font=ctk.CTkFont(
            weight="bold")).pack(anchor="w", padx=10, pady=(10, 0))
        self.ingredients_label = ctk.CTkLabel(self.ing_frame, text="Brak", font=ctk.CTkFont(
            size=16), text_color="#34d399", wraplength=700)
        self.ingredients_label.pack(anchor="w", padx=10, pady=10)

        ctk.CTkLabel(self.main_panel, text="Dopasowane przepisy ze Spoonacular:", font=ctk.CTkFont(
            size=16, weight="bold")).grid(row=2, column=0, sticky="w", pady=(0, 10))
        self.recipes_scroll = ctk.CTkScrollableFrame(self.main_panel)
        self.recipes_scroll.grid(row=3, column=0, sticky="nsew")
        self.main_panel.grid_rowconfigure(3, weight=1)

    def update_status(self, message, color="white"):
        self.status_label.configure(
            text=f"Status: {message}", text_color=color)

    def start_recording(self):
        self.record_btn.configure(state="disabled")
        self.file_btn.configure(state="disabled")
        self.update_status("Nasłuchuję... Mów teraz!", "yellow")
        threading.Thread(target=self._record_thread, daemon=True).start()

    def _record_thread(self):
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(
                    source, timeout=10, phrase_time_limit=30)
            self.process_audio(audio)
        except sr.WaitTimeoutError:
            self.update_status("Nie usłyszałem mowy.", "red")
            self.reset_buttons()
        except Exception as e:
            self.update_status("Błąd mikrofonu.", "red")
            self.reset_buttons()

    def load_audio_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Audio Files", "*.wav *.aiff *.flac")])
        if not file_path:
            return
        self.update_status("Przetwarzam plik...", "yellow")
        threading.Thread(target=self._file_thread, args=(
            file_path,), daemon=True).start()

    def _file_thread(self, file_path):
        try:
            with sr.AudioFile(file_path) as source:
                audio = self.recognizer.record(source)
            self.process_audio(audio)
        except Exception as e:
            self.update_status("Błąd pliku.", "red")
            self.reset_buttons()

    def reset_buttons(self):
        self.record_btn.configure(state="normal")
        self.file_btn.configure(state="normal")

    def process_audio(self, audio):
        engine = self.engine_var.get()
        extracted_ingredients = []

        try:
            if engine == "Gemini API (Chmura)":
                if not GEMINI_API_KEY:
                    raise ValueError(
                        "Brak klucza GEMINI_API_KEY w pliku .env!")

                self.update_status("Zapisywanie audio...", "yellow")

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                    temp_audio.write(audio.get_wav_data())
                    temp_audio.flush()  # bez zrzutu gemini dostaje pusty plik
                    temp_path = temp_audio.name

                file_size = os.path.getsize(temp_path)
                print(
                    f"[DEBUG] Rozmiar zapisanego pliku audio: {file_size} bajtów")

                if file_size < 1000:
                    os.remove(temp_path)
                    raise ValueError(
                        "Nagranie jest puste")

                self.update_status(
                    "Analiza przez Gemini", "yellow")

                # Wymuszamy typ pliku jako audio/wav
                uploaded_file = genai.upload_file(
                    temp_path, mime_type="audio/wav")

                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = """
                Listen to this audio carefully. The user can speak different languages.
                Identify any food ingredients mentioned. 
                Return ONLY a comma-separated list of these ingredients translated into English (e.g., 'chicken, rice, tomato'). 
                If you cannot hear any clear food ingredients, return exactly the word: NONE.
                Do not add any other words, punctuation, or explanations.
                """

                response = model.generate_content([prompt, uploaded_file])

                try:
                    genai.delete_file(uploaded_file.name)
                    os.remove(temp_path)
                except Exception as e:
                    print(
                        f"[DEBUG] Błąd podczas usuwania plików tymczasowych: {e}")

                raw_response = "NONE"
                if response.candidates and response.candidates[0].content.parts:
                    raw_response = response.candidates[0].content.parts[0].text.strip(
                    )

                self.transcript_box.delete("1.0", "end")
                self.transcript_box.insert(
                    "1.0", f"[Wykorzystano Gemini API]\nZwrócono: {raw_response}")

                if raw_response == "NONE" or not raw_response:
                    extracted_ingredients = []
                else:
                    extracted_ingredients = [x.strip().lower()
                                             for x in raw_response.split(",")]

            else:

                self.update_status(
                    "Analiza lokalna (Whisper medium)", "yellow")
                raw_text = self.recognizer.recognize_whisper(
                    audio, model="medium")

                self.update_status("Tłumaczenie i NLP", "yellow")
                try:
                    detected_lang = detect(raw_text)
                except LangDetectException:
                    detected_lang = "nieznany"

                working_text = raw_text
                if detected_lang != "en":
                    translator = GoogleTranslator(source='auto', target='en')
                    working_text = translator.translate(raw_text)
                    display_text = f"[Wykryto: {detected_lang}] {raw_text}\n\n[Tłumaczenie]: {working_text}"
                else:
                    display_text = f"[Wykryto: EN] {raw_text}"

                self.transcript_box.delete("1.0", "end")
                self.transcript_box.insert("1.0", display_text)

                extracted_ingredients = self._extract_ingredients_local(
                    working_text)

            if not extracted_ingredients:
                self.ingredients_label.configure(
                    text="Nie rozpoznano żadnych składników.", text_color="red")
                self._display_recipes([])
                self.update_status("Gotowy", "green")
                self.reset_buttons()
                return

            self.ingredients_label.configure(text=", ".join(
                extracted_ingredients).upper(), text_color="#34d399")

            self.update_status(
                "Szukam przepisów w Spoonacular API", "yellow")

            matched_recipes = get_recipes_by_ingredients(
                extracted_ingredients, limit=6)

            self._display_recipes(matched_recipes)
            self.update_status("Sukces", "green")

        except Exception as e:
            print(e)
            self.update_status(f"Błąd: {str(e)}", "red")
        finally:
            self.reset_buttons()

    def _extract_ingredients_local(self, text):
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        stop_words = {
            "i", "have", "got", "some", "want", "to", "make", "cook", "with",
            "and", "or", "a", "an", "the", "my", "is", "are", "we", "can",
            "you", "find", "recipes", "recipe", "food", "need", "there",
            "in", "fridge", "of", "for", "me", "show", "what", "how", "about",
            "yes", "no", "please", "little", "bit", "much", "many", "few"
        }

        found = set()
        for word in words:
            if word not in stop_words and len(word) > 2:
                found.add(word)

        return list(found)

    def _display_recipes(self, recipes):
        # Czyszczenie poprzednich wyników
        for widget in self.recipes_scroll.winfo_children():
            widget.destroy()

        if not recipes:
            ctk.CTkLabel(self.recipes_scroll, text="Brak wyników.",
                         text_color="gray").pack(pady=20)
            return

        for recipe in recipes:
            # Główna karta przepisu
            card = ctk.CTkFrame(self.recipes_scroll,
                                fg_color="#1f2937", corner_radius=10)
            card.pack(fill="x", padx=10, pady=5)

            # Wewnętrzna ramka do układu poziomego (zdjęcie lewo, tekst prawo)
            content_frame = ctk.CTkFrame(card, fg_color="transparent")
            content_frame.pack(fill="x", padx=15, pady=15)

            # --- POBIERANIE I WYŚWIETLANIE ZDJĘCIA ---
            image_url = recipe.get("image_url", "")
            if image_url:
                try:
                    response = requests.get(image_url, timeout=5)
                    img_data = Image.open(BytesIO(response.content))

                    ctk_img = ctk.CTkImage(
                        light_image=img_data, dark_image=img_data, size=(120, 90))

                    img_label = ctk.CTkLabel(
                        content_frame, image=ctk_img, text="")
                    img_label.image = ctk_img
                    img_label.pack(side="left", padx=(0, 15))
                except Exception as e:
                    print(f"[DEBUG] Nie udało się załadować zdjęcia: {e}")

            # --- RAMKA NA TEKST ---
            text_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            text_frame.pack(side="left", fill="both", expand=True)

            title = ctk.CTkLabel(text_frame, text=f"🍲 {recipe['name']}", font=ctk.CTkFont(
                size=18, weight="bold"))
            title.pack(anchor="w", pady=(0, 5))

            ings = ", ".join(recipe["ingredients"])
            ing_label = ctk.CTkLabel(
                text_frame, text=f"Składniki: {ings}", text_color="#9ca3af", wraplength=450, justify="left")
            ing_label.pack(anchor="w")


if __name__ == "__main__":
    app = RecipeApp()
    app.mainloop()
