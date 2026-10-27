"""Этап 1: чтение и валидация CSV-конфигурации."""
import csv
import os
import re
from dataclasses import dataclass


class ConfigError(Exception):
    """Ошибка конфигурации (понятное сообщение для пользователя)."""


REQUIRED_KEYS = [
    "package_name",
    "repo_url",
    "test_mode",
    "output_file",
    "max_depth",
    "filter_substring",
]
OPTIONAL_EMPTY = {"filter_substring"}  # может быть пустым


@dataclass
class Config:
    package_name: str
    repo_url: str
    test_mode: bool
    output_file: str
    max_depth: int
    filter_substring: str


def _read_raw(path: str) -> dict:
    if not os.path.exists(path):
        raise ConfigError(f"файл конфигурации не найден: {path}")
    if not os.path.isfile(path):
        raise ConfigError(f"путь к конфигурации не является файлом: {path}")
    raw = {}
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            for lineno, row in enumerate(csv.reader(f), 1):
                if not row or not row[0].strip() or row[0].lstrip().startswith("#"):
                    continue
                if len(row) < 2:
                    raise ConfigError(f"строка {lineno}: ожидался формат 'ключ,значение'")
                key, value = row[0].strip(), row[1].strip()
                if key not in REQUIRED_KEYS:
                    raise ConfigError(f"строка {lineno}: неизвестный параметр '{key}'")
                if key in raw:
                    raise ConfigError(f"строка {lineno}: параметр '{key}' задан повторно")
                raw[key] = value
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        raise ConfigError(f"не удалось прочитать {path}: {e}")
    return raw


def load_config(path: str) -> Config:
    raw = _read_raw(path)

    missing = [k for k in REQUIRED_KEYS if k not in raw]
    if missing:
        raise ConfigError("не заданы параметры: " + ", ".join(missing))
    for k in REQUIRED_KEYS:
        if not raw[k] and k not in OPTIONAL_EMPTY:
            raise ConfigError(f"параметр '{k}' не может быть пустым")

    # test_mode
    tm = raw["test_mode"].lower()
    if tm in ("true", "1", "yes", "да"):
        test_mode = True
    elif tm in ("false", "0", "no", "нет"):
        test_mode = False
    else:
        raise ConfigError(f"test_mode: ожидалось true/false, получено '{raw['test_mode']}'")

    # max_depth
    try:
        max_depth = int(raw["max_depth"])
    except ValueError:
        raise ConfigError(f"max_depth: ожидалось целое число, получено '{raw['max_depth']}'")
    if max_depth < 0:
        raise ConfigError("max_depth: значение не может быть отрицательным")

    # repo_url / путь к тестовому репозиторию
    repo = raw["repo_url"]
    if test_mode:
        if not os.path.isfile(repo):
            raise ConfigError(f"repo_url: файл тестового репозитория не найден: {repo}")
    elif not re.match(r"^https?://\S+$", repo):
        raise ConfigError(f"repo_url: ожидался URL вида http(s)://..., получено '{repo}'")

    # package_name
    pkg = raw["package_name"]
    if test_mode:
        if not re.fullmatch(r"[A-Z]+", pkg):
            raise ConfigError(
                f"package_name: в тестовом режиме имя — большие латинские буквы, получено '{pkg}'")
    else:
        parts = pkg.split(":")
        if len(parts) != 3 or not all(p.strip() for p in parts):
            raise ConfigError(
                f"package_name: ожидался формат groupId:artifactId:version, получено '{pkg}'")

    # output_file
    out = raw["output_file"]
    if not out.lower().endswith(".png"):
        raise ConfigError("output_file: имя файла должно оканчиваться на .png")
    out_dir = os.path.dirname(out)
    if out_dir and not os.path.isdir(out_dir):
        raise ConfigError(f"output_file: каталог не существует: {out_dir}")

    # filter_substring
    sub = raw["filter_substring"]
    if sub and sub in pkg:
        raise ConfigError(
            f"filter_substring: подстрока '{sub}' содержится в имени анализируемого пакета")

    return Config(pkg, repo, test_mode, out, max_depth, sub)
