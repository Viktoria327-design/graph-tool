"""Этапы 3-4: граф зависимостей (BFS с рекурсией), тестовый репозиторий, порядок загрузки."""
import re
import sys
from typing import Callable, Dict, List

import maven

Graph = Dict[str, List[str]]


# ---------- источники дочерних вершин ----------
def load_test_repo(path: str) -> Dict[str, List[str]]:
    """Файл вида 'A: B C'. Имена пакетов — большие латинские буквы."""
    repo: Dict[str, List[str]] = {}
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                raise ValueError(f"{path}, строка {lineno}: ожидался формат 'A: B C'")
            name, deps = line.split(":", 1)
            name, deps = name.strip(), deps.split()
            for n in [name] + deps:
                if not re.fullmatch(r"[A-Z]+", n):
                    raise ValueError(f"{path}, строка {lineno}: имя '{n}' не из больших латинских букв")
            repo.setdefault(name, [])
            for d in deps:
                if d not in repo[name]:
                    repo[name].append(d)
    return repo


def test_children_func(repo: Dict[str, List[str]]) -> Callable[[str], List[str]]:
    return lambda node: repo.get(node, [])


def maven_children_func(repo_url: str) -> Callable[[str], List[str]]:
    cache: Dict[str, List[str]] = {}

    def children(node: str) -> List[str]:
        if node in cache:
            return cache[node]
        g, a, v = node.split(":")
        try:
            deps = maven.get_direct_dependencies(repo_url, g, a, v)
        except maven.MavenError as e:
            print(f"предупреждение: {node}: {e}", file=sys.stderr)
            deps = []
        # транзитивно, как Maven, не берём test/provided/system и optional
        names = []
        for d in deps:
            if d.scope in ("test", "provided", "system") or d.optional:
                continue
            if d.name not in names:
                names.append(d.name)
        cache[node] = names
        return names

    return children


# ---------- построение графа ----------
def build_graph(root: str, get_children: Callable[[str], List[str]],
                max_depth: int, substring: str) -> Graph:
    """BFS: уровень за уровнем, переход на следующий уровень — рекурсивным вызовом."""
    graph: Graph = {root: []}
    visited = {root}

    def bfs(level: List[str], depth: int) -> None:
        if not level or depth >= max_depth:
            return
        next_level: List[str] = []
        for node in level:
            for child in get_children(node):
                if substring and substring in child:
                    continue  # фильтр по подстроке
                if child not in graph[node]:
                    graph[node].append(child)
                if child not in visited:  # защита от циклов и повторов
                    visited.add(child)
                    graph[child] = []
                    next_level.append(child)
        bfs(next_level, depth + 1)

    bfs([root], 0)
    return graph


# ---------- этап 4: порядок загрузки ----------
def load_order(graph: Graph, root: str):
    """Пост-порядок DFS: сначала зависимости, затем зависимый пакет.
    Возвращает (порядок, список найденных циклов)."""
    state: Dict[str, int] = {}
    order: List[str] = []
    cycles: List[List[str]] = []

    def dfs(node: str, stack: List[str]) -> None:
        state[node] = 1
        stack.append(node)
        for child in graph.get(node, []):
            if state.get(child) == 1:
                cycles.append(stack[stack.index(child):] + [child])
            elif child not in state:
                dfs(child, stack)
        stack.pop()
        state[node] = 2
        order.append(node)

    dfs(root, [])
    return order, cycles
