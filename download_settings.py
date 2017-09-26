"""
Parameter download from BeamOptikDll.
"""

import os
import sys
import signal
import logging
import threading
import itertools
import functools

# Load Qt4 or Qt5
from qtconsole.qt_loaders import load_qt
QtCore, QtGui, QtSvg, QT_API = load_qt(['pyqt', 'pyqt5'])
if QT_API == 'pyqt':
    from PyQt4 import uic
elif QT_API == 'pyqt5':
    from PyQt5 import uic


from hit.online_control.beamoptikdll import BeamOptikDLL
#from hit.online_control.stub import BeamOptikDllProxy


DATA_FOLDER = os.path.dirname(__file__)

VACCS       = [1]
ENERGIES    = [1, 18, 48, 78, 108, 138, 168, 198, 228, 255]
FOCUSES     = [4]
INTENSITIES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


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
        self.load_params(param_file)
        # signals
        self.btn_download.clicked.connect(self.start)
        self.btn_cancel.clicked.connect(self.cancel)
        self.ctrl_vacc.textChanged.connect(self.update_ui)
        self.ctrl_energy.textChanged.connect(self.update_ui)
        self.ctrl_focus.textChanged.connect(self.update_ui)
        self.ctrl_intensity.textChanged.connect(self.update_ui)
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

    def mefi(self):
        return (parse_ints(self.ctrl_vacc.text()),
                parse_ints(self.ctrl_energy.text()),
                parse_ints(self.ctrl_focus.text()),
                parse_ints(self.ctrl_intensity.text()))

    def can_start(self):
        try:
            mefi = self.mefi()
        except ValueError:
            return False
        return all(mefi)

    def start(self):
        self.ctrl_tab.setCurrentIndex(2)
        self.running = True
        try:
            mefi = (parse_ints(self.ctrl_vacc.text()),
                    parse_ints(self.ctrl_energy.text()),
                    parse_ints(self.ctrl_focus.text()),
                    parse_ints(self.ctrl_intensity.text()))
            pars = [self.ctrl_params.item(i).text()
                    for i in range(self.ctrl_params.count())]
            args = (pars, mefi)
            self.worker = threading.Thread(target=self.download, args=args)
            self.worker.start()
        except:
            self.running = False
            raise

    def cancel(self):
        self.running = False

    def log(self, text, *args, **kwargs):
        self.logged.emit(text.format(*args, **kwargs))

    def load_dll(self):
        self.log('Connecting DLL')
        # dll = BeamOptikDLL(BeamOptikDllProxy({}))
        dll = BeamOptikDLL.load_library()
        dll.GetInterfaceInstance()
        self.dll = dll
        self.log('Connected')

    def download(self, params, mefis):
        if self.dll is None:
            self.load_dll()
        mul = lambda a, b: a * b
        num = functools.reduce(mul, map(len, mefis))
        for i, mefi in enumerate(itertools.product(*mefis)):
            if not self.running:
                break
            progress = '{}/{} = {:.0f}%'.format(i, num, i/num*100)
            self.download_mefi(params, mefi, progress)


    def download_mefi(self, params, mefi, progress):

        folder = os.path.join(DATA_FOLDER, 'params')
        try:
            os.makedirs(folder)
        except OSError:     # no exist_ok on py2
            pass
        filename = os.path.join(folder, 'M{}-E{}-F{}-I{}.str'.format(*mefi))

        with open(filename, 'w') as f:
            vacc, energy, focus, intensity = mefi
            if vacc != self.dll.GetSelectedVAcc():
                self.log('SelectVAcc({})', vacc)
                self.dll.SelectVAcc(vacc)
            self.log('[{}] SelectMEFI(M={}, E={}, F={}, I={})', vacc, *mefi)
            self.dll.SelectMEFI(*mefi)

            for param in params:
                if not self.running:
                    break
                self.log('... {}', param)
                try:
                    val = self.dll.GetFloatValue(param)
                except RuntimeError as e:
                    self.log(' -> FAILED: {}', e)
                else:
                    self.log(' -> {}', val)
                    # MADX compatible output format:
                    f.write('{} = {:.15e};\n'.format(param, val))


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
