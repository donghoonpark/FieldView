import os
import platform
import importlib.metadata


def _configure_threads():
    """
    Configures thread environment variables for specific conditions.
    Sets single-threaded execution for BLAS libraries on ARM CPUs with Numpy < 2
    to avoid overhead on small matrices.
    """
    try:
        # Check for ARM CPU
        machine = platform.machine().lower()
        is_arm = "arm" in machine or "aarch64" in machine

        # Check Numpy version
        numpy_version = importlib.metadata.version("numpy")
        is_numpy_old = int(numpy_version.split(".")[0]) < 2

        if is_arm and is_numpy_old:
            os.environ["OMP_NUM_THREADS"] = "1"
            os.environ["OPENBLAS_NUM_THREADS"] = "1"
            os.environ["MKL_NUM_THREADS"] = "1"
            os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
            os.environ["NUMEXPR_NUM_THREADS"] = "1"

            print(
                "Due to the issue with numpy < 2, the performance may be affected on ARM devices."
            )

    except Exception:
        # Fail silently if metadata check fails or other issues occur
        pass


_configure_threads()

from .ui.field_view import FieldView as FieldView  # noqa: E402
