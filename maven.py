"""Этап 2: получение прямых зависимостей из pom.xml (Maven) без сторонних библиотек."""
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional


class MavenError(Exception):
    pass


@dataclass
class Dependency:
    group: str
    artifact: str
    version: str
    scope: str = "compile"
    optional: bool = False

    @property
    def name(self) -> str:
        return f"{self.group}:{self.artifact}:{self.version}"


def pom_url(repo: str, group: str, artifact: str, version: str) -> str:
    return f"{repo.rstrip('/')}/{group.replace('.', '/')}/{artifact}/{version}/{artifact}-{version}.pom"


def _strip_ns(root: ET.Element) -> ET.Element:
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def _text(el: Optional[ET.Element], tag: str) -> Optional[str]:
    if el is None:
        return None
    child = el.find(tag)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def fetch_pom(repo: str, group: str, artifact: str, version: str) -> ET.Element:
    url = pom_url(repo, group, artifact, version)
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        raise MavenError(f"не удалось получить {url}: HTTP {e.code}")
    except (urllib.error.URLError, OSError) as e:
        raise MavenError(f"репозиторий недоступен ({url}): {e}")
    try:
        return _strip_ns(ET.fromstring(data))
    except ET.ParseError as e:
        raise MavenError(f"некорректный XML в {url}: {e}")


def _resolve(value: Optional[str], props: dict) -> Optional[str]:
    if value is None:
        return None
    for _ in range(10):
        new = re.sub(r"\$\{([^}]+)\}", lambda m: props.get(m.group(1), m.group(0)), value)
        if new == value:
            break
        value = new
    return value


def _clean_version(v: str) -> str:
    """Диапазон версий [1.0,2.0) -> берём нижнюю границу (упрощение)."""
    if v and v[0] in "[(":
        inner = v.strip("[]()").split(",")
        for part in inner:
            if part.strip():
                return part.strip()
    return v


def _load_effective(repo, group, artifact, version, depth=0):
    """Возвращает (pom, properties, dependencyManagement) с учётом цепочки parent."""
    root = fetch_pom(repo, group, artifact, version)
    props, managed = {}, {}
    parent = root.find("parent")
    pver = None
    if parent is not None and depth < 10:
        pg, pa, pv = _text(parent, "groupId"), _text(parent, "artifactId"), _text(parent, "version")
        pver = pv
        if pg and pa and pv:
            try:
                _, props, managed = _load_effective(repo, pg, pa, pv, depth + 1)
                props, managed = dict(props), dict(managed)
            except MavenError:
                pass  # parent недоступен — продолжаем без него

    own_version = _text(root, "version") or pver or version
    own_group = _text(root, "groupId") or (_text(parent, "groupId") if parent is not None else None) or group
    props.update({
        "project.version": own_version, "version": own_version, "pom.version": own_version,
        "project.groupId": own_group, "groupId": own_group,
        "project.artifactId": artifact,
    })
    if pver:
        props["project.parent.version"] = pver
    p = root.find("properties")
    if p is not None:
        for el in p:
            if isinstance(el.tag, str) and el.text:
                props[el.tag] = el.text.strip()

    for d in root.findall("dependencyManagement/dependencies/dependency"):
        g, a = _resolve(_text(d, "groupId"), props), _resolve(_text(d, "artifactId"), props)
        v = _resolve(_text(d, "version"), props)
        if g and a and v:
            managed[f"{g}:{a}"] = v
    return root, props, managed


def get_direct_dependencies(repo: str, group: str, artifact: str, version: str) -> List[Dependency]:
    root, props, managed = _load_effective(repo, group, artifact, version)
    result = []
    for d in root.findall("dependencies/dependency"):
        g = _resolve(_text(d, "groupId"), props)
        a = _resolve(_text(d, "artifactId"), props)
        v = _resolve(_text(d, "version"), props) or managed.get(f"{g}:{a}")
        if not (g and a):
            continue
        if not v or "${" in v:
            continue  # версию определить не удалось
        scope = _resolve(_text(d, "scope"), props) or "compile"
        optional = (_resolve(_text(d, "optional"), props) or "false").lower() == "true"
        result.append(Dependency(g, a, _clean_version(v), scope, optional))
    return result
