//  -----------------------------------------------------------------------------
// This file was autogenerated by symforce. Do NOT modify by hand.
// -----------------------------------------------------------------------------
#pragma once

#include <ostream>
#include <random>
#include <vector>
#include <Eigen/Dense>

#include <geo/ops/storage_ops.h>

namespace cam {

/**
 * Autogenerated C++ implementation of <class 'symforce.cam.atan_camera_cal.ATANCameraCal'>.
 *
 * ATAN camera with 5 parameters [fx, fy, cx, cy, omega].
 * (fx, fy) representing focal length, (cx, cy) representing principal point,
 * and omega representing the distortion parameter.
 *
 * See here for more details:
 * https://hal.inria.fr/inria-00267247/file/distcalib.pdf
 */
template <typename ScalarType>
class ATANCameraCal {
 public:
  // Typedefs
  using Scalar = ScalarType;
  using Self = ATANCameraCal<Scalar>;
  using DataVec = Eigen::Matrix<Scalar, 5, 1>;

  // Construct from data vec
  explicit ATANCameraCal(const DataVec& data) : data_(data) {}

  // Access underlying storage as const
  inline const DataVec& Data() const {
      return data_;
  }

  // --------------------------------------------------------------------------
  // StorageOps concept
  // --------------------------------------------------------------------------

  static constexpr int32_t StorageDim() {
    return geo::StorageOps<Self>::StorageDim();
  }

  void ToStorage(std::vector<Scalar>* vec) const {
    return geo::StorageOps<Self>::ToStorage(*this, vec);
  }

  static ATANCameraCal FromStorage(const std::vector<Scalar>& vec) {
    return geo::StorageOps<Self>::FromStorage(vec);
  }

  // --------------------------------------------------------------------------
  // Camera model methods
  // --------------------------------------------------------------------------
  
  /**
  * Project a 3D point in the camera frame into 2D pixel coordinates.
  *
  * Return:
  *     pixel: (x, y) coordinate in pixels if valid
  *     is_valid: 1 if the operation is within bounds else 0
  *
  */
  Eigen::Matrix<Scalar, 2, 1> PixelFromCameraPoint(const Eigen::Matrix<Scalar, 3, 1>& point, const Scalar epsilon, Scalar* const is_valid) const;
  
  /**
  * Backproject a 2D pixel coordinate into a 3D ray in the camera frame.
  *
  * Return:
  *     camera_ray: The ray in the camera frame (NOT normalized)
  *     is_valid: 1 if the operation is within bounds else 0
  *
  */
  Eigen::Matrix<Scalar, 3, 1> CameraRayFromPixel(const Eigen::Matrix<Scalar, 2, 1>& pixel, const Scalar epsilon, Scalar* const is_valid) const;

  // --------------------------------------------------------------------------
  // General Helpers
  // --------------------------------------------------------------------------

  bool IsApprox(const Self& b, const Scalar tol) const {
    // isApprox is multiplicative so we check the norm for the exact zero case
    // https://eigen.tuxfamily.org/dox/classEigen_1_1DenseBase.html#ae8443357b808cd393be1b51974213f9c
    if (b.Data() == DataVec::Zero()) {
      return Data().norm() < tol;
    }

    return Data().isApprox(b.Data(), tol);
  }

  template <typename ToScalar>
  ATANCameraCal<ToScalar> Cast() const {
    return ATANCameraCal<ToScalar>(Data().template cast<ToScalar>());
  }

  bool operator==(const ATANCameraCal& rhs) const {
    return data_ == rhs.Data();
  }

 protected:
  DataVec data_;
};

// Shorthand for scalar types
using ATANCameraCald = ATANCameraCal<double>;
using ATANCameraCalf = ATANCameraCal<float>;

}  // namespace cam

// Externs to reduce duplicate instantiation
extern template class cam::ATANCameraCal<double>;
extern template class cam::ATANCameraCal<float>;

// Print definitions
std::ostream& operator<<(std::ostream& os, const cam::ATANCameraCal<double>& a);
std::ostream& operator<<(std::ostream& os, const cam::ATANCameraCal<float>& a);

// Concept implementations for this class
#include "./ops/atan_camera_cal/storage_ops.h"
