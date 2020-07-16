//  -----------------------------------------------------------------------------
// This file was autogenerated by symforce. Do NOT modify by hand.
// -----------------------------------------------------------------------------
#pragma once

#include <Eigen/Dense>

namespace cam {

/**
 * Camera with a given camera calibration and an optionally specified image size.
 * If the image size is specified, we use it to check whether pixels (either given or computed by
 * projection of 3D points into the image frame) are in the image frame and thus valid/invalid.
 */
template <typename CameraCalType>
class Camera {
 public:
  using Scalar = typename CameraCalType::Scalar;

  Camera(const CameraCalType& calibration, const Eigen::Vector2i& image_size=Eigen::Vector2i(-1, -1))
    : calibration_(calibration),
      image_size_(image_size) {
  }
  
  /**
  * Project a 3D point in the camera frame into 2D pixel coordinates.
  *
  * Return:
  *     pixel: (x, y) coordinate in pixels if valid
  *     is_valid: 1 if the operation is within bounds (including image_size bounds) else 0
  *
  */
  Eigen::Matrix<Scalar, 2, 1> PixelFromCameraPoint(const Eigen::Matrix<Scalar, 3, 1>& point, const Scalar epsilon, Scalar* const is_valid) const {
    const Eigen::Matrix<Scalar, 2, 1> pixel = calibration_.PixelFromCameraPoint(point, epsilon, is_valid);
    if (is_valid != nullptr) {
      *is_valid *= MaybeCheckInView(pixel);
    }
    return pixel;
  }
  
  /**
  * Backproject a 2D pixel coordinate into a 3D ray in the camera frame.
  *
  * NOTE: If image_size is specified and the given pixel is out of
  * bounds, is_valid will be set to zero.
  *
  * Return:
  *     camera_ray: The ray in the camera frame (NOT normalized)
  *     is_valid: 1 if the operation is within bounds else 0
  *
  */
  Eigen::Matrix<Scalar, 3, 1> CameraRayFromPixel(const Eigen::Matrix<Scalar, 2, 1>& pixel, const Scalar epsilon, Scalar* const is_valid) const {
    const Eigen::Matrix<Scalar, 3, 1> camera_ray = calibration_.CameraRayFromPixel(pixel, epsilon, is_valid);
    if (is_valid != nullptr) {
      *is_valid *= MaybeCheckInView(pixel);
    }
    return camera_ray;
  }
  
  Scalar MaybeCheckInView(const Eigen::Matrix<Scalar, 2, 1>& pixel) const {
    if(image_size_[0] <= 0 || image_size_[1] <= 0) {
      // image size is not defined, don't check if the pixel is in view
      return 1;
    }
    return InView(pixel, image_size_);
  }
  
  /**
  * Returns 1.0 if the pixel coords are in bounds of the image, 0.0 otherwise.
  *
  */
  static Scalar InView(const Eigen::Matrix<Scalar, 2, 1>& pixel, const Eigen::Matrix<int, 2, 1>& image_size) {
    const bool x_in_view = (pixel[0] >= 0) && (pixel[0] <= image_size[0] - 1);
    const bool y_in_view = (pixel[1] >= 0) && (pixel[1] <= image_size[1] - 1);
    return (x_in_view && y_in_view) ? 1 : 0;
  }

  CameraCalType Calibration() const {
    return calibration_;
  }

  Eigen::Matrix<int, 2, 1> ImageSize() const {
    return image_size_;
  }

  private:
    CameraCalType calibration_;
    Eigen::Matrix<int, 2, 1> image_size_;
};

}  // namespace cam
