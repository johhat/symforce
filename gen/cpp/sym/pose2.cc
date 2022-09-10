// -----------------------------------------------------------------------------
// This file was autogenerated by symforce from template:
//     geo_package/CLASS.cc.jinja
// Do NOT modify by hand.
// -----------------------------------------------------------------------------

#include "./pose2.h"

namespace sym {

// Print implementations
std::ostream& operator<<(std::ostream& os, const Pose2d& a) {
  const Eigen::IOFormat fmt(Eigen::StreamPrecision, Eigen::DontAlignCols, ", ", "\n", "[", "]");
  os << "<Pose2d " << a.Data().transpose().format(fmt) << ">";
  return os;
}
std::ostream& operator<<(std::ostream& os, const Pose2f& a) {
  const Eigen::IOFormat fmt(Eigen::StreamPrecision, Eigen::DontAlignCols, ", ", "\n", "[", "]");
  os << "<Pose2f " << a.Data().transpose().format(fmt) << ">";
  return os;
}

}  // namespace sym

// --------------------------------------------------------------------------
// Custom generated methods
// --------------------------------------------------------------------------

template <typename Scalar>
sym::Rot2<Scalar> sym::Pose2<Scalar>::Rotation() const {
  // Total ops: 0

  // Input arrays
  const Eigen::Matrix<Scalar, 4, 1>& _self = Data();

  // Intermediate terms (0)

  // Output terms (1)
  Eigen::Matrix<Scalar, 2, 1> _res;

  _res[0] = _self[0];
  _res[1] = _self[1];

  return sym::Rot2<Scalar>(_res);
}

template <typename Scalar>
Eigen::Matrix<Scalar, 2, 1> sym::Pose2<Scalar>::Position() const {
  // Total ops: 0

  // Input arrays
  const Eigen::Matrix<Scalar, 4, 1>& _self = Data();

  // Intermediate terms (0)

  // Output terms (1)
  Eigen::Matrix<Scalar, 2, 1> _res;

  _res(0, 0) = _self[2];
  _res(1, 0) = _self[3];

  return _res;
}

template <typename Scalar>
Eigen::Matrix<Scalar, 2, 1> sym::Pose2<Scalar>::ComposeWithPoint(
    const Eigen::Matrix<Scalar, 2, 1>& right) const {
  // Total ops: 8

  // Input arrays
  const Eigen::Matrix<Scalar, 4, 1>& _self = Data();

  // Intermediate terms (0)

  // Output terms (1)
  Eigen::Matrix<Scalar, 2, 1> _res;

  _res(0, 0) = _self[0] * right(0, 0) - _self[1] * right(1, 0) + _self[2];
  _res(1, 0) = _self[0] * right(1, 0) + _self[1] * right(0, 0) + _self[3];

  return _res;
}

template <typename Scalar>
Eigen::Matrix<Scalar, 2, 1> sym::Pose2<Scalar>::InverseCompose(
    const Eigen::Matrix<Scalar, 2, 1>& point) const {
  // Total ops: 14

  // Input arrays
  const Eigen::Matrix<Scalar, 4, 1>& _self = Data();

  // Intermediate terms (0)

  // Output terms (1)
  Eigen::Matrix<Scalar, 2, 1> _res;

  _res(0, 0) =
      -_self[0] * _self[2] + _self[0] * point(0, 0) - _self[1] * _self[3] + _self[1] * point(1, 0);
  _res(1, 0) =
      -_self[0] * _self[3] + _self[0] * point(1, 0) + _self[1] * _self[2] - _self[1] * point(0, 0);

  return _res;
}

template <typename Scalar>
Eigen::Matrix<Scalar, 3, 3> sym::Pose2<Scalar>::ToHomogenousMatrix() const {
  // Total ops: 1

  // Input arrays
  const Eigen::Matrix<Scalar, 4, 1>& _self = Data();

  // Intermediate terms (0)

  // Output terms (1)
  Eigen::Matrix<Scalar, 3, 3> _res;

  _res(0, 0) = _self[0];
  _res(1, 0) = _self[1];
  _res(2, 0) = 0;
  _res(0, 1) = -_self[1];
  _res(1, 1) = _self[0];
  _res(2, 1) = 0;
  _res(0, 2) = _self[2];
  _res(1, 2) = _self[3];
  _res(2, 2) = 1;

  return _res;
}

// Explicit instantiation
template class sym::Pose2<double>;
template class sym::Pose2<float>;
