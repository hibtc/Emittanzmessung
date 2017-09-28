# encoding: utf+8
"""
Module for calculating the emittance from at least 3 monitor measurements and
the corresponding transfer maps.
"""

from __future__ import unicode_literals

from math import sqrt
import numpy as np

nan = float("nan")


def calc_emit(records,
              transfer_maps,
              calc_long=True,
              calc_4D=False,
              use_dispersion=False):
    """
    Calculate emittances.

    :param list records:        dictionaries with keys 'envx', 'envy' for the
                                measured beam envelopes at the monitor positions.
    :param list transfer_maps:  transfer maps between the monitor positions,
                                M(X₀→X₁), M(X₁→X₂), M(X₂→X₃), …
    :param bool calc_long:      use the sectormaps from the start of the sequence.
    :param bool calc_4D:        calculate with 4D sectormap, rather than 2*2D
    :param bool use_dispersion: requires 6 monitors. NOTE: this is not working yet.
    :returns:   dict with keys 'ex', 'ey', 'betx', 'bety', 'alfx', 'alfy', 'pt'.
                Note that 'pt' is only useful if ``use_dispersion`` was ``True``
    """
    # TODO: use_dispersion is not working yet

    assert len(records) >= 3 + 3*bool(use_dispersion)
    assert len(records) == len(transfer_maps)

    # prepare LHS of equation
    tms = list(transfer_maps)
    if not calc_long:
        tms[0] = np.eye(7)
    tms = list(accumulate(tms, lambda a, b: np.dot(b, a)))
    tms = np.array(tms)[:,[0,1,2,3,5],:][:,:,[0,1,2,3,5]]   # X,PX,Y,PY,PT

    # prepare RHS of equation
    envx = [m['envx'] for m in records]
    envy = [m['envy'] for m in records]
    xcs = [[(0, cx**2), (2, cy**2)]
           for cx, cy in zip(envx, envy)]

    # check coupling
    coup_xy = not np.allclose(tms[:,0:2,2:4], 0)
    coup_yx = not np.allclose(tms[:,2:4,0:2], 0)
    coup_xt = not np.allclose(tms[:,0:2,4:5], 0)
    coup_yt = not np.allclose(tms[:,2:4,4:5], 0)
    coupled = coup_xy or coup_yx
    dispersive = coup_xt or coup_yt

    # TODO: do we need to add dpt*D to sig11 in online control?

    def calc_sigma(tms, xcs, dispersive):
        if dispersive and not use_dispersion:
            print("Warning: dispersive lattice")
        if not use_dispersion:
            tms = tms[:,:-1,:-1]
        sigma, residuals, singular = solve_emit_sys(tms, xcs)
        return sigma

    # TODO: assert no dispersion / or use 6 monitors...
    if calc_4D:
        sigma = calc_sigma(tms, xcs, dispersive)
        ex, betx, alfx = twiss_from_sigma(sigma[0:2,0:2])
        ey, bety, alfy = twiss_from_sigma(sigma[2:4,2:4])
        pt = sigma[-1,-1]

    else:   # 2 * 2D
        if coupled:
            print("Warning: coupled lattice")
        tmx = np.delete(np.delete(tms, [2,3], axis=1), [2,3], axis=2)
        tmy = np.delete(np.delete(tms, [0,1], axis=1), [0,1], axis=2)
        xcx = [[(0, cx[1])] for cx, cy in xcs]
        xcy = [[(0, cy[1])] for cx, cy in xcs]
        sigmax = calc_sigma(tmx, xcx, coup_xt)
        sigmay = calc_sigma(tmy, xcy, coup_yt)
        ex, betx, alfx = twiss_from_sigma(sigmax[0:2,0:2])
        ey, bety, alfy = twiss_from_sigma(sigmay[0:2,0:2])
        pt = sigmax[-1,-1]

    # pt only valid if use_dispersion=True
    return {
        'ex':   float(ex),
        'ey':   float(ey),
        'betx': float(betx),
        'bety': float(bety),
        'alfx': float(alfx),
        'alfy': float(alfy),
        'pt':   float(pt),
    }


def accumulate(iterable, func):
    """Return running totals."""
    # Stolen from:
    # https://docs.python.org/3/library/itertools.html#itertools.accumulate
    it = iter(iterable)
    total = next(it)
    yield total
    for element in it:
        total = func(total, element)
        yield total


def solve_emit_sys(Ms, XCs):
    """
    Solve the linear system of equations ``(MSMᵀ)ₓₓ=C`` for S.

    M can be coupled, but S is assumed to be block diagonal, i.e. decoupled:

        S = (X 0 0
             0 Y 0
             0 0 T)

    Returns S as numpy array.
    """
    d = Ms[0].shape[0]                      # matrix dimension d=2 or d=4

    con_func = lambda u: [
        M[[x]].dot(u).dot(M[[x]].T).sum()   # linear beam transport!
        for M, xc in zip(Ms, XCs)           # for every given transfer matrix
        for x, _ in xc                      # and measured constraint
    ]

    sq_matrix_basis = np.eye(d*d,d*d).reshape((d*d,d,d))
    is_upper_triang = [i for i, m in enumerate(sq_matrix_basis)
                       if np.allclose(np.triu(m), m)
                       and (d < 4 or np.allclose(m[0:2,2:4], 0))]
    ut_matrix_basis = sq_matrix_basis[is_upper_triang]

    lhs = np.vstack([
        con_func(2*u-np.tril(u))    # double weight for off-diagonal entries
        for u in ut_matrix_basis
    ]).T
    rhs = [c for xc in XCs for _, c in xc]

    x0, residuals, rank, singular = np.linalg.lstsq(lhs, rhs)

    res = np.tensordot(x0, ut_matrix_basis, 1)
    res = res + res.T - np.tril(res)
    return res, sum(residuals), (rank<len(x0))


def twiss_from_sigma(sigma):
    """Compute 1D twiss parameters from 2x2 sigma matrix."""
    # S = [[b a], [a c]]
    b = sigma[0,0]
    a = sigma[0,1]  # = sigma[1,0] !
    c = sigma[1,1]
    if b*c <= a*a:
        return nan, nan, nan
    emit = sqrt(b*c - a*a)
    beta = b/emit
    alfa = a/emit * (-1)
    return emit, beta, alfa
