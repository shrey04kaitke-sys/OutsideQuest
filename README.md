# OutsideQuest — Your AI Adventure Buddy

OutsideQuest turns the time, energy, interests, budget, and activity preference you have today into one safe, achievable real-world mission. It uses a local Ollama model—no paid API, cloud AI provider, account, or API key is required.

## Features

- A responsive Streamlit interface with a calm, welcoming design.
- Choose the time available, energy level, interests, budget, and indoor/outdoor preference.
- Personalized missions with a reason, practical steps, estimated time and cost, and a safety tip.
- Local generation with Ollama and `qwen2.5:3b`; clearly labeled, built-in fallback missions when generation is unavailable or fails validation.
- Regenerate missions and mark an adventure complete.
- A progress tracker and reflection journal.
- Local-only JSON persistence in `data/user_data.json`.
- Input and generated-output checks for time/budget limits, unsafe suggestions, and unverified place or venue claims.
- No location lookup: the app does not supply or verify nearby places, routes, conditions, or venue details.
- Loopback-only web server configuration and disabled Streamlit usage statistics.

## Architecture

```text
app.py
  ├── outsidequest/adventure.py  Ollama HTTP client, prompts, fallback missions
  ├── outsidequest/models.py     Preferences, mission validation, safety checks
  └── outsidequest/storage.py    Local JSON progress and journal persistence

tests/test_outsidequest.py       Unit tests for validation, Ollama failures, and storage
```

The app calls Ollama's local `/api/generate` endpoint with structured JSON output. Model output is validated before display; unavailable Ollama, invalid output, or failed safety checks produce a visibly labeled built-in mission instead. Progress is saved locally using an atomic file replacement. There is no account system or cloud backend.

## Prerequisites

- Windows 10/11.
- Python 3.10 or newer (Python 3.13 is supported).
- [Ollama for Windows](https://ollama.com/download).
- A model available in Ollama. The default is `qwen2.5:3b`.

The application works without Ollama using the built-in fallback missions. Model suggestions are generated content, not verified local advice; review a mission and its safety tip before setting out.

## Windows setup

Open PowerShell in the project folder:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use the venv executable directly in the commands below:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Confirm Ollama and the model are available:

```powershell
ollama list
ollama pull qwen2.5:3b
```

`ollama pull` is only needed if the model is not already listed. Ollama Desktop normally starts the local service automatically. Otherwise, start Ollama before launching OutsideQuest. Confirm the local API is responding with:

```powershell
Invoke-RestMethod http://localhost:11434/api/tags
```

You should see `qwen2.5:3b` in the returned model list.

## Run the app

```powershell
streamlit run app.py
```

Then open `http://localhost:8501`. Streamlit is configured to listen on your computer
only (`127.0.0.1`), and its usage-statistics collection is disabled. If the `streamlit`
command is unavailable, use `.\.venv\Scripts\streamlit.exe run app.py`.

Optional local settings can be provided with environment variables:

```powershell
$env:OUTSIDEQUEST_OLLAMA_URL = "http://localhost:11434"
$env:OUTSIDEQUEST_OLLAMA_MODEL = "qwen2.5:3b"
streamlit run app.py
```

No `.env` file or secrets are needed. The app sends generation requests only to the configured local Ollama server.

## Run tests

```powershell
python -m unittest discover -s tests -v
```

The test suite uses Python's standard `unittest` runner; no separate test package is needed.

## Data and privacy

Completed missions and reflections are saved to `data/user_data.json` on this computer. That folder is excluded by `.gitignore`. Back up or delete that file yourself to manage your saved progress. User-entered interests and preferences are sent to your local Ollama endpoint only when asking it to generate a mission.

## Troubleshooting

- **Ollama unavailable:** Confirm the Ollama app/service is running, then check `ollama list`. OutsideQuest remains usable with clearly labeled fallback missions.
- **Model not found:** Run `ollama pull qwen2.5:3b`, or set `OUTSIDEQUEST_OLLAMA_MODEL` to an installed model name.
- **Ollama uses a different address:** Set `OUTSIDEQUEST_OLLAMA_URL` to its local HTTP base URL, such as `http://localhost:11434`.
- **Slow generation:** Small local models may need time to load. The app allows up to 45 seconds for a model response; if it times out, it shows a safe fallback and explains why.
- **PowerShell will not activate `.venv`:** Use `.\.venv\Scripts\python.exe -m pip ...` and `.\.venv\Scripts\streamlit.exe run app.py`.
- **Progress file cannot be read:** The app surfaces the path and error rather than silently replacing saved data. Make a copy of `data/user_data.json` before repairing it.

## Screenshots

Screenshots can be added here after launching the app. The repository does not yet include screenshots.

## Planned improvements

- Add user-controlled export and import for local progress.
- Improve accessibility checks and add more focused keyboard/screen-reader testing.
- Expand the automated safety-screening cases and fallback mission library.
- Add optional localization and user-selectable currency display.

## License

Released under the [MIT License](LICENSE), a conventional permissive open-source license that allows reuse, modification, and redistribution while retaining the copyright and license notice.
