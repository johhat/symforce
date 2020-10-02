import numpy as np

import symforce
from symforce import ops
from symforce.ops.interfaces import LieGroup
from symforce import sympy as sm
from symforce import types as _T  # We already have a Matrix.T which collides
from symforce import python_util


class Matrix(LieGroup):
    """
    Matrix type that inherits from the Sympy Matrix class. Care has been taken to allow this class
    to create fixed-size child classes like Matrix31. Anytime __new__ is called, the appropriate
    fixed size class is returned rather than the type of the arguments. The API is meant to parallel
    the way Eigen's C++ matrix classes work with dynamic and fixed sizes.

    References:

        https://docs.sympy.org/latest/tutorial/matrices.html
        https://eigen.tuxfamily.org/dox/group__TutorialMatrixClass.html
        https://en.wikipedia.org/wiki/Vector_space

    It is also treated as lie group that represents the linear space of two dimensional matrices
    under the *addition* operation. This causes some confusion between the naming of methods, such
    as `.identity()` and `.inverse()`. The linear algebra equivalents are available at
    `.matrix_identity()` and `.matrix_inverse()`. Splitting the matrix type and the lie group ops
    is a possible action to make this better.
    """

    # Type that represents this or any subclasses
    MatrixT = _T.TypeVar("MatrixT", bound="Matrix")

    # Static dimensions of this type. (-1, -1) means there is no size information, like if
    # we are using geo.Matrix directly instead of geo.Matrix31.
    # Once a matrix is constructed it should be of a type where the .shape instance variable matches
    # this class variable as a strong internal consistency check.
    SHAPE = (-1, -1)

    def __new__(cls, *args, **kwargs):
        # type: (_T.Any, _T.Any) -> Matrix
        """
        Beast of a method for creating a Matrix. Handles a variety of construction use cases
        and *always* returns a fixed size child class of Matrix rather than Matrix itself. The
        available construction options depend on whether cls is a fixed size type or not.

        Generally modeled after the Eigen interface, but must also support internal use within
        sympy and symengine which we cannot change.

        Examples:
            1) Matrix32()  # Zero constructed Matrix32
            2) Matrix(sm.Matrix([[1, 2], [3, 4]]))  # Matrix22 with [1, 2, 3, 4] data
            3A) Matrix([[1, 2], [3, 4]])  # Matrix22 with [1, 2, 3, 4] data
            3B) Matrix22([1, 2, 3, 4])  # Matrix22 with [1, 2, 3, 4] data (must matched fixed shape)
            3C) Matrix([1, 2, 3, 4])  # Matrix41 with [1, 2, 3, 4] data - column vector assumed
            4) Matrix(4, 3)  # Zero constructed Matrix43
            5) Matrix(2, 2, [1, 2, 3, 4])  # Matrix22 with [1, 2, 3, 4] data (first two are shape)
            6) Matrix(2, 2, lambda row, col: row + col)  # Matrix22 with [0, 1, 1, 2] data
            7) Matrix22(1, 2, 3, 4)  # Matrix22 with [1, 2, 3, 4] data (must match fixed length)
        """

        # 1) Default construction allowed for fixed size.
        if len(args) == 0:
            assert cls._is_fixed_size(), "Cannot default construct non-fixed matrix."
            return cls.zero()

        # 2) Construct with another Matrix - this is easy
        elif len(args) == 1 and hasattr(args[0], "is_Matrix") and args[0].is_Matrix:
            rows, cols = args[0].shape
            flat_list = list(args[0])

        # 3) If there's one argument and it's an array, works for fixed or dynamic size.
        elif len(args) == 1 and isinstance(args[0], (_T.Sequence, np.ndarray)):
            array = args[0]
            # 2D array, shape is known
            if len(array) > 0 and isinstance(array[0], (_T.Sequence, np.ndarray)):
                # 2D array of scalars
                assert not isinstance(
                    array[0][0], Matrix
                ), "Use Matrix.block_matrix to construct using matrices"
                rows, cols = len(array), len(array[0])
                assert all(len(arr) == cols for arr in array), "Inconsistent columns: {}".format(
                    args
                )
                flat_list = [v for row in array for v in row]

            # 1D array - if fixed size this must match data length. If not, assume column vec.
            else:
                if cls._is_fixed_size():
                    assert len(array) == cls.storage_dim(), "Gave args {} for {}".format(args, cls)
                    rows, cols = cls.SHAPE
                else:
                    # Only set the second dimension to 1 if the array is nonempty
                    if len(array) == 0:
                        rows, cols = 0, 0
                    else:
                        rows, cols = len(array), 1
                flat_list = list(array)

        # 4) If there are two arguments and this is not a fixed size matrix, treat it as a size
        # constructor with (rows, cols) arguments.
        # NOTE(hayk): I've had to override several routines on Matrix that in their symengine
        # versions construct a result with __class__(rows, cols), which for a fixed size type fails
        # here. We need it to fail because it's ambiguous in the case of geo.M21(10, 20) whether
        # the args are values or sizes. So I've overriden several operator methods to first convert
        # to an sm.Matrix, do the operation, then convert back.
        elif len(args) == 2 and cls.SHAPE == (-1, -1):
            rows, cols = args[0], args[1]
            assert isinstance(rows, int)
            assert isinstance(cols, int)
            flat_list = [0 for row in range(rows) for col in range(cols)]

        # 5) If there are two integer arguments and then a sequence, treat this as a shape and a
        # data list directly.
        elif len(args) == 3 and isinstance(args[-1], (np.ndarray, _T.Sequence)):
            assert isinstance(args[0], int), args
            assert isinstance(args[1], int), args
            rows, cols = args[0], args[1]
            assert len(args[2]) == rows * cols, "Inconsistent args: {}".format(args)
            flat_list = list(args[2])

        # 6) Two integer arguments plus a callable to initialize values based on (row, col)
        # NOTE(hayk): sympy.Symbol is callable, hence the last check.
        elif len(args) == 3 and callable(args[-1]) and not hasattr(args[-1], "is_Symbol"):
            assert isinstance(args[0], int), args
            assert isinstance(args[1], int), args
            rows, cols = args[0], args[1]
            flat_list = [args[2](row, col) for row in range(rows) for col in range(cols)]

        # 7) If we have args equal to the fixed type, treat that as a convenience constructor like
        # Matrix31(1, 2, 3) which is the same as Matrix31(3, 1, [1, 2, 3]). Also works for
        # Matrix22([1, 2, 3, 4]).
        elif cls._is_fixed_size() and len(args) == cls.storage_dim():
            rows, cols = cls.SHAPE
            flat_list = list(args)

        # 8) No match, error out.
        else:
            raise AssertionError("Unknown {} constructor for: {}".format(cls, args))

        # Get the proper fixed size child class
        fixed_size_type = fixed_type_from_shape((rows, cols))

        # Build object
        instance = LieGroup.__new__(fixed_size_type)

        # Set the underlying sympy array
        instance.mat = sm.Matrix(rows, cols, flat_list)

        return instance

    def __init__(self, *args, **kwargs):
        # type: (_T.Any, _T.Any) -> None
        if _T.TYPE_CHECKING:
            self.mat = sm.Matrix()

        assert self.__class__.SHAPE == self.mat.shape, "Inconsistent Matrix"

    @property
    def rows(self):
        # type: () -> int
        return self.mat.rows

    @property
    def cols(self):
        # type: () -> int
        return self.mat.cols

    @property
    def shape(self):
        # type: () -> _T.Sequence[int]
        return self.mat.shape

    def __len__(self):
        # type: () -> int
        return len(self.mat)

    @property
    def is_Matrix(self):
        # type: () -> bool
        return True

    # -------------------------------------------------------------------------
    # Storage concept - see symforce.ops.storage_ops
    # -------------------------------------------------------------------------

    def __repr__(self):
        # type: () -> str
        return self.mat.__repr__()

    @classmethod
    def storage_dim(cls):
        # type: () -> int
        assert cls._is_fixed_size(), "Type has no size info: {}".format(cls)
        return cls.SHAPE[0] * cls.SHAPE[1]

    @classmethod
    def from_storage(cls, vec):
        # type: (_T.Sequence[_T.Scalar]) -> Matrix
        assert cls._is_fixed_size(), "Type has no size info: {}".format(cls)
        return cls(vec)

    def to_storage(self):
        # type: () -> _T.List[_T.Scalar]
        return self.to_tangent()

    # -------------------------------------------------------------------------
    # Group concept - see symforce.ops.group_ops
    # -------------------------------------------------------------------------

    @classmethod
    def identity(cls):
        # type: (_T.Type[MatrixT]) -> MatrixT
        return cls.zero()

    def compose(self, other):
        # type: (MatrixT, MatrixT) -> MatrixT
        return self + other

    def inverse(self):
        # type: (MatrixT) -> MatrixT
        return -self

    # -------------------------------------------------------------------------
    # Lie group concept - see symforce.ops.lie_group_ops
    # -------------------------------------------------------------------------

    @classmethod
    def tangent_dim(cls):
        # type: () -> int
        return cls.storage_dim()

    @classmethod
    def from_tangent(cls, vec, epsilon=0):
        # type: (_T.Sequence[_T.Scalar], _T.Scalar) -> Matrix
        assert cls._is_fixed_size(), "Type has no size info: {}".format(cls)
        return cls(cls.SHAPE[0], cls.SHAPE[1], list(vec))

    def to_tangent(self, epsilon=0):
        # type: (_T.Scalar) -> _T.List[_T.Scalar]
        return list(self.mat)

    def storage_D_tangent(self):
        # type: () -> Matrix
        return Matrix.eye(self.storage_dim(), self.tangent_dim())  # type: ignore

    def tangent_D_storage(self):
        # type: () -> Matrix
        return Matrix.eye(self.tangent_dim(), self.storage_dim())  # type: ignore

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    @classmethod
    def zero(cls):
        # type: (_T.Type[MatrixT]) -> MatrixT
        """
        Matrix of zeros.
        """
        assert cls._is_fixed_size(), "Type has no size info: {}".format(cls)
        return cls.zeros(*cls.SHAPE)  # type: ignore

    @classmethod
    def zeros(cls, rows, cols):  # pylint: disable=signature-differs
        # type: (int, int) -> Matrix
        """
        Matrix of zeros.
        """
        return cls([[sm.S.Zero] * cols for _ in range(rows)])

    @classmethod
    def one(cls):
        # type: (_T.Type[MatrixT]) -> MatrixT
        """
        Matrix of ones.
        """
        assert cls._is_fixed_size(), "Type has no size info: {}".format(cls)
        return cls.ones(*cls.SHAPE)  # type: ignore

    @classmethod
    def ones(cls, rows, cols):  # pylint: disable=signature-differs
        # type: (int, int) -> Matrix
        """
        Matrix of ones.
        """
        return cls([[sm.S.One] * cols for _ in range(rows)])

    @classmethod
    def diag(cls, diagonal):
        # type: (_T.List[_T.Scalar]) -> Matrix
        """
        Construct a square matrix from the diagonal.
        """
        mat = cls.zeros(len(diagonal), len(diagonal))
        for i in range(len(diagonal)):
            mat[i, i] = diagonal[i]
        return mat

    @classmethod
    def eye(cls, rows, cols=None):
        # type: (int, int) -> Matrix
        """
        Construct an identity matrix of the given dimensions. Square if cols is None.
        """
        if cols is None:
            cols = rows
        mat = cls.zeros(rows, cols)
        for i in range(min(rows, cols)):
            mat[i, i] = sm.S.One
        return mat

    @classmethod
    def matrix_identity(cls):
        # type: (_T.Type[MatrixT]) -> MatrixT
        """
        Identity matrix - ones on the diagonal, rest zeros.
        """
        assert cls._is_fixed_size(), "Type has no size info: {}".format(cls)
        return cls.eye(*cls.SHAPE)  #  type: ignore

    def matrix_inverse(self, method="LU"):
        # type: (MatrixT, str) -> MatrixT
        """
        Inverse of the matrix.
        """
        return self.__class__(self.mat.inv(method=method))

    @classmethod
    def symbolic(cls, name, **kwargs):
        # type: (_T.Type[MatrixT], str, _T.Any) -> MatrixT
        """
        Create with symbols.

        Args:
            name (str): Name prefix of the symbols
            **kwargs (dict): Forwarded to `sm.Symbol`
        """
        assert cls._is_fixed_size(), "Type has no size info: {}".format(cls)
        rows, cols = cls.SHAPE  # pylint: disable=unpacking-non-sequence

        row_names = [str(r_i) for r_i in range(rows)]
        col_names = [str(c_i) for c_i in range(cols)]

        assert len(row_names) == rows
        assert len(col_names) == cols

        if cols == 1:
            symbols = []
            for r_i in range(rows):
                _name = "{}{}".format(name, row_names[r_i])
                symbols.append(sm.Symbol(_name, **kwargs))
        else:
            symbols = []
            for r_i in range(rows):
                col_symbols = []
                for c_i in range(cols):
                    _name = "{}{}_{}".format(name, row_names[r_i], col_names[c_i])
                    col_symbols.append(sm.Symbol(_name, **kwargs))
                symbols.append(col_symbols)

        return cls(sm.Matrix(symbols))

    def row_join(self, right):
        # type: (Matrix) -> Matrix
        """
        Concatenates self with another matrix on the right
        """
        return Matrix(self.mat.row_join(right.mat))

    def col_join(self, bottom):
        # type: (Matrix) -> Matrix
        """
        Concatenates self with another matrix below
        """
        return Matrix(self.mat.col_join(bottom.mat))

    @classmethod
    def block_matrix(cls, array):
        # type: (_T.Sequence[_T.Sequence[Matrix]]) -> Matrix
        """
        Constructs a matrix from block elements. For example:
        [[Matrix22(...), Matrix23(...)], [Matrix11(...), Matrix14(...)]] -> Matrix35 with elements equal to given blocks
        """
        # Sum rows of matrices in the first column
        rows = sum([mat_row[0].shape[0] for mat_row in array])
        # Sum columns of matrices in the first row
        cols = sum([mat.shape[1] for mat in array[0]])

        # Check for size consistency
        for mat_row in array:
            block_rows = mat_row[0].shape[0]
            block_cols = 0
            for mat in mat_row:
                assert (
                    mat.shape[0] == block_rows
                ), "Inconsistent row number accross block: expected {} got {}".format(
                    block_rows, mat.shape[0]
                )
                block_cols += mat.shape[1]
            assert (
                block_cols == cols
            ), "Inconsistent column number accross block: expected {} got {}".format(
                cols, block_cols
            )

        # Fill the new matrix data vector
        flat_list = []
        for mat_row in array:
            for row in range(mat_row[0].shape[0]):
                for mat in mat_row:
                    if mat.shape[1] == 1:
                        flat_list += [mat[row]]
                    else:
                        flat_list += list(mat[row, :])

        return Matrix(rows, cols, flat_list)

    def simplify(self, *args, **kwargs):
        # type: (_T.Any, _T.Any) -> Matrix
        """
        Simplify this expression.

        This overrides the sympy implementation because that clobbers the class type.
        """
        return self.__class__(sm.simplify(self.mat, *args, **kwargs))

    def jacobian(self, X, tangent_space=True):
        # type: (_T.Any, bool) -> Matrix
        """
        Compute the jacobian with respect to the tangent space of X if tangent_space = True,
        otherwise returns the jacobian wih respect to the storage elements of X.

        This overrides the sympy implementation so that we can construct jacobians with
        respect to symforce objects.
        """
        assert self.cols == 1, "Jacobian is for column vectors."

        # Compute jacobian wrt X storage
        self_D_storage = Matrix(
            [[vi.diff(xi) for xi in ops.StorageOps.to_storage(X)] for vi in self.mat]
        )

        if tangent_space:
            # Return jacobian wrt X tangent space
            return self_D_storage * ops.LieGroupOps.storage_D_tangent(X)

        # Return jacobian wrt X storage
        return self_D_storage

    def diff(self, *args):
        # type: (_T.Tuple[_T.Scalar]) -> Matrix
        """
        Differentiate wrt a scalar.
        """
        return self.__class__(self.mat.diff(*args))

    @property
    def T(self):
        # type: () -> Matrix
        """
        Matrix Transpose
        """
        return self.transpose()

    def transpose(self):
        # type: () -> Matrix
        """
        Matrix Transpose
        """
        return self.__class__(self.mat.transpose())

    def reshape(self, rows, cols):
        # type: (int, int) -> Matrix
        return self.__class__(self.mat.reshape(rows, cols))

    def dot(self, other):
        # type: (Matrix) -> Matrix
        """
        Dot product.
        """
        ret = self.mat.dot(other.mat)
        if isinstance(ret, sm.Matrix):
            ret = self.__class__(ret)
        else:
            # Result is a Scalar, wrap in a Matrix
            ret = self.__class__([[ret]])
        return ret

    def cross(self, other):
        # type: (Matrix31) -> Matrix31
        """
        Cross product.
        """
        if self.shape != (3, 1):
            raise TypeError(
                "Cross can only be called on shape (3, 1), this matrix is shape {}".format(
                    self.shape
                )
            )

        return Matrix31(self.mat.cross(other.mat))

    def squared_norm(self):
        # type: () -> _T.Scalar
        """
        Squared norm of a vector, equivalent to the dot product with itself.
        """
        self._assert_is_vector()
        return self.dot(self)[0, 0]

    def norm(self, epsilon=0):
        # type: (_T.Scalar) -> _T.Scalar
        """
        Norm of a vector (square root of magnitude).
        """
        return sm.sqrt(self.squared_norm() + epsilon)

    def normalized(self, epsilon=0):
        # type: (MatrixT, _T.Scalar) -> MatrixT
        """
        Returns a unit vector in this direction (divide by norm).
        """
        return self / self.norm(epsilon=epsilon)

    def applyfunc(self, func):
        # type: (MatrixT, _T.Callable) -> MatrixT
        """
        Apply a unary operation to every scalar.
        """
        return self.__class__(self.mat.applyfunc(func))

    def __getitem__(self, item):
        # type: (_T.Any) -> _T.Any
        """
        Get a scalar value or submatrix slice.
        """
        ret = self.mat.__getitem__(item)
        if isinstance(ret, sm.Matrix):
            ret = self.__class__(ret)
        return ret

    def __setitem__(self, key, value):
        # type: (_T.Any, _T.Scalar) -> None
        if isinstance(value, Matrix):
            value = value.mat
        ret = self.mat.__setitem__(key, value)
        if isinstance(ret, sm.Matrix):
            ret = self.__class__(ret)
        return ret

    def __neg__(self):
        # type: (MatrixT) -> MatrixT
        """
        Negate matrix.
        """
        return self.__class__(-self.mat)

    def __add__(self, right):
        # type: (MatrixT, _T.Union[_T.Scalar, MatrixT]) -> MatrixT
        """
        Add a scalar or matrix to this matrix.
        """
        if python_util.scalar_like(right):
            return self.applyfunc(lambda x: x + right)
        elif isinstance(right, Matrix):
            return self.__class__(self.mat + right.mat)
        else:
            return self.__class__(self.mat + right)

    def __sub__(self, right):
        # type: (MatrixT, _T.Union[_T.Scalar, MatrixT]) -> MatrixT
        """
        Subtract a scalar or matrix from this matrix.
        """
        if python_util.scalar_like(right):
            return self.applyfunc(lambda x: x - right)
        elif isinstance(right, Matrix):
            return self.__class__(self.mat - right.mat)
        else:
            return self.__class__(self.mat - right)

    @_T.overload
    def __mul__(self, right):  # pragma: no cover
        # type: (MatrixT, _T.Scalar) -> MatrixT
        pass

    @_T.overload
    def __mul__(self, right):  # pragma: no cover
        # type: (_T.Union[Matrix, sm.Matrix]) -> Matrix
        pass

    def __mul__(self, right):
        # type: (_T.Union[MatrixT, _T.Scalar, Matrix, sm.Matrix]) -> _T.Union[MatrixT, Matrix]
        """
        Multiply a matrix by a scalar or matrix
        """
        if python_util.scalar_like(right):
            return self.applyfunc(lambda x: x * right)
        elif isinstance(right, Matrix):
            return self.__class__(self.mat * right.mat)
        else:
            return self.__class__(self.mat * right)

    @_T.overload
    def __rmul__(self, left):  # pragma: no cover
        # type: (MatrixT, _T.Scalar) -> MatrixT
        pass

    @_T.overload
    def __rmul__(self, left):  # pragma: no cover
        # type: (_T.Union[Matrix, sm.Matrix]) -> Matrix
        pass

    def __rmul__(self, left):
        # type: (_T.Union[MatrixT, _T.Scalar, Matrix, sm.Matrix]) -> _T.Union[MatrixT, Matrix]
        """
        Left multiply a matrix by a scalar or matrix
        """
        if python_util.scalar_like(left):
            return self.applyfunc(lambda x: left * x)
        elif isinstance(left, Matrix):
            return self.__class__(left.mat * self.mat)
        else:
            return self.__class__(left * self.mat)

    @_T.overload
    def __div__(self, right):  # pragma: no cover
        # type: (MatrixT, _T.Scalar) -> MatrixT
        pass

    @_T.overload
    def __div__(self, right):  # pragma: no cover
        # type: (_T.Union[Matrix, sm.Matrix]) -> Matrix
        pass

    def __div__(self, right):
        # type: (_T.Union[MatrixT, _T.Scalar, Matrix, sm.Matrix]) -> _T.Union[MatrixT, Matrix]
        """
        Divide a matrix by a scalar or a matrix (which takes the inverse).
        """
        if python_util.scalar_like(right):
            return self.applyfunc(lambda x: x / sm.S(right))
        elif isinstance(right, Matrix):
            return self * right.matrix_inverse()
        else:
            return self.__class__(self.mat * _T.cast(sm.Matrix, right).inv())

    def LU(self):
        # type: () -> _T.Tuple[Matrix, Matrix]
        """
        LU matrix decomposition
        """
        L, U = self.mat.LU()
        return self.__class__(L), self.__class__(U)

    def LDL(self):
        # type: () -> _T.Tuple[Matrix, Matrix]
        """
        LDL matrix decomposition (stable cholesky)
        """
        L, D = self.mat.LU()
        return self.__class__(L), self.__class__(D)

    def FFLU(self):
        # type: () -> _T.Tuple[Matrix, Matrix]
        """
        Fraction-free LU matrix decomposition
        """
        L, U = self.mat.FFLU()
        return self.__class__(L), self.__class__(U)

    def FFLDU(self):
        # type: () -> _T.Tuple[Matrix, Matrix, Matrix]
        """
        Fraction-free LDU matrix decomposition
        """
        L, D, U = self.mat.FFLDU()
        return self.__class__(L), self.__class__(D), self.__class__(U)

    def solve(self, b, method="LU"):
        # type: (Matrix, str) -> Matrix
        """
        Solve a linear system using the given method.
        """
        return self.__class__(self.mat.solve(b, method=method))

    __truediv__ = __div__

    @staticmethod
    def are_parallel(a, b, epsilon):
        # type: (Matrix31, Matrix31, _T.Scalar) -> _T.Scalar
        """
        Returns 1 if a and b are parallel within epsilon, and 0 otherwise.
        """
        return (1 - sm.sign(a.cross(b).norm() - epsilon)) / 2

    def evalf(self):
        # type: () -> Matrix
        """
        Perform numerical evaluation of each element in the matrix.
        """
        return self.__class__.from_storage([ops.StorageOps.evalf(v) for v in self.to_storage()])

    def to_list(self):
        # type: () -> _T.List[_T.List[_T.Scalar]]
        """
        Convert to a nested list
        """
        return self.mat.tolist()

    def to_flat_list(self):
        # type: () -> _T.List[_T.Scalar]
        """
        Convert to a flattened list
        """
        return list(self.mat)

    def to_numpy(self, scalar_type=np.float64):
        # type: (type) -> np.ndarray
        """
        Convert to a numpy array.
        """
        return np.array(self.evalf().to_storage(), dtype=scalar_type).reshape(self.shape)

    @classmethod
    def column_stack(cls, *columns):
        # type: (Matrix) -> Matrix
        """Take a sequence of 1-D vectors and stack them as columns to make a single 2-D Matrix.

        Args:
            columns (tuple(Matrix)): 1-D vectors

        Returns:
            Matrix:
        """
        if not columns:
            return cls()

        for col in columns:
            # assert that each column is a vector
            assert col.shape == columns[0].shape
            assert sum([dim > 1 for dim in col.shape]) <= 1

        return cls([col.to_flat_list() for col in columns]).T

    def _assert_is_vector(self):
        # type: () -> None
        assert (self.shape[0] == 1) or (self.shape[1] == 1), "Not a vector."

    def _assert_sanity(self):
        # type: () -> None
        assert self.shape == self.SHAPE, "Inconsistent Matrix!. shape={}, SHAPE={}".format(
            self.shape, self.SHAPE
        )

    def __hash__(self):
        # type: () -> int
        return LieGroup.__hash__(self)

    @classmethod
    def _is_fixed_size(cls):
        # type: () -> bool
        """
        Return True if this is a type with fixed dimensions set, ie Matrix31 instead of Matrix.
        """
        return cls.SHAPE[0] > 0 and cls.SHAPE[1] > 0

    def _ipython_display_(self):
        # type: () -> None
        """
        Display self.mat in IPython, with SymPy's pretty printing
        """
        display(self.mat)  # type: ignore # not defined outside of ipython

    @staticmethod
    def init_printing():
        # type: () -> None
        """
        Initialize SymPy pretty printing

        _ipython_display_ is sufficient in Jupyter, but this covers other locations
        """
        ip = None
        try:
            ip = get_ipython()  # type: ignore # only exists in ipython
        except NameError:
            pass

        if ip is not None:
            plaintext_formatter = ip.display_formatter.formatters["text/plain"]
            sympy_plaintext_formatter = plaintext_formatter.for_type(sm.Matrix)
            if sympy_plaintext_formatter is not None:
                plaintext_formatter.for_type(
                    Matrix, lambda arg, p, cycle: sympy_plaintext_formatter(arg.mat, p, cycle)
                )

            png_formatter = ip.display_formatter.formatters["image/png"]
            sympy_png_formatter = png_formatter.for_type(sm.Matrix)
            if sympy_png_formatter is not None:
                png_formatter.for_type(Matrix, lambda o: sympy_png_formatter(o.mat))

            latex_formatter = ip.display_formatter.formatters["text/latex"]
            sympy_latex_formatter = latex_formatter.for_type(sm.Matrix)
            if sympy_latex_formatter is not None:
                latex_formatter.for_type(Matrix, lambda o: sympy_latex_formatter(o.mat))


# -----------------------------------------------------------------------------
# Statically define fixed matrix types. We could dynamically generate in a
# loop but this is nice for IDE understanding and static analysis.
# -----------------------------------------------------------------------------

# TODO(hayk): It could be nice to put these in another file but there's a circular dependency..


class Matrix11(Matrix):
    SHAPE = (1, 1)


class Matrix21(Matrix):
    SHAPE = (2, 1)


class Matrix31(Matrix):
    SHAPE = (3, 1)


class Matrix41(Matrix):
    SHAPE = (4, 1)


class Matrix51(Matrix):
    SHAPE = (5, 1)


class Matrix61(Matrix):
    SHAPE = (6, 1)


class Matrix71(Matrix):
    SHAPE = (7, 1)


class Matrix81(Matrix):
    SHAPE = (8, 1)


class Matrix91(Matrix):
    SHAPE = (9, 1)


class Matrix12(Matrix):
    SHAPE = (1, 2)


class Matrix22(Matrix):
    SHAPE = (2, 2)


class Matrix32(Matrix):
    SHAPE = (3, 2)


class Matrix42(Matrix):
    SHAPE = (4, 2)


class Matrix52(Matrix):
    SHAPE = (5, 2)


class Matrix62(Matrix):
    SHAPE = (6, 2)


class Matrix13(Matrix):
    SHAPE = (1, 3)


class Matrix23(Matrix):
    SHAPE = (2, 3)


class Matrix33(Matrix):
    SHAPE = (3, 3)


class Matrix43(Matrix):
    SHAPE = (4, 3)


class Matrix53(Matrix):
    SHAPE = (5, 3)


class Matrix63(Matrix):
    SHAPE = (6, 3)


class Matrix14(Matrix):
    SHAPE = (1, 4)


class Matrix24(Matrix):
    SHAPE = (2, 4)


class Matrix34(Matrix):
    SHAPE = (3, 4)


class Matrix44(Matrix):
    SHAPE = (4, 4)


class Matrix54(Matrix):
    SHAPE = (5, 4)


class Matrix64(Matrix):
    SHAPE = (6, 4)


class Matrix15(Matrix):
    SHAPE = (1, 5)


class Matrix25(Matrix):
    SHAPE = (2, 5)


class Matrix35(Matrix):
    SHAPE = (3, 5)


class Matrix45(Matrix):
    SHAPE = (4, 5)


class Matrix55(Matrix):
    SHAPE = (5, 5)


class Matrix65(Matrix):
    SHAPE = (6, 5)


class Matrix16(Matrix):
    SHAPE = (1, 6)


class Matrix26(Matrix):
    SHAPE = (2, 6)


class Matrix36(Matrix):
    SHAPE = (3, 6)


class Matrix46(Matrix):
    SHAPE = (4, 6)


class Matrix56(Matrix):
    SHAPE = (5, 6)


class Matrix66(Matrix):
    SHAPE = (6, 6)


# Dictionary of shapes to static types.
DIMS_TO_FIXED_TYPE = {
    m.SHAPE: m
    for m in (
        Matrix11,
        Matrix12,
        Matrix13,
        Matrix14,
        Matrix15,
        Matrix16,
        Matrix21,
        Matrix22,
        Matrix23,
        Matrix24,
        Matrix25,
        Matrix26,
        Matrix31,
        Matrix32,
        Matrix33,
        Matrix34,
        Matrix35,
        Matrix36,
        Matrix41,
        Matrix42,
        Matrix43,
        Matrix44,
        Matrix45,
        Matrix46,
        Matrix51,
        Matrix52,
        Matrix53,
        Matrix54,
        Matrix55,
        Matrix56,
        Matrix61,
        Matrix62,
        Matrix63,
        Matrix64,
        Matrix65,
        Matrix66,
        Matrix71,
        Matrix81,
        Matrix91,
    )
}  # type: _T.Dict[_T.Tuple[int, int], type]


def fixed_type_from_shape(shape):
    # type: (_T.Tuple[int, int]) -> type
    """
    Return a fixed size matrix type (like Matrix32) given a shape. Either use the statically
    defined ones or dynamically create a new one if not available.
    """
    if shape not in DIMS_TO_FIXED_TYPE:
        DIMS_TO_FIXED_TYPE[shape] = type(
            "Matrix{}_{}".format(shape[0], shape[1]), (Matrix,), {"SHAPE": shape}
        )

    return DIMS_TO_FIXED_TYPE[shape]


# Shorthand
M = Matrix

Vector1 = V1 = M11 = Matrix11
Vector2 = V2 = M21 = Matrix21
Vector3 = V3 = M31 = Matrix31
Vector4 = V4 = M41 = Matrix41
Vector5 = V5 = M51 = Matrix51
Vector6 = V6 = M61 = Matrix61
Vector7 = V7 = M71 = Matrix71
Vector8 = V8 = M81 = Matrix81
Vector9 = V9 = M91 = Matrix91

M12 = Matrix12
M22 = Matrix22
M32 = Matrix32
M42 = Matrix42
M52 = Matrix52
M62 = Matrix62
M13 = Matrix13
M23 = Matrix23
M33 = Matrix33
M43 = Matrix43
M53 = Matrix53
M63 = Matrix63
M14 = Matrix14
M24 = Matrix24
M34 = Matrix34
M44 = Matrix44
M54 = Matrix54
M64 = Matrix64
M15 = Matrix15
M25 = Matrix25
M35 = Matrix35
M45 = Matrix45
M55 = Matrix55
M65 = Matrix65
M16 = Matrix16
M26 = Matrix26
M36 = Matrix36
M46 = Matrix46
M56 = Matrix56
M66 = Matrix66


# Identity convenience names
I1 = I11 = M11.matrix_identity
I2 = I22 = M22.matrix_identity
I3 = I33 = M33.matrix_identity
I4 = I44 = M44.matrix_identity
I5 = I55 = M55.matrix_identity
I6 = I66 = M66.matrix_identity


# Register printing for ipython
Matrix.init_printing()
