// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

#include <cstddef>
#include <stdexcept>
#include <string>
#include <testvorlage/prova/cmdline.hpp>
#include <utility>
#include <vector>

namespace testvorlage::prova::cmdline {

auto parse(int argc, char** argv) -> result
{
  bool input_specified = false;
  bool output_specified = false;
  std::string input;
  std::string output;
  std::vector<std::string> residual;
  residual.reserve(static_cast<std::size_t>(argc));

  for (int i = 0; i < argc; ++i) {
    auto const argument = std::string(argv[i]);
    if (argument == "--input" || argument == "--output") {
      if (i + 1 >= argc) {
        throw std::runtime_error("Expected an argument to " + argument);
      }

      auto& specified = argument == "--input" ? input_specified : output_specified;
      if (specified) {
        throw std::runtime_error(argument + " specified more than once");
      }
      specified = true;

      auto& value = argument == "--input" ? input : output;
      value = argv[++i];
      continue;
    }

    residual.push_back(argument);
  }

  if (!input_specified) {
    throw std::runtime_error("Input not specified");
  }
  if (!output_specified) {
    throw std::runtime_error("Output not specified");
  }

  return {testvorlage::prova::data::path(std::move(input), std::move(output)), std::move(residual)};
}

} // namespace testvorlage::prova::cmdline
