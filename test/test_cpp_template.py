from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from besa.cli import cpp_generate, cpp_update


def _run(command: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and result.returncode != 0:
        pytest.fail(
            f"Command failed with exit code {result.returncode}: {' '.join(command)}\n\n{result.stdout}",
            pytrace=False,
        )
    return result


@pytest.mark.cpp
@pytest.mark.parametrize(("preset", "compiler"), [("gcc", "g++"), ("clang", "clang++")])
def test_generated_cpp_project_builds_with_multiple_compilers(
    tmp_path: Path, preset: str, compiler: str
) -> None:
    if shutil.which("cmake") is None or shutil.which(compiler) is None:
        pytest.skip(f"CMake and {compiler} are required")
    project = cpp_generate(tmp_path, f"example_{preset}")
    _run(["cmake", "--workflow", "--preset", preset, "--fresh"], project)
    assert (project / "build" / preset / "src" / f"example_{preset}").exists()


@pytest.mark.cpp
def test_generated_cpp_project_installs_and_exports_package(tmp_path: Path) -> None:
    if shutil.which("cmake") is None or shutil.which("g++") is None:
        pytest.skip("CMake and g++ are required")
    project = cpp_generate(tmp_path, "example_install")
    _run(["cmake", "--workflow", "--preset", "gcc", "--fresh"], project)
    prefix = tmp_path / "prefix"
    _run(["cmake", "--install", "build/gcc", "--prefix", str(prefix)], project)

    config = prefix / "lib" / "cmake" / "example_install" / "example_installConfig.cmake"
    assert config.is_file()
    text = config.read_text(encoding="utf-8")
    assert '${CMAKE_CURRENT_LIST_DIR}/example_installTargets.cmake' in text
    assert "find_dependency(besa" not in text.lower()
    assert "besa::" not in text.lower()

    consumer = tmp_path / "consumer"
    consumer.mkdir()
    (consumer / "CMakeLists.txt").write_text(
        """\
cmake_minimum_required(VERSION 3.26.1)
project(consumer LANGUAGES CXX)
find_package(example_install CONFIG REQUIRED)
add_executable(consumer main.cpp)
target_link_libraries(consumer PRIVATE example_install::libexample_install)
""",
        encoding="utf-8",
    )
    (consumer / "main.cpp").write_text(
        "#include <example_install/example_install.hpp>\nint main(){return example_install::hello().empty();}\n",
        encoding="utf-8",
    )
    _run(
        [
            "cmake",
            "-S",
            ".",
            "-B",
            "build",
            f"-DCMAKE_PREFIX_PATH={prefix}",
        ],
        consumer,
    )
    _run(["cmake", "--build", "build"], consumer)


@pytest.mark.cpp
def test_feature_override_can_disable_defaults(tmp_path: Path) -> None:
    project = cpp_generate(tmp_path, "example_features")
    result = _run(
        [
            "cmake",
            "-S",
            ".",
            "-B",
            "build/no-source",
            "-DPROJECT_FEATURES=~build-source;~toolchain-cpp",
        ],
        project,
    )
    assert "Configuring done" in result.stdout


@pytest.mark.cpp
def test_duplicate_feature_override_is_an_error(tmp_path: Path) -> None:
    project = cpp_generate(tmp_path, "example_duplicate")
    result = _run(
        [
            "cmake",
            "-S",
            ".",
            "-B",
            "build/duplicate",
            "-DPROJECT_FEATURES=toolchain-cpp;~toolchain-cpp",
        ],
        project,
        check=False,
    )
    assert result.returncode != 0
    assert "feature 'toolchain-cpp'" in result.stdout
    assert "PROJECT_FEATURES" in result.stdout


@pytest.mark.cpp
def test_registered_feature_constraint_rejects_invalid_combination(tmp_path: Path) -> None:
    project = tmp_path / "constraint"
    project.mkdir()
    cpp_update(project)
    (project / "CMakeLists.txt").write_text(
        """\
cmake_minimum_required(VERSION 3.26.1)
project(constraint LANGUAGES NONE)
list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa")
find_package(besa CONFIG REQUIRED)

function(no_c_and_cpp)
  besa_feature_constraint_arguments_parse(PREFIX ARG ARGUMENTS ${ARGN})
  if("toolchain-c" IN_LIST ARG_FEATURES AND "toolchain-cpp" IN_LIST ARG_FEATURES)
    set("${ARG_OUTPUT_VARIABLE}" FALSE PARENT_SCOPE)
    set("${ARG_ERROR_VARIABLE}" "C and C++ are forbidden together in this test" PARENT_SCOPE)
    return()
  endif()
  set("${ARG_OUTPUT_VARIABLE}" TRUE PARENT_SCOPE)
  set("${ARG_ERROR_VARIABLE}" "" PARENT_SCOPE)
endfunction()

besa_features_add(FEATURES toolchain-c toolchain-cpp)
besa_features_default(FEATURES toolchain-cpp)
besa_register_feature_constraint(FUNCTION no_c_and_cpp)
besa_configure_complete()
""",
        encoding="utf-8",
    )
    result = _run(
        [
            "cmake",
            "-S",
            ".",
            "-B",
            "build",
            "-DPROJECT_FEATURES=toolchain-c",
        ],
        project,
        check=False,
    )
    assert result.returncode != 0
    assert "C and C++ are forbidden together" in result.stdout


@pytest.mark.cpp
def test_regex_and_list_selectors(tmp_path: Path) -> None:
    project = tmp_path / "selectors"
    project.mkdir()
    cpp_update(project)
    for name in ("any", "all", "regex"):
        directory = project / name
        directory.mkdir()
        (directory / "CMakeLists.txt").write_text(
            f'file(WRITE "${{PROJECT_BINARY_DIR}}/{name}.selected" "yes")\n', encoding="utf-8"
        )
    (project / "CMakeLists.txt").write_text(
        """\
cmake_minimum_required(VERSION 3.26.1)
project(selectors LANGUAGES NONE)
list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa")
find_package(besa CONFIG REQUIRED)
besa_features_add(FEATURES alpha beta project-one)
besa_features_default(FEATURES alpha project-one)
besa_configure_complete()
besa_add_directory(NAME any WHEN ANY_OF beta alpha)
besa_add_directory(NAME all WHEN ALL_OF alpha ~beta)
besa_add_directory(NAME regex WHEN REGEX "^project-")
""",
        encoding="utf-8",
    )
    _run(["cmake", "-S", ".", "-B", "build"], project)
    for name in ("any", "all", "regex"):
        assert (project / "build" / f"{name}.selected").is_file()

@pytest.mark.cpp
def test_function_selector_callback_uses_named_arguments(tmp_path: Path) -> None:
    project = tmp_path / "function_selector"
    project.mkdir()
    cpp_update(project)
    selected = project / "selected"
    selected.mkdir()
    (selected / "CMakeLists.txt").write_text(
        'file(WRITE "${PROJECT_BINARY_DIR}/function.selected" "yes")\n', encoding="utf-8"
    )
    (project / "CMakeLists.txt").write_text(
        """\
cmake_minimum_required(VERSION 3.26.1)
project(function_selector LANGUAGES NONE)
list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa")
find_package(besa CONFIG REQUIRED)

function(select_alpha)
  besa_selector_arguments_parse(PREFIX ARG ARGUMENTS ${ARGN})
  if("alpha" IN_LIST ARG_FEATURES)
    set("${ARG_OUTPUT_VARIABLE}" TRUE PARENT_SCOPE)
  else()
    set("${ARG_OUTPUT_VARIABLE}" FALSE PARENT_SCOPE)
  endif()
  set("${ARG_ERROR_VARIABLE}" "" PARENT_SCOPE)
endfunction()

besa_features_add(FEATURES alpha)
besa_features_default(FEATURES alpha)
besa_configure_complete()
besa_add_directory(NAME selected WHEN FUNCTION select_alpha)
""",
        encoding="utf-8",
    )
    _run(["cmake", "-S", ".", "-B", "build"], project)
    assert (project / "build" / "function.selected").is_file()


@pytest.mark.cpp
def test_release_version_is_written_to_generated_header(tmp_path: Path) -> None:
    if shutil.which("cmake") is None or shutil.which("g++") is None:
        pytest.skip("CMake and g++ are required")
    project = cpp_generate(tmp_path, "example_version")
    _run(
        [
            "cmake",
            "-S",
            ".",
            "-B",
            "build/version",
            "-DRELEASE_TYPE=rc",
            "-DRELEASE_REVISION=3",
        ],
        project,
    )
    version_header = project / "build" / "version" / "generated" / "include" / "example_version" / "version.hpp"
    assert '0.1.0-rc.3' in version_header.read_text(encoding="utf-8")


@pytest.mark.cpp
def test_surrogate_instrumentation_builds_public_headers_in_isolation(tmp_path: Path) -> None:
    if shutil.which("cmake") is None or shutil.which("clang++") is None:
        pytest.skip("CMake and clang++ are required")
    project = tmp_path / "surrogate_case"
    (project / "src" / "cpp" / "include" / "surrogate_case").mkdir(parents=True)
    (project / "src" / "cpp" / "lib").mkdir(parents=True)
    cpp_update(project)
    (project / "src" / "cpp" / "include" / "surrogate_case" / "api.hpp").write_text(
        '#pragma once\n#include <string>\nnamespace surrogate_case { inline std::string hello(){ return "hello"; } }\n',
        encoding="utf-8",
    )
    (project / "src" / "cpp" / "lib" / "api.cpp").write_text(
        '#include <surrogate_case/api.hpp>\n', encoding="utf-8"
    )
    (project / "CMakeLists.txt").write_text(
        """\
cmake_minimum_required(VERSION 3.26.1)
project(surrogate_case VERSION 0.1.0 LANGUAGES NONE)
list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa")
find_package(besa CONFIG REQUIRED)
set(PROJECT_DEVTOOLS "surrogate" CACHE STRING "")
set(PROJECT_WARNINGS "none" CACHE STRING "")
set(BUILD_TESTING ON CACHE BOOL "")
include(CTest)
besa_features_add(FEATURES toolchain-cpp)
besa_features_default(FEATURES toolchain-cpp)
besa_configure_complete()
besa_add_source_directory(NAME src/cpp LANGUAGE CXX WHEN ALL_OF toolchain-cpp)
""",
        encoding="utf-8",
    )
    _run(["cmake", "-S", ".", "-B", "build", "-DCMAKE_CXX_COMPILER=clang++"], project)
    _run(["cmake", "--build", "build"], project)
    result = _run(["ctest", "--test-dir", "build", "-R", "surrogate", "--output-on-failure"], project)
    assert "surrogate.libsurrogate_case.t" in result.stdout
    assert (project / "build" / "surrogate" / "libsurrogate_case" / "surrogate_case" / "api.cpp").is_file()


@pytest.mark.cpp
def test_clang_coverage_instrumentation_generates_report(tmp_path: Path) -> None:
    required = ("cmake", "clang++", "llvm-profdata", "llvm-cov")
    if any(shutil.which(tool) is None for tool in required):
        pytest.skip("Clang coverage tools are required")
    project = tmp_path / "coverage_case"
    (project / "test" / "cpp").mkdir(parents=True)
    cpp_update(project)
    (project / "test" / "cpp" / "hello.t.cpp").write_text(
        'int main(){ int value = 1; return value == 1 ? 0 : 1; }\n', encoding="utf-8"
    )
    (project / "CMakeLists.txt").write_text(
        """\
cmake_minimum_required(VERSION 3.26.1)
project(coverage_case VERSION 0.1.0 LANGUAGES NONE)
list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa")
find_package(besa CONFIG REQUIRED)
set(PROJECT_DEVTOOLS "coverage" CACHE STRING "")
set(PROJECT_WARNINGS "none" CACHE STRING "")
set(BUILD_TESTING ON CACHE BOOL "")
include(CTest)
besa_features_add(FEATURES toolchain-cpp)
besa_features_default(FEATURES toolchain-cpp)
besa_configure_complete()
besa_test_add_directory(NAME test/cpp PREFIX unit LABELS unit COVERAGE_GROUP unit)
""",
        encoding="utf-8",
    )
    _run(["cmake", "-S", ".", "-B", "build", "-DCMAKE_CXX_COMPILER=clang++"], project)
    _run(["cmake", "--build", "build"], project)
    _run(["ctest", "--test-dir", "build", "--output-on-failure"], project)
    assert (project / "build" / "coverage" / "unit" / "coverage.json").is_file()
    assert (project / "build" / "coverage" / "unit" / "summary.txt").is_file()

@pytest.mark.cpp
def test_only_normal_dependencies_are_written_to_package_config(tmp_path: Path) -> None:
    if shutil.which("cmake") is None or shutil.which("g++") is None:
        pytest.skip("CMake and g++ are required")
    project = tmp_path / "dependency_export"
    project.mkdir()
    cpp_update(project)
    (project / "library.cpp").write_text("int dependency_export_value(){ return 1; }\n", encoding="utf-8")
    (project / "CMakeLists.txt").write_text(
        """\
cmake_minimum_required(VERSION 3.26.1)
project(dependency_export VERSION 1.2.3 LANGUAGES NONE)
list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa")
find_package(besa CONFIG REQUIRED)
set(PROJECT_WARNINGS "none" CACHE STRING "")
besa_features_add(FEATURES toolchain-cpp)
besa_features_default(FEATURES toolchain-cpp)
besa_configure_complete()
besa_dependency_add(NAME Threads KIND NORMAL PROVIDER CMAKE)
besa_dependency_add(NAME Git KIND BUILD PROVIDER CMAKE)
besa_add_library(NAME libdependency_export SOURCES library.cpp)
""",
        encoding="utf-8",
    )
    _run(["cmake", "-S", ".", "-B", "build"], project)
    _run(["cmake", "--build", "build"], project)
    prefix = tmp_path / "dependency_prefix"
    _run(["cmake", "--install", "build", "--prefix", str(prefix)], project)
    config = prefix / "lib" / "cmake" / "dependency_export" / "dependency_exportConfig.cmake"
    text = config.read_text(encoding="utf-8")
    assert "find_dependency(Threads)" in text
    assert "find_dependency(Git)" not in text

@pytest.mark.cpp
def test_devtool_constraint_rejects_invalid_combination(tmp_path: Path) -> None:
    project = tmp_path / "devtool_constraint"
    project.mkdir()
    cpp_update(project)
    (project / "CMakeLists.txt").write_text(
        """\
cmake_minimum_required(VERSION 3.26.1)
project(devtool_constraint LANGUAGES NONE)
list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa")
find_package(besa CONFIG REQUIRED)
set(PROJECT_DEVTOOLS "asan;coverage" CACHE STRING "")
set(PROJECT_WARNINGS "none" CACHE STRING "")

function(no_asan_and_coverage)
  besa_devtool_constraint_arguments_parse(PREFIX ARG ARGUMENTS ${ARGN})
  if("asan" IN_LIST ARG_DEVTOOLS AND "coverage" IN_LIST ARG_DEVTOOLS)
    set("${ARG_OUTPUT_VARIABLE}" FALSE PARENT_SCOPE)
    set("${ARG_ERROR_VARIABLE}" "ASan and coverage are forbidden together in this test" PARENT_SCOPE)
    return()
  endif()
  set("${ARG_OUTPUT_VARIABLE}" TRUE PARENT_SCOPE)
  set("${ARG_ERROR_VARIABLE}" "" PARENT_SCOPE)
endfunction()

besa_register_devtool_constraint(FUNCTION no_asan_and_coverage)
besa_configure_complete()
""",
        encoding="utf-8",
    )
    result = _run(["cmake", "-S", ".", "-B", "build"], project, check=False)
    assert result.returncode != 0
    assert "ASan and coverag" in result.stdout


@pytest.mark.cpp
def test_test_mode_constraint_rejects_invalid_combination(tmp_path: Path) -> None:
    project = tmp_path / "test_mode_constraint"
    project.mkdir()
    cpp_update(project)
    (project / "CMakeLists.txt").write_text(
        """\
cmake_minimum_required(VERSION 3.26.1)
project(test_mode_constraint LANGUAGES NONE)
list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa")
find_package(besa CONFIG REQUIRED)
set(PROJECT_WARNINGS "none" CACHE STRING "")

function(no_commit_and_merge)
  besa_test_mode_constraint_arguments_parse(PREFIX ARG ARGUMENTS ${ARGN})
  if("ci-commit" IN_LIST ARG_MODES AND "ci-merge" IN_LIST ARG_MODES)
    set("${ARG_OUTPUT_VARIABLE}" FALSE PARENT_SCOPE)
    set("${ARG_ERROR_VARIABLE}" "ci-commit and ci-merge are mutually exclusive in this test" PARENT_SCOPE)
    return()
  endif()
  set("${ARG_OUTPUT_VARIABLE}" TRUE PARENT_SCOPE)
  set("${ARG_ERROR_VARIABLE}" "" PARENT_SCOPE)
endfunction()

besa_test_modes_add(MODES ci-commit ci-merge)
besa_test_modes_default(MODES ci-commit)
besa_register_test_mode_constraint(FUNCTION no_commit_and_merge)
besa_configure_complete()
""",
        encoding="utf-8",
    )
    result = _run(
        ["cmake", "-S", ".", "-B", "build", "-DTEST_MODES=ci-merge"],
        project,
        check=False,
    )
    assert result.returncode != 0
    assert "ci-commit and c" in result.stdout


@pytest.mark.cpp
def test_duplicate_test_mode_override_is_an_error(tmp_path: Path) -> None:
    project = tmp_path / "duplicate_test_mode"
    project.mkdir()
    cpp_update(project)
    (project / "CMakeLists.txt").write_text(
        """\
cmake_minimum_required(VERSION 3.26.1)
project(duplicate_test_mode LANGUAGES NONE)
list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa")
find_package(besa CONFIG REQUIRED)
besa_test_modes_add(MODES ci-commit)
besa_test_modes_default(MODES ci-commit)
besa_configure_complete()
""",
        encoding="utf-8",
    )
    result = _run(
        ["cmake", "-S", ".", "-B", "build", "-DTEST_MODES=ci-commit;~ci-commit"],
        project,
        check=False,
    )
    assert result.returncode != 0
    assert "test mode 'ci-commit'" in result.stdout
    assert "TEST_MODES" in result.stdout


@pytest.mark.cpp
def test_test_registration_respects_supported_modes(tmp_path: Path) -> None:
    if shutil.which("cmake") is None or shutil.which("g++") is None:
        pytest.skip("CMake and g++ are required")
    project = tmp_path / "test_modes"
    (project / "tests").mkdir(parents=True)
    cpp_update(project)
    (project / "tests" / "hello.t.cpp").write_text("int main(){ return 0; }\n", encoding="utf-8")
    (project / "CMakeLists.txt").write_text(
        """\
cmake_minimum_required(VERSION 3.26.1)
project(test_modes LANGUAGES NONE)
list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa")
find_package(besa CONFIG REQUIRED)
set(BUILD_TESTING ON CACHE BOOL "")
set(PROJECT_WARNINGS "none" CACHE STRING "")
include(CTest)
besa_features_add(FEATURES toolchain-cpp)
besa_features_default(FEATURES toolchain-cpp)
besa_test_modes_add(MODES ci-commit ci-merge)
besa_test_modes_default(MODES ci-commit)
besa_configure_complete()
besa_test_add_directory(NAME tests PREFIX mode MODES ci-merge)
""",
        encoding="utf-8",
    )

    _run(["cmake", "-S", ".", "-B", "build/commit"], project)
    commit_tests = _run(["ctest", "--test-dir", "build/commit", "-N"], project)
    assert "mode.hello.t" not in commit_tests.stdout

    _run(
        [
            "cmake",
            "-S",
            ".",
            "-B",
            "build/merge",
            "-DTEST_MODES=ci-merge;~ci-commit",
        ],
        project,
    )
    _run(["cmake", "--build", "build/merge"], project)
    merge_tests = _run(["ctest", "--test-dir", "build/merge", "-N"], project)
    assert "mode.hello.t" in merge_tests.stdout


@pytest.mark.cpp
def test_warning_policies_are_composable(tmp_path: Path) -> None:
    if shutil.which("cmake") is None or shutil.which("g++") is None:
        pytest.skip("CMake and g++ are required")
    project = cpp_generate(tmp_path, "example_warnings")
    _run(
        [
            "cmake",
            "-S",
            ".",
            "-B",
            "build/warnings",
            "-DPROJECT_WARNINGS=essential;error",
        ],
        project,
    )
    _run(["cmake", "--build", "build/warnings"], project)


@pytest.mark.cpp
def test_toolchain_language_mapping_includes_hip_and_asm(tmp_path: Path) -> None:
    """Reserved HIP and ASM toolchain features map to the corresponding CMake languages."""
    script = tmp_path / "toolchain-language-map.cmake"
    feature_module = Path(__file__).resolve().parents[1] / "share" / "besa" / "cpp" / "cmake" / "feature.cmake"
    script.write_text(
        f'''include([[{feature_module}]])
_besa_toolchain_language("toolchain-hip" hip_language)
_besa_toolchain_language("toolchain-asm" asm_language)
if(NOT hip_language STREQUAL "HIP")
  message(FATAL_ERROR "toolchain-hip mapped to '${{hip_language}}' instead of HIP")
endif()
if(NOT asm_language STREQUAL "ASM")
  message(FATAL_ERROR "toolchain-asm mapped to '${{asm_language}}' instead of ASM")
endif()
''',
        encoding="utf-8",
    )
    _run(["cmake", "-P", str(script)], tmp_path)


@pytest.mark.cpp
def test_generated_cpp_project_can_enable_asm_toolchain(tmp_path: Path) -> None:
    """ASM is a real toolchain feature and can be enabled in a generated C++ project."""
    project = cpp_generate(tmp_path, "asmproject")
    _run(
        [
            "cmake",
            "-S",
            ".",
            "-B",
            "build-asm",
            "-DPROJECT_FEATURES=toolchain-asm",
        ],
        project,
    )

@pytest.mark.cpp
def test_generated_cpp_project_contains_properdocs_and_versioned_api_docs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util
    from types import SimpleNamespace

    project = cpp_generate(tmp_path, "example_docs")
    docs = project / "docs"
    api_docs = project / "api-docs"

    # ProperDocs owns the checked-in documentation information architecture.
    assert (project / "properdocs.yml").is_file()
    multiversion_config = project / "properdocs.multiversion.yml"
    assert multiversion_config.is_file()
    multiversion_config_text = multiversion_config.read_text(encoding="utf-8")
    assert "INHERIT: properdocs.yml" in multiversion_config_text
    assert "  - .git/refs" in multiversion_config_text
    assert "  - properdocs_multiversion_hook.py" in multiversion_config_text
    assert (project / "properdocs_multiversion_hook.py").is_file()
    assert (docs / "index.md").is_file()
    assert (docs / "reference" / "index.md").is_file()
    api_landing = docs / "reference" / "api.md"
    assert api_landing.is_file()
    assert 'fetch("versions.json")' in api_landing.read_text(encoding="utf-8")

    # Sphinx/Breathe/Exhale/Doxygen is a separate API-only source tree. Exhale owns the generated
    # entity pages; the project does not maintain a hand-selected doxygenindex list.
    assert (api_docs / "conf.py").is_file()
    assert (api_docs / "Doxyfile").is_file()
    assert (api_docs / "index.rst").is_file()
    assert (api_docs / "_static" / "css" / "besa-api.css").is_file()
    versioning = api_docs / "_templates" / "versioning.html"
    project_links = api_docs / "_templates" / "project-links.html"
    assert versioning.is_file()
    assert project_links.is_file()
    assert "Main documentation" in versioning.read_text(encoding="utf-8")
    assert "API versions" in versioning.read_text(encoding="utf-8")
    assert "Main documentation" in project_links.read_text(encoding="utf-8")
    assert not (docs / "conf.py").exists()

    conf_text = (api_docs / "conf.py").read_text(encoding="utf-8")
    assert '"breathe"' in conf_text
    assert '"exhale"' in conf_text
    assert '"sphinx_multiversion"' in conf_text
    assert 'html_theme = "pydata_sphinx_theme"' in conf_text
    assert '"containmentFolder": "./generated"' in conf_text
    assert '"rootFileName": "library_root.rst"' in conf_text
    assert 'smv_branch_whitelist = r"^.*$"' in conf_text
    assert 'smv_tag_whitelist = r"^.*$"' in conf_text
    assert 'smv_outputdir_format = r"{ref.name}"' in conf_text
    assert "BESA_PROPERDOCS_ROOT_DEPTH" in conf_text
    assert "Path(app.srcdir).resolve()" in conf_text
    assert "doxygenindex" not in (api_docs / "index.rst").read_text(encoding="utf-8")

    doxyfile_text = (api_docs / "Doxyfile").read_text(encoding="utf-8")
    assert "EXTRACT_ALL            = YES" in doxyfile_text
    assert "EXCLUDE_PATTERNS       = */bin/* */lib/*" in doxyfile_text

    css = (api_docs / "_static" / "css" / "besa-api.css").read_text(encoding="utf-8")
    assert ".bd-page-width" in css
    assert "max-width: 90rem" in css
    assert "min-width: 13rem" in css
    assert ".besa-api-project-links" in css
    assert "gap: 1.25rem" in css
    assert ".breathe-sectiondef-title" in css
    assert "font-style: normal" in css

    project_links = (api_docs / "_templates" / "project-links.html").read_text(
        encoding="utf-8"
    )
    assert 'class="navbar-item besa-api-project-links"' in project_links

    # Load conf.py without Sphinx installed. Extensions are strings; Doxygen runs only from the
    # builder callback and each real build gets its source checkout from app.srcdir.
    doxygen_base = tmp_path / "doxygen-xml"
    monkeypatch.setenv("BESA_DOXYGEN_BASE_DIRECTORY", str(doxygen_base))
    monkeypatch.setenv("BESA_PROPERDOCS_ROOT_DEPTH", "3")
    spec = importlib.util.spec_from_file_location("example_docs_conf", api_docs / "conf.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.project == "example_docs"
    assert module.release == "0.1.0"
    assert module.breathe_default_project == "example_docs"
    assert module.html_context["besa_properdocs_root_depth"] == 3

    events: dict[str, tuple[object, int]] = {}

    class FakeApp:
        def __init__(self, srcdir: Path) -> None:
            self.srcdir = str(srcdir)
            self.config = SimpleNamespace(
                version=None,
                release=None,
                breathe_projects=None,
                breathe_default_project=None,
                exhale_args=dict(module.exhale_args),
            )

        def connect(self, event: str, callback: object, priority: int = 500) -> None:
            events[event] = (callback, priority)

    current_app = FakeApp(api_docs)
    module.setup(current_app)
    callback, priority = events["builder-inited"]
    assert callback is module._prepare_api
    assert priority < 500

    fake_doxygen = tmp_path / "fake-doxygen"
    fake_doxygen.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_doxygen.chmod(0o755)
    monkeypatch.setenv("BESA_DOXYGEN_EXECUTABLE", str(fake_doxygen))
    module._prepare_api(current_app)

    current_output = module._doxygen_output_for(project)
    generated = current_output / "Doxyfile"
    generated_text = generated.read_text(encoding="utf-8")
    assert 'GENERATE_XML           = YES' in generated_text
    assert 'GENERATE_HTML          = NO' in generated_text
    assert 'PROJECT_NUMBER = "0.1.0"' in generated_text
    assert str(project / "src").replace("\\", "/") in generated_text
    assert current_app.config.release == "0.1.0"
    assert current_app.config.breathe_projects == {
        "example_docs": str(current_output / "xml")
    }
    assert current_app.config.exhale_args["containmentFolder"] == str(api_docs / "generated")
    assert current_app.config.exhale_args["doxygenStripFromPath"] == str(project)

    # Reproduce sphinx-multiversion's important shape: conf.py remains in the current checkout while
    # app.srcdir points at a different checkout. The generated Doxyfile must use only that checkout.
    historical = tmp_path / "historical"
    historical_api = historical / "api-docs"
    historical_api.mkdir(parents=True)
    (historical / "src").mkdir()
    (historical / "CMakeLists.txt").write_text(
        "project(example_docs VERSION 9.8.7 LANGUAGES NONE)\n", encoding="utf-8"
    )
    (historical_api / "Doxyfile").write_text(
        (api_docs / "Doxyfile").read_text(encoding="utf-8"), encoding="utf-8"
    )

    historical_app = FakeApp(historical_api)
    module._prepare_api(historical_app)
    historical_output = module._doxygen_output_for(historical)
    historical_text = (historical_output / "Doxyfile").read_text(encoding="utf-8")
    assert 'PROJECT_NUMBER = "9.8.7"' in historical_text
    assert str(historical / "src").replace("\\", "/") in historical_text
    assert str(project / "src").replace("\\", "/") not in historical_text
    assert historical_app.config.release == "9.8.7"
    assert historical_app.config.breathe_projects == {
        "example_docs": str(historical_output / "xml")
    }
    assert historical_app.config.exhale_args["containmentFolder"] == str(
        historical_api / "generated"
    )
    assert historical_app.config.exhale_args["doxygenStripFromPath"] == str(historical)
    assert str(project / "api-docs" / "generated") not in historical_app.config.exhale_args.values()


@pytest.mark.cpp
def test_generated_cpp_combined_docs_build_when_toolchain_is_available(tmp_path: Path) -> None:
    required = (
        "cmake",
        "g++",
        "git",
        "doxygen",
        "dot",
        "properdocs",
        "sphinx-build",
        "sphinx-multiversion",
    )
    if any(shutil.which(tool) is None for tool in required):
        pytest.skip("ProperDocs, Doxygen, Sphinx, Breathe, sphinx-multiversion, Git, and CMake are required")

    extensions = subprocess.run(
        [
            sys.executable,
            "-c",
            "import breathe, exhale, pydata_sphinx_theme, sphinx_multiversion",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if extensions.returncode != 0:
        pytest.skip("Breathe, Exhale, PyData Sphinx Theme, and sphinx-multiversion are required")

    project = cpp_generate(tmp_path, "example_multidocs")
    _run(["git", "init", "-b", "main"], project)
    _run(["git", "config", "user.email", "besa-test@example.invalid"], project)
    _run(["git", "config", "user.name", "BESA Test"], project)
    _run(["git", "config", "commit.gpgSign", "false"], project)
    _run(["git", "config", "tag.gpgSign", "false"], project)
    _run(["git", "add", "."], project)
    _run(["git", "commit", "-m", "initial"], project)
    _run(["git", "tag", "v0.1.0"], project)

    # Add an API symbol only after v0.1.0. The old tag must never see this declaration even though
    # sphinx-multiversion uses the current checkout's conf.py as its configuration directory.
    header = project / "src" / "cpp" / "include" / "example_multidocs" / "example_multidocs.hpp"
    header.write_text(
        header.read_text(encoding="utf-8")
        + "\n/// API introduced in v0.2.0.\ninline int future_api() { return 2; }\n",
        encoding="utf-8",
    )
    cmake_lists = project / "CMakeLists.txt"
    cmake_lists.write_text(
        cmake_lists.read_text(encoding="utf-8").replace(
            "project(example_multidocs VERSION 0.1.0",
            "project(example_multidocs VERSION 0.2.0",
        ),
        encoding="utf-8",
    )
    _run(["git", "add", "CMakeLists.txt", str(header.relative_to(project))], project)
    _run(["git", "commit", "-m", "add future API"], project)
    _run(["git", "tag", "v0.2.0"], project)
    _run(["git", "branch", "docs-branch"], project)

    configured = _run(
        [
            "cmake",
            "-S",
            ".",
            "-B",
            "build/docs",
            "-DPROJECT_FEATURES=user-docs",
            "-DPROJECT_WARNINGS=none",
        ],
        project,
        check=False,
    )
    if configured.returncode != 0 and "breathe" in configured.stdout.lower():
        pytest.skip("Breathe is not available to the Sphinx installation")
    assert configured.returncode == 0, configured.stdout

    # The raw multiversion target remains useful for API debugging.
    _run(["cmake", "--build", "build/docs", "--target", "user.docs.multiversion"], project)
    raw_api = project / "build" / "docs" / "doc" / "api" / "multiversion"
    assert (raw_api / "main" / "index.html").is_file()
    assert (raw_api / "docs-branch" / "index.html").is_file()
    assert (raw_api / "v0.1.0" / "index.html").is_file()
    assert (raw_api / "v0.2.0" / "index.html").is_file()
    assert (raw_api / "versions.json").is_file()
    assert not (raw_api / "index.html").exists()

    def html_text(directory: Path) -> str:
        return "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in directory.rglob("*.html")
        )

    assert "future_api" not in html_text(raw_api / "v0.1.0")
    assert "future_api" in html_text(raw_api / "v0.2.0")
    assert "future_api" in html_text(raw_api / "main")

    # Exhale should produce a structured API tree rather than one monolithic doxygenindex page.
    assert (raw_api / "main" / "generated" / "library_root.html").is_file()
    assert any((raw_api / "main" / "generated").glob("namespace_*.html")) or any(
        (raw_api / "main" / "generated").glob("file_*.html")
    )

    # user.docs is the publication target: ProperDocs at the root, API versions below reference/api.
    _run(["cmake", "--build", "build/docs", "--target", "user.docs"], project)
    site = project / "build" / "docs" / "doc" / "site"
    assert (site / "index.html").is_file()
    assert (site / "reference" / "api" / "index.html").is_file()
    assert (site / "reference" / "api" / "versions.json").is_file()
    assert (site / "reference" / "api" / "main" / "index.html").is_file()
    assert (site / "reference" / "api" / "docs-branch" / "index.html").is_file()
    assert (site / "reference" / "api" / "v0.1.0" / "index.html").is_file()
    assert (site / "reference" / "api" / "v0.2.0" / "index.html").is_file()
    assert (site / ".nojekyll").is_file()

    # A full CMake install also installs the normal project targets. The documentation targets above
    # do not build those targets as a side effect, so build the ordinary project before exercising
    # the complete install path.
    _run(["cmake", "--build", "build/docs"], project)

    prefix = tmp_path / "docs-prefix"
    _run(["cmake", "--install", "build/docs", "--prefix", str(prefix)], project)
    installed_docs = prefix / "share" / "doc" / "example_multidocs"
    assert (installed_docs / "index.html").is_file()
    assert (installed_docs / "reference" / "api" / "index.html").is_file()
    assert (installed_docs / "reference" / "api" / "main" / "index.html").is_file()


@pytest.mark.cpp
def test_configure_prints_resolved_besa_configuration(tmp_path: Path) -> None:
    project = tmp_path / "configuration_summary"
    project.mkdir()
    cpp_update(project)
    (project / "CMakeLists.txt").write_text(
        """\
cmake_minimum_required(VERSION 3.26.1)
project(configuration_summary VERSION 1.2.3 LANGUAGES NONE)
list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa")
find_package(besa CONFIG REQUIRED)
set(PROJECT_DEVTOOLS "none" CACHE STRING "")
set(PROJECT_WARNINGS "none" CACHE STRING "")
set(BUILD_TESTING ON CACHE BOOL "")
include(CTest)
besa_features_add(FEATURES alpha)
besa_features_default(FEATURES alpha)
besa_test_modes_add(MODES ci-commit)
besa_test_modes_default(MODES ci-commit)
besa_configure_complete()
""",
        encoding="utf-8",
    )

    result = _run(["cmake", "-S", ".", "-B", "build", "-DRELEASE_TYPE=release"], project)
    assert "-- BESA configuration:" in result.stdout
    assert "Features      : alpha" in result.stdout
    assert "Devtools      : none" in result.stdout
    assert "Warning policy: none" in result.stdout
    assert "Test modes    : ci-commit" in result.stdout
    assert "Languages     : none" in result.stdout
    assert "Build testing : ON" in result.stdout
    assert "Release type  : release" in result.stdout
    assert "Version       : 1.2.3" in result.stdout


@pytest.mark.cpp
def test_multiversion_api_metadata_is_generated(tmp_path: Path) -> None:
    output = tmp_path / "api"
    for version in ("main", "1.0.0", "2.0.0", "release/3.0"):
        (output / version / "_static").mkdir(parents=True)
        (output / version / "index.html").write_text(version, encoding="utf-8")

    script = (
        Path(__file__).resolve().parents[1]
        / "share"
        / "besa"
        / "cpp"
        / "cmake"
        / "userdocs"
        / "multiversion-metadata.cmake"
    )
    _run(
        [
            "cmake",
            f"-DOUTPUT_DIRECTORY={output}",
            "-DDEFAULT_VERSION=main",
            "-P",
            str(script),
        ],
        tmp_path,
    )

    # A nested API page named index.html must not be mistaken for another ref.
    (output / "main" / "detail").mkdir()
    (output / "main" / "detail" / "index.html").write_text("detail", encoding="utf-8")

    import json

    metadata = json.loads((output / "versions.json").read_text(encoding="utf-8"))
    assert metadata["default"] == "main"
    assert metadata["versions"][0] == {"name": "main", "url": "main/"}
    assert {item["name"] for item in metadata["versions"]} == {
        "main",
        "1.0.0",
        "2.0.0",
        "release/3.0",
    }
    assert "main/detail" not in {item["name"] for item in metadata["versions"]}
    assert not (output / "index.html").exists()


@pytest.mark.cpp
def test_user_docs_assembly_keeps_properdocs_root_and_api_landing(tmp_path: Path) -> None:
    properdocs = tmp_path / "properdocs"
    api = tmp_path / "api"
    output = tmp_path / "site"

    (properdocs / "reference" / "api").mkdir(parents=True)
    (properdocs / "index.html").write_text("properdocs-home", encoding="utf-8")
    (properdocs / "reference" / "api" / "index.html").write_text(
        "properdocs-api-landing", encoding="utf-8"
    )
    (api / "main").mkdir(parents=True)
    (api / "main" / "index.html").write_text("api-main", encoding="utf-8")
    (api / "versions.json").write_text('{"default":"main","versions":[]}', encoding="utf-8")

    script = (
        Path(__file__).resolve().parents[1]
        / "share"
        / "besa"
        / "cpp"
        / "cmake"
        / "userdocs"
        / "assemble-site.cmake"
    )
    _run(
        [
            "cmake",
            f"-DPROPERDOCS_DIRECTORY={properdocs}",
            f"-DAPI_DIRECTORY={api}",
            f"-DOUTPUT_DIRECTORY={output}",
            "-DAPI_PATH=reference/api",
            "-P",
            str(script),
        ],
        tmp_path,
    )

    assert (output / "index.html").read_text(encoding="utf-8") == "properdocs-home"
    assert (
        output / "reference" / "api" / "index.html"
    ).read_text(encoding="utf-8") == "properdocs-api-landing"
    assert (output / "reference" / "api" / "main" / "index.html").is_file()
    assert (output / "reference" / "api" / "versions.json").is_file()
    assert (output / ".nojekyll").is_file()

@pytest.mark.cpp
def test_generated_cpp_spack_environment_uses_amstack_and_local_dev_bundle(
    tmp_path: Path,
) -> None:
    project = cpp_generate(tmp_path, "example")

    manifest = (project / "spack.yaml").read_text(encoding="utf-8")
    assert "https://github.com/ambhora/amstack.git" in manifest
    assert "branch: main" in manifest
    assert "dev: spack/spack_repo/dev" in manifest
    assert "- example@main" not in manifest
    assert "dev-env@1.1 +docs +tests" in manifest
    assert "develop:" not in manifest
    assert "spack/repos.yaml" not in manifest
    assert "BESA_FEATURES" not in manifest
    assert not (project / "pyproject.toml").exists()
    assert not (project / "spack" / "repos.yaml").exists()

    repo = project / "spack" / "spack_repo" / "dev"
    assert (repo / "repo.yaml").is_file()
    assert "namespace: dev" in (repo / "repo.yaml").read_text(encoding="utf-8")

    environment_package = (
        repo / "packages" / "dev_env" / "package.py"
    ).read_text(encoding="utf-8")
    assert "from spack_repo.builtin.build_systems.bundle import BundlePackage" in environment_package
    assert "class DevEnv(BundlePackage):" in environment_package
    assert 'version("1.1")' in environment_package
    for variant in ("docs", "tests", "coverage", "cuda", "hip"):
        assert f'variant("{variant}"' in environment_package
    assert 'depends_on("doxygen", when="+docs")' in environment_package
    assert 'depends_on("py-sphinx@:8", when="+docs")' in environment_package
    assert 'depends_on("py-breathe", when="+docs")' in environment_package
    assert 'depends_on("py-exhale", when="+docs")' in environment_package
    assert 'depends_on("py-pydata-sphinx-theme", when="+docs")' in environment_package
    assert 'depends_on("py-sphinx-multiversion", when="+docs")' in environment_package
    assert 'depends_on("properdocs", when="+docs")' in environment_package
    assert 'depends_on("cuda", when="+cuda")' in environment_package
    assert 'depends_on("hip", when="+hip")' in environment_package
    assert not (repo / "packages" / "properdocs").exists()

    compile(environment_package, "dev_env/package.py", "exec")


@pytest.mark.cpp
def test_generated_properdocs_serve_hook_rebuilds_current_api_without_env_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util
    import json

    project = cpp_generate(tmp_path, "example_serve_docs")
    hook_path = project / "properdocs_hook.py"
    assert hook_path.is_file()

    config_text = (project / "properdocs.yml").read_text(encoding="utf-8")
    assert "watch:" in config_text
    assert "  - src" in config_text
    assert "  - api-docs" in config_text
    assert "hooks:" in config_text
    assert "  - properdocs_hook.py" in config_text

    spec = importlib.util.spec_from_file_location("example_serve_docs_hook", hook_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        commands.append(list(command))
        return None

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    module._build_current_api()
    assert any("-DPROJECT_FEATURES=user-docs" in item for item in commands[0])
    assert commands[1][-1] == "user.docs.api"

    fake_api = tmp_path / "current-api"
    fake_api.mkdir()
    (fake_api / "index.html").write_text("current-api", encoding="utf-8")
    module.API_BUILD_DIRECTORY = fake_api

    site = tmp_path / "served-site"
    (site / "reference" / "api").mkdir(parents=True)
    (site / "reference" / "api" / "index.html").write_text(
        "properdocs-api-landing", encoding="utf-8"
    )
    module._publish_current_api(site)

    assert (site / "reference" / "api" / "index.html").read_text(
        encoding="utf-8"
    ) == "properdocs-api-landing"
    assert (site / "reference" / "api" / "main" / "index.html").read_text(
        encoding="utf-8"
    ) == "current-api"
    metadata = json.loads(
        (site / "reference" / "api" / "versions.json").read_text(encoding="utf-8")
    )
    assert metadata == {
        "default": "main",
        "versions": [{"name": "main", "url": "main/"}],
    }

    module.on_startup(command="build")
    assert module._serve_active is False
    module.on_startup(command="serve")
    assert module._serve_active is True


@pytest.mark.cpp
def test_generated_properdocs_hook_fingerprints_api_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.util

    project = cpp_generate(tmp_path, "example_watch_docs")
    hook_path = project / "properdocs_hook.py"
    spec = importlib.util.spec_from_file_location("example_watch_docs_hook", hook_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    fake_api = tmp_path / "current-api"
    fake_api.mkdir()
    module.API_BUILD_DIRECTORY = fake_api

    builds = 0

    def fake_build() -> None:
        nonlocal builds
        builds += 1

    monkeypatch.setattr(module, "_build_current_api", fake_build)
    module._last_source_fingerprint = None
    module._ensure_current_api()
    module._ensure_current_api()
    assert builds == 1

    source = project / "src" / "cpp" / "include" / "example_watch_docs" / "example_watch_docs.hpp"
    source.write_text(source.read_text(encoding="utf-8") + "\n// docs changed\n", encoding="utf-8")
    module._ensure_current_api()
    assert builds == 2


@pytest.mark.cpp
def test_generated_properdocs_multiversion_serve_hook_overlays_live_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util
    import json

    project = cpp_generate(tmp_path, "example_multi_serve")
    hook_path = project / "properdocs_multiversion_hook.py"
    spec = importlib.util.spec_from_file_location("example_multi_serve_hook", hook_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        commands.append(list(command))
        return None

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    module._configure()
    module._build("user.docs.multiversion")
    module._build("user.docs.api")
    assert any("-DPROJECT_FEATURES=user-docs" in item for item in commands[0])
    assert commands[1][-1] == "user.docs.multiversion"
    assert commands[2][-1] == "user.docs.api"

    raw_versions = tmp_path / "raw-versions"
    (raw_versions / "main").mkdir(parents=True)
    (raw_versions / "1.0.0").mkdir()
    (raw_versions / "main" / "index.html").write_text("committed-main", encoding="utf-8")
    (raw_versions / "1.0.0" / "index.html").write_text("one", encoding="utf-8")
    (raw_versions / "versions.json").write_text(
        json.dumps(
            {
                "default": "main",
                "versions": [
                    {"name": "main", "url": "main/"},
                    {"name": "1.0.0", "url": "1.0.0/"},
                ],
            }
        ),
        encoding="utf-8",
    )

    current = tmp_path / "current"
    current.mkdir()
    (current / "index.html").write_text("working-tree-main", encoding="utf-8")
    module.MULTIVERSION_API_BUILD_DIRECTORY = raw_versions
    module.CURRENT_API_BUILD_DIRECTORY = current

    site = tmp_path / "site"
    api_root = site / "reference" / "api"
    api_root.mkdir(parents=True)
    (api_root / "index.html").write_text("properdocs-api-landing", encoding="utf-8")
    (api_root / "stale-version").mkdir()

    module._publish_multiversion_api(site)

    assert (api_root / "index.html").read_text(encoding="utf-8") == "properdocs-api-landing"
    assert (api_root / "main" / "index.html").read_text(encoding="utf-8") == "working-tree-main"
    assert (api_root / "1.0.0" / "index.html").read_text(encoding="utf-8") == "one"
    assert not (api_root / "stale-version").exists()
    metadata = json.loads((api_root / "versions.json").read_text(encoding="utf-8"))
    assert metadata["default"] == "main"
    assert metadata["versions"][0] == {"name": "main", "url": "main/"}
    assert (site / ".nojekyll").is_file()

    module.on_startup(command="build")
    assert module._serve_active is False
    module.on_startup(command="serve")
    assert module._serve_active is True


@pytest.mark.cpp
def test_generated_properdocs_multiversion_hook_rebuilds_refs_and_current_independently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util

    project = cpp_generate(tmp_path, "example_multi_watch")
    hook_path = project / "properdocs_multiversion_hook.py"
    spec = importlib.util.spec_from_file_location("example_multi_watch_hook", hook_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    current = tmp_path / "current"
    versions = tmp_path / "versions"
    current.mkdir()
    versions.mkdir()
    module.CURRENT_API_BUILD_DIRECTORY = current
    module.MULTIVERSION_API_BUILD_DIRECTORY = versions

    source_state = [[("src/a.hpp", 1, 1)]]
    refs_state = [[(".git/refs/heads/main", 1, 1)]]
    monkeypatch.setattr(module, "_source_fingerprint", lambda: tuple(source_state[0]))
    monkeypatch.setattr(module, "_refs_fingerprint", lambda: tuple(refs_state[0]))

    configured = 0
    targets: list[str] = []

    def fake_configure() -> None:
        nonlocal configured
        configured += 1

    monkeypatch.setattr(module, "_configure", fake_configure)
    monkeypatch.setattr(module, "_build", targets.append)

    module._ensure_multiversion_api()
    assert configured == 1
    assert targets == ["user.docs.multiversion", "user.docs.api"]

    module._ensure_multiversion_api()
    assert configured == 1

    source_state[0] = [("src/a.hpp", 2, 1)]
    module._ensure_multiversion_api()
    assert configured == 2
    assert targets[-1] == "user.docs.api"

    refs_state[0] = [(".git/refs/heads/main", 2, 1)]
    module._ensure_multiversion_api()
    assert configured == 3
    assert targets[-1] == "user.docs.multiversion"


@pytest.mark.cpp
def test_generated_cpp_license_headers_use_only_spdx_identifier(tmp_path: Path) -> None:
    project = cpp_generate(tmp_path, "example_license", "MIT")
    spdx_files: list[Path] = []

    for path in project.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "SPDX-License-Identifier:" not in text:
            continue

        spdx_files.append(path)
        if "cmake/besa" not in path.as_posix():
            assert "SPDX-License-Identifier: MIT" in text
        assert "SPDX-FileCopyrightText:" not in text
        assert "Copyright (C)" not in text

    assert spdx_files


@pytest.mark.cpp
def test_generated_cpp_project_ignores_spack_work_state_and_python_caches(tmp_path: Path) -> None:
    project = cpp_generate(tmp_path, "example_ignore")
    gitignore = (project / ".gitignore").read_text(encoding="utf-8")

    assert ".spack-env/" in gitignore
    assert "__pycache__/" in gitignore
    assert "*.py[cod]" in gitignore
    assert "/api-docs/generated/" in gitignore
    ignored_entries = {line.strip() for line in gitignore.splitlines() if line.strip() and not line.startswith("#")}
    assert "spack.yaml" not in ignored_entries
    assert "spack.lock" not in ignored_entries
    assert "spack/" not in ignored_entries
