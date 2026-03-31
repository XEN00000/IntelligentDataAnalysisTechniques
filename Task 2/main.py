import customtkinter as ctk
import speech_recognition as sr
import threading
import re
from tkinter import filedialog, messagebox
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

from recipe_api import get_recipes_by_ingredients


class RecipeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Smart Recipe STT - Zaawansowana Filtracja Przepisów")
        self.geometry("1100x750")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.recognizer = sr.Recognizer()

        self.build_ui()

    def build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(self.sidebar, text="KONTROLKI AUDIO", font=ctk.CTkFont(
            size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))

        ctk.CTkLabel(self.sidebar, text="Język mówiony (STT):").grid(
            row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.lang_var = ctk.StringVar(value="pl-PL")
        self.lang_dropdown = ctk.CTkComboBox(self.sidebar, values=[
                                             "pl-PL", "en-US", "es-ES", "de-DE"], variable=self.lang_var)
        self.lang_dropdown.grid(row=2, column=0, padx=20, pady=(0, 20))

        self.record_btn = ctk.CTkButton(
            self.sidebar, text="🎤 Nagraj z mikrofonu", command=self.start_recording)
        self.record_btn.grid(row=3, column=0, padx=20, pady=10)

        self.file_btn = ctk.CTkButton(
            self.sidebar, text="📁 Wczytaj plik audio", command=self.load_audio_file)
        self.file_btn.grid(row=4, column=0, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(
            self.sidebar, text="Status: Oczekuję...", text_color="gray")
        self.status_label.grid(row=5, column=0, padx=20, pady=20, sticky="s")

        self.main_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.main_panel.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_panel.grid_columnconfigure(0, weight=1)

        self.text_frame = ctk.CTkFrame(self.main_panel)
        self.text_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))

        ctk.CTkLabel(self.text_frame, text="Zrozumiany tekst:", font=ctk.CTkFont(
            weight="bold")).pack(anchor="w", padx=10, pady=(10, 0))
        self.transcript_box = ctk.CTkTextbox(self.text_frame, height=80)
        self.transcript_box.pack(fill="x", padx=10, pady=10)

        self.meta_frame = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        self.meta_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))

        self.detected_lang_label = ctk.CTkLabel(
            self.meta_frame, text="Wykryty język: ---", font=ctk.CTkFont(weight="bold"), text_color="#5fa5f9")
        self.detected_lang_label.pack(side="left", padx=10)

        self.ing_frame = ctk.CTkFrame(self.main_panel)
        self.ing_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        ctk.CTkLabel(self.ing_frame, text="Wykryte unikalne składniki:", font=ctk.CTkFont(
            weight="bold")).pack(anchor="w", padx=10, pady=(10, 0))
        self.ingredients_label = ctk.CTkLabel(self.ing_frame, text="Brak", font=ctk.CTkFont(
            size=16), text_color="#34d399", wraplength=700)
        self.ingredients_label.pack(anchor="w", padx=10, pady=10)

        ctk.CTkLabel(self.main_panel, text="Dopasowane przepisy (wymagają WSZYSTKICH składników):",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(row=3, column=0, sticky="w", pady=(0, 10))
        self.recipes_scroll = ctk.CTkScrollableFrame(self.main_panel)
        self.recipes_scroll.grid(row=4, column=0, sticky="nsew")
        self.main_panel.grid_rowconfigure(4, weight=1)

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
                    source, timeout=5, phrase_time_limit=15)
            self.process_audio(audio)
        except sr.WaitTimeoutError:
            self.update_status("Nie usłyszałem mowy.", "red")
        except Exception as e:
            self.update_status("Błąd mikrofonu.", "red")
        finally:
            self.record_btn.configure(state="normal")
            self.file_btn.configure(state="normal")

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
            self.record_btn.configure(state="normal")

    def process_audio(self, audio):
        self.update_status("Łączenie z chmurą STT...", "yellow")
        try:
            selected_lang = self.lang_var.get()
            raw_text = self.recognizer.recognize_google(
                audio, language=selected_lang)

            self.update_status("Analiza NLP...", "yellow")

            try:
                detected_lang = detect(raw_text)
            except LangDetectException:
                detected_lang = "nieznany"

            lang_name = {"pl": "Polski", "en": "Angielski", "es": "Hiszpański",
                         "de": "Niemiecki"}.get(detected_lang, detected_lang.upper())
            self.detected_lang_label.configure(
                text=f"Wykryty język: {lang_name} ({detected_lang})")

            working_text = raw_text
            if detected_lang != "en":
                translator = GoogleTranslator(source='auto', target='en')
                working_text = translator.translate(raw_text)
                display_text = f"{raw_text}\n\n[Przetłumaczono na EN]: {working_text}"
            else:
                display_text = raw_text

            self.transcript_box.delete("1.0", "end")
            self.transcript_box.insert("1.0", display_text)

            extracted_ingredients = self._extract_ingredients(working_text)

            if not extracted_ingredients:
                self.ingredients_label.configure(
                    text="Nie usłyszałem żadnych znanych składników.", text_color="red")
                self._display_recipes([])
                self.update_status("Gotowy", "green")
                return

            self.ingredients_label.configure(text=", ".join(
                extracted_ingredients).upper(), text_color="#34d399")

            self.update_status("Szukam przepisów online...", "yellow")
            matched_recipes = get_recipes_by_ingredients(
                extracted_ingredients, limit=10)

            self._display_recipes(matched_recipes)
            self.update_status("Zakończono sukcesem!", "green")

        except sr.UnknownValueError:
            self.update_status(
                "Nie rozpoznano mowy. Spróbuj mówić wyraźniej.", "red")
        except sr.RequestError:
            self.update_status(
                "Błąd sieci. Sprawdź połączenie z internetem.", "red")
        except Exception as e:
            self.update_status(f"Błąd krytyczny: {str(e)}", "red")

        finally:
            self.record_btn.configure(state="normal")
            self.file_btn.configure(state="normal")

    def _extract_ingredients(self, text):
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
        for widget in self.recipes_scroll.winfo_children():
            widget.destroy()

        if not recipes:
            ctk.CTkLabel(self.recipes_scroll, text="Brak przepisów zawierających wszystkie podane składniki.",
                         text_color="gray").pack(pady=20)
            return

        for recipe in recipes:
            card = ctk.CTkFrame(self.recipes_scroll,
                                fg_color="#1f2937", corner_radius=10)
            card.pack(fill="x", padx=10, pady=5)

            title = ctk.CTkLabel(
                card, text=f"🍲 {recipe['name']}", font=ctk.CTkFont(size=16, weight="bold"))
            title.pack(anchor="w", padx=15, pady=(10, 0))

            ings = ", ".join(recipe["ingredients"])
            ing_label = ctk.CTkLabel(
                card, text=f"Składniki: {ings}", text_color="#9ca3af", wraplength=600, justify="left")
            ing_label.pack(anchor="w", padx=15, pady=(5, 10))


if __name__ == "__main__":
    app = RecipeApp()
    app.mainloop()
