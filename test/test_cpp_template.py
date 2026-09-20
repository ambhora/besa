# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
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
    assert (project / "build" / preset / f"example_{preset}").exists()

    if preset == "clang":
        compile_commands = (project / "build" / preset / "compile_commands.json").read_text(
            encoding="utf-8"
        )
        assert "-fcomment-block-commands=projectdocs" in compile_commands


@pytest.mark.cpp
def test_generated_cpp_project_groups_library_sources_by_library(tmp_path: Path) -> None:
    project = cpp_generate(tmp_path, "example_layout")

    cpp_library = project / "src" / "cpp" / "lib" / "example_layout"
    assert (cpp_library / "example_layout.cpp").is_file()
    assert not (project / "src" / "cpp" / "lib" / "example_layout.cpp").exists()

    source_roots = {path.name for path in (project / "src").iterdir() if path.is_dir()}
    assert source_roots == {"cpp"}

    root_cmake = (project / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "set(CMAKE_EXPORT_COMPILE_COMMANDS ON)" in root_cmake
    assert "besa_model_realize" in root_cmake
    model = (project / "besa.toml").read_text(encoding="utf-8")
    for feature in ("toolchain-cpp", "toolchain-cuda", "toolchain-hip"):
        assert f"[features.{feature}]" in model
    for feature in ("toolchain-c", "toolchain-asm"):
        assert f"[features.{feature}]" not in model

    dev_env = (
        project / "spack" / "spack_repo" / "dev" / "packages" / "dev_env" / "package.py"
    ).read_text(encoding="utf-8")
    assert 'variant("hip"' not in dev_env
    assert 'depends_on("hip"' not in dev_env


@pytest.mark.cpp
def test_generated_cpp_project_vendors_and_builds_prova_support(tmp_path: Path) -> None:
    if shutil.which("cmake") is None or shutil.which("g++") is None:
        pytest.skip("CMake and g++ are required")

    project = cpp_generate(tmp_path, "example_prova")
    base = project / "test" / "base"
    assert (base / "CMakeLists.txt").is_file()
    cuda_variant = base / "cuda" / "include" / "testexample_prova" / "cuda_variant.hpp"
    assert cuda_variant.is_file()
    assert "cuda_variant_only" in cuda_variant.read_text(encoding="utf-8")
    catch_main = base / "cpp" / "include" / "testexample_prova" / "prova" / "catch_main.hpp"
    assert catch_main.is_file()
    catch_main_text = catch_main.read_text(encoding="utf-8")
    assert "#define TESTEXAMPLE_PROVA_PROVA_CATCH_MAIN" in catch_main_text
    assert "#define TESTEXAMPLE_PROVA_PROVA_CATCH_GROUP" in catch_main_text
    assert "#define PROVA_CATCH_MAIN" not in catch_main_text
    assert "#define PROVA_CATCH_GROUP" not in catch_main_text
    assert "MOL_CATCH" not in catch_main_text

    unit_main = project / "test" / "unit" / "cpp" / "main.cpp"
    assert unit_main.is_file()
    assert 'TESTEXAMPLE_PROVA_PROVA_CATCH_MAIN("unit")' in unit_main.read_text(encoding="utf-8")
    assert "Catch2::Catch2WithMain" not in (project / "test" / "CMakeLists.txt").read_text(
        encoding="utf-8"
    )

    # Configure against a minimal Catch2 package so this test checks that the vendored Prova target
    # is structurally complete without requiring Catch2 to be installed in BESA's own test runner.
    catch2_prefix = tmp_path / "catch2"
    catch2_cmake = catch2_prefix / "lib" / "cmake" / "Catch2"
    catch2_include = catch2_prefix / "include" / "catch2"
    catch2_cmake.mkdir(parents=True)
    catch2_include.mkdir(parents=True)
    (catch2_cmake / "Catch2Config.cmake").write_text(
        f'''\
add_library(Catch2::Catch2 INTERFACE IMPORTED)
set_target_properties(Catch2::Catch2 PROPERTIES
  INTERFACE_INCLUDE_DIRECTORIES [[{catch2_prefix / "include"}]]
)
''',
        encoding="utf-8",
    )
    (catch2_cmake / "Catch2ConfigVersion.cmake").write_text(
        '''\
set(PACKAGE_VERSION "3.0.0")
set(PACKAGE_VERSION_COMPATIBLE TRUE)
set(PACKAGE_VERSION_EXACT FALSE)
''',
        encoding="utf-8",
    )
    (catch2_include / "catch_session.hpp").write_text(
        '''\
#pragma once
namespace Catch {
class Session {
public:
  int applyCommandLine(int, char const* const*) { return 0; }
  int run() { return 0; }
};
} // namespace Catch
''',
        encoding="utf-8",
    )
    (catch2_include / "catch_test_macros.hpp").write_text(
        '''\
#pragma once
#define TEST_CASE(...) static void test_case()
#define REQUIRE(...) do { } while (false)
#define FAIL(...) do { } while (false)
''',
        encoding="utf-8",
    )

    prova_main = base / "prova_main.cpp"
    prova_main.write_text(
        "#include <testexample_prova/prova/catch_main.hpp>\nTESTEXAMPLE_PROVA_PROVA_CATCH_MAIN(\"smoke\")\n",
        encoding="utf-8",
    )
    with (project / "test" / "CMakeLists.txt").open("a", encoding="utf-8") as cmake_file:
        cmake_file.write(
            "\nbesa_add_executable(\n"
            "  NAME prova.runner.t\n"
            "  INSTALL FALSE\n"
            "  SOURCES base/prova_main.cpp\n"
            "  LINK_LIBRARIES example_prova.test.runtime\n"
            ")\n"
        )

    _run(
        [
            "cmake",
            "-S",
            ".",
            "-B",
            "build/prova",
            "-DBUILD_TESTING=ON",
            "-DPROJECT_WARNINGS=none",
            f"-DCMAKE_PREFIX_PATH={catch2_prefix}",
        ],
        project,
    )
    _run(["cmake", "--build", "build/prova", "--target", "libtestexample_prova"], project)
    _run(["cmake", "--build", "build/prova", "--target", "prova.runner.t"], project)
    _run(["cmake", "--build", "build/prova", "--target", "unit.version.t"], project)
    _run(
        ["ctest", "--test-dir", "build/prova", "-R", "^unit.version.t$", "--output-on-failure"],
        project,
    )


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
        "#include <example_install/example_install.hpp>\n"
        "int main(){constexpr auto v = example_install::meta::version(); "
        "static_assert(v.major == 0 && v.minor == 1 && v.patch == 0); return 0;}\n",
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
            "-DPKGBUILDER_ID=spack",
            "-DPKGBUILDER_REVISION=7",
        ],
        project,
    )
    version_header = project / "build" / "codegen" / "meta" / "include" / "example_version" / "version.hpp"
    version_text = version_header.read_text(encoding="utf-8")
    assert "#ifndef EXAMPLE_VERSION_VERSION_HPP" in version_text
    assert "#define EXAMPLE_VERSION_VERSION_HPP" in version_text
    assert "#pragma once" not in version_text
    assert "namespace example_version::meta" in version_text
    assert "struct semantic_version" in version_text
    assert "struct release_info" in version_text
    assert "struct package_info" in version_text
    assert "struct build_info" in version_text
    assert "Project major version generated for this artifact" in version_text
    assert "Project tweak version generated for this artifact" in version_text
    assert 'release_type::release_candidate, // Release channel generated for this artifact.' in version_text
    assert '3,     // Release revision generated for this artifact.' in version_text
    assert '"spack",       // Package builder recorded for this artifact.' in version_text
    assert '"7", // Packaging revision recorded for this artifact.' in version_text
    assert 'return "0.1.0";' in version_text
    assert 'return "rc.3";' in version_text


@pytest.mark.cpp
def test_generated_include_registry_attaches_and_installs_all_generators(tmp_path: Path) -> None:
    if shutil.which("cmake") is None or shutil.which("g++") is None:
        pytest.skip("CMake and g++ are required")

    project = cpp_generate(tmp_path, "example_generated")
    cmake = project / "CMakeLists.txt"
    text = cmake.read_text(encoding="utf-8")
    generator_script = project / "generate-schema.cmake"
    generator_script.write_text(
        "get_filename_component(OUTPUT_DIRECTORY \"${OUTPUT}\" DIRECTORY)\n"
        "file(MAKE_DIRECTORY \"${OUTPUT_DIRECTORY}\")\n"
        "file(WRITE \"${OUTPUT}\" \"#ifndef EXAMPLE_GENERATED_SCHEMA_HPP\\n#define EXAMPLE_GENERATED_SCHEMA_HPP\\n#endif\\n\")\n",
        encoding="utf-8",
    )
    insertion = """\
besa_generated_include_add(NAME schema TARGET schema.generate OUTPUT_VARIABLE SCHEMA_INCLUDE)
add_custom_target(
  schema.generate
  COMMAND "${CMAKE_COMMAND}"
    "-DOUTPUT=${SCHEMA_INCLUDE}/example_generated/schema.hpp"
    -P "${CMAKE_CURRENT_SOURCE_DIR}/generate-schema.cmake"
  VERBATIM
)

"""
    text += "\n" + insertion
    cmake.write_text(text, encoding="utf-8")

    _run(["cmake", "-S", ".", "-B", "build/generated"], project)

    meta_root = project / "build" / "codegen" / "meta" / "include"
    schema_root = project / "build" / "codegen" / "schema" / "include"
    assert (meta_root / "example_generated" / "version.hpp").is_file()
    assert not (schema_root / "example_generated" / "schema.hpp").exists()

    commands = (project / "build" / "generated" / "compile_commands.json").read_text(
        encoding="utf-8"
    )
    assert str(meta_root) in commands
    assert str(schema_root) in commands

    _run(["cmake", "--build", "build/generated"], project)
    assert (schema_root / "example_generated" / "schema.hpp").is_file()
    prefix = tmp_path / "generated-prefix"
    _run(
        ["cmake", "--install", "build/generated", "--prefix", str(prefix)],
        project,
    )
    assert (prefix / "include" / "example_generated" / "version.hpp").is_file()
    assert (prefix / "include" / "example_generated" / "schema.hpp").is_file()


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
def test_generated_cpp_project_contains_properdocs_and_versioned_api_docs(
    tmp_path: Path,
) -> None:
    project = cpp_generate(tmp_path, "example_docs")
    docs = project / "docs"
    api_docs = project / "api-docs"

    # The project site and API reference are deliberately separate ProperDocs sites. The former is
    # non-versioned; the latter is generated per Git ref and mounted below reference/api/.
    assert (project / "properdocs.yml").is_file()
    assert (project / "properdocs.multiversion.yml").is_file()
    assert (project / "properdocs_multiversion_hook.py").is_file()
    assert (docs / "index.md").is_file()
    reference_landing = docs / "reference" / "index.md"
    assert reference_landing.is_file()
    reference_text = reference_landing.read_text(encoding="utf-8")
    assert "## Versioned API" in reference_text
    assert "separate ProperDocs site" in reference_text
    assert "compiler-semantic API with Clang" in reference_text

    contributing = docs / "contributing.md"
    assert contributing.is_file()
    contributing_text = contributing.read_text(encoding="utf-8")
    assert "# Contributing" in contributing_text
    assert "## Documentation" in contributing_text
    assert "## Software" in contributing_text
    assert "### License Compliance" in contributing_text
    assert "REUSE Specification" in contributing_text
    assert "Developer Certificate of Origin (DCO) 1.1" in contributing_text
    assert "Signed-off-by: Name <email@example.com>" in contributing_text

    properdocs_config = (project / "properdocs.yml").read_text(encoding="utf-8")
    assert "- content.action.edit" in properdocs_config
    assert "- Contributing: contributing.md" in properdocs_config
    assert "second, versioned ProperDocs site" in properdocs_config
    for page in (
        "tutorials/index.md",
        "how-to/index.md",
        "explanations/index.md",
        "showcases/index.md",
        "blog/index.md",
        "users.md",
        "cite-us.md",
        "about/index.md",
    ):
        assert (docs / page).is_file()

    # besa.toml remains the authoritative declaration of API profiles. The semantic C++ backend
    # realizes each selected profile through CMake and asks Clang what API exists in that concrete
    # compilation environment.
    model = (project / "besa.toml").read_text(encoding="utf-8")
    assert "schema = 1" in model
    assert '[project]\nname = "example_docs"\nversion = "0.1.0"' in model
    for profile in ("cpu", "cuda", "hip"):
        assert f"[api.profiles.{profile}]" in model
    assert 'path = "src/cpp"' in model
    assert 'api = "public"' in model
    assert 'when = { all = ["user-docs"] }' in model
    assert 'name = "Doxygen"' not in model

    backend = project / "cmake" / "besa" / "userdocs" / "api_reference"
    for module in (
        "__main__.py",
        "model.py",
        "clang_backend.py",
        "cpp_backend.py",
        "python_backend.py",
        "rust_backend.py",
        "render.py",
        "versioning.py",
    ):
        assert (backend / module).is_file()

    api_cmake = (project / "cmake" / "besa" / "userdocs.cmake").read_text(encoding="utf-8")
    for needle in (
        "function(besa_add_semantic_api_docs)",
        "BESA_API_PROFILES",
        "-m api_reference build-cpp",
        "-m api_reference build-versions",
        "Generating semantic C++ API documentation with Clang and ProperDocs",
        "besa_add_semantic_api_docs(",
    ):
        assert needle in api_cmake

    # The shared API layout is language-neutral. C++, Python, and Rust all render through these
    # ProperDocs assets rather than through Sphinx/Breathe/Exhale presentation machinery.
    api_template = api_docs / "properdocs"
    api_css = (api_template / "assets" / "stylesheets" / "besa-api.css").read_text(
        encoding="utf-8"
    )
    api_js = (api_template / "assets" / "javascripts" / "besa-api.js").read_text(
        encoding="utf-8"
    )
    assert ".md-sidebar--primary" in api_css
    assert ".md-sidebar--secondary" in api_css
    assert ".besa-api-entity-card" in api_css
    assert "Outline" in api_js
    assert "Project documentation" in api_js
    assert "versionRoot" in api_js

    docs_cmake = (docs / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "besa_add_user_docs(" in docs_cmake
    assert "API_PATH reference/api" in docs_cmake


@pytest.mark.cpp
def test_generated_cpp_combined_docs_build_when_toolchain_is_available(tmp_path: Path) -> None:
    required = ("cmake", "g++", "git", "clang++", "properdocs")
    if any(shutil.which(tool) is None for tool in required):
        pytest.skip("ProperDocs, Clang, Git, and CMake are required")

    project = cpp_generate(tmp_path, "example_multidocs")
    _run(["git", "init", "-b", "main"], project)
    _run(["git", "config", "user.email", "besa-test@example.invalid"], project)
    _run(["git", "config", "user.name", "BESA Test"], project)
    _run(["git", "config", "commit.gpgSign", "false"], project)
    _run(["git", "config", "tag.gpgSign", "false"], project)
    _run(["git", "add", "."], project)
    _run(["git", "commit", "-m", "initial"], project)
    _run(["git", "tag", "v0.1.0"], project)

    # Add an API symbol only after v0.1.0. Historical sites are rebuilt from detached Git worktrees,
    # so the old tag must retain its own compiler-semantic API rather than seeing the current tree.
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

    # Restrict this smoke test to the CPU profile so it does not require optional CUDA/HIP
    # toolchains. Publication builds normally leave BESA_API_PROFILES empty and realize all profiles.
    _run(
        [
            "cmake",
            "-S",
            ".",
            "-B",
            "build/docs",
            "-DPROJECT_FEATURES=user-docs",
            "-DPROJECT_WARNINGS=none",
            "-DBESA_API_PROFILES=cpu",
        ],
        project,
    )

    # The raw multiversion target is a collection of independent ProperDocs API sites plus metadata;
    # it deliberately has no publication-root index.html.
    _run(["cmake", "--build", "build/docs", "--target", "user.docs.multiversion"], project)
    raw_api = project / "build" / "docs" / "doc" / "api" / "multiversion"
    assert (raw_api / "main" / "index.html").is_file()
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

    # Source locations use the public include namespace rather than leaking repository/build paths.
    main_api_text = html_text(raw_api / "main")
    assert "version.hpp" in main_api_text
    assert "example_multidocs/example_multidocs.hpp" in main_api_text
    assert "src/cpp/include" not in main_api_text

    # Semantic symbol aliases are emitted directly by the common renderer, without a Sphinx domain.
    assert (raw_api / "main" / "_symbols" / "future_api" / "index.html").is_file()

    # user.docs is the publication target: non-versioned project ProperDocs at the root and versioned
    # API ProperDocs sites below reference/api/.
    _run(["cmake", "--build", "build/docs", "--target", "user.docs"], project)
    site = project / "build" / "docs" / "doc" / "site"
    assert (site / "index.html").is_file()
    assert (site / "reference" / "api" / "index.html").is_file()
    assert (site / "reference" / "api" / "versions.json").is_file()
    assert (site / "reference" / "api" / "main" / "index.html").is_file()
    assert (site / "reference" / "api" / "v0.1.0" / "index.html").is_file()
    assert (site / "reference" / "api" / "v0.2.0" / "index.html").is_file()
    assert (site / ".nojekyll").is_file()

    # Documentation targets do not build the ordinary project as a side effect. Build it before
    # exercising the complete install path.
    _run(["cmake", "--build", "build/docs"], project)

    prefix = tmp_path / "docs-prefix"
    _run(["cmake", "--install", "build/docs", "--prefix", str(prefix)], project)
    installed_docs = prefix / "share" / "doc" / "example_multidocs"
    assert (installed_docs / "index.html").is_file()
    assert (installed_docs / "reference" / "api" / "index.html").is_file()
    assert (installed_docs / "reference" / "api" / "main" / "index.html").is_file()


@pytest.mark.cpp
def test_configure_prints_resolved_project_configuration(tmp_path: Path) -> None:
    project = tmp_path / "configuration_summary"
    project.mkdir()
    cpp_update(project)
    (project / "CMakeLists.txt").write_text(
        """\
cmake_minimum_required(VERSION 3.26.1)
project(Configuration_Summary VERSION 1.2.3 LANGUAGES NONE)
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
    assert "-- configuration_summary configuration:" in result.stdout
    assert "Features      : alpha" in result.stdout
    assert "Devtools      : none" in result.stdout
    assert "Warning policy: none" in result.stdout
    assert "Test modes    : ci-commit" in result.stdout
    assert "Languages     : none" in result.stdout
    assert "Build testing : ON" in result.stdout
    assert "Release type  : release" in result.stdout
    assert "Version       : 1.2.3" in result.stdout


@pytest.mark.cpp
def test_generated_api_version_selectors_choose_semantic_tags_and_exact_refs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util

    if shutil.which("git") is None:
        pytest.skip("Git is required")

    project = cpp_generate(tmp_path, "example_versions")
    _run(["git", "init", "-b", "main"], project)
    _run(["git", "config", "user.email", "besa-test@example.invalid"], project)
    _run(["git", "config", "user.name", "BESA Test"], project)
    _run(["git", "add", "."], project)
    _run(["git", "commit", "-m", "initial"], project)
    for tag in ("v0.8.0", "v0.9.0", "v0.10.0", "v0.11.0-rc.1", "v0.11.0", "nightly"):
        _run(["git", "tag", tag], project)
    _run(["git", "branch", "maintenance"], project)

    versioning = project / "cmake" / "besa" / "userdocs" / "api_reference" / "versioning.py"
    spec = importlib.util.spec_from_file_location("example_versions_driver", versioning)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.selected_ref_names(project, "all") == [
        "main",
        "v0.11.0",
        "v0.11.0-rc.1",
        "v0.10.0",
        "v0.9.0",
        "v0.8.0",
    ]
    assert module.selected_ref_names(project, "latest:3") == [
        "main",
        "v0.11.0",
        "v0.11.0-rc.1",
        "v0.10.0",
    ]
    assert module.selected_ref_names(project, "range:>=0.9,<0.11") == [
        "main",
        "v0.11.0-rc.1",
        "v0.10.0",
        "v0.9.0",
    ]
    assert module.selected_ref_names(project, "refs:v0.8.0,maintenance") == [
        "main",
        "v0.8.0",
        "maintenance",
    ]

    with pytest.raises(RuntimeError, match="unknown BESA API Git refs"):
        module.selected_ref_names(project, "refs:v9.9.9")

    monkeypatch.delenv("BESA_API_VERSIONS", raising=False)
    properdocs = project / "properdocs.yml"
    properdocs.write_text(
        properdocs.read_text(encoding="utf-8").replace(
            "besa_api_versions: all", "besa_api_versions: latest:2"
        ),
        encoding="utf-8",
    )
    assert module.selector(project) == "latest:2"


@pytest.mark.cpp
def test_semantic_multiversion_builder_uses_git_worktrees(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib
    import sys
    from argparse import Namespace

    project = tmp_path / "project"
    project.mkdir()
    output = tmp_path / "api"
    work = tmp_path / "work"
    backend_root = (
        Path(__file__).resolve().parents[1] / "share" / "besa" / "cpp" / "cmake" / "userdocs"
    )
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    driver = importlib.import_module("api_reference.__main__")

    monkeypatch.setattr(driver, "selector", lambda _root: "all")
    monkeypatch.setattr(driver, "selected_ref_names", lambda _root, _selector: ["main", "v1.0.0"])

    git_calls: list[list[str]] = []

    def fake_git(command: list[str], *, cwd: Path) -> None:
        git_calls.append(command)
        if command[:2] == ["worktree", "add"]:
            checkout = Path(command[-2])
            checkout.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(driver, "_git", fake_git)

    built: list[tuple[str, Path]] = []

    def fake_build_cpp(arguments):
        from api_reference.model import ApiGraph

        built.append((arguments.version, arguments.project_root))
        return ApiGraph(project="example", version=arguments.version, language="cpp")

    monkeypatch.setattr(driver, "_build_cpp", fake_build_cpp)

    def fake_render(graph, **kwargs):
        destination = kwargs["output_directory"]
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "index.html").write_text(graph.version, encoding="utf-8")

    monkeypatch.setattr(driver, "_render_graph", fake_render)

    args = Namespace(
        project_root=project,
        work_directory=work,
        output_directory=output,
        template_directory=tmp_path / "template",
        properdocs="properdocs",
        project_docs_url="../../../../../",
        default_version="main",
        cmake="cmake",
        clang="clang++",
        profile=[],
    )
    assert driver._build_versions(args) == 0
    assert built[0] == ("main", project.resolve())
    assert built[1][0] == "v1.0.0"
    assert built[1][1] != project.resolve()
    assert git_calls[0][:3] == ["worktree", "add", "--detach"]
    assert git_calls[-1][:3] == ["worktree", "remove", "--force"]
    assert (output / "main" / "index.html").read_text(encoding="utf-8") == "main"
    assert (output / "v1.0.0" / "index.html").read_text(encoding="utf-8") == "v1.0.0"


@pytest.mark.cpp
def test_multiversion_api_metadata_is_generated(tmp_path: Path) -> None:
    import importlib
    import json
    import sys

    backend_root = (
        Path(__file__).resolve().parents[1] / "share" / "besa" / "cpp" / "cmake" / "userdocs"
    )
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    driver = importlib.import_module("api_reference.__main__")

    output = tmp_path / "api"
    for version in ("main", "1.0.0", "2.0.0", "release/3.0"):
        (output / version).mkdir(parents=True)
        (output / version / "index.html").write_text(version, encoding="utf-8")

    # Nested pages belong to a version's page manifest; branch names containing slashes remain one
    # semantic version entry because the ref list, not directory discovery, defines the versions.
    (output / "main" / "detail").mkdir()
    (output / "main" / "detail" / "index.html").write_text("detail", encoding="utf-8")

    refs = ["main", "1.0.0", "2.0.0", "release/3.0"]
    driver._write_versions(output, refs, "main")

    metadata = json.loads((output / "versions.json").read_text(encoding="utf-8"))
    assert metadata["default"] == "main"
    assert metadata["versions"][0] == {
        "name": "main",
        "url": "main/",
        "pages": ["detail/index.html", "index.html"],
    }
    assert {item["name"] for item in metadata["versions"]} == set(refs)
    assert "main/detail" not in {item["name"] for item in metadata["versions"]}
    assert not (output / "index.html").exists()


@pytest.mark.cpp
def test_user_docs_assembly_mounts_versioned_api_below_reference(tmp_path: Path) -> None:
    properdocs = tmp_path / "properdocs"
    api = tmp_path / "api"
    output = tmp_path / "site"

    (properdocs / "reference").mkdir(parents=True)
    (properdocs / "index.html").write_text("properdocs-home", encoding="utf-8")
    (properdocs / "reference" / "index.html").write_text(
        "properdocs-reference-with-versioned-api", encoding="utf-8"
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
    assert (output / "reference" / "index.html").read_text(
        encoding="utf-8"
    ) == "properdocs-reference-with-versioned-api"
    assert not (output / "reference" / "api" / "index.html").exists()
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
    dev_env_spec = next(
        line.strip()[2:].replace(" ", "")
        for line in manifest.splitlines()
        if line.strip().startswith("- dev-env@")
    )
    assert dev_env_spec.startswith("dev-env@1.2")
    assert sorted(filter(None, dev_env_spec.removeprefix("dev-env@1.2").split("+"))) == [
        "docs",
        "tests",
    ]
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
    assert 'version("1.2")' in environment_package
    for variant in ("docs", "tests", "coverage"):
        assert f'variant("{variant}"' in environment_package
    assert 'depends_on("properdocs", when="+docs")' in environment_package
    assert 'depends_on("py-packaging", when="+docs")' in environment_package
    for obsolete in (
        "doxygen",
        "py-sphinx",
        "py-breathe",
        "py-exhale",
        "py-pydata-sphinx-theme",
        "py-sphinx-multiversion",
    ):
        assert obsolete not in environment_package
    for toolchain in ("cuda", "hip"):
        assert f'variant("{toolchain}"' not in environment_package
        assert f'depends_on("{toolchain}"' not in environment_package
    assert not (repo / "packages" / "properdocs").exists()

    assert not (repo / "packages" / "doxygen").exists()

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
    assert "  - .git/refs" in config_text
    assert "hooks:" in config_text
    assert "  - properdocs_multiversion_hook.py" in config_text

    spec = importlib.util.spec_from_file_location("example_serve_docs_hook", hook_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.PROPERDOCS_WORK_DIRECTORY == project.parent / "build" / "properdocs"
    assert module.BUILD_DIRECTORY == project.parent / "build" / "properdocs" / "cmake"
    assert module.DOCS_BUILD_DIRECTORY == project.parent / "build" / "properdocs" / "docs"
    assert (
        module.API_BUILD_DIRECTORY
        == project.parent / "build" / "properdocs" / "docs" / "api" / "current"
    )

    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        commands.append(list(command))
        return None

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    module._build_current_api()
    assert any("-DPROJECT_FEATURES=user-docs" in item for item in commands[0])
    assert f"-DBESA_WORKSPACE={module.PROPERDOCS_WORK_DIRECTORY}" in commands[0]
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
        "versions": [{"name": "main", "url": "main/", "pages": ["index.html"]}],
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

    assert module.PROPERDOCS_WORK_DIRECTORY == project.parent / "build" / "properdocs"
    assert module.BUILD_DIRECTORY == project.parent / "build" / "properdocs" / "cmake"
    assert module.DOCS_BUILD_DIRECTORY == project.parent / "build" / "properdocs" / "docs"
    assert (
        module.API_BUILD_DIRECTORY
        == project.parent / "build" / "properdocs" / "docs" / "api" / "current"
    )

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

    assert module.PROPERDOCS_WORK_DIRECTORY == project.parent / "build" / "properdocs"
    assert module.BUILD_DIRECTORY == project.parent / "build" / "properdocs" / "cmake"
    assert module.DOCS_BUILD_DIRECTORY == project.parent / "build" / "properdocs" / "docs"
    assert (
        module.CURRENT_API_BUILD_DIRECTORY
        == project.parent / "build" / "properdocs" / "docs" / "api" / "current"
    )
    assert (
        module.MULTIVERSION_API_BUILD_DIRECTORY
        == project.parent / "build" / "properdocs" / "docs" / "api" / "multiversion"
    )

    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        commands.append(list(command))
        return None

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    module._configure()
    module._build("user.docs.multiversion")
    module._build("user.docs.api")
    assert any("-DPROJECT_FEATURES=user-docs" in item for item in commands[0])
    assert f"-DBESA_WORKSPACE={module.PROPERDOCS_WORK_DIRECTORY}" in commands[0]
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
    (api_root / "index.html").write_text("stale-api-landing", encoding="utf-8")
    (api_root / "stale-version").mkdir()

    module._publish_multiversion_api(site)

    assert not (api_root / "index.html").exists()
    assert (api_root / "main" / "index.html").read_text(encoding="utf-8") == "working-tree-main"
    assert (api_root / "1.0.0" / "index.html").read_text(encoding="utf-8") == "one"
    assert not (api_root / "stale-version").exists()
    metadata = json.loads((api_root / "versions.json").read_text(encoding="utf-8"))
    assert metadata["default"] == "main"
    assert metadata["versions"][0] == {
        "name": "main",
        "url": "main/",
        "pages": ["index.html"],
    }
    assert metadata["versions"][1] == {
        "name": "1.0.0",
        "url": "1.0.0/",
        "pages": ["index.html"],
    }
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

    def fake_build(target: str, api_versions: str | None = None) -> None:
        targets.append(f"{target}:{api_versions or '-'}")

    monkeypatch.setattr(module, "_configure", fake_configure)
    monkeypatch.setattr(module, "_build", fake_build)

    module._ensure_multiversion_api("all")
    assert configured == 1
    assert targets == ["user.docs.multiversion:all", "user.docs.api:-"]

    module._ensure_multiversion_api("all")
    assert configured == 1

    source_state[0] = [("src/a.hpp", 2, 1)]
    module._ensure_multiversion_api("all")
    assert configured == 2
    assert targets[-1] == "user.docs.api:-"

    refs_state[0] = [(".git/refs/heads/main", 2, 1)]
    module._ensure_multiversion_api("all")
    assert configured == 3
    assert targets[-2:] == [
        "user.docs.multiversion:all",
        "user.docs.api:-",
    ]

    module._ensure_multiversion_api("latest:3")
    assert configured == 4
    assert targets[-1] == "user.docs.multiversion:latest:3"


@pytest.mark.cpp
def test_generated_properdocs_source_links_follow_human_refs_and_404_issues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util
    import re
    from types import SimpleNamespace

    project = cpp_generate(tmp_path, "example_source_docs")
    hook_path = project / "properdocs_multiversion_hook.py"
    spec = importlib.util.spec_from_file_location("example_source_docs_hook", hook_path)
    assert spec is not None and spec.loader is not None
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)

    monkeypatch.setenv("BESA_SOURCE_REF", "feature/docs-links")
    github_config = {
        "repo_url": "https://github.com/example/example_source_docs.git",
        "extra": {},
    }
    hook.on_config(github_config)
    assert github_config["extra"]["besa_source_ref"] == "feature/docs-links"
    assert github_config["extra"]["besa_repo_provider"] == "github"
    assert github_config["extra"]["besa_issue_url"] == (
        "https://github.com/example/example_source_docs/issues/new"
    )

    page = SimpleNamespace(
        file=SimpleNamespace(abs_src_path=str(project / "docs" / "reference" / "index.md"))
    )
    context = hook.on_page_context({}, page, github_config, nav=None)
    assert context["besa_source_url"] == (
        "https://github.com/example/example_source_docs/blob/feature/docs-links/"
        "docs/reference/index.md"
    )
    assert context["besa_edit_url"] == (
        "https://github.com/example/example_source_docs/edit/feature/docs-links/"
        "docs/reference/index.md"
    )
    assert not re.search(r"/[0-9a-f]{40}/", context["besa_source_url"])
    assert not re.search(r"/[0-9a-f]{40}/", context["besa_edit_url"])

    # Unknown/self-hosted repository hosts use GitLab's URL layout unless explicitly overridden.
    gitlab_config = {
        "repo_url": "https://code.example.org/software/example_source_docs",
        "extra": {},
    }
    hook.on_config(gitlab_config)
    assert gitlab_config["extra"]["besa_repo_provider"] == "gitlab"
    assert gitlab_config["extra"]["besa_issue_url"] == (
        "https://code.example.org/software/example_source_docs/-/issues/new"
    )
    gitlab_context = hook.on_page_context({}, page, gitlab_config, nav=None)
    assert gitlab_context["besa_source_url"] == (
        "https://code.example.org/software/example_source_docs/-/blob/feature/docs-links/"
        "docs/reference/index.md"
    )
    assert gitlab_context["besa_edit_url"] == (
        "https://code.example.org/software/example_source_docs/-/edit/feature/docs-links/"
        "docs/reference/index.md"
    )

    # Explicit issue/provider configuration wins over inference.
    explicit = {
        "repo_url": "https://git.example.org/example_source_docs",
        "extra": {
            "besa_repo_provider": "bitbucket",
            "besa_issue_url": "https://issues.example.org/new",
        },
    }
    hook.on_config(explicit)
    assert explicit["extra"]["besa_issue_url"] == "https://issues.example.org/new"
    explicit_context = hook.on_page_context({}, page, explicit, nav=None)
    assert "/src/feature/docs-links/docs/reference/index.md" in explicit_context["besa_source_url"]
    assert explicit_context["besa_edit_url"].endswith(
        "/src/feature/docs-links/docs/reference/index.md?mode=edit"
    )


@pytest.mark.cpp
def test_generated_documentation_cross_references_are_semantic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util
    from types import SimpleNamespace

    project = cpp_generate(tmp_path, "example_xrefs")
    hook_path = project / "properdocs_multiversion_hook.py"
    hook_spec = importlib.util.spec_from_file_location("example_xrefs_hook", hook_path)
    assert hook_spec is not None and hook_spec.loader is not None
    hook = importlib.util.module_from_spec(hook_spec)
    hook_spec.loader.exec_module(hook)

    # The project documentation resolves language-neutral semantic names. C++ uses :: while Python
    # may use dots; both map to the same _symbols hierarchy produced by the shared API renderer.
    page = SimpleNamespace(file=SimpleNamespace(dest_uri="reference/index.html"))
    rendered = hook.on_page_markdown(
        "Build metadata: @apidocs::example_xrefs::meta::build.",
        page,
        {"extra": {"besa_api_version": "main"}},
    )
    assert (
        "[`example_xrefs::meta::build`]"
        "(api/main/_symbols/example_xrefs/meta/build/)"
    ) in rendered

    rendered_python = hook.on_page_markdown(
        "Python solver: @apidocs::example_xrefs.linalg.solve.",
        page,
        {"extra": {"besa_api_version": "main"}},
    )
    assert (
        "[`example_xrefs.linalg.solve`]"
        "(api/main/_symbols/example_xrefs/linalg/solve/)"
    ) in rendered_python

    rendered_versioned = hook.on_page_markdown(
        "Released metadata: @apidocs[v0.2.0]::example_xrefs::meta::build.",
        page,
        {"extra": {"besa_api_version": "main"}},
    )
    assert (
        "[`example_xrefs::meta::build`]"
        "(api/v0.2.0/_symbols/example_xrefs/meta/build/)"
    ) in rendered_versioned

    # During `properdocs serve`, unresolved references are checked against the generated semantic
    # aliases. No Sphinx domain/inventory is involved.
    current = tmp_path / "current-api"
    current_alias = current / "_symbols" / "example_xrefs" / "meta" / "build" / "index.html"
    current_alias.parent.mkdir(parents=True)
    current_alias.write_text("alias", encoding="utf-8")
    hook.CURRENT_API_BUILD_DIRECTORY = current
    monkeypatch.setattr(hook, "_serve_active", True)
    hook.on_page_markdown(
        "@apidocs::example_xrefs::meta::build",
        page,
        {"extra": {"besa_api_version": "main"}},
    )
    with pytest.raises(RuntimeError, match="unresolved API documentation reference"):
        hook.on_page_markdown(
            "@apidocs::example_xrefs::meta::missing",
            page,
            {"extra": {"besa_api_version": "main"}},
        )

    hook.MULTIVERSION_API_BUILD_DIRECTORY = tmp_path / "multiversion"
    released_alias = (
        hook.MULTIVERSION_API_BUILD_DIRECTORY
        / "v0.2.0"
        / "_symbols"
        / "example_xrefs"
        / "meta"
        / "build"
        / "index.html"
    )
    released_alias.parent.mkdir(parents=True)
    released_alias.write_text("released", encoding="utf-8")
    hook.on_page_markdown(
        "@apidocs[v0.2.0]::example_xrefs::meta::build",
        page,
        {"extra": {"besa_api_version": "main"}},
    )
    with pytest.raises(RuntimeError, match="version 'v9.9.9'"):
        hook.on_page_markdown(
            "@apidocs[v9.9.9]::example_xrefs::meta::build",
            page,
            {"extra": {"besa_api_version": "main"}},
        )


@pytest.mark.cpp
def test_generated_cpp_project_has_reuse_metadata(tmp_path: Path) -> None:
    project = cpp_generate(tmp_path, "example_reuse")
    project_copyright = "Example Reuse developers"

    assert (project / "LICENSES" / "Apache-2.0.txt").is_file()
    assert "Apache License" in (project / "LICENSES" / "Apache-2.0.txt").read_text(
        encoding="utf-8"
    )

    for path in project.rglob("*"):
        if not path.is_file() or path.name.endswith(".license"):
            continue
        relative = path.relative_to(project)
        if relative.parts and relative.parts[0] == "LICENSES":
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = ""

        if "SPDX-FileCopyright" "Text:" in text and "SPDX-License-" "Identifier:" in text:
            metadata = text
        else:
            sidecar = Path(str(path) + ".license")
            assert sidecar.is_file(), f"missing REUSE metadata for {relative}"
            metadata = sidecar.read_text(encoding="utf-8")

        assert "SPDX-FileCopyright" "Text:" in metadata
        assert "SPDX-License-" "Identifier: Apache-2.0" in metadata
        if relative.parts[:2] == ("cmake", "besa"):
            assert "BESA developers" in metadata
        else:
            assert project_copyright in metadata

    assert (project / "CMakePresets.json.license").is_file()
    assert (project / "cmake" / "besa" / ".besa-cmake-module.license").is_file()


@pytest.mark.cpp
def test_generated_cpp_custom_license_requires_and_installs_license_text(tmp_path: Path) -> None:
    license_text = tmp_path / "MIT.txt"
    license_text.write_text("MIT License\n", encoding="utf-8")
    project = cpp_generate(tmp_path, "example_license", "MIT", license_text=license_text)

    assert (project / "LICENSES" / "Apache-2.0.txt").is_file()
    assert (project / "LICENSES" / "MIT.txt").read_text(encoding="utf-8") == "MIT License\n"
    assert "SPDX-License-" "Identifier: MIT" in (project / "CMakeLists.txt").read_text(
        encoding="utf-8"
    )
    assert "SPDX-License-" "Identifier: Apache-2.0" in (
        project / "cmake" / "besa" / "besaConfig.cmake"
    ).read_text(encoding="utf-8")


@pytest.mark.cpp
def test_generated_cpp_project_ignores_spack_work_state_and_python_caches(tmp_path: Path) -> None:
    project = cpp_generate(tmp_path, "example_ignore")
    gitignore = (project / ".gitignore").read_text(encoding="utf-8")

    assert ".spack-env/" in gitignore
    assert "__pycache__/" in gitignore
    assert "*.py[cod]" in gitignore
    assert "/api-docs/generated/" not in gitignore
    assert "/site/" not in gitignore
    ignored_entries = {line.strip() for line in gitignore.splitlines() if line.strip() and not line.startswith("#")}
    assert "spack.yaml" not in ignored_entries
    assert "spack.lock" not in ignored_entries
    assert "spack/" not in ignored_entries
