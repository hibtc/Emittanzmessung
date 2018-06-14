"""
Parameter download from BeamOptikDll.
"""

from __future__ import division

import os
import sys
import signal
import logging
import threading
import itertools
import functools
import collections

# Load Qt4 or Qt5
try:
    import types
    from PyQt5 import QtCore, QtGui, uic, QtWidgets
    QtGuiCompat = types.ModuleType('QtGui')
    QtGuiCompat.__dict__.update(QtGui.__dict__)
    QtGuiCompat.__dict__.update(QtWidgets.__dict__)
    QtGui = QtGuiCompat
except ImportError:
    import sip
    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)
    from PyQt4 import QtCore, QtGui, uic

DATA_FOLDER = os.path.dirname(__file__)

# allow shipping and importing beamoptikdll.py from same folder
sys.path.append(DATA_FOLDER)
from beamoptikdll import BeamOptikDLL

from mefi_combinations import VACCS, ENERGIES, FOCUSES, INTENSITIES, ANGLES


def fmt_ints(ints):
    return ', '.join(map(str, ints))

def parse_ints(text):
    return [int(x) for x in text.split(',')]


class MainWindow(QtGui.QWidget):

    worker = None
    dll = None
    running = False
    logged = QtCore.pyqtSignal(str)

    def __init__(self, param_file=None):
        super(MainWindow, self).__init__()
        uic.loadUi(os.path.join(DATA_FOLDER, 'dialog.ui'), self)
        self.ctrl_vacc.setText(fmt_ints(VACCS))
        self.ctrl_energy.setText(fmt_ints(ENERGIES))
        self.ctrl_focus.setText(fmt_ints(FOCUSES))
        self.ctrl_intensity.setText(fmt_ints(INTENSITIES))
        self.ctrl_angle.setText(fmt_ints(ANGLES))
        self.load_params(param_file)
        # signals
        self.btn_download.clicked.connect(self.start)
        self.btn_cancel.clicked.connect(self.cancel)
        self.ctrl_vacc.textChanged.connect(self.update_ui)
        self.ctrl_energy.textChanged.connect(self.update_ui)
        self.ctrl_focus.textChanged.connect(self.update_ui)
        self.ctrl_intensity.textChanged.connect(self.update_ui)
        self.ctrl_angle.textChanged.connect(self.update_ui)
        #
        self.logged.connect(self.ctrl_log.appendPlainText)

    def closeEvent(self, event):
        self.cancel()
        super(MainWindow, self).closeEvent(event)

    def load_params(self, param_file=None):
        with open(param_file or os.path.join(DATA_FOLDER, 'params.txt')) as f:
            params = [line.strip() for line in f]
        self.ctrl_params.clear()
        self.ctrl_params.addItems(sorted(params))

    def update_ui(self):
        running = self.running
        can_start = self.can_start()
        self.btn_download.setEnabled(can_start and not self.running)
        self.btn_cancel.setEnabled(running)
        self.ctrl_vacc.setReadOnly(running)
        self.ctrl_energy.setReadOnly(running)
        self.ctrl_focus.setReadOnly(running)
        self.ctrl_intensity.setReadOnly(running)
        self.ctrl_angle.setReadOnly(running)

    def mefi(self):
        return (parse_ints(self.ctrl_vacc.text()),
                parse_ints(self.ctrl_energy.text()),
                parse_ints(self.ctrl_focus.text()),
                parse_ints(self.ctrl_intensity.text()),
                parse_ints(self.ctrl_angle.text()))

    def can_start(self):
        try:
            mefi = self.mefi()
        except ValueError:
            return False
        return all(mefi)

    def start(self):
        self.ctrl_tab.setCurrentIndex(2)
        self.running = True
        self.update_ui()
        try:
            mefi = self.mefi()
            pars = [self.ctrl_params.item(i).text()
                    for i in range(self.ctrl_params.count())]
            args = (pars, mefi)
            self.worker = threading.Thread(target=self.download, args=args)
            self.worker.start()
        except:
            self.running = False
            self.update_ui()
            raise

    def cancel(self):
        self.running = False
        self.update_ui()

    def log(self, text, *args, **kwargs):
        self.logged.emit(text.format(*args, **kwargs))

    def load_dll(self):
        self.log('Connecting DLL')
        dll = BeamOptikDLL.load_library()
        dll.GetInterfaceInstance()
        dll.SelectVAcc(1)
        self.dll = dll
        self.log('Connected')

    def download(self, params, mefis):
        if self.dll is None:
            self.load_dll()
        par = collections.defaultdict(lambda: list(params))
        mul = lambda a, b: a * b
        num = functools.reduce(mul, map(len, mefis))
        for i, mefi in enumerate(itertools.product(*mefis)):
            if not self.running:
                break
            vacc = mefi[0]
            progress = '{}/{} = {:.0f}%'.format(i, num, i/num*100)
            self.download_mefi(par[vacc], mefi, progress)

    def download_mefi(self, params, mefi, progress):

        folder = os.path.join(DATA_FOLDER, 'params')
        try:
            os.makedirs(folder)
        except OSError:     # no exist_ok on py2
            pass
        basename = 'M{}-E{}-F{}-I{}-G{}.str'.format(*mefi)
        filename = os.path.join(folder, basename)

        with open(filename, 'w') as f:
            vacc = mefi[0]
            if vacc != self.dll.GetSelectedVAcc():
                self.log('SelectVAcc({})', vacc)
                self.dll.SelectVAcc(vacc)
            self.log('[{}] SelectMEFI(M={}, E={}, F={}, I={}, G={})', progress, *mefi)
            mefi_values = self.dll.SelectMEFI(*mefi)
            f.write('beam_energy = {};\n'
                    'focus_value = {};\n'
                    'intensity_value = {};\n'
                    'gantry_angle = {};\n'
                    .format(*mefi_values))

            num_params = len(params)
            for param in list(params):
                if not self.running:
                    break
                try:
                    val = self.dll.GetFloatValue(param)
                    #self.log('{} -> {}', param, val)
                except RuntimeError as e:
                    self.log('{} -> FAILED: {}', param, e)
                    # forget this parameter for current VAcc for efficiency:
                    params.remove(param)
                except BaseException as e:
                    self.log('{} -> ERROR: {}', param, e)
                    raise
                else:
                    # MADX compatible output format:
                    f.write('{} = {};\n'.format(param, val))
            self.log('FINISHED M{2} E{3} F{4} I{5} G{6}, read {0}/{1} params\n', len(params), num_params, *mefi)


def main(param_file=None):
    """Invoke GUI application."""
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QtGui.QApplication(sys.argv)
    window = MainWindow(param_file)

    logging.basicConfig(level=logging.INFO)

    window.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
