#!/usr/bin/env python3
"""维护一个精简且兼容 clangd 的编译数据库。
GN 可能为同一个源文件生成多条编译命令。clangd 15 会枚举去重后的文件，并为每个文件使用第一条命令。本工具保持该行为，只保留每个规范化绝对源文件路径对应的第一条记录。
本工具不会修改原始数据库。输出文件采用原子替换，并发执行会串行处理，同时保留一份最近可用的 ``.previous`` 文件。
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import Iterator

REQUIRED_FIELDS = ("file", "directory", "command")

def source_fingerprint(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {
        "source_device": stat.st_dev,
        "source_inode": stat.st_ino,
        "source_size": stat.st_size,
        "source_mtime_ns": stat.st_mtime_ns,
    }

def normalized_path(directory: object, filename: object) -> str:
    if not isinstance(directory, str) or not isinstance(filename, str):
        raise ValueError("every entry must contain string file and directory fields")
    path = filename if os.path.isabs(filename) else os.path.join(directory, filename)
    return os.path.normpath(path)

def normalized_file(entry: dict) -> str:
    return normalized_path(entry.get("directory"), entry.get("file"))

def field_offset(raw_line: bytes, field: str) -> int | None:
    offset = 0
    while offset < len(raw_line) and raw_line[offset] in b" \t":
        offset += 1
    token = f'"{field}":'.encode("ascii")
    return offset + len(token) if raw_line.startswith(token, offset) else None

def parse_identity_field(raw_line: bytes, field: str) -> str | None:
    value_offset = field_offset(raw_line, field)
    if value_offset is None:
        return None
    field_text = raw_line.lstrip().rstrip()
    if field_text.endswith(b","):
        field_text = field_text[:-1]
    value = json.loads(b"{" + field_text + b"}").get(field)
    if not isinstance(value, str):
        raise ValueError(f"field {field!r} must be a string")
    return value

def has_string_field(raw_line: bytes, field: str) -> bool:
    value_offset = field_offset(raw_line, field)
    if value_offset is None:
        return False
    while value_offset < len(raw_line) and raw_line[value_offset] in b" \t":
        value_offset += 1
    return value_offset < len(raw_line) and raw_line[value_offset] == ord('"')

def iter_gn_database(
    path: Path, digest: "hashlib._Hash", seen: set[str]
) -> Iterator[dict | None]:
    """流式读取 GN JSON；重复文件返回 None，且不解析其超长 command。"""
    current: list[bytes] | None = None
    filename: str | None = None
    directory: str | None = None
    classified = False
    duplicate = False
    saw_command = False
    saw_array_start = False
    saw_array_end = False

    with path.open("rb") as source:
        for line_number, raw_line in enumerate(source, 1):
            digest.update(raw_line)

            if current is not None and duplicate:
                if has_string_field(raw_line, "command"):
                    saw_command = True
                stripped = raw_line.strip() if len(raw_line) <= 16 else b""
                if stripped in {b"}", b"},"}:
                    if not saw_command:
                        raise ValueError(
                            f"entry ending at line {line_number} has invalid required fields"
                        )
                    yield None
                    current = None
                    filename = None
                    directory = None
                    classified = False
                    duplicate = False
                    saw_command = False
                continue

            stripped = raw_line.strip()

            if not saw_array_start:
                if stripped != b"[":
                    raise ValueError("source database does not start with an array")
                saw_array_start = True
                continue

            if current is None and stripped == b"]":
                saw_array_end = True
                continue

            if stripped == b"{":
                if current is not None:
                    raise ValueError(f"nested object at line {line_number}")
                current = [raw_line]
                filename = None
                directory = None
                classified = False
                duplicate = False
                saw_command = False
                continue

            if current is None:
                if stripped:
                    raise ValueError(f"unexpected content at line {line_number}")
                continue

            current.append(raw_line)
            if filename is None:
                filename = parse_identity_field(raw_line, "file")
            if directory is None:
                directory = parse_identity_field(raw_line, "directory")
            if has_string_field(raw_line, "command"):
                saw_command = True

            if not classified and filename is not None and directory is not None:
                file_key = normalized_path(directory, filename)
                classified = True
                if file_key in seen:
                    duplicate = True
                    current.clear()
                    continue
                seen.add(file_key)

            if stripped in {b"}", b"},"}:
                text = b"".join(current).rstrip()
                if text.endswith(b","):
                    text = text[:-1]
                value = json.loads(text)
                if not isinstance(value, dict):
                    raise ValueError(f"entry ending at line {line_number} is not an object")

                if not classified:
                    file_key = normalized_file(value)
                    if file_key in seen:
                        yield None
                        current = None
                        continue
                    seen.add(file_key)
                yield value
                current = None

    if not saw_array_start or not saw_array_end:
        raise ValueError("source database is not a complete JSON array")
    if current is not None:
        raise ValueError("source database contains an unterminated object")
def validate_output(path: Path, expected_entries: int) -> None:
    count = 0
    with path.open("r", encoding="utf-8") as generated:
        if generated.readline().strip() != "[":
            raise ValueError("generated database does not start with an array")
        for line in generated:
            stripped = line.strip()
            if stripped == "]":
                break
            if stripped.endswith(","):
                stripped = stripped[:-1]
            entry = json.loads(stripped)
            if not isinstance(entry, dict) or not all(key in entry for key in REQUIRED_FIELDS):
                raise ValueError(f"invalid generated entry at item {count + 1}")
            count += 1
        else:
            raise ValueError("generated database does not end with an array")
    if count != expected_entries:
        raise ValueError(f"expected {expected_entries} entries, validated {count}")

def load_report(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

def write_json_atomic(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as output:
            json.dump(value, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)

def rotate_previous(destination: Path) -> None:
    if not destination.exists():
        return
    previous = destination.with_name(destination.name + ".previous")
    temporary = previous.with_name(f".{previous.name}.{os.getpid()}.tmp")
    try:
        os.link(destination, temporary)
        os.replace(temporary, previous)
    finally:
        temporary.unlink(missing_ok=True)

def generate(source: Path, destination: Path, report_path: Path) -> dict:
    source = source.resolve(strict=True)
    destination = destination.resolve(strict=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    report_path = report_path.resolve(strict=False)
    lock_path = destination.parent / ".compile-commands-update.lock"

    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        before = source_fingerprint(source)
        old_report = load_report(report_path)
        if (
            destination.is_file()
            and old_report.get("source") == str(source)
            and old_report.get("destination") == str(destination)
            and all(old_report.get(key) == value for key, value in before.items())
            and destination.stat().st_size == old_report.get("output_size")
        ):
            result = dict(old_report)
            result["status"] = "source-unchanged"
            return result

        temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
        source_digest = hashlib.sha256()
        output_digest = hashlib.sha256()
        seen: set[str] = set()
        input_entries = 0
        output_entries = 0

        try:
            with temporary.open("wb") as output:
                header = b"[\n"
                output.write(header)
                output_digest.update(header)
                first = True

                for entry in iter_gn_database(source, source_digest, seen):
                    input_entries += 1
                    if entry is None:
                        continue
                    if not all(isinstance(entry.get(key), str) for key in REQUIRED_FIELDS):
                        raise ValueError(f"entry {input_entries} has invalid required fields")

                    prefix = b"" if first else b",\n"
                    payload = json.dumps(
                        entry, ensure_ascii=False, separators=(",", ":")
                    ).encode("utf-8")
                    output.write(prefix)
                    output.write(payload)
                    output_digest.update(prefix)
                    output_digest.update(payload)
                    first = False
                    output_entries += 1

                footer = b"\n]\n"
                output.write(footer)
                output_digest.update(footer)
                output.flush()
                os.fsync(output.fileno())

            after = source_fingerprint(source)
            if after != before:
                raise RuntimeError("source database changed while it was being read")
            validate_output(temporary, output_entries)

            output_sha256 = output_digest.hexdigest()
            output_size = temporary.stat().st_size
            unchanged = (
                destination.is_file()
                and old_report.get("output_sha256") == output_sha256
                and destination.stat().st_size == output_size
            )
            if unchanged:
                temporary.unlink()
                status = "output-unchanged"
            else:
                rotate_previous(destination)
                os.replace(temporary, destination)
                directory_fd = os.open(destination.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
                status = "updated"

            report = {
                **after,
                "source": str(source),
                "destination": str(destination),
                "rule": "first-command-per-normalized-file",
                "input_entries": input_entries,
                "output_entries": output_entries,
                "removed_entries": input_entries - output_entries,
                "source_sha256": source_digest.hexdigest(),
                "output_sha256": output_sha256,
                "output_size": output_size,
                "status": status,
            }
            write_json_atomic(report_path, report)
            return report
        finally:
            temporary.unlink(missing_ok=True)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report_path = args.report or args.destination.with_name("generation-report.json")
    report = generate(args.source, args.destination, report_path)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
