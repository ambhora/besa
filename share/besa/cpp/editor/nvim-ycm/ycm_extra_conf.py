# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------

import glob
import json
import os
import shlex


ROOT = os.path.dirname(os.path.abspath(__file__))

CXXFLAGS = [
    "-Weverything",
    "-Wno-c++98-compat",
    "-Wno-c++98-compat-pedantic",
    "-Wno-covered-switch-default",
    "-Wno-padded",
    "-Wno-weak-vtables",
    "-Wno-exit-time-destructors",
    "-Wno-global-constructors",
    "-std=c++26",
    "-x",
    "c++",
]

CFLAGS = [
    "-Wextra",
    "-Wall",
    "-std=c17",
    "-x",
    "c",
]

_PATH_FLAGS_WITH_ARGUMENT = {
    "-I",
    "-F",
    "-idirafter",
    "-iframework",
    "-iquote",
    "-isystem",
    "-isysroot",
    "--sysroot",
}

_PATH_FLAG_PREFIXES = (
    "-idirafter",
    "-iframework",
    "-iquote",
    "-isystem",
    "-isysroot",
    "--sysroot=",
    "-I",
    "-F",
)

_FLAGS_WITH_ARGUMENT_TO_DROP = {
    "-MF",
    "-MJ",
    "-MQ",
    "-MT",
    "-o",
}

_FLAGS_TO_DROP = {
    "-c",
    "-MD",
    "-MMD",
    "-MP",
}

_SOURCE_EXTENSIONS = {
    "c": ".c",
    "cpp": ".cpp",
    "cuda": ".cu",
    "hip": ".hip",
}

_DATABASE_CACHE = {
    "path": None,
    "mtime_ns": None,
    "entries": {},
}


def _absolute_path(path, working_directory):
    if os.path.isabs(path):
        return os.path.normpath(path)
    return os.path.normpath(os.path.join(working_directory, path))


def _include_directories():
    patterns = [
        os.path.join(ROOT, "src", "**", "include"),
        os.path.join(ROOT, "test", "**", "include"),
        os.path.join(ROOT, "build", "**", "generated", "include"),
        os.path.join(ROOT, "..", "build", "**", "generated", "include"),
    ]
    directories = set()
    for pattern in patterns:
        directories.update(path for path in glob.glob(pattern, recursive=True) if os.path.isdir(path))
    return sorted(os.path.normpath(path) for path in directories)


def _compile_commands_path():
    direct_candidates = [
        os.path.join(ROOT, "compile_commands.json"),
        os.path.join(ROOT, "build", "compile_commands.json"),
        os.path.join(ROOT, "..", "build", "compile_commands.json"),
    ]
    for candidate in direct_candidates:
        if os.path.isfile(candidate):
            return os.path.normpath(candidate)

    recursive_candidates = []
    for pattern in (
        os.path.join(ROOT, "build", "**", "compile_commands.json"),
        os.path.join(ROOT, "..", "build", "**", "compile_commands.json"),
    ):
        recursive_candidates.extend(glob.glob(pattern, recursive=True))

    candidates = [path for path in recursive_candidates if os.path.isfile(path)]
    if not candidates:
        return None
    return max(candidates, key=lambda path: os.stat(path).st_mtime_ns)


def _command_arguments(entry):
    arguments = entry.get("arguments")
    if isinstance(arguments, list):
        return [str(argument) for argument in arguments]

    command = entry.get("command")
    if isinstance(command, str):
        return shlex.split(command)

    return []


def _normalise_path_flag(argument, next_argument, working_directory):
    if argument in _PATH_FLAGS_WITH_ARGUMENT:
        if next_argument is None:
            return None, 1
        return [argument, _absolute_path(next_argument, working_directory)], 2

    for prefix in _PATH_FLAG_PREFIXES:
        if not argument.startswith(prefix) or argument == prefix:
            continue
        path = argument[len(prefix) :]
        if not path:
            continue
        return [prefix + _absolute_path(path, working_directory)], 1

    return None, 1


def _compile_flags(arguments, working_directory, source_file):
    if not arguments:
        return []

    source_file = os.path.normpath(source_file)
    result = []
    index = 1

    while index < len(arguments):
        argument = arguments[index]
        next_argument = arguments[index + 1] if index + 1 < len(arguments) else None

        path_flags, consumed = _normalise_path_flag(argument, next_argument, working_directory)
        if path_flags is not None:
            result.extend(path_flags)
            index += consumed
            continue

        if argument in _FLAGS_WITH_ARGUMENT_TO_DROP:
            index += 2 if next_argument is not None else 1
            continue

        if argument in _FLAGS_TO_DROP:
            index += 1
            continue

        if argument.startswith("-o") and argument != "-o":
            index += 1
            continue

        candidate = _absolute_path(argument, working_directory)
        if candidate == source_file:
            index += 1
            continue

        result.append(argument)
        index += 1

    return result


def _load_compilation_database():
    path = _compile_commands_path()
    if path is None:
        return {}

    mtime_ns = os.stat(path).st_mtime_ns
    if _DATABASE_CACHE["path"] == path and _DATABASE_CACHE["mtime_ns"] == mtime_ns:
        return _DATABASE_CACHE["entries"]

    try:
        with open(path, encoding="utf-8") as stream:
            database = json.load(stream)
    except (OSError, ValueError):
        return {}

    entries = {}
    for entry in database:
        if not isinstance(entry, dict):
            continue

        working_directory = entry.get("directory")
        source_file = entry.get("file")
        if not isinstance(working_directory, str) or not isinstance(source_file, str):
            continue

        working_directory = os.path.abspath(working_directory)
        source_file = _absolute_path(source_file, working_directory)
        entries[source_file] = _compile_flags(
            _command_arguments(entry),
            working_directory,
            source_file,
        )

    _DATABASE_CACHE.update(
        {
            "path": path,
            "mtime_ns": mtime_ns,
            "entries": entries,
        }
    )
    return entries


def _layout_language(filename):
    try:
        relative = os.path.relpath(filename, ROOT)
    except ValueError:
        return None

    parts = relative.split(os.sep)
    for marker in ("include", "lib", "bin"):
        if marker not in parts:
            continue
        index = parts.index(marker)
        if index > 0 and parts[index - 1] in _SOURCE_EXTENSIONS:
            return parts[index - 1]
    return None


def _source_analogue(filename):
    try:
        relative = os.path.relpath(filename, ROOT)
    except ValueError:
        return None

    parts = relative.split(os.sep)
    if "include" not in parts:
        return None

    include_index = parts.index("include")
    if include_index == 0:
        return None

    language = parts[include_index - 1]
    extension = _SOURCE_EXTENSIONS.get(language)
    if extension is None:
        return None

    parts[include_index] = "lib"
    stem, _ = os.path.splitext(parts[-1])
    parts[-1] = stem + extension
    return os.path.normpath(os.path.join(ROOT, *parts))


def _baseline_flags(filename):
    language = _layout_language(filename)
    if language == "c" or os.path.splitext(filename)[1] == ".c":
        return list(CFLAGS)
    return list(CXXFLAGS)


def _fallback_includes():
    return ["-I" + path for path in _include_directories()]


def Settings(filename, **kwargs):
    filename = os.path.normpath(os.path.abspath(filename))
    flags = _baseline_flags(filename)
    entries = _load_compilation_database()

    compile_flags = entries.get(filename)
    if compile_flags is None:
        analogue = _source_analogue(filename)
        if analogue is not None:
            compile_flags = entries.get(analogue)

    if compile_flags is not None:
        flags.extend(compile_flags)
    else:
        flags.extend(_fallback_includes())

    return {"flags": flags}
