import logging

import numpy as np
import qcelemental as qcel

from .exceptions import AlgError, OptError
from . import v3d
from .misc import delta, hguess_lindh_rho
from .simple import Simple


class Stre(Simple):
    """ stretching coordinate between two atoms

    Parameters
    ----------
    a : int
        atom 1 (zero indexing)
    b : int
        atom 2 (zero indexing)
    frozen : boolean, optional
        set stretch as frozen
    fixed_eq_val : double
        value to fix stretch at
    inverse : boolean
        identifies 1/R coordinate

    """
    def __init__(self, a, b, frozen=False, fixed_eq_val=None, inverse=False):

        self._inverse = inverse  # bool - is really 1/R coordinate?

        if a < b:
            atoms = (a, b)
        else:
            atoms = (b, a)

        Simple.__init__(self, atoms, frozen, fixed_eq_val)

    def __str__(self):
        if self.frozen:
            s = '*'
        else:
            s = ' '

        if self.inverse:
            s += '1/R'
        else:
            s += 'R'

        s += "(%d,%d)" % (self.A + 1, self.B + 1)
        if self.fixed_eq_val:
            s += "[%.4f]" % (self.fixed_eq_val * self.q_show_factor)
        return s

    def __eq__(self, other):
        if self.atoms != other.atoms:
            return False
        elif not isinstance(other, Stre):
            return False
        elif self.inverse != other.inverse:
            return False
        else:
            return True

    @property
    def inverse(self):
        return self._inverse

    @inverse.setter
    def inverse(self, setval):
        self._inverse = bool(setval)

    def q(self, geom):
        return v3d.dist(geom[self.A], geom[self.B])

    def q_show(self, geom):
        return self.q_show_factor * self.q(geom)

    @property
    def q_show_factor(self):
        return qcel.constants.bohr2angstroms

    @property
    def f_show_factor(self):
        return qcel.constants.hartree2aJ / qcel.constants.bohr2angstroms

    # If mini == False, dqdx is 1x(3*number of atoms in fragment).
    # if mini == True, dqdx is 1x6.
    def DqDx(self, geom, dqdx, mini=False):
        try:
            eAB = v3d.eAB(geom[self.A], geom[self.B])  # A->B
        except AlgError as error:
            raise AlgError("Stre.DqDx: could not normalize s vector") from error

        if mini:
            startA = 0
            startB = 3
        else:
            startA = 3 * self.A
            startB = 3 * self.B

        dqdx[startA:startA + 3] = -1 * eAB[0:3]
        dqdx[startB:startB + 3] = eAB[0:3]

        if self._inverse:
            val = self.q(geom)
            dqdx[startA:startA + 3] *= -1.0 * val * val  # -(1/R)^2 * (dR/da)
            dqdx[startB:startB + 3] *= -1.0 * val * val

    def Dq2Dx2(self, geom, dq2dx2):
        """
        # Return derivative B matrix elements.  Matrix is cart X cart and passed in.
        Parameters
        ----------
        geom : np.ndarray
        dq2dx2 : np.ndarray
            to be added to

        Returns
        -------

        """
        try:
            eAB = v3d.eAB(geom[self.A], geom[self.B])  # A->B
        except AlgError as error:
            raise AlgError("Stre.Dq2Dx2: could not normalize s vector") from error

        if not self._inverse:
            length = self.q(geom)

            for a in range(2):
                for a_xyz in range(3):
                    for b in range(2):
                        for b_xyz in range(3):
                            tval = (
                                eAB[a_xyz] * eAB[b_xyz] - delta(a_xyz, b_xyz)) / length
                            if a == b:
                                tval *= -1.0
                            dq2dx2[3*self.atoms[a]+a_xyz,
                                   3*self.atoms[b]+b_xyz] = tval

        else:  # using 1/R
            val = self.q(geom)

            dqdx = np.zeros((3 * len(self.atoms)) )
            self.DqDx(geom, dqdx, mini=True)  # returned matrix is 1x6 for stre

            for a in range(2):
                for a_xyz in range(3):
                    for b in range(2):
                        for b_xyz in range(3):
                            dq2dx2[3*self.atoms[a]+a_xyz, 3*self.atoms[b]+b_xyz] \
                                = 2.0 / val * dqdx[3*a+a_xyz] * dqdx[3*b+b_xyz]

    def diagonal_hessian_guess(self, geom, Z, connectivity, guess_type="SIMPLE"):
        """ Generates diagonal empirical Hessians in a.u. such as
        Schlegel, Theor. Chim. Acta, 66, 333 (1984) and
        Fischer and Almlof, J. Phys. Chem., 96, 9770 (1992).
        """
        logger = logging.getLogger(__name__)
        if guess_type == "SIMPLE":
            return 0.5

        if guess_type == "SCHLEGEL":
            R = v3d.dist(geom[self.A], geom[self.B])
            PerA = qcel.periodictable.to_period(Z[self.A])
            PerB = qcel.periodictable.to_period(Z[self.B])

            AA = 1.734
            if PerA == 1:
                if PerB == 1:
                    BB = -0.244
                elif PerB == 2:
                    BB = 0.352
                else:
                    BB = 0.660
            elif PerA == 2:
                if PerB == 1:
                    BB = 0.352
                elif PerB == 2:
                    BB = 1.085
                else:
                    BB = 1.522
            else:
                if PerB == 1:
                    BB = 0.660
                elif PerB == 2:
                    BB = 1.522
                else:
                    BB = 2.068

            F = AA / ((R - BB) * (R - BB) * (R - BB))
            return F

        elif guess_type == "FISCHER":
            Rcov = qcel.covalentradii.get(Z[self.A], missing=4.0) + qcel.covalentradii.get(Z[self.B], missing=4.0)
            R = v3d.dist(geom[self.A], geom[self.B])
            AA = 0.3601
            BB = 1.944
            return AA * (np.exp(-BB * (R - Rcov)))

        elif guess_type == "LINDH_SIMPLE":
            R = v3d.dist(geom[self.A], geom[self.B])
            k_r = 0.45
            return k_r * hguess_lindh_rho(Z[self.A], Z[self.B], R)

        else:
            logger.warning("Hessian guess encountered unknown coordinate type.\n")
            return 1.0


class HBond(Stre):
    def __str__(self):
        if self.frozen:
            s = '*'
        else:
            s = ' '

        if self.inverse:
            s += '1/H'
        else:
            s += 'H'

        s += "(%d,%d)" % (self.A + 1, self.B + 1)
        if self.fixed_eq_val:
            s += "[%.4f]" % self.fixed_eq_val
        return s

    # overrides Stre eq in comparisons, regardless of order
    def __eq__(self, other):
        if self.atoms != other.atoms:
            return False
        elif not isinstance(other, HBond):
            return False
        elif self.inverse != other.inverse:
            return False
        else:
            return True

    def diagonal_hessian_guess(self, geom, Z, connectivity, guess_type='SIMPLE'):
        """ Generates diagonal empirical Hessians in a.u. such as
        Schlegel, Theor. Chim. Acta, 66, 333 (1984) and
        Fischer and Almlof, J. Phys. Chem., 96, 9770 (1992).
        """
        logger = logging.getLogger(__name__)
        if guess_type == "SIMPLE":
            return 0.5
        elif guess_type in ['SCHLEGEL', 'FISCHER']:
            return 0.03
        elif guess_type == 'LINDH_SIMPLE':
            # Same as standard stretch
            R = v3d.dist(geom[self.A], geom[self.B])
            k_r = 0.45
            return k_r * hguess_lindh_rho(Z[self.A], Z[self.B], R)
        else:
            logger.warning("Hessian guess encountered unknown coordinate type.\n")
            return 1.0
