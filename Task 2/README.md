# 🍲 Smart Recipe - AI Audio Filter

*Aplikacja do rozpoznawania ingredientów z audio i wyszukiwania przepisów.*

---

## 🚀 Szybki Start (Docker)

### Wymagania
- **Docker Desktop** (Windows/macOS): https://www.docker.com/products/docker-desktop
- **Python 3.10+** + Virtual Environment
- **~5GB wolnego miejsca** (dla modelu Mistral)

### 3-Krokowy Setup

**1. Start Ollama w Dockerze**

Opcja A - Automatycznie (Windows):
```bash
# Double-click: start-docker.bat
# lub z terminala:
.\start-docker.bat
```

Opcja B - Ręcznie:
```bash
docker-compose up -d
```

**2. Czekaj na health check** (~40 sekund)
```bash
docker-compose ps
# Powinno pokazać: "healthy"
```

**3. Uruchom Aplikację**
```bash
# Terminal nowy
.\venv\Scripts\Activate.ps1
python main.py
```

---

## 📚 Dokumentacja

- **[DOCKER_SETUP.md](DOCKER_SETUP.md)** - Pełna dokumentacja Docker
- **[DOCKER_vs_LOCALHOST.md](DOCKER_vs_LOCALHOST.md)** - Porównanie Docker vs. lokalnie
- **[CONFIG_OLLAMA.md](CONFIG_OLLAMA.md)** - Setup Ollama (jeśli bez Dockera)

---

## 🎯 Funkcje

✅ **Rozpoznawanie Mowy**
- Gemini API (chmura) - wymaga klucza API
- Whisper (lokalnie) - bez internetu

✅ **Tłumaczenie**
- Ollama (lokalnie) - bezpłatne, szybkie
- Automatyczne wykrywanie języka

✅ **Wyszukiwanie Przepisów**
- Spoonacular API
- Filtrowanie po składnikach

✅ **Obsługa Błędów**
- Automatyczny fallback Gemini → Whisper
- Dialogi "Ponów" dla błędów sieciowych
- Rekurencyjne retry

---

## 📋 Wymagania

```
customtkinter>=5.2.2        # GUI
SpeechRecognition>=3.10.0   # Speech to Text
PyAudio>=0.2.14            # Audio capture
langdetect>=1.0.9          # Language detection
python-dotenv              # .env support
soundfile                  # Audio file handling
requests                   # HTTP requests
openai-whisper             # Local speech recognition
google-genai               # Gemini API
Pillow                     # Image processing
```

---

## ⚙️ Konfiguracja

Edytuj `.env`:

```env
# API Keys
GEMINI_API_KEY=twoj_klucz_tutaj              # Optional
SPOONACULAR_API_KEY=47d6ddf0c8144d2394d...  # Required

# URLs
SPOONACULAR_URL=https://api.spoonacular.com/recipes/findByIngredients
OLLAMA_URL=http://localhost:11434            # Optional (domyślnie)
```

---

## 🐳 Docker vs. Lokalnie

| Aspekt | Docker | Lokalnie |
|--------|:------:|:--------:|
| Setup | ✅ 1 komenda | ❌ Wielokrokowy |
| Izolacja | ✅ Tak | ❌ Zaśmieca system |
| Przenośność | ✅ Doskonała | ❌ Problematyczna |
| Performance | ⚠️ Nieznacznie wolniejsze | ✅ Natywne |

**Rekomendacja**: Użyj **Docker** dla najlepszego doświadczenia.

---

## 🛠️ Zarządzanie Docker

```bash
# Start
docker-compose up -d

# Status
docker-compose ps
docker-compose logs -f ollama

# Stop
docker-compose stop

# Restart
docker-compose restart

# Cleanup (usuwa voluminy!)
docker-compose down -v
```

---

## 🔍 Troubleshooting

### "Nie mogę się połączyć z Ollama"
```bash
curl http://localhost:11434/api/tags
docker-compose logs ollama
```

### "Port 11434 już używany"
```bash
# Zmień port w docker-compose.yml: ports: "11435:11434"
# Lub: docker-compose down
```

### "Build trwa bardzo długo"
- First time: ~10-15 minut (pobieranie modelu ~5GB)
- Kolejne: ~20 sekund

### "Docker nie znaleziony"
- Zainstaluj: https://www.docker.com/products/docker-desktop
- Uruchom Docker Desktop

---

## 📁 Struktura Projektu

```
.
├── main.py                 # Główna aplikacja GUI
├── recipe_api.py          # Integracja Spoonacular API
├── stop_words.py          # Ekstrakcja ingredientów
├── requirements.txt       # Python dependencies
├── .env                   # Konfiguracja (nie commit!)
├── docker-compose.yml     # Docker setup
├── Dockerfile.ollama      # Build Ollama image
├── start-docker.bat       # Windows batch script
├── start-docker.ps1       # Windows PowerShell script
├── CONFIG_OLLAMA.md       # Ollama dokumentacja
├── DOCKER_SETUP.md        # Docker instrukcje
└── DOCKER_vs_LOCALHOST.md # Porównanie
```

---

## 🚀 Deployment

### Lokalny Server (Development)
```bash
docker-compose up -d
python main.py
```

### Cloud Deployment (Scaling)
1. Push obraz do Docker Hub
2. Deploy docker-compose na serwer
3. Ustaw OLLAMA_URL na production hostname

---

## 📝 Notes

- **Audio Format**: WAV, AIFF, FLAC
- **Language Support**: Wszystkie (auto-detect + tłumaczenie)
- **API Rate Limits**: Spoonacular ~100 req/day (free tier)
- **Model Size**: Mistral ~5GB

---

## 🤝 Contribution

Issues? Chcesz ulepszeń?

```bash
git status
git add .
git commit -m "Feature: [description]"
git push origin develop
```

---

## 📄 Licencja

Projekt edukacyjny - Intelligent Data Analysis Techniques
Semestr 6 - Studium

---

## 📞 Support

- **Docker Issues**: [Docker Docs](https://docs.docker.com)
- **Ollama**: [Ollama GitHub](https://github.com/ollama/ollama)
- **Whisper**: [OpenAI Whisper](https://github.com/openai/whisper)
- **Gemini API**: [Google Generative AI](https://ai.google.dev)
- **Spoonacular**: [Recipe API](https://spoonacular.com/food-api)

---

## ✨ Technologie

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![AI](https://img.shields.io/badge/AI-Ollama%20%2B%20Whisper%20%2B%20Gemini-orange)
![GUI](https://img.shields.io/badge/GUI-CustomTkinter-green)

---

**Ostatnia aktualizacja**: April 2026  
**Status**: ✅ Production Ready
