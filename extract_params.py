"""
Call this file with the CSV parameter export of the DVM-Parameter.xls list to
filter out the list of parameters that are useful for MAD-X, i.e. QUADRUPOLE,
SBEND and KICKER strengths, 
"""

import sys

def extract(filename):

    print('\n'.join([
        'BEAMLINE_ID',
        'A_POSTSTRIP',
        'Z_POSTSTRIP',
        'Q_POSTSTRIP',
        'E_HEBT',
        'beta_HEBT',
        'BRho_HEBT',
    ]))

    whitelist = (
        'kl',
        'ks',
        'ax',
        'ay',
        'axgeo',
        'dax',
        'day',
    )

    with open(sys.argv[1]) as f:

        for line in f:
            param = line.split(';')[1]
            parts = param.lower().split('_')
            if parts[0] in whitelist and len(parts) == 2:
                print(param)


if __name__ == '__main__':
    extract(*sys.argv[1:])
