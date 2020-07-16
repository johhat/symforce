// ----------------------------------------------------------------------------
// This file was autogenerated by symforce. Do NOT modify by hand.
// ----------------------------------------------------------------------------
#pragma once

#include <cassert>
#include <vector>

namespace codegen_multi_function {
namespace StorageOps {

template<>
inline size_t StorageDim<outputs_2_t>() {
  return 1;
};

template<>
inline void ToStorage<outputs_2_t>(const outputs_2_t& value, std::vector<double>* vec) {
  assert(vec != nullptr);
  std::vector<double>& v = (*vec);
  v.resize(1);

  v[0] = value.foo;
}

template<typename Container>
void FromStorage(const Container& elements, outputs_2_t* out) {
  assert(out != nullptr);
  out->foo = elements[0];
}

}  // namespace StorageOps
}  // namespace codegen_multi_function
