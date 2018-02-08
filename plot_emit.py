
import itertools
import os

import yaml
import matplotlib.pyplot as plt


def is_nan(n):
    return n != n


def yaml_load(filename):
    with open(filename, 'rb') as f:
        return yaml.safe_load(f.read().decode('utf-8'))


def mefi_from_filename(filename):
    base, ext = os.path.splitext(filename)
    parts = base.split('-')
    return (len(parts) == 5 and
            parts[0][0] == 'M' and
            parts[1][0] == 'E' and
            parts[2][0] == 'F' and
            parts[3][0] == 'I' and
            parts[4][0] == 'G' and
            tuple(int(part[1:]) for part in parts))


def reslice(tup, indices):
    return tuple(tup[i] for i in indices)


def plot_var(data, foreach, xname, yname):

    order = 'MEFIG'
    var_order = [c for c in order if c not in (foreach, xname)]
    var_order += [foreach, xname]
    var_order = [order.index(c) for c in var_order]

    mefis = sorted(data, key=lambda mefi: reslice(mefi, var_order))

    # iterate over settings going to different files (MFG)
    for k_file, mefis_file in itertools.groupby(
            mefis, lambda mefi: reslice(mefi, var_order[:-2])):

        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.set_xlabel(xname)
        ax.set_ylabel(yname)
        ax.yaxis.get_major_formatter().set_powerlimits([-3, +3])

        # iterate over multiple curves plotted into the same file (E)
        for k_curve, mefis_curve in itertools.groupby(
                mefis_file, lambda mefi: mefi[var_order[-2]]):
            # get X, Y values for
            curve = [
                (xval, yval)
                for mefi in mefis_curve
                for xval in [mefi[var_order[-1]]]
                for yval in [data[mefi][yname]]
                #if not is_nan(yval)
            ]
            x, y = zip(*curve)
            ax.plot(x, y, '-x', label="{}{}".format(foreach, k_curve))

        ax.legend()
        basename = '-'.join('{}{}'.format(order[i], v)
                            for i, v in zip(var_order, k_file))
        fig.savefig('graphs/{}({})_{}.pdf'.format(yname, xname, basename), bbox_inches='tight')
        plt.close(fig)


def load_data(path):
    return {
        mefi: yaml_load(fullname)
        for filename in os.listdir(path)
        for fullname in [os.path.join(path, filename)]
        for mefi in [mefi_from_filename(filename)]
    }


data = load_data('results')
plot_var(data, 'E', 'I', 'ex')
plot_var(data, 'E', 'I', 'ey')
plot_var(data, 'I', 'E', 'ex')
plot_var(data, 'I', 'E', 'ey')
plot_var(data, 'I', 'E', 'betx')
plot_var(data, 'I', 'E', 'bety')
plot_var(data, 'I', 'E', 'alfx')
plot_var(data, 'I', 'E', 'alfy')
