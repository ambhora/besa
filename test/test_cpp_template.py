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
    for feature in ("toolchain-c", "toolchain-hip", "toolchain-asm", "toolchain-cuda"):
        assert f"    {feature}\n" not in root_cmake

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
        ],
        project,
    )
    version_header = project / "build" / "version" / "generated" / "meta" / "include" / "example_version" / "version.hpp"
    version_text = version_header.read_text(encoding="utf-8")
    assert "#ifndef EXAMPLE_VERSION_VERSION_HPP" in version_text
    assert "#define EXAMPLE_VERSION_VERSION_HPP" in version_text
    assert "#pragma once" not in version_text
    assert "namespace example_version::meta" in version_text
    assert "struct semantic_version" in version_text
    assert "struct release_info" in version_text
    assert "struct build_info" in version_text
    assert "return {0, 1, 0, 0};" in version_text
    assert 'return {release_type::release_candidate, 3};' in version_text
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
    text = text.replace(
        "# --------------------------------------------------------------------------------------------------\n# PROJECT STRUCTURE\n",
        insertion
        + "# --------------------------------------------------------------------------------------------------\n# PROJECT STRUCTURE\n",
    )
    cmake.write_text(text, encoding="utf-8")

    _run(["cmake", "-S", ".", "-B", "build/generated"], project)

    meta_root = project / "build" / "generated" / "generated" / "meta" / "include"
    schema_root = project / "build" / "generated" / "generated" / "schema" / "include"
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
    config_text = (project / "properdocs.yml").read_text(encoding="utf-8")
    assert "site_dir: ../build/properdocs/site" in config_text
    assert "besa_api_version: main" in config_text
    assert "besa_api_versions: all" in config_text
    assert "  - test/base" in config_text
    assert "  - .git/refs" in config_text
    assert "  - properdocs_multiversion_hook.py" in config_text
    assert (project / "properdocs_multiversion_hook.py").is_file()
    assert (docs / "index.md").is_file()
    reference_landing = docs / "reference" / "index.md"
    assert reference_landing.is_file()
    assert not (docs / "reference" / "api.md").exists()
    reference_text = reference_landing.read_text(encoding="utf-8")
    assert "## Versioned API" in reference_text
    assert 'new URL("api/", window.location.href)' in reference_text
    assert 'new URL("versions.json", apiRoot)' in reference_text
    assert 'href="api/main/"' in reference_text
    assert "API reference: reference/api.md" not in config_text
    assert "  - Reference: reference/index.md" in config_text
    assert "  - assets/stylesheets/ambhora.css" in config_text
    assert "copyright: Copyright &copy; example_docs developers &middot; Apache-2.0" in config_text
    assert "generator: false" in config_text
    assert "custom_dir: overrides" in config_text
    assert "# repo_url:" in config_text
    actions_template = project / "overrides" / "partials" / "actions.html"
    not_found_template = project / "overrides" / "404.html"
    assert actions_template.is_file()
    assert not_found_template.is_file()
    actions_text = actions_template.read_text(encoding="utf-8")
    assert "besa_source_url" in actions_text
    assert "View this page's source" in actions_text
    not_found_text = not_found_template.read_text(encoding="utf-8")
    assert "This documentation page isn't here." in not_found_text
    assert "besa_issue_url" in not_found_text
    assert "Report a documentation issue" in not_found_text
    brand_css = docs / "assets" / "stylesheets" / "ambhora.css"
    assert brand_css.is_file()
    brand_text = brand_css.read_text(encoding="utf-8")
    assert "#3B97C4" in brand_text
    assert "#97C43B" in brand_text
    assert "#C43B97" in brand_text
    assert ".md-header {" in brand_text
    assert "background: var(--ambhora-blue)" in brand_text
    assert "border-bottom: 0.2rem solid var(--ambhora-green)" not in brand_text
    assert "min-height: 2.1rem" in brand_text
    assert "height: 1.8rem" in brand_text
    assert "border-bottom: 0.12rem solid var(--ambhora-green)" in brand_text
    assert ".besa-404" in brand_text
    assert ".besa-404__actions" in brand_text

    # Sphinx/Breathe/Exhale/Doxygen is a separate API-only source tree. Exhale owns the generated
    # entity pages; the project does not maintain a hand-selected doxygenindex list.
    assert (api_docs / "conf.py").is_file()
    assert (api_docs / "besa_exhale_compat.py").is_file()
    assert (api_docs / "Doxyfile.in").is_file()
    assert (api_docs / "index.rst").is_file()
    assert (api_docs / "_static" / "css" / "besa-api.css").is_file()
    project_links = api_docs / "_templates" / "project-links.html"
    version_script = api_docs / "_static" / "js" / "besa-api-version.js"
    presentation_script = api_docs / "_static" / "js" / "besa-api-presentation.js"
    assert project_links.is_file()
    assert not (api_docs / "_templates" / "versioning.html").exists()
    assert version_script.is_file()
    assert presentation_script.is_file()
    project_links_text = project_links.read_text(encoding="utf-8")
    assert "← Project documentation" in project_links_text
    assert "API version" in project_links_text
    assert "data-besa-api-root" in project_links_text
    assert "data-besa-api-page" in project_links_text
    version_script_text = version_script.read_text(encoding="utf-8")
    assert 'fetch(new URL("versions.json", apiRoot))' in version_script_text
    assert "version.pages.includes(page)" in version_script_text
    assert "return root.href" in version_script_text
    assert 'document.readyState === "loading"' in version_script_text
    assert 'document.addEventListener("DOMContentLoaded", initializeAll' in version_script_text
    presentation_script_text = presentation_script.read_text(encoding="utf-8")
    assert '"inline"' in presentation_script_text
    assert '"constexpr"' in presentation_script_text
    assert "noexcept" in presentation_script_text
    assert 'className = "besa-api-qualifiers"' in presentation_script_text
    assert 'document.addEventListener("DOMContentLoaded", initialize' in presentation_script_text
    assert not (docs / "conf.py").exists()

    conf_text = (api_docs / "conf.py").read_text(encoding="utf-8")
    assert '"besa_exhale_compat"' in conf_text
    assert conf_text.index('"besa_exhale_compat"') < conf_text.index('"exhale"')
    assert "sys.path.insert(0, str(CONFIG_DIRECTORY))" in conf_text
    assert '"breathe"' in conf_text
    assert '"exhale"' in conf_text
    assert '"sphinx_multiversion"' in conf_text
    assert 'html_theme = "pydata_sphinx_theme"' in conf_text
    assert 'html_title = f"{project} documentation"' in conf_text
    assert "html_short_title = html_title" in conf_text
    assert '"show_prev_next": False' in conf_text
    assert 'html_js_files = ["js/besa-api-version.js", "js/besa-api-presentation.js"]' in conf_text
    assert '"kindsWithContentsDirectives": ["namespace", "file"]' in conf_text
    assert '"navbar_align": "right"' in conf_text
    assert '"navbar_center": []' in conf_text
    assert '"navbar_persistent": []' in conf_text
    assert '"search-button-field"' in conf_text
    assert '"**": ["api-sidebar.html"]' in conf_text
    assert '"sidebar-collapse"' not in conf_text
    api_sidebar = (api_docs / "_templates" / "api-sidebar.html").read_text(encoding="utf-8")
    assert "startdepth=0" in api_sidebar
    assert '"sidebar"' in api_sidebar
    assert '"primary_sidebar_end"' not in conf_text
    assert '"containmentFolder": "./generated"' in conf_text
    assert '"rootFileName": "library_root.rst"' in conf_text
    assert 'smv_branch_whitelist = os.environ.get("BESA_SMV_BRANCH_WHITELIST", r"^main$")' in conf_text
    assert 'smv_tag_whitelist = os.environ.get("BESA_SMV_TAG_WHITELIST", r"^.*$")' in conf_text
    assert 'smv_outputdir_format = r"{ref.name}"' in conf_text
    assert "_selected_smv_refs" not in conf_text
    assert "packaging.version" not in conf_text
    assert "cpp_maximum_signature_line_length = 80" in conf_text
    assert "BESA_PROPERDOCS_ROOT_DEPTH" in conf_text
    assert "BESA_API_PROJECT_SOURCE_DIRECTORY" in conf_text
    assert "_configured_doxyfile" in conf_text
    assert "Path(app.srcdir).resolve()" in conf_text
    api_index_text = (api_docs / "index.rst").read_text(encoding="utf-8")
    assert "doxygenindex" not in api_index_text
    assert "|projectdocs|_" in api_index_text
    assert ".. include:: generated/api_landing.rst.include" in api_index_text
    assert "generated/library_root" not in api_index_text
    assert ".. _projectdocs:" in conf_text
    assert "_write_api_symbol_aliases" in conf_text
    assert "projectdocs{{1}}" in conf_text
    assert "projectdocs{{2}}" in conf_text

    project_cmake = (project / "CMakeLists.txt").read_text(encoding="utf-8")
    assert 'set(CMAKE_EXPORT_COMPILE_COMMANDS ON)' in project_cmake
    assert '"${PROJECT_SOURCE_DIR}/api-docs/Doxyfile.in"' in project_cmake
    assert '"${PROJECT_BINARY_DIR}/api-docs/Doxyfile"' in project_cmake

    userdocs_cmake = (project / "cmake" / "besa" / "userdocs.cmake").read_text(encoding="utf-8")
    assert 'set(_besa_current_sphinx_source "${PROJECT_BINARY_DIR}/doc/work/sphinx-current")' in userdocs_cmake
    assert '"BESA_API_PROJECT_SOURCE_DIRECTORY=${PROJECT_SOURCE_DIR}"' in userdocs_cmake
    assert '"${_besa_current_sphinx_source}" "${ARG_OUTPUT_DIRECTORY}"' in userdocs_cmake
    assert 'userdocs/multiversion.py' in userdocs_cmake
    assert '"--sphinx-multiversion" "${_besa_sphinx_multiversion}"' in userdocs_cmake
    multiversion_driver = project / "cmake" / "besa" / "userdocs" / "multiversion.py"
    assert multiversion_driver.is_file()
    driver_text = multiversion_driver.read_text(encoding="utf-8")
    assert 'environment["BESA_API_VERSIONS"] = "all"' in driver_text
    assert 'environment["BESA_SMV_BRANCH_WHITELIST"] = branch_pattern' in driver_text
    assert 'environment["BESA_SMV_TAG_WHITELIST"] = tag_pattern' in driver_text

    doxyfile_text = (api_docs / "Doxyfile.in").read_text(encoding="utf-8")
    assert "EXTRACT_ALL            = YES" in doxyfile_text
    assert "synthetic public-header tree" in doxyfile_text
    assert "CLANG_ASSISTED_PARSING = YES" in doxyfile_text
    assert "CLANG_ADD_INC_PATHS    = YES" in doxyfile_text
    assert 'CLANG_DATABASE_PATH    = "@CMAKE_BINARY_DIR@"' in doxyfile_text
    assert "EXCLUDE_PATTERNS" not in doxyfile_text

    css = (api_docs / "_static" / "css" / "besa-api.css").read_text(encoding="utf-8")
    assert ".bd-page-width" in css
    assert "max-width: 90rem" in css
    assert "min-width: 13rem" in css
    assert ".navbar-header-items__end" in css
    assert "margin-inline-start: auto" in css
    assert ".besa-api-project-links" in css
    assert "gap: 1.25rem" in css
    assert ".besa-api-version-select" in css
    assert ".breathe-sectiondef-title" in css
    assert ".api-kind" in css
    assert ".besa-api-qualifiers" in css
    assert ".besa-api-qualifier" in css
    assert "dt.besa-multiline-signature .sig-return-type" in css
    assert "display: block" in css
    assert "font-size: 0.84rem" in css
    assert "font-size: 0.68rem" in css
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
    assert module._rst_role_title("tag_result< Tag, Args... >") == "tag_result\\< Tag, Args... >"
    assert module._rst_role_title("operator<()") == "operator\\<()"

    staged_api = tmp_path / "external-work" / "api-docs"
    monkeypatch.setenv("BESA_API_PROJECT_SOURCE_DIRECTORY", str(project))
    assert module._api_project_root(staged_api) == project.resolve()
    monkeypatch.delenv("BESA_API_PROJECT_SOURCE_DIRECTORY")

    events: dict[str, list[tuple[object, int]]] = {}

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
            events.setdefault(event, []).append((callback, priority))

    current_app = FakeApp(api_docs)
    module.setup(current_app)
    builder_callbacks = events["builder-inited"]
    assert (module._prepare_api, 100) in builder_callbacks
    assert (module._prepare_api_landing, 900) in builder_callbacks
    assert (module._mark_multiline_signatures, 500) in events["doctree-read"]
    assert (module._write_api_symbol_aliases, 500) in events["build-finished"]
    assert "env-before-read-docs" not in events

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
    current_configured_build = current_output / "project-build"
    assert f'CLANG_DATABASE_PATH    = "{current_configured_build}"' in generated_text
    current_public = current_output / "public-include"
    assert str(current_public).replace("\\", "/") in generated_text
    assert str(project / "src").replace("\\", "/") not in generated_text
    assert (current_public / "example_docs" / "example_docs.hpp").is_file()
    test_base_header = current_public / "testexample_docs" / "prova" / "cmdline.hpp"
    assert test_base_header.is_file()
    test_base_text = test_base_header.read_text(encoding="utf-8")
    assert "@projectdocs" in test_base_text
    assert "@projectdocs{reference/testing,the testing reference}" in test_base_text
    assert 'ALIASES += "projectdocs=' in generated_text
    assert 'ALIASES += "projectdocs{1}=' in generated_text
    assert 'ALIASES += "projectdocs{2}=' in generated_text
    assert '../../../../\\1/' in generated_text
    current_version = current_public / "example_docs" / "version.hpp"
    assert current_version.is_file()
    assert "namespace example_docs::meta" in current_version.read_text(encoding="utf-8")
    assert current_app.config.release == "0.1.0"
    assert current_app.config.breathe_projects == {
        "example_docs": str(current_output / "xml")
    }
    assert current_app.config.exhale_args["containmentFolder"] == str(api_docs / "generated")
    assert current_app.config.exhale_args["doxygenStripFromPath"] == str(current_public)

    # Exhale generates all detailed pages, then BESA writes a compact synopsis fragment included by
    # index.rst. Overloads are intentionally collapsed by name on this page.
    xml_dir = current_output / "xml"
    xml_dir.mkdir(parents=True, exist_ok=True)
    (xml_dir / "index.xml").write_text(
        """\
<doxygenindex>
  <compound kind="namespace" refid="namespaceexample__docs">
    <name>example_docs</name>
  </compound>
  <compound kind="namespace" refid="namespaceexample__docs_1_1meta">
    <name>example_docs::meta</name>
    <member kind="function" refid="function1"><name>to_string</name></member>
    <member kind="function" refid="function2"><name>to_string</name></member>
    <member kind="function" refid="function3"><name>version</name></member>
    <member kind="function" refid="function4"><name>to_static_array</name></member>
    <member kind="function" refid="guide1"><name>box</name></member>
    <member kind="function" refid="function5"><name>operator&lt;</name></member>
    <member kind="enum" refid="enum1"><name>release_type</name></member>
    <member kind="concept" refid="conceptexample__docs_1_1meta_1asortable"><name>sortable</name></member>
  </compound>
  <compound kind="struct" refid="struct1">
    <name>example_docs::meta::semantic_version</name>
  </compound>
  <compound kind="struct" refid="struct2">
    <name>example_docs::meta::box</name>
  </compound>
  <compound kind="struct" refid="struct3">
    <name>example_docs::meta::tag_result&lt; Tag, Args... &gt;</name>
  </compound>
  <compound kind="concept" refid="conceptexample__docs_1_1meta_1asortable">
    <name>example_docs::meta::sortable</name>
  </compound>
</doxygenindex>
""",
        encoding="utf-8",
    )
    (xml_dir / "namespaceexample__docs_1_1meta.xml").write_text(
        """\
<doxygen>
  <compounddef id="namespaceexample__docs_1_1meta" kind="namespace">
    <sectiondef kind="func">
      <memberdef kind="function" id="function1">
        <type>std::string_view</type>
        <name>to_string</name>
        <qualifiedname>example_docs::meta::to_string</qualifiedname>
        <param><type>semantic_version</type><declname>value</declname></param>
      </memberdef>
      <memberdef kind="function" id="function2">
        <type>std::string_view</type>
        <name>to_string</name>
        <qualifiedname>example_docs::meta::to_string</qualifiedname>
        <param><type>release_type</type><declname>value</declname></param>
      </memberdef>
      <memberdef kind="function" id="function3">
        <type>semantic_version</type>
        <name>version</name>
        <qualifiedname>example_docs::meta::version</qualifiedname>
      </memberdef>
      <memberdef kind="function" id="function4">
        <type>static_array&lt;T, sizeof...(Args)&gt;</type>
        <name>to_static_array</name>
        <qualifiedname>example_docs::meta::to_static_array</qualifiedname>
        <param><type>Args &amp;&amp;...</type><declname>args</declname></param>
      </memberdef>
      <memberdef kind="function" id="guide1">
        <type></type>
        <name>box</name>
        <qualifiedname>example_docs::meta::box</qualifiedname>
        <param><type>int</type><declname>value</declname></param>
      </memberdef>
      <memberdef kind="function" id="function5">
        <type>bool</type>
        <name>operator&lt;</name>
        <qualifiedname>example_docs::meta::operator&lt;</qualifiedname>
        <param><type>box const &amp;</type><declname>left</declname></param>
        <param><type>box const &amp;</type><declname>right</declname></param>
      </memberdef>
    </sectiondef>
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )
    generated_api = api_docs / "generated"
    generated_api.mkdir(parents=True, exist_ok=True)
    (generated_api / "library_root.rst").write_text("old noisy root\n", encoding="utf-8")
    (generated_api / "namespaceexample__docs.rst").write_text(
        ".. doxygennamespace:: example_docs\n", encoding="utf-8"
    )
    (generated_api / "namespaceexample__docs_1_1meta.rst").write_text(
        """\
.. doxygennamespace:: example_docs::meta

Classes
-------

- :ref:`Struct semantic_version <exhale_struct_struct1>`

Enums
-----

- :ref:`Enum release_type <exhale_enum_enum1>`

Functions
---------

- :ref:`Function example_docs::meta::version <exhale_function_function1>`
""",
        encoding="utf-8",
    )
    (generated_api / "file_view_hierarchy.rst.include").write_text(
        "* Directory example_docs\n", encoding="utf-8"
    )
    (generated_api / "unabridged_api.rst.include").write_text(
        """\
.. toctree::
   :maxdepth: 1

   namespaceexample__docs.rst
   namespaceexample__docs_1_1meta.rst
   struct1.rst
   enum1.rst
   function1.rst
   function_unique.rst
   function_guide.rst
   function_operator.rst
   define1.rst
""",
        encoding="utf-8",
    )
    (generated_api / "struct1.rst").write_text(
        """\
.. _exhale_struct_struct1:

Struct example_docs::meta::semantic_version
===========================================

Struct Documentation
--------------------

.. doxygenstruct:: example_docs::meta::semantic_version
""",
        encoding="utf-8",
    )
    (generated_api / "enum1.rst").write_text(
        """\
.. _exhale_enum_enum1:

Enum example_docs::meta::release_type
=====================================

Enum Documentation
------------------

.. doxygenenum:: example_docs::meta::release_type
""",
        encoding="utf-8",
    )
    (generated_api / "function1.rst").write_text(
        """\
.. _exhale_function_function1:

Function example_docs::meta::version
====================================

Function Documentation
----------------------

.. doxygenfunction:: example_docs::meta::version
""",
        encoding="utf-8",
    )
    (generated_api / "function_unique.rst").write_text(
        """\
.. _exhale_function_function4:

Function example_docs::meta::to_static_array
============================================

Function Documentation
----------------------

.. doxygenfunction:: example_docs::meta::to_static_array(Args&&...)
""",
        encoding="utf-8",
    )
    (generated_api / "function_guide.rst").write_text(
        """\
.. _exhale_function_guide1:

Function example_docs::meta::box
================================

Function Documentation
----------------------

.. doxygenfunction:: example_docs::meta::box(int)
""",
        encoding="utf-8",
    )
    (generated_api / "function_operator.rst").write_text(
        """\
.. _exhale_function_function5:

Function example_docs::meta::operator<
======================================

Function Documentation
----------------------

.. doxygenfunction:: example_docs::meta::operator<(box const&, box const&)
""",
        encoding="utf-8",
    )
    (generated_api / "define1.rst").write_text(
        """\
.. _exhale_define_define1:

Define TESTEXAMPLE_DOCS_FEATURE
===============================

Define Documentation
--------------------

.. doxygendefine:: TESTEXAMPLE_DOCS_FEATURE
""",
        encoding="utf-8",
    )
    module._prepare_api_landing(current_app)
    overview_text = (generated_api / "api_namespace_overview.rst.include").read_text(
        encoding="utf-8"
    )
    assert ":api-kind:`N` :ref:`example_docs <namespace_example_docs>`" in overview_text
    assert ":api-kind:`N` :ref:`meta <namespace_example_docs__meta>`" in overview_text
    assert "* :api-kind:`N` :ref:`example_docs <namespace_example_docs>`\n\n  * :api-kind:`N`" in overview_text
    assert "  * :api-kind:`N` :ref:`meta <namespace_example_docs__meta>`\n\n    * :api-kind:`" in overview_text
    assert overview_text.count("to_string()") == 1
    assert ":api-kind:`F` :doc:`to_string() </generated/api_overload_example_docs_meta_to_string>`" in overview_text
    overload_text = (generated_api / "api_overload_example_docs_meta_to_string.rst").read_text(
        encoding="utf-8"
    )
    assert overload_text.startswith("to_string\n=========\n")
    assert "Function example_docs::meta::to_string" not in overload_text
    assert ":cpp:func:`to_string(semantic_version) <std::string_view example_docs::meta::to_string(semantic_version)>`" in overload_text
    assert ":cpp:func:`to_string(release_type) <std::string_view example_docs::meta::to_string(release_type)>`" in overload_text
    assert ":api-kind:`F` :cpp:func:`version() <example_docs::meta::version>`" in overview_text
    assert ":api-kind:`S` :cpp:struct:`semantic_version <example_docs::meta::semantic_version>`" in overview_text
    assert ":api-kind:`E` :cpp:enum:`release_type <example_docs::meta::release_type>`" in overview_text
    assert ":api-kind:`K` :cpp:concept:`sortable <example_docs::meta::sortable>`" in overview_text
    assert ":api-kind:`S` :cpp:struct:`tag_result\\< Tag, Args... > <example_docs::meta::tag_result< Tag, Args... >>`" in overview_text
    assert ":api-kind:`F` :cpp:func:`operator\\<() <example_docs::meta::operator<>`" in overview_text
    assert ":api-kind:`S` :cpp:struct:`box <example_docs::meta::box>`" in overview_text
    assert ":api-kind:`F` :cpp:func:`box() <example_docs::meta::box>`" not in overview_text
    landing_text = (generated_api / "api_landing.rst.include").read_text(encoding="utf-8")
    assert "Namespace hierarchy" in landing_text
    assert "Class Hierarchy" not in landing_text
    assert "Full API" not in landing_text
    assert landing_text.count("/generated/file_view_hierarchy.rst.include") == 1
    assert "   :hidden:" in landing_text
    assert "   /generated/namespaceexample__docs" in landing_text
    root_text = (generated_api / "library_root.rst").read_text(encoding="utf-8")
    assert root_text == ":orphan:\n"
    unique_function_page = (generated_api / "function_unique.rst").read_text(encoding="utf-8")
    assert ".. doxygenfunction:: example_docs::meta::to_static_array\n" in unique_function_page
    assert "Args&&..." not in unique_function_page
    assert not (generated_api / "function_guide.rst").exists()
    assert "/generated/function_guide" not in landing_text
    concept_page = generated_api / "besa_concept_conceptexample__docs_1_1meta_1asortable.rst"
    assert concept_page.is_file()
    concept_text = concept_page.read_text(encoding="utf-8")
    assert ".. doxygenconcept:: example_docs::meta::sortable" in concept_text
    assert "/generated/besa_concept_conceptexample__docs_1_1meta_1asortable" in landing_text

    # Historical refs from before the landing-page merge still point index.rst at library_root.rst.
    # Current BESA configuration must continue to render those old refs without changing their source.
    (api_docs / "index.rst").write_text(
        "API reference\n=============\n\n.. toctree::\n\n   generated/library_root\n",
        encoding="utf-8",
    )
    (generated_api / "library_root.rst").write_text("old noisy root\n", encoding="utf-8")
    module._prepare_api_landing(current_app)
    legacy_root = (generated_api / "library_root.rst").read_text(encoding="utf-8")
    assert legacy_root.startswith("example_docs API\n================\n")
    assert "Namespace hierarchy" in legacy_root
    assert "api_landing.rst.include" not in legacy_root

    struct_page = (generated_api / "struct1.rst").read_text(encoding="utf-8")
    enum_page = (generated_api / "enum1.rst").read_text(encoding="utf-8")
    function_page = (generated_api / "function1.rst").read_text(encoding="utf-8")
    assert struct_page.startswith(".. _exhale_struct_struct1:\n\nsemantic_version\n================")
    assert enum_page.startswith(".. _exhale_enum_enum1:\n\nrelease_type\n============")
    assert function_page.startswith(".. _exhale_function_function1:\n\nversion\n=======")
    assert "Documentation\n" not in struct_page
    assert "Documentation\n" not in enum_page
    assert "Documentation\n" not in function_page
    assert ".. doxygenstruct:: example_docs::meta::semantic_version" in struct_page
    assert ".. doxygenenum:: example_docs::meta::release_type" in enum_page
    assert ".. doxygenfunction:: example_docs::meta::version" in function_page
    root_namespace_page = (generated_api / "namespaceexample__docs.rst").read_text(
        encoding="utf-8"
    )
    assert "Members\n-------" in root_namespace_page
    assert ":api-kind:`N` :ref:`meta <namespace_example_docs__meta>`" in root_namespace_page
    assert ":api-kind:`S` :cpp:struct:`semantic_version <example_docs::meta::semantic_version>`" in root_namespace_page
    assert ":api-kind:`E` :cpp:enum:`release_type <example_docs::meta::release_type>`" in root_namespace_page
    assert ":api-kind:`F` :cpp:func:`version() <example_docs::meta::version>`" in root_namespace_page

    namespace_page = (generated_api / "namespaceexample__docs_1_1meta.rst").read_text(
        encoding="utf-8"
    )
    assert "Members\n-------" in namespace_page
    assert ":api-kind:`S` :cpp:struct:`semantic_version <example_docs::meta::semantic_version>`" in namespace_page
    assert ":api-kind:`E` :cpp:enum:`release_type <example_docs::meta::release_type>`" in namespace_page
    assert ":api-kind:`F` :cpp:func:`version() <example_docs::meta::version>`" in namespace_page
    assert ":api-kind:`K` :cpp:concept:`sortable <example_docs::meta::sortable>`" in namespace_page
    assert ":api-kind:`S` :cpp:struct:`tag_result\\< Tag, Args... > <example_docs::meta::tag_result< Tag, Args... >>`" in namespace_page
    assert ":api-kind:`F` :cpp:func:`box() <example_docs::meta::box>`" not in namespace_page
    assert "Struct semantic_version" not in namespace_page
    assert "Enum release_type" not in namespace_page
    assert "Function example_docs::meta::version" not in namespace_page

    define_page = (generated_api / "define1.rst").read_text(encoding="utf-8")
    assert define_page.startswith(
        ".. _exhale_define_define1:\n\nTESTEXAMPLE_DOCS_FEATURE\n========================"
    )
    assert "Define TESTEXAMPLE_DOCS_FEATURE" not in define_page
    assert "Define Documentation" not in define_page
    assert ".. doxygendefine:: TESTEXAMPLE_DOCS_FEATURE" in define_page

    # Reproduce sphinx-multiversion's important shape: conf.py remains in the current checkout while
    # app.srcdir points at a different checkout. The generated Doxyfile must use only that checkout.
    historical = tmp_path / "historical"
    historical_api = historical / "api-docs"
    historical_api.mkdir(parents=True)
    historical_header = historical / "src" / "cpp" / "include" / "example_docs" / "historical.hpp"
    historical_header.parent.mkdir(parents=True)
    historical_header.write_text("#ifndef EXAMPLE_DOCS_HISTORICAL_HPP\n#define EXAMPLE_DOCS_HISTORICAL_HPP\n#endif\n", encoding="utf-8")
    shutil.copytree(project / "cmake" / "besa", historical / "cmake" / "besa")
    (historical / "CMakeLists.txt").write_text(
        """\
cmake_minimum_required(VERSION 3.26.1)
project(example_docs VERSION 9.8.7 LANGUAGES NONE)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
file(MAKE_DIRECTORY "${PROJECT_BINARY_DIR}/api-docs")
configure_file(
  "${PROJECT_SOURCE_DIR}/api-docs/Doxyfile.in"
  "${PROJECT_BINARY_DIR}/api-docs/Doxyfile"
  @ONLY
)
list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/besa")
find_package(besa CONFIG REQUIRED)
set(PROJECT_FEATURES "" CACHE STRING "")
set(PROJECT_DEVTOOLS "none" CACHE STRING "")
set(PROJECT_WARNINGS "essential" CACHE STRING "")
set(TEST_MODES "" CACHE STRING "")
set(BUILD_TESTING OFF CACHE BOOL "")
set(RELEASE_TYPE "release" CACHE STRING "")
set(RELEASE_REVISION "1" CACHE STRING "")
besa_features_add(FEATURES user-docs)
besa_configure_complete()
besa_generated_include_add(NAME schema OUTPUT_VARIABLE SCHEMA_INCLUDE)
file(MAKE_DIRECTORY "${SCHEMA_INCLUDE}/example_docs")
file(WRITE "${SCHEMA_INCLUDE}/example_docs/schema.hpp" "#ifndef EXAMPLE_DOCS_SCHEMA_HPP\n#define EXAMPLE_DOCS_SCHEMA_HPP\n#endif\n")
""",
        encoding="utf-8",
    )
    (historical_api / "Doxyfile.in").write_text(
        (api_docs / "Doxyfile.in").read_text(encoding="utf-8"), encoding="utf-8"
    )

    historical_app = FakeApp(historical_api)
    module._prepare_api(historical_app)
    historical_output = module._doxygen_output_for(historical)
    historical_text = (historical_output / "Doxyfile").read_text(encoding="utf-8")
    assert 'PROJECT_NUMBER = "9.8.7"' in historical_text
    historical_configured_build = historical_output / "project-build"
    assert f'CLANG_DATABASE_PATH    = "{historical_configured_build}"' in historical_text
    historical_public = historical_output / "public-include"
    assert str(historical_public).replace("\\", "/") in historical_text
    assert str(historical / "src").replace("\\", "/") not in historical_text
    assert str(project / "src").replace("\\", "/") not in historical_text
    assert (historical_public / "example_docs" / "historical.hpp").is_file()
    historical_version = historical_public / "example_docs" / "version.hpp"
    assert historical_version.is_file()
    assert 'return "9.8.7";' in historical_version.read_text(encoding="utf-8")
    assert (historical_public / "example_docs" / "schema.hpp").is_file()
    assert historical_app.config.release == "9.8.7"
    assert historical_app.config.breathe_projects == {
        "example_docs": str(historical_output / "xml")
    }
    assert historical_app.config.exhale_args["containmentFolder"] == str(
        historical_api / "generated"
    )
    assert historical_app.config.exhale_args["doxygenStripFromPath"] == str(historical_public)
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

    # The file-oriented API mirrors the installed include namespace. Generated version.hpp is part
    # of that public tree, while repository-only src/cpp/include path components stay hidden.
    main_api_text = html_text(raw_api / "main")
    assert "version.hpp" in main_api_text
    assert "example_multidocs/example_multidocs.hpp" in main_api_text
    assert "src/cpp/include" not in main_api_text

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
    import re

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

    driver = project / "cmake" / "besa" / "userdocs" / "multiversion.py"
    spec = importlib.util.spec_from_file_location("example_versions_driver", driver)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    all_branches, all_tags = module.selected_refs(project, "all")
    assert all_branches == r"^(?:main)$"
    assert all_tags == r"^.*$"

    latest_branches, latest_tags = module.selected_refs(project, "latest:3")
    assert re.fullmatch(latest_branches, "main")
    assert not re.fullmatch(latest_branches, "maintenance")
    assert re.fullmatch(latest_tags, "v0.11.0")
    assert re.fullmatch(latest_tags, "v0.11.0-rc.1")
    assert re.fullmatch(latest_tags, "v0.10.0")
    assert not re.fullmatch(latest_tags, "v0.9.0")
    assert not re.fullmatch(latest_tags, "nightly")

    _range_branches, ranged_tags = module.selected_refs(project, "range:>=0.9,<0.11")
    assert re.fullmatch(ranged_tags, "v0.9.0")
    assert re.fullmatch(ranged_tags, "v0.10.0")
    assert re.fullmatch(ranged_tags, "v0.11.0-rc.1")
    assert not re.fullmatch(ranged_tags, "v0.8.0")
    assert not re.fullmatch(ranged_tags, "v0.11.0")

    explicit_branches, explicit_tags = module.selected_refs(
        project, "refs:v0.8.0,maintenance"
    )
    assert re.fullmatch(explicit_branches, "main")
    assert re.fullmatch(explicit_branches, "maintenance")
    assert re.fullmatch(explicit_tags, "v0.8.0")
    assert not re.fullmatch(explicit_tags, "v0.9.0")

    with pytest.raises(RuntimeError, match="unknown BESA API Git refs"):
        module.selected_refs(project, "refs:v9.9.9")

    monkeypatch.delenv("BESA_API_VERSIONS", raising=False)
    properdocs = project / "properdocs.yml"
    properdocs.write_text(
        properdocs.read_text(encoding="utf-8").replace(
            "besa_api_versions: all", "besa_api_versions: latest:2"
        ),
        encoding="utf-8",
    )
    assert module._selector(project) == "latest:2"


@pytest.mark.cpp
def test_multiversion_driver_neutralizes_selector_inside_historical_configs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util

    project = cpp_generate(tmp_path, "example_versions_driver")
    driver = project / "cmake" / "besa" / "userdocs" / "multiversion.py"
    spec = importlib.util.spec_from_file_location("example_versions_runtime_driver", driver)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setenv("BESA_API_VERSIONS", "latest:2")
    monkeypatch.setattr(
        module,
        "selected_refs",
        lambda _root, selector: (r"^(?:main)$", r"^(?:v0\.3\.0|v1\.0\.0)$")
        if selector == "latest:2"
        else (_ for _ in ()).throw(AssertionError(selector)),
    )

    calls = []

    def fake_run(command, *, cwd, check, env):
        calls.append((command, cwd, check, env))

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module.main(
        [
            "--sphinx-multiversion",
            "/bin/sphinx-multiversion",
            "--project-root",
            str(project),
            "--source-directory",
            "api-docs",
            "--output-directory",
            str(tmp_path / "out"),
            "--",
            "-W",
            "--keep-going",
        ]
    ) == 0

    assert len(calls) == 1
    command, cwd, check, environment = calls[0]
    assert cwd == project.resolve()
    assert check is True
    assert environment["BESA_API_VERSIONS"] == "all"
    assert environment["BESA_SMV_BRANCH_WHITELIST"] == r"^(?:main)$"
    assert environment["BESA_SMV_TAG_WHITELIST"] == r"^(?:v0\.3\.0|v1\.0\.0)$"
    assert not any(argument.startswith("smv_branch_whitelist=") for argument in command)
    assert not any(argument.startswith("smv_tag_whitelist=") for argument in command)


@pytest.mark.cpp
def test_multiversion_api_metadata_is_generated(tmp_path: Path) -> None:
    output = tmp_path / "api"
    for version in ("main", "1.0.0", "2.0.0", "release/3.0"):
        (output / version / "_static").mkdir(parents=True)
        (output / version / "index.html").write_text(version, encoding="utf-8")

    # Nested pages belong to a version's page manifest; they must not be mistaken for refs.
    (output / "main" / "detail").mkdir()
    (output / "main" / "detail" / "index.html").write_text("detail", encoding="utf-8")

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

    import json

    metadata = json.loads((output / "versions.json").read_text(encoding="utf-8"))
    assert metadata["default"] == "main"
    assert metadata["versions"][0] == {
        "name": "main",
        "url": "main/",
        "pages": ["detail/index.html", "index.html"],
    }
    assert {item["name"] for item in metadata["versions"]} == {
        "main",
        "1.0.0",
        "2.0.0",
        "release/3.0",
    }
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
    assert 'depends_on("doxygen+libclang", when="+docs")' in environment_package
    assert 'depends_on("py-sphinx@:8", when="+docs")' in environment_package
    assert 'depends_on("py-breathe", when="+docs")' in environment_package
    assert 'depends_on("py-exhale", when="+docs")' in environment_package
    assert 'depends_on("py-pydata-sphinx-theme", when="+docs")' in environment_package
    assert 'depends_on("py-sphinx-multiversion", when="+docs")' in environment_package
    assert 'depends_on("properdocs", when="+docs")' in environment_package
    for toolchain in ("cuda", "hip"):
        assert f'variant("{toolchain}"' not in environment_package
        assert f'depends_on("{toolchain}"' not in environment_package
    assert not (repo / "packages" / "properdocs").exists()

    doxygen_package_path = repo / "packages" / "doxygen" / "package.py"
    assert doxygen_package_path.is_file()
    doxygen_package = doxygen_package_path.read_text(encoding="utf-8")
    assert "from spack_repo.builtin.packages.doxygen.package import Doxygen as BuiltinDoxygen" in doxygen_package
    assert "class Doxygen(BuiltinDoxygen):" in doxygen_package
    assert 'variant(\n        "libclang"' in doxygen_package
    assert 'depends_on("llvm+clang", when="+libclang")' in doxygen_package
    assert 'define_from_variant("use_libclang", "libclang")' in doxygen_package

    compile(environment_package, "dev_env/package.py", "exec")
    compile(doxygen_package, "doxygen/package.py", "exec")


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
    assert targets[-1] == "user.docs.multiversion:all"

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
    assert not re.search(r"/[0-9a-f]{40}/", context["besa_source_url"])

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


@pytest.mark.cpp
def test_generated_documentation_cross_references_are_semantic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util
    import json
    from types import SimpleNamespace

    project = cpp_generate(tmp_path, "example_xrefs")
    api_docs = project / "api-docs"

    spec = importlib.util.spec_from_file_location("example_xrefs_conf", api_docs / "conf.py")
    assert spec is not None and spec.loader is not None
    api_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api_module)

    class FakeCppDomain:
        @staticmethod
        def get_objects():
            return [
                (
                    "example_xrefs::meta::build()",
                    "example_xrefs::meta::build()",
                    "function",
                    "generated/function_build",
                    "_CPPv4N13example_xrefs4meta5buildEv",
                    1,
                )
            ]

    class FakeEnv:
        @staticmethod
        def get_domain(name: str):
            assert name == "cpp"
            return FakeCppDomain()

    class FakeBuilder:
        @staticmethod
        def get_target_uri(docname: str) -> str:
            return f"{docname}.html"

    output = tmp_path / "api-output"
    output.mkdir()
    app = SimpleNamespace(
        env=FakeEnv(),
        builder=FakeBuilder(),
        outdir=str(output),
        config=SimpleNamespace(release="0.1.0"),
    )
    api_module._write_api_symbol_aliases(app, None)

    alias = output / "_symbols" / "example_xrefs" / "meta" / "build" / "index.html"
    assert alias.is_file()
    alias_text = alias.read_text(encoding="utf-8")
    assert "../../../../generated/function_build.html#_CPPv4" in alias_text

    symbols = json.loads((output / "symbols.json").read_text(encoding="utf-8"))
    assert symbols["symbols"]["example_xrefs::meta::build"].startswith(
        "generated/function_build.html#"
    )

    hook_path = project / "properdocs_multiversion_hook.py"
    hook_spec = importlib.util.spec_from_file_location("example_xrefs_hook", hook_path)
    assert hook_spec is not None and hook_spec.loader is not None
    hook = importlib.util.module_from_spec(hook_spec)
    hook_spec.loader.exec_module(hook)

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

    rendered_versioned = hook.on_page_markdown(
        "Released metadata: @apidocs[v0.2.0]::example_xrefs::meta::build.",
        page,
        {"extra": {"besa_api_version": "main"}},
    )
    assert (
        "[`example_xrefs::meta::build`]"
        "(api/v0.2.0/_symbols/example_xrefs/meta/build/)"
    ) in rendered_versioned

    hook.CURRENT_API_BUILD_DIRECTORY = output
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
    assert "/api-docs/generated/" not in gitignore
    assert "/site/" not in gitignore
    ignored_entries = {line.strip() for line in gitignore.splitlines() if line.strip() and not line.startswith("#")}
    assert "spack.yaml" not in ignored_entries
    assert "spack.lock" not in ignored_entries
    assert "spack/" not in ignored_entries
