"""Этап 5: текст диаграммы D2 и рендер в PNG."""
import os
import shutil
import subprocess
from typing import Dict, List


class RenderError(Exception):
    pass


def _q(name: str) -> str:
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def to_d2(graph: Dict[str, List[str]], root: str) -> str:
    lines = [f'{_q(root)}: {{style: {{fill: "#ffe9a8"}}}}']
    for node, children in graph.items():
        if node != root and not children:
            lines.append(_q(node))
        for c in children:
            lines.append(f"{_q(node)} -> {_q(c)}")
    return "\n".join(lines) + "\n"


def render_png(d2_text: str, png_path: str) -> str:
    """Сохраняет .d2 рядом с PNG и вызывает консольную утилиту d2."""
    d2_path = os.path.splitext(png_path)[0] + ".d2"
    try:
        with open(d2_path, "w", encoding="utf-8") as f:
            f.write(d2_text)
    except OSError as e:
        raise RenderError(f"не удалось записать {d2_path}: {e}")
    if shutil.which("d2") is None:
        raise RenderError(
            f"утилита d2 не найдена в PATH (установите: https://d2lang.com). "
            f"Файл {d2_path} сохранён, PNG можно получить вручную: d2 {d2_path} {png_path}")
    res = subprocess.run(["d2", d2_path, png_path], capture_output=True, text=True)
    if res.returncode != 0:
        raise RenderError(f"d2 завершилась с ошибкой: {res.stderr.strip()}")
    return d2_path
