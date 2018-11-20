from math import fabs, sqrt
import numpy as np
import operator

from .exceptions import AlgError, OptError
#  Linear algebra routines. #


def norm(V):
    return np.linalg.norm(V)


def absMax(V):
    return max(abs(elem) for elem in V)


def absMin(V):
    return min(abs(elem) for elem in V)


def rms(V):
    return np.sqrt(np.mean(V**2))


def signOfDouble(d):
    if d > 0:
        return 1
    elif d < 0:
        return -1
    else:
        return 0


# Returns eigenvectors as rows?
def symmMatEig(mat):
    try:
        evals, evects = np.linalg.eigh(mat)
    except:
        raise OptError("symmMatEig: could not compute eigenvectors")
        # could be ALG_FAIL ?
    evects = evects.T
    return evals, evects


def asymmMatEig(mat):
    """Compute the eigenvalues and right eigenvectors of a square array.
    Wraps numpy.linalg.eig to sort eigenvalues, put eigenvectors in rows, and suppress complex.

    Parameters
    ----------
    mat : ndarray
        (n, n) Square matrix to diagonalize.

    Returns
    -------
    ndarray, ndarray
        (n, ), (n, n) sorted eigenvalues and normalized corresponding eigenvectors in rows.

    Raises
    ------
    OptError
        When eigenvalue computation does not converge.

    """
    try:
        evals, evects = np.linalg.eig(mat)
    except np.LinAlgError as e:
        raise OptError("asymmMatEig: could not compute eigenvectors") from e

    idx = np.argsort(evals)
    evals = evals[idx]
    evects = evects[:, idx]

    return evals.real, evects.real.T


#  Return the inverse of a real, symmetric matrix.  If "redundant" == true,
#  then a generalized inverse is permitted.
def symmMatInv(A, redundant=False, redundant_eval_tol=1.0e-10):
    dim = A.shape[0]
    if dim == 0:
        return np.zeros((0, 0), float)
    det = 1.0

    try:
        evals, evects = symmMatEig(A)
    except LinAlgError:
        raise OptError("symmMatrixInv: could not compute eigenvectors")
        # could be LinAlgError?

    for i in range(dim):
        det *= evals[i]

    if not redundant and fabs(det) < 1E-10:
        raise OptError(
            "symmMatrixInv: non-generalized inverse failed; very small determinant")
        # could be LinAlgError?

    diagInv = np.zeros((dim, dim), float)

    if redundant:
        for i in range(dim):
            if fabs(evals[i]) > redundant_eval_tol:
                diagInv[i, i] = 1.0 / evals[i]
    else:
        for i in range(dim):
            diagInv[i, i] = 1.0 / evals[i]

    # A^-1 = P^t D^-1 P
    tmpMat = np.dot(diagInv, evects)
    AInv = np.dot(evects.T, tmpMat)
    return AInv


# Compute A^(1/2) for a positive-definite matrix.  A^(-1/2) if Inverse == True
def symmMatRoot(A, Inverse=None):
    try:
        evals, evects = np.linalg.eigh(A)
        # Eigenvectors of A are in columns of evects
        # Evals in ascending order
    except LinAlgError:
        raise OptError("symmMatRoot: could not compute eigenvectors")

    evals[ np.abs(evals) < 5*np.finfo(np.float).resolution ] = 0.0
    evects[ np.abs(evects) < 5*np.finfo(np.float).resolution ] = 0.0

    rootMatrix = np.zeros((len(evals), len(evals)), float)
    if Inverse:
        for i in range(0, len(evals)):
            evals[i] = 1 / evals[i]

    for i in range(0, len(evals)):
        rootMatrix[i][i] = sqrt(evals[i])

    A = np.dot(evects, np.dot(rootMatrix, evects.T))

    return A

