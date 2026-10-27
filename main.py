#!/usr/bin/env python3
"""Инструмент визуализации графа зависимостей (Maven).

Запуск:  python main.py [--config config.csv] [--stage 1..5]
  stage 1 — вывести параметры конфигурации
  stage 2 — вывести прямые зависимости пакета
  stage 3 — построить граф (BFS, глубина, фильтр, циклы) и вывести рёбра
  stage 4 — вывести порядок загрузки зависимостей
  stage 5 — (по умолчанию) сгенерировать D2 и PNG
"""
import argparse
import sys

import d2gen
import graph as G
import maven
from config import ConfigError, load_config


def direct_deps(cfg):
    if cfg.test_mode:
        repo = G.load_test_repo(cfg.repo_url)
        if cfg.package_name not in repo:
            raise ValueError(f"пакет '{cfg.package_name}' отсутствует в тестовом репозитории")
        return repo[cfg.package_name]
    g, a, v = cfg.package_name.split(":")
    return [f"{d.name}  (scope={d.scope}{', optional' if d.optional else ''})"
            for d in maven.get_direct_dependencies(cfg.repo_url, g, a, v)]


def make_graph(cfg):
    if cfg.test_mode:
        repo = G.load_test_repo(cfg.repo_url)
        if cfg.package_name not in repo:
            raise ValueError(f"пакет '{cfg.package_name}' отсутствует в тестовом репозитории")
        children = G.test_children_func(repo)
    else:
        children = G.maven_children_func(cfg.repo_url)
        # проверяем, что корневой пакет доступен, до обхода
        g, a, v = cfg.package_name.split(":")
        maven.get_direct_dependencies(cfg.repo_url, g, a, v)
    return G.build_graph(cfg.package_name, children, cfg.max_depth, cfg.filter_substring)


def main() -> int:
    ap = argparse.ArgumentParser(description="Визуализация графа зависимостей")
    ap.add_argument("--config", default="config.csv", help="путь к CSV-конфигурации")
    ap.add_argument("--stage", type=int, choices=range(1, 6), default=5)
    args = ap.parse_args()

    try:
        cfg = load_config(args.config)

        if args.stage == 1:
            for k, v in vars(cfg).items():
                print(f"{k}: {v}")
            return 0

        if args.stage == 2:
            print(f"Прямые зависимости {cfg.package_name}:")
            deps = direct_deps(cfg)
            print("\n".join("  " + d for d in deps) if deps else "  (нет)")
            return 0

        graph = make_graph(cfg)

        if args.stage == 3:
            print(f"Граф зависимостей (глубина <= {cfg.max_depth}):")
            for node, children in graph.items():
                print(f"  {node} -> {', '.join(children) if children else '-'}")
            return 0

        if args.stage == 4:
            order, cycles = G.load_order(graph, cfg.package_name)
            print("Порядок загрузки:", " -> ".join(order))
            for c in cycles:
                print("  обнаружен цикл:", " -> ".join(c))
            return 0

        text = d2gen.to_d2(graph, cfg.package_name)
        print(text)
        d2_path = d2gen.render_png(text, cfg.output_file)
        print(f"D2: {d2_path}\nPNG: {cfg.output_file}")
        return 0

    except (ConfigError, maven.MavenError, d2gen.RenderError, ValueError, OSError) as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
