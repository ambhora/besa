// -------------------------------------------------------------------------------------------------
// SPDX-License-Identifier: Apache-2.0
// -------------------------------------------------------------------------------------------------

#include <functional>
#include <iostream>
#include <numeric>
#include <thread>
#include <vector>

void call_from_thread(unsigned int tid, unsigned int& output)
{
  std::cout << "Launched by thread " << tid << '\n';
  output = tid;
}

auto main() -> int
{
  auto const num_threads = std::thread::hardware_concurrency();
  std::vector<std::thread> t(num_threads);
  std::vector<unsigned int> t_result(num_threads, 0);

  // Launch a group of threads
  for (unsigned int i = 0; i < num_threads; ++i) {
    t[i] = std::thread(call_from_thread, i, std::ref(t_result[i]));
  }

  std::cout << "Launched from the main concurrently with threads\n";

  // Join the threads with the main thread
  for (unsigned i = 0; i < num_threads; ++i) {
    t[i].join();
  }

  unsigned int const result
    = std::accumulate(t_result.begin(), t_result.end(), static_cast<unsigned int>(0));
  std::cout << "Launched from the main\n";

  if (result != (num_threads * (num_threads - 1)) / 2) {
    return EXIT_FAILURE;
  }

  return EXIT_SUCCESS;
}
