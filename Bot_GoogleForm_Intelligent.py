from __future__ import annotations

import html
import json
import random
import re
import time
import unicodedata
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable

import requests


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20
PROJECT_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = PROJECT_DIR / "runtime"
LOG_DIR = PROJECT_DIR / "logs"
LOG_FILE = LOG_DIR / "activity.jsonl"
LAST_FORM_FILE = RUNTIME_DIR / "last_form.json"
LAST_SIMULATION_FILE = RUNTIME_DIR / "last_simulation.json"

QUESTION_TYPE_LABELS = {
    0: "Reponse courte",
    1: "Paragraphe",
    2: "Choix multiple",
    3: "Liste deroulante",
    4: "Cases a cocher",
    5: "Echelle lineaire",
    7: "Grille a choix unique",
    8: "Grille a cases",
    9: "Date",
    10: "Heure",
    13: "Depot de fichier",
}

SUPPORTED_TYPES = {0, 1, 2, 3, 4, 5, 7, 8, 9, 10}
AUTO_PROFILES = ("prudent", "equilibre", "varie")

AUTO_SHORT_TEXT_SAMPLES = [
    "Test",
    "Validation",
    "Participation",
    "Essai",
    "Reponse automatique",
    "Sans remarque",
]

AUTO_PARAGRAPH_SAMPLES = [
    "Reponse automatique generee pour verifier le formulaire.",
    "Participation de test avec un texte coherent et simple.",
    "Verification du parcours de soumission sur un formulaire public.",
    "Texte genere automatiquement pour controler la compatibilite du formulaire.",
]

FIRST_NAMES = ["Mathias", "Emma", "Lucas", "Chloe", "Hugo", "Lina", "Theo", "Jade"]
LAST_NAMES = ["Martin", "Bernard", "Dubois", "Petit", "Moreau", "Fournier", "Roux", "Lambert"]
CITIES = ["Paris", "Lyon", "Marseille", "Lille", "Nantes", "Bordeaux", "Toulouse", "Nice"]
COMPANIES = ["Studio Nova", "Atelier Horizon", "Pixel Forge", "Maison Atlas", "Blue Signal"]
JOBS = ["Designer", "Developpeur", "Chef de projet", "Consultant", "Etudiant"]
COUNTRIES = ["France", "Belgique", "Suisse", "Canada"]
STREETS = [
    "12 rue des Fleurs",
    "8 avenue Victor Hugo",
    "41 boulevard Voltaire",
    "3 impasse des Tilleuls",
]
DOMAINS = ["example.com", "mail.test", "demo.local"]

YES_WORDS = ("oui", "yes", "ok", "d'accord", "j'accepte", "accepte", "agree")
NO_WORDS = ("non", "no", "refuse", "refuser", "disagree")
NEUTRAL_WORDS = ("peut-etre", "maybe", "sans avis", "nspp", "aucun avis")
AVOID_OPTION_WORDS = ("autre", "other", "aucun", "none", "je ne sais pas", "nsp")
CONSENT_HINT_WORDS = (
    "consent",
    "autorise",
    "autorisation",
    "accord",
    "accepte",
    "accept",
    "newsletter",
    "conditions",
    "cgu",
    "rgpd",
)

ProgressCallback = Callable[[dict[str, Any]], None]
StopCallback = Callable[[], bool]
PauseCallback = Callable[[], bool]


class HiddenInputParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hidden_fields: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "input":
            return

        attrs_map = {key.lower(): value or "" for key, value in attrs}
        if attrs_map.get("type", "").lower() != "hidden":
            return

        name = attrs_map.get("name", "").strip()
        if name:
            self.hidden_fields[name] = html.unescape(attrs_map.get("value", ""))


def ensure_runtime_dirs() -> None:
    RUNTIME_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)


def save_json_snapshot(path: Path, payload: Any) -> None:
    ensure_runtime_dirs()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_log(event_type: str, message: str, **extra: Any) -> None:
    ensure_runtime_dirs()
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event_type": event_type,
        "message": message,
        "extra": extra,
    }
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_recent_logs(limit: int = 25) -> list[dict[str, Any]]:
    if limit <= 0 or not LOG_FILE.exists():
        return []

    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    entries: list[dict[str, Any]] = []
    for raw_line in reversed(lines):
        try:
            entries.append(json.loads(raw_line))
        except json.JSONDecodeError:
            continue
        if len(entries) >= limit:
            break
    return list(reversed(entries))


def clear_local_history() -> int:
    ensure_runtime_dirs()
    deleted_count = 0
    targets = [
        LOG_FILE,
        LAST_FORM_FILE,
        LAST_SIMULATION_FILE,
        LOG_DIR / "google_form_studio.log",
    ]
    for path in targets:
        if path.exists() and path.is_file():
            path.unlink()
            deleted_count += 1
    return deleted_count


def format_log_entry(entry: dict[str, Any]) -> str:
    timestamp = entry.get("timestamp", "")
    clock = timestamp[11:19] if len(timestamp) >= 19 else timestamp
    event_type = str(entry.get("event_type", "info")).upper()
    message = str(entry.get("message", ""))
    return f"[{clock}] {event_type} | {message}"


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").lower().strip()


def safe_get(value: Any, *path: Any) -> Any:
    current = value
    for key in path:
        try:
            current = current[key]
        except (IndexError, KeyError, TypeError):
            return None
    return current


def normalize_form_urls(url_public: str) -> tuple[str, str]:
    url_view = url_public.strip().split("?", 1)[0].rstrip("/")
    url_view = (
        url_view.replace("/edit", "")
        .replace("/viewform", "")
        .replace("/formResponse", "")
    )
    if not url_view.endswith("/viewform"):
        url_view = f"{url_view}/viewform"
    return url_view, url_view.replace("/viewform", "/formResponse")


def describe_request_error(error: Exception) -> str:
    if isinstance(error, requests.Timeout):
        return "Le serveur a mis trop de temps a repondre."
    if isinstance(error, requests.ConnectionError):
        return "Connexion impossible vers Google Forms."
    if isinstance(error, requests.HTTPError):
        status_code = getattr(getattr(error, "response", None), "status_code", "inconnu")
        return f"Erreur HTTP {status_code}."
    if isinstance(error, requests.RequestException):
        return "Erreur reseau pendant la communication avec Google Forms."
    return str(error)


def extract_fb_public_load_data(html_text: str) -> str:
    marker = "var FB_PUBLIC_LOAD_DATA_ = "
    start = html_text.find(marker)
    if start == -1:
        raise ValueError("Le code FB_PUBLIC_LOAD_DATA_ est introuvable dans la page.")

    index = start + len(marker)
    while index < len(html_text) and html_text[index].isspace():
        index += 1

    if index >= len(html_text) or html_text[index] != "[":
        raise ValueError("Le bloc FB_PUBLIC_LOAD_DATA_ n'a pas le format attendu.")

    depth = 0
    in_string = False
    escape = False

    for end_index in range(index, len(html_text)):
        char = html_text[end_index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return html_text[index : end_index + 1]

    raise ValueError("Le bloc FB_PUBLIC_LOAD_DATA_ est incomplet.")


def extract_hidden_fields(html_text: str) -> dict[str, str]:
    parser = HiddenInputParser()
    parser.feed(html_text)
    parser.close()
    return parser.hidden_fields


def parse_options(raw_options: Any) -> list[str]:
    options: list[str] = []
    for option in raw_options or []:
        label = option[0] if isinstance(option, list) and option else option
        if label is None:
            continue
        text = html.unescape(str(label)).strip()
        if text:
            options.append(text)
    return options


def build_grid_row(entry_id: Any, label: str) -> dict[str, str]:
    return {
        "entry_id": str(entry_id),
        "field_name": f"entry.{entry_id}",
        "label": label,
    }


def _extract_row_labels(entry_blocks: list[Any]) -> list[str]:
    if not entry_blocks:
        return []

    first_row_labels = parse_options(safe_get(entry_blocks, 0, 3))
    if len(first_row_labels) == len(entry_blocks):
        return first_row_labels

    labels: list[str] = []
    for index, block in enumerate(entry_blocks):
        block_labels = parse_options(safe_get(block, 3))
        if len(block_labels) == 1:
            labels.append(block_labels[0])
        elif index < len(first_row_labels):
            labels.append(first_row_labels[index])

    return labels or first_row_labels


def _build_grid_rows(entry_blocks: list[Any], row_labels: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, block in enumerate(entry_blocks):
        entry_id = safe_get(block, 0)
        if entry_id is None:
            continue

        block_labels = parse_options(safe_get(block, 3))
        if len(block_labels) == 1:
            label = block_labels[0]
        elif index < len(row_labels):
            label = row_labels[index]
        elif block_labels:
            label = block_labels[0]
        else:
            label = f"Ligne {index + 1}"

        rows.append(build_grid_row(entry_id, label))
    return rows


def build_question(q_raw: Any) -> dict[str, Any] | None:
    entry_blocks = safe_get(q_raw, 4) or []
    primary_block = safe_get(entry_blocks, 0)
    entry_id = safe_get(primary_block, 0)
    question_type = safe_get(q_raw, 3)

    if entry_id is None or question_type is None:
        return None

    options = parse_options(safe_get(primary_block, 1))
    row_labels = _extract_row_labels(entry_blocks)
    grid_rows = _build_grid_rows(entry_blocks, row_labels) if question_type in {7, 8} else []

    question = {
        "entry_id": str(entry_id),
        "field_name": f"entry.{entry_id}",
        "text": html.unescape(str(safe_get(q_raw, 1) or "Question sans titre")).strip(),
        "type": int(question_type),
        "type_label": QUESTION_TYPE_LABELS.get(question_type, f"Type {question_type}"),
        "required": bool(safe_get(primary_block, 2)),
        "options": options,
        "row_labels": row_labels,
        "supported": question_type in SUPPORTED_TYPES,
        "includes_year": False,
        "is_duration": False,
        "grid_rows": grid_rows,
    }

    if question["type"] in {2, 3, 4, 5} and not options:
        question["supported"] = False

    if question["type"] in {7, 8}:
        question["supported"] = bool(options and grid_rows)
        if not question["row_labels"]:
            question["row_labels"] = [row["label"] for row in grid_rows]

    if question["type"] == 9:
        date_config = safe_get(primary_block, 7) or []
        question["includes_year"] = len(date_config) > 1 and bool(date_config[1])

    if question["type"] == 10:
        time_config = safe_get(primary_block, 6) or []
        question["is_duration"] = bool(time_config and time_config[0])

    return question


def parse_form(url_public: str) -> dict[str, Any]:
    url_view, url_post = normalize_form_urls(url_public)
    try:
        response = requests.get(
            url_view,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        message = describe_request_error(error)
        append_log("analyse_error", message, url=url_view)
        raise RuntimeError(message) from error

    try:
        raw_payload = extract_fb_public_load_data(response.text)
        data = json.loads(raw_payload)
        questions = [question for q_raw in safe_get(data, 1, 1) or [] if (question := build_question(q_raw))]

        form_data = {
            "title": html.unescape(str(safe_get(data, 1, 8) or "Formulaire Google")).strip(),
            "url_view": url_view,
            "url_post": url_post,
            "questions": questions,
            "hidden_fields": extract_hidden_fields(response.text),
        }
        save_json_snapshot(LAST_FORM_FILE, form_data)
        append_log(
            "analyse_ok",
            f"Formulaire analyse : {form_data['title']}",
            question_count=len(questions),
            url=url_view,
        )
        return form_data
    except Exception as error:
        append_log("analyse_error", str(error), url=url_view)
        raise


def print_separator() -> None:
    print("----------------------------------------------------------------------")


def display_question(question: dict[str, Any], index: int, total: int) -> None:
    print_separator()
    print(f"Question {index}/{total}")
    print(f"Type : {question['type_label']}")
    print(f"Obligatoire : {'Oui' if question['required'] else 'Non'}")
    print(question["text"])

    if question["type"] in {7, 8} and question.get("grid_rows"):
        print("Lignes :")
        for row in question["grid_rows"]:
            print(f"  - {row['label']}")

    if question["options"]:
        for option_index, option in enumerate(question["options"], start=1):
            print(f"{option_index}. {option}")


def parse_positive_integer(raw_value: str) -> int:
    value = raw_value.strip()
    if not value.isdigit() or int(value) <= 0:
        raise ValueError("Entrez un nombre entier superieur a 0.")
    return int(value)


def parse_non_negative_integer(raw_value: str) -> int:
    value = raw_value.strip()
    if not value.isdigit():
        raise ValueError("Entrez un nombre entier superieur ou egal a 0.")
    return int(value)


def parse_delay_value(raw_value: str) -> float:
    value = raw_value.strip().replace(",", ".")
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValueError("Entrez un delai numerique valide.") from error
    if parsed < 0:
        raise ValueError("Le delai doit etre superieur ou egal a 0.")
    return parsed


def validate_delay_range(min_delay: float, max_delay: float) -> tuple[float, float]:
    if max_delay < min_delay:
        raise ValueError("Le delai maximum doit etre superieur ou egal au minimum.")
    return min_delay, max_delay


def format_duration_compact(seconds: float | None) -> str:
    if seconds is None:
        return "--"

    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds_value = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {seconds_value:02d}s"
    return f"{seconds_value}s"


def parse_profile(raw_value: str) -> str:
    profile = normalize_text(raw_value)
    aliases = {
        "prudent": "prudent",
        "prudente": "prudent",
        "1": "prudent",
        "equilibre": "equilibre",
        "equilibree": "equilibre",
        "2": "equilibre",
        "varie": "varie",
        "variee": "varie",
        "3": "varie",
    }
    if profile not in aliases:
        raise ValueError("Profil inconnu. Choisis prudent, equilibre ou varie.")
    return aliases[profile]


def ask_positive_integer(prompt_text: str) -> int:
    while True:
        try:
            return parse_positive_integer(input(prompt_text))
        except ValueError as error:
            print(error)


def ask_yes_no(prompt_text: str, default: bool = False) -> bool:
    accepted_yes = {"o", "oui", "y", "yes"}
    accepted_no = {"n", "non", "no"}
    suffix = "[O/n]" if default else "[o/N]"
    while True:
        answer = input(f"{prompt_text} {suffix} : ").strip().lower()
        if not answer:
            return default
        if answer in accepted_yes:
            return True
        if answer in accepted_no:
            return False
        print("Reponds par oui ou non.")


def ask_profile() -> str:
    while True:
        print("Profils automatiques :")
        print("  1. prudent")
        print("  2. equilibre")
        print("  3. varie")
        try:
            return parse_profile(input("Choisissez un profil : "))
        except ValueError as error:
            print(error)


def ask_delay_range() -> tuple[float, float]:
    while True:
        try:
            min_delay = parse_delay_value(input("Delai minimum entre deux envois (secondes) : "))
            max_delay = parse_delay_value(input("Delai maximum entre deux envois (secondes) : "))
            return validate_delay_range(min_delay, max_delay)
        except ValueError as error:
            print(error)


def ask_text_answer(question: dict[str, Any]) -> str | None:
    prompt = "Votre texte" if question["type"] == 1 else "Votre reponse"
    while True:
        answer = input(f"{prompt} : ").strip()
        if answer:
            return answer
        if not question["required"]:
            return None
        print("Cette question est obligatoire.")


def _ask_single_option(options: list[str], required: bool, prompt_text: str) -> str | None:
    while True:
        answer = input(prompt_text).strip()
        if not answer:
            if not required:
                return None
            print("Cette question est obligatoire.")
            continue
        if answer.isdigit():
            index = int(answer)
            if 1 <= index <= len(options):
                return options[index - 1]
        print("Entrez un numero valide parmi les choix proposes.")


def ask_single_choice(question: dict[str, Any]) -> str | None:
    return _ask_single_option(question["options"], question["required"], "Choisissez un numero : ")


def _parse_multiple_choice(raw_value: str, options: list[str]) -> list[str]:
    parts = [part.strip() for part in raw_value.split(",") if part.strip()]
    if not parts:
        raise ValueError("Entrez au moins un numero valide.")
    if not all(part.isdigit() for part in parts):
        raise ValueError("Utilisez seulement des numeros, par exemple : 1,3")

    indexes = [int(part) for part in parts]
    if any(index < 1 or index > len(options) for index in indexes):
        raise ValueError("Un ou plusieurs numeros sont hors liste.")

    selected: list[str] = []
    for index in indexes:
        option = options[index - 1]
        if option not in selected:
            selected.append(option)
    return selected


def ask_multiple_choice(question: dict[str, Any], *, required: bool | None = None) -> list[str]:
    is_required = question["required"] if required is None else required
    while True:
        answer = input("Choisissez un ou plusieurs numeros separes par des virgules : ").strip()
        if not answer:
            if is_required:
                print("Entrez au moins un choix.")
                continue
            return []
        try:
            return _parse_multiple_choice(answer, question["options"])
        except ValueError as error:
            print(error)


def ask_scale_answer(question: dict[str, Any]) -> str | None:
    return _ask_single_option(question["options"], question["required"], "Entrez la note souhaitee : ")


def parse_date_input(raw_value: str, includes_year: bool) -> dict[str, str | None]:
    match = re.match(r"^\s*(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\s*$", raw_value)
    if not match:
        raise ValueError("Format attendu : JJ/MM ou JJ/MM/AAAA")

    day = int(match.group(1))
    month = int(match.group(2))
    year_text = match.group(3)

    if includes_year and not year_text:
        raise ValueError("Cette date doit inclure l'annee.")
    if not includes_year and year_text:
        raise ValueError("Cette question attend seulement JJ/MM.")

    year = int(year_text) if year_text else None
    datetime(year or 2000, month, day)

    return {
        "day": f"{day:02d}",
        "month": f"{month:02d}",
        "year": str(year) if year is not None else None,
        "display": f"{day:02d}/{month:02d}/{year}" if year is not None else f"{day:02d}/{month:02d}",
    }


def ask_date_answer(question: dict[str, Any]) -> dict[str, str | None] | None:
    expected = "JJ/MM/AAAA" if question.get("includes_year") else "JJ/MM"
    while True:
        answer = input(f"Entrez la date ({expected}) : ").strip()
        if not answer:
            if not question["required"]:
                return None
            print("Cette question est obligatoire.")
            continue
        try:
            return parse_date_input(answer, bool(question.get("includes_year")))
        except ValueError as error:
            print(error)


def parse_time_input(raw_value: str) -> dict[str, str]:
    match = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", raw_value)
    if not match:
        raise ValueError("Format attendu : HH:MM")

    hour = int(match.group(1))
    minute = int(match.group(2))
    if not 0 <= hour <= 23:
        raise ValueError("L'heure doit etre comprise entre 00 et 23.")
    if not 0 <= minute <= 59:
        raise ValueError("Les minutes doivent etre comprises entre 00 et 59.")

    return {
        "hour": f"{hour:02d}",
        "minute": f"{minute:02d}",
        "display": f"{hour:02d}:{minute:02d}",
    }


def ask_time_answer(question: dict[str, Any]) -> dict[str, str] | None:
    label = "Entrez la duree (HH:MM)" if question.get("is_duration") else "Entrez l'heure (HH:MM)"
    while True:
        answer = input(f"{label} : ").strip()
        if not answer:
            if not question["required"]:
                return None
            print("Cette question est obligatoire.")
            continue
        try:
            return parse_time_input(answer)
        except ValueError as error:
            print(error)


def build_grid_answer(rows: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "__grid__": True,
        "rows": rows,
        "display": "; ".join(f"{row['label']}: {row['value']}" for row in rows),
    }


def build_grid_multi_answer(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "__grid_multi__": True,
        "rows": rows,
        "display": "; ".join(f"{row['label']}: {', '.join(row['values'])}" for row in rows if row["values"]),
    }


def ask_grid_answer(question: dict[str, Any]) -> dict[str, Any] | str | None:
    grid_rows = question.get("grid_rows") or []
    if len(grid_rows) <= 1:
        return _ask_single_option(question["options"], question["required"], "Choisissez un numero : ")

    rows: list[dict[str, str]] = []
    for row in grid_rows:
        print(f"Ligne : {row['label']}")
        selected = _ask_single_option(question["options"], question["required"], "Choisissez un numero : ")
        if selected is not None:
            rows.append(
                {
                    "field_name": row["field_name"],
                    "label": row["label"],
                    "value": selected,
                }
            )

    return build_grid_answer(rows) if rows else None


def ask_grid_multi_answer(question: dict[str, Any]) -> dict[str, Any] | None:
    rows: list[dict[str, Any]] = []
    required = question["required"]
    for row in question.get("grid_rows") or []:
        print(f"Ligne : {row['label']}")
        values = ask_multiple_choice(question, required=required)
        rows.append(
            {
                "field_name": row["field_name"],
                "label": row["label"],
                "values": values,
            }
        )
    return build_grid_multi_answer(rows) if rows else None


def ask_answer(question: dict[str, Any], index: int, total: int) -> Any:
    display_question(question, index, total)

    if not question["supported"]:
        print("Ce type de question n'est pas encore gere par ce script.")
        return "__UNSUPPORTED__"

    question_type = question["type"]
    if question_type in {0, 1}:
        return ask_text_answer(question)
    if question_type in {2, 3}:
        return ask_single_choice(question)
    if question_type == 4:
        return ask_multiple_choice(question)
    if question_type == 5:
        return ask_scale_answer(question)
    if question_type == 7:
        return ask_grid_answer(question)
    if question_type == 8:
        return ask_grid_multi_answer(question)
    if question_type == 9:
        return ask_date_answer(question)
    if question_type == 10:
        return ask_time_answer(question)
    return "__UNSUPPORTED__"


def _required_unsupported_questions(questions: list[dict[str, Any]]) -> list[str]:
    return [question["text"] for question in questions if question["required"] and not question["supported"]]


def _print_unsupported_message(title: str, items: list[str]) -> None:
    print_separator()
    print(title)
    for item in items:
        print(f"- {item}")


def collect_answers(questions: list[dict[str, Any]]) -> dict[str, Any] | None:
    unsupported_required = _required_unsupported_questions(questions)
    if unsupported_required:
        _print_unsupported_message(
            "Impossible de continuer car certaines questions obligatoires ne sont pas encore gerees :",
            unsupported_required,
        )
        return None

    answers: dict[str, Any] = {}
    total = len(questions)
    for index, question in enumerate(questions, start=1):
        answer = ask_answer(question, index, total)
        if answer != "__UNSUPPORTED__":
            answers[question["field_name"]] = answer
    return answers


def random_identity() -> dict[str, str]:
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    city = random.choice(CITIES)
    company = random.choice(COMPANIES)
    domain = random.choice(DOMAINS)
    username = f"{normalize_text(first_name)}.{normalize_text(last_name)}{random.randint(1, 99)}"
    return {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": f"{first_name} {last_name}",
        "email": f"{username}@{domain}",
        "phone": f"06{random.randint(10, 99):02d}{random.randint(10, 99):02d}{random.randint(10, 99):02d}{random.randint(10, 99):02d}",
        "city": city,
        "postcode": str(random.choice(["75012", "69003", "13006", "33000", "44000"])),
        "company": company,
        "job": random.choice(JOBS),
        "country": random.choice(COUNTRIES),
        "address": random.choice(STREETS),
        "url": f"https://{normalize_text(company).replace(' ', '-')}.{domain}",
        "social": f"@{normalize_text(first_name)}_{normalize_text(last_name)}",
        "age": str(random.randint(18, 58)),
    }


def guess_text_category(question_text: str) -> str:
    text = normalize_text(question_text)
    if any(word in text for word in ("e-mail", "email", "mail")):
        return "email"
    if any(word in text for word in ("telephone", "tel", "mobile", "portable", "whatsapp")):
        return "phone"
    if "prenom" in text or "first name" in text:
        return "first_name"
    if "nom complet" in text or "full name" in text:
        return "full_name"
    if "nom" in text or "last name" in text or "surname" in text:
        return "last_name"
    if any(word in text for word in ("entreprise", "societe", "company")):
        return "company"
    if "ville" in text or "city" in text:
        return "city"
    if any(word in text for word in ("code postal", "postal", "zip")):
        return "postcode"
    if "pays" in text or "country" in text:
        return "country"
    if any(word in text for word in ("adresse", "address", "rue", "street")):
        return "address"
    if any(word in text for word in ("poste", "metier", "job", "profession", "fonction")):
        return "job"
    if any(word in text for word in ("site web", "website", "url", "linkedin")):
        return "url"
    if any(word in text for word in ("instagram", "tiktok", "twitter", "reseau social", "pseudo")):
        return "social"
    if any(word in text for word in ("age", "anciennete")):
        return "age"
    return "generic"


def _profile_optional_skip_probability(profile: str) -> float:
    return {
        "prudent": 0.35,
        "equilibre": 0.20,
        "varie": 0.05,
    }[profile]


def choose_smart_option(options: list[str], question_text: str, profile: str) -> str:
    normalized_question = normalize_text(question_text)
    normalized_options = [normalize_text(option) for option in options]

    if options and all(option.isdigit() for option in options):
        if profile == "prudent":
            return options[max(0, len(options) // 2 - 1)]
        if profile == "equilibre":
            return options[len(options) // 2]
        return random.choice(options)

    if any(hint in normalized_question for hint in CONSENT_HINT_WORDS):
        for index, option in enumerate(normalized_options):
            if any(word in option for word in YES_WORDS):
                return options[index]

    if "sexe" in normalized_question or "genre" in normalized_question or "gender" in normalized_question:
        for candidate in ("femme", "homme", "autre"):
            if candidate in normalized_options:
                return options[normalized_options.index(candidate)]

    weighted_indexes = [
        index
        for index, option in enumerate(normalized_options)
        if not any(word in option for word in AVOID_OPTION_WORDS)
    ]
    pool = weighted_indexes or list(range(len(options)))

    if profile == "prudent":
        for index in pool:
            option = normalized_options[index]
            if any(word in option for word in YES_WORDS + NEUTRAL_WORDS):
                return options[index]
        return options[pool[0]]

    if profile == "equilibre":
        midpoint = pool[len(pool) // 2]
        return options[midpoint]

    return options[random.choice(pool)]


def random_text_answer(question: dict[str, Any], profile: str = "equilibre") -> str:
    category = guess_text_category(question["text"])
    identity = random_identity()

    if question["type"] == 1:
        if category in {"generic", "job", "company"}:
            return random.choice(AUTO_PARAGRAPH_SAMPLES)
        return (
            "Reponse automatique generee pour verifier le formulaire. "
            f"Contexte detecte : {category.replace('_', ' ')}."
        )

    if category in identity:
        return identity[category]

    if category == "generic" and any(word in normalize_text(question["text"]) for word in ("commentaire", "avis", "message")):
        return "Avis positif genere automatiquement pour test."

    base = random.choice(AUTO_SHORT_TEXT_SAMPLES)
    if profile == "varie":
        return f"{base} {random.choice(CITIES)} {random.randint(1, 999)}"
    if len(question["text"]) < 40:
        return f"{base} {random.randint(1, 999)}"
    return base


def random_scale_answer(question: dict[str, Any], profile: str = "equilibre") -> str:
    if question["options"]:
        return choose_smart_option(question["options"], question["text"], profile)
    if profile == "prudent":
        return "3"
    if profile == "equilibre":
        return "4"
    return str(random.randint(1, 5))


def random_date_answer(question: dict[str, Any]) -> dict[str, str | None]:
    normalized_question = normalize_text(question["text"])
    if any(word in normalized_question for word in ("naissance", "birth")):
        start_date = datetime.now().date() - timedelta(days=365 * 55)
        random_day = start_date + timedelta(days=random.randint(0, 365 * 35))
    else:
        start_date = datetime.now().date() - timedelta(days=180)
        random_day = start_date + timedelta(days=random.randint(0, 365))

    answer = {
        "day": f"{random_day.day:02d}",
        "month": f"{random_day.month:02d}",
        "year": str(random_day.year) if question.get("includes_year") else None,
    }
    answer["display"] = (
        f"{answer['day']}/{answer['month']}/{answer['year']}"
        if answer["year"] is not None
        else f"{answer['day']}/{answer['month']}"
    )
    return answer


def random_time_answer() -> dict[str, str]:
    hour = random.randint(8, 20)
    minute = random.choice((0, 15, 30, 45))
    return {
        "hour": f"{hour:02d}",
        "minute": f"{minute:02d}",
        "display": f"{hour:02d}:{minute:02d}",
    }


def generate_random_answer(question: dict[str, Any], profile: str = "equilibre") -> Any:
    if not question["required"] and random.random() < _profile_optional_skip_probability(profile):
        if question["type"] == 4:
            return []
        if question["type"] == 8:
            return build_grid_multi_answer([])
        return None

    if question["type"] in {0, 1}:
        return random_text_answer(question, profile)
    if question["type"] in {2, 3}:
        return choose_smart_option(question["options"], question["text"], profile)
    if question["type"] == 4:
        if profile == "prudent":
            return [choose_smart_option(question["options"], question["text"], profile)]
        if profile == "equilibre":
            count = min(len(question["options"]), max(1, len(question["options"]) // 2))
            return random.sample(question["options"], count)
        count = random.randint(1, len(question["options"]))
        return random.sample(question["options"], count)
    if question["type"] == 5:
        return random_scale_answer(question, profile)
    if question["type"] == 7:
        grid_rows = question.get("grid_rows") or []
        if len(grid_rows) <= 1:
            return choose_smart_option(question["options"], question["text"], profile)
        return build_grid_answer(
            [
                {
                    "field_name": row["field_name"],
                    "label": row["label"],
                    "value": choose_smart_option(question["options"], row["label"], profile),
                }
                for row in grid_rows
            ]
        )
    if question["type"] == 8:
        rows = []
        for row in question.get("grid_rows") or []:
            if profile == "prudent":
                values = [choose_smart_option(question["options"], row["label"], profile)]
            elif profile == "equilibre":
                values = random.sample(question["options"], min(2, len(question["options"])))
            else:
                values = random.sample(question["options"], random.randint(1, len(question["options"])))
            rows.append({"field_name": row["field_name"], "label": row["label"], "values": values})
        return build_grid_multi_answer(rows)
    if question["type"] == 9:
        return random_date_answer(question)
    if question["type"] == 10:
        return random_time_answer()
    return "__UNSUPPORTED__"


def collect_random_answers(questions: list[dict[str, Any]], profile: str = "equilibre") -> dict[str, Any] | None:
    unsupported_required = _required_unsupported_questions(questions)
    if unsupported_required:
        _print_unsupported_message(
            "Impossible d'utiliser le mode automatique car certaines questions obligatoires ne sont pas gerees :",
            unsupported_required,
        )
        return None

    answers: dict[str, Any] = {}
    for question in questions:
        answer = generate_random_answer(question, profile)
        if answer != "__UNSUPPORTED__":
            answers[question["field_name"]] = answer
    return answers


def is_blank_answer(answer: Any) -> bool:
    if answer in (None, "", []):
        return True
    if isinstance(answer, dict) and answer.get("__grid__"):
        return not answer.get("rows")
    if isinstance(answer, dict) and answer.get("__grid_multi__"):
        rows = answer.get("rows", [])
        return not rows or not any(row.get("values") for row in rows)
    return False


def format_answer_for_summary(question: dict[str, Any], answer: Any) -> str:
    if is_blank_answer(answer):
        return "(vide)"

    if isinstance(answer, dict) and ("__grid__" in answer or "__grid_multi__" in answer):
        return str(answer.get("display") or "(vide)")

    if isinstance(answer, list):
        return ", ".join(answer)

    if isinstance(answer, dict):
        return str(answer.get("display") or answer)

    return str(answer)


def build_summary_text(questions: list[dict[str, Any]], answers: dict[str, Any]) -> str:
    lines = []
    for index, question in enumerate(questions, start=1):
        answer = answers.get(question["field_name"])
        lines.append(f"{index}. {question['text']}\n   -> {format_answer_for_summary(question, answer)}")
    return "\n\n".join(lines)


def show_summary(questions: list[dict[str, Any]], answers: dict[str, Any]) -> None:
    print_separator()
    print("Recapitulatif avant envoi")
    print(build_summary_text(questions, answers))


def build_payload(form_data: dict[str, Any], answers: dict[str, Any]) -> list[tuple[str, str]]:
    payload = list(form_data["hidden_fields"].items())

    for question in form_data["questions"]:
        field_name = question["field_name"]
        answer = answers.get(field_name)
        if is_blank_answer(answer):
            continue

        question_type = question["type"]
        if question_type in {0, 1, 2, 3, 5}:
            payload.append((field_name, str(answer)))
        elif question_type == 4:
            payload.extend((field_name, selected) for selected in answer)
        elif question_type == 7:
            if isinstance(answer, dict) and answer.get("__grid__"):
                payload.extend((row["field_name"], row["value"]) for row in answer.get("rows", []))
            else:
                payload.append((field_name, str(answer)))
        elif question_type == 8:
            for row in answer.get("rows", []):
                payload.extend((row["field_name"], value) for value in row.get("values", []))
        elif question_type == 9:
            payload.append((f"{field_name}_day", answer["day"]))
            payload.append((f"{field_name}_month", answer["month"]))
            if answer["year"] is not None:
                payload.append((f"{field_name}_year", answer["year"]))
        elif question_type == 10:
            payload.append((f"{field_name}_hour", answer["hour"]))
            payload.append((f"{field_name}_minute", answer["minute"]))

    return payload


def simulate_submission(form_data: dict[str, Any], answers: dict[str, Any], label: str = "simulation") -> dict[str, Any]:
    payload = build_payload(form_data, answers)
    filled_count = sum(
        1 for question in form_data["questions"] if not is_blank_answer(answers.get(question["field_name"]))
    )
    simulation = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "label": label,
        "title": form_data["title"],
        "url_view": form_data["url_view"],
        "url_post": form_data["url_post"],
        "question_count": len(form_data["questions"]),
        "filled_count": filled_count,
        "payload_count": len(payload),
        "payload": payload,
        "summary_text": build_summary_text(form_data["questions"], answers),
    }
    save_json_snapshot(LAST_SIMULATION_FILE, simulation)
    append_log(
        "simulation",
        f"Simulation preparee pour {form_data['title']}",
        label=label,
        payload_count=len(payload),
        filled_count=filled_count,
    )
    return simulation


def format_simulation_report(simulation: dict[str, Any]) -> str:
    payload_lines = "\n".join(f"- {key} = {value}" for key, value in simulation["payload"]) or "- aucun champ utile"
    return (
        f"Simulation : {simulation['label']}\n"
        f"Formulaire : {simulation['title']}\n"
        f"Questions detectees : {simulation['question_count']}\n"
        f"Questions remplies : {simulation['filled_count']}\n"
        f"Champs du payload : {simulation['payload_count']}\n"
        f"URL cible : {simulation['url_post']}\n\n"
        "Payload qui serait envoye :\n"
        f"{payload_lines}\n\n"
        "Recapitulatif :\n"
        f"{simulation['summary_text']}"
    )


def normalize_text_for_checks(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").lower()


def submit_form(form_data: dict[str, Any], answers: dict[str, Any]) -> None:
    payload = build_payload(form_data, answers)
    try:
        response = requests.post(
            form_data["url_post"],
            data=payload,
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": form_data["url_view"],
            },
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
    except requests.RequestException as error:
        message = describe_request_error(error)
        append_log("submit_error", message, form_title=form_data["title"])
        raise RuntimeError(message) from error

    if response.status_code not in {200, 302}:
        message = f"Erreur HTTP {response.status_code}."
        append_log("submit_error", message, form_title=form_data["title"])
        raise RuntimeError(message)

    body = normalize_text_for_checks(response.text)
    known_failures = (
        "this form is no longer accepting responses",
        "ce formulaire n'accepte plus de reponses",
        "you need permission",
        "vous devez disposer des autorisations necessaires",
        "this is a required question",
        "veuillez repondre a cette question",
    )
    if any(marker in body for marker in known_failures):
        message = "Google a refuse la soumission du formulaire."
        append_log("submit_error", message, form_title=form_data["title"])
        raise RuntimeError(message)

    append_log(
        "submit_ok",
        f"Reponse envoyee pour {form_data['title']}",
        payload_count=len(payload),
    )


def _wait_while_paused(
    pause_requested: PauseCallback | None,
    stop_requested: StopCallback | None,
) -> tuple[bool, float]:
    if not pause_requested or not pause_requested():
        return False, 0.0

    paused_started = time.monotonic()
    while pause_requested():
        if stop_requested and stop_requested():
            return True, time.monotonic() - paused_started
        time.sleep(0.1)
    return False, time.monotonic() - paused_started


def _sleep_with_controls(
    duration: float,
    stop_requested: StopCallback | None,
    pause_requested: PauseCallback | None,
) -> tuple[bool, float]:
    if duration <= 0:
        return False, 0.0

    remaining = duration
    paused_total = 0.0
    while remaining > 0:
        if stop_requested and stop_requested():
            return True, paused_total

        stopped, paused_delta = _wait_while_paused(pause_requested, stop_requested)
        paused_total += paused_delta
        if stopped:
            return True, paused_total

        slice_duration = min(0.1, remaining)
        started_at = time.monotonic()
        time.sleep(slice_duration)
        remaining -= time.monotonic() - started_at

    return False, paused_total


def _build_progress_snapshot(
    *,
    index: int,
    count: int,
    success_count: int,
    error_count: int,
    sent_count: int,
    retry_count_total: int,
    max_retries: int,
    simulate_only: bool,
    error: str | None,
    started_at: float,
    paused_total: float,
) -> dict[str, Any]:
    processed_count = success_count + error_count
    pending_count = max(0, count - processed_count)
    elapsed_seconds = max(0.0, time.monotonic() - started_at - paused_total)
    eta_seconds = None
    if processed_count and pending_count:
        eta_seconds = (elapsed_seconds / processed_count) * pending_count

    return {
        "index": index,
        "count": count,
        "processed_count": processed_count,
        "pending_count": pending_count,
        "success_count": success_count,
        "error_count": error_count,
        "sent_count": sent_count,
        "retry_count_total": retry_count_total,
        "max_retries": max_retries,
        "error": error,
        "stopped": False,
        "simulate_only": simulate_only,
        "elapsed_seconds": elapsed_seconds,
        "eta_seconds": eta_seconds,
    }


def run_random_submissions(
    form_data: dict[str, Any],
    count: int,
    *,
    profile: str = "equilibre",
    min_delay: float = 0.4,
    max_delay: float = 1.2,
    simulate_only: bool = False,
    max_retries: int = 0,
    on_progress: ProgressCallback | None = None,
    stop_requested: StopCallback | None = None,
    pause_requested: PauseCallback | None = None,
) -> dict[str, Any]:
    validate_delay_range(min_delay, max_delay)
    if max_retries < 0:
        raise ValueError("Le nombre de retries doit etre superieur ou egal a 0.")

    append_log(
        "batch_start",
        f"Lancement d'une serie de {count} reponse(s) sur {form_data['title']}",
        count=count,
        profile=profile,
        simulate_only=simulate_only,
        min_delay=min_delay,
        max_delay=max_delay,
        max_retries=max_retries,
    )

    success_count = 0
    error_count = 0
    last_error = ""
    sent_count = 0
    retry_count_total = 0
    stopped = False
    paused_total = 0.0
    started_at = time.monotonic()

    for index in range(1, count + 1):
        if stop_requested and stop_requested():
            stopped = True
            break

        paused_stop, paused_delta = _wait_while_paused(pause_requested, stop_requested)
        paused_total += paused_delta
        if paused_stop:
            stopped = True
            break

        answers = collect_random_answers(form_data["questions"], profile)
        if answers is None:
            raise RuntimeError("Le mode automatique ne peut pas completer ce formulaire.")

        current_error = None
        completed = False
        attempt_number = 0
        while not completed:
            attempt_number += 1
            try:
                if simulate_only:
                    simulate_submission(form_data, answers, label=f"simulation serie {index}/{count}")
                else:
                    submit_form(form_data, answers)
                success_count += 1
                sent_count += 1
                current_error = None
                completed = True
            except Exception as error:  # pragma: no cover - depends on live form/network
                current_error = str(error)
                last_error = current_error
                if attempt_number <= max_retries:
                    retry_count_total += 1
                    append_log(
                        "batch_retry",
                        f"Retry {attempt_number + 1}/{max_retries + 1} pour {form_data['title']}",
                        index=index,
                        error=current_error,
                        retry_count_total=retry_count_total,
                    )
                    retry_delay = min(3.0, 0.8 * attempt_number)
                    retry_stop, retry_paused = _sleep_with_controls(
                        retry_delay,
                        stop_requested,
                        pause_requested,
                    )
                    paused_total += retry_paused
                    if retry_stop:
                        stopped = True
                        break
                    continue

                error_count += 1
                completed = True

        if stopped and not completed:
            break

        if on_progress:
            on_progress(
                _build_progress_snapshot(
                    index=index,
                    count=count,
                    success_count=success_count,
                    error_count=error_count,
                    sent_count=sent_count,
                    retry_count_total=retry_count_total,
                    max_retries=max_retries,
                    simulate_only=simulate_only,
                    error=current_error,
                    started_at=started_at,
                    paused_total=paused_total,
                )
            )

        if index < count:
            delay = random.uniform(min_delay, max_delay)
            delay_stop, delay_paused = _sleep_with_controls(delay, stop_requested, pause_requested)
            paused_total += delay_paused
            if delay_stop:
                stopped = True
                break

    processed_count = success_count + error_count
    elapsed_seconds = max(0.0, time.monotonic() - started_at - paused_total)
    summary = {
        "success_count": success_count,
        "error_count": error_count,
        "last_error": last_error,
        "processed_count": processed_count,
        "pending_count": max(0, count - processed_count),
        "sent_count": sent_count,
        "retry_count_total": retry_count_total,
        "max_retries": max_retries,
        "stopped": stopped,
        "simulate_only": simulate_only,
        "requested_count": count,
        "elapsed_seconds": elapsed_seconds,
        "eta_seconds": 0 if processed_count == count else None,
    }
    append_log(
        "batch_end",
        f"Serie terminee sur {form_data['title']}",
        **summary,
    )
    return summary


def ask_menu_choice() -> str:
    while True:
        print_separator()
        print("Choisissez un mode")
        print("  1. Mode manuel")
        print("  2. Mode automatique aleatoire")
        answer = input("Entrez 1 ou 2 : ").strip()
        if answer in {"1", "2"}:
            return answer
        print("Choisissez 1 ou 2.")


def run_auto_mode(form_data: dict[str, Any]) -> int:
    questions = form_data["questions"]
    count = ask_positive_integer("Combien de reponses aleatoires voulez-vous envoyer ? : ")
    profile = ask_profile()
    min_delay, max_delay = ask_delay_range()
    simulate_only = ask_yes_no("Souhaitez-vous simuler sans envoyer ?", default=False)

    sample_answers = collect_random_answers(questions, profile)
    if sample_answers is None:
        return 1

    print_separator()
    print("Mode automatique")
    print(f"Nombre de reponses prevu : {count}")
    print(f"Profil : {profile}")
    print(f"Delais : {min_delay:.2f}s -> {max_delay:.2f}s")
    print(f"Simulation uniquement : {'oui' if simulate_only else 'non'}")
    print("Exemple d'une reponse qui sera generee :")
    show_summary(questions, sample_answers)
    print_separator()

    confirmation = input("Tapez AUTO pour lancer la serie, ou appuyez sur Entree pour annuler : ").strip()
    if confirmation.upper() != "AUTO":
        print("Envoi automatique annule.")
        return 0

    summary = run_random_submissions(
        form_data,
        count,
        profile=profile,
        min_delay=min_delay,
        max_delay=max_delay,
        simulate_only=simulate_only,
        on_progress=lambda payload: print(
            f"[{payload['processed_count']}/{payload['count']}] "
            f"{'Simulees' if simulate_only else 'Envoyees'} : {payload['success_count']} | "
            f"En attente : {payload['pending_count']} | "
            f"Erreurs : {payload['error_count']} | "
            f"Retries : {payload['retry_count_total']} | "
            f"Reste estime : {format_duration_compact(payload['eta_seconds'])}"
            + ("" if payload["error"] is None else f" | Derniere erreur : {payload['error']}")
        ),
    )
    print_separator()
    print(
        "Mode automatique termine : "
        f"{summary['success_count']} succes, {summary['error_count']} erreur(s)."
        + (" Serie interrompue." if summary["stopped"] else "")
    )
    return 0 if summary["success_count"] else 1


def main_interactive_flow(url_public: str) -> int:
    try:
        url_view, _url_post = normalize_form_urls(url_public)
        print(f"\nAnalyse du formulaire : {url_view}")
        form_data = parse_form(url_public)
    except Exception as error:
        print(f"\nErreur pendant l'analyse du formulaire : {error}")
        return 1

    questions = form_data["questions"]
    if not questions:
        print("\nAucune question exploitable n'a ete detectee.")
        return 1

    print_separator()
    print(f"Formulaire trouve : {form_data['title']}")
    print(f"Nombre de questions detectees : {len(questions)}")

    if ask_menu_choice() == "2":
        return run_auto_mode(form_data)

    answers = collect_answers(questions)
    if answers is None:
        return 1

    show_summary(questions, answers)
    if ask_yes_no("Souhaitez-vous simuler la reponse avant envoi ?", default=False):
        report = format_simulation_report(simulate_submission(form_data, answers, label="simulation manuelle"))
        print_separator()
        print(report)
        print_separator()

    confirmation = input("Tapez ENVOYER pour confirmer l'envoi, ou appuyez sur Entree pour annuler : ").strip()
    if confirmation.upper() != "ENVOYER":
        print("Envoi annule.")
        return 0

    try:
        submit_form(form_data, answers)
    except Exception as error:
        print(f"Erreur lors de l'envoi : {error}")
        return 1

    print("Reponse envoyee avec succes.")
    return 0


def ask_restart_or_close() -> str:
    while True:
        print_separator()
        print("Que voulez-vous faire maintenant ?")
        print("  1. Recommencer")
        print("  2. Fermer")
        answer = input("Entrez 1 ou 2 : ").strip()
        if answer in {"1", "2"}:
            return answer
        print("Choisissez 1 ou 2.")


def main() -> int:
    while True:
        print_separator()
        print("Assistant Google Forms")
        print("Collez l'URL d'un formulaire public, puis utilisez le mode manuel ou automatique.")
        print_separator()

        lien = input("Collez le lien du Google Form ici : ").strip()
        if not lien:
            print("Aucun lien fourni. Abandon.")
            result = 1
        else:
            result = main_interactive_flow(lien)

        if ask_restart_or_close() == "2":
            return result


if __name__ == "__main__":
    raise SystemExit(main())
