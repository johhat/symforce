// -----------------------------------------------------------------------------
// This file was autogenerated by symforce. Do NOT modify by hand.
// -----------------------------------------------------------------------------
#pragma once

#include "./codegen_multi_function_ns/inputs_t.h"
#include "./codegen_multi_function_ns/outputs_1_t.h"

#include "./codegen_multi_function_ns/storage_ops.h"

namespace codegen_multi_function_ns {


/**
* This function was autogenerated. Do not modify by hand.
*
* Arg type(s): Values
* Return type(s): Values
*
*/
template <typename Scalar>
void CodegenMultiFunctionTest1(const codegen_multi_function_ns::inputs_t& inputs, codegen_multi_function_ns::outputs_1_t* const outputs_1) {
    // Input arrays
    std::vector<Scalar> inputs_array;
    codegen_multi_function_ns::StorageOps::ToStorage<codegen_multi_function_ns::inputs_t>(inputs, &inputs_array);
    const Eigen::Matrix<Scalar, 9, 1> _inputs(inputs_array.data());
    assert( outputs_1 != nullptr );

    // Intermediate terms (1)
    const Scalar _tmp0 = (_inputs[0] * _inputs[0]);

    // Output terms (1)
    Eigen::Matrix<Scalar, 2, 1> _outputs_1;
    _outputs_1[0] = _inputs[5] + _tmp0;
    _outputs_1[1] = _inputs[6] + _tmp0 + std::sin(_inputs[1]);
    codegen_multi_function_ns::StorageOps::FromStorage<Eigen::Matrix<Scalar, 2, 1>>(_outputs_1, outputs_1);


}

}  // namespace codegen_multi_function_ns
