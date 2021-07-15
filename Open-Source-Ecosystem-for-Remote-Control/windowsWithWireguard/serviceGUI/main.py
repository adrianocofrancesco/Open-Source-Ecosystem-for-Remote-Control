#
#   Copyright 2021  Adriano Cofrancesco
#   Open-Source-Ecosystem-for-Remote-Control is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#   Open-Source-Ecosystem-for-Remote-Control is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import sys, serial, subprocess, shutil, os, traceback
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from TCPClientRSA import TCPClientRSA
from TCPServer import TCPServer

from pic2str import icon_s, logo, redLed, greenLed
import base64
from io import BytesIO
from PIL import Image, ImageQt

ERROR_STATE = "KO"


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(str)


class Worker(QRunnable):
    # Worker thread
    #
    # Inherits from QRunnable to handler worker thread setup, signals and wrap-up.
    #
    # :param callback: The function callback to run on this worker thread. Supplied args and
    #                  kwargs will be passed through to the runner.
    # :type callback: function
    # :param args: Arguments to pass to the callback function
    # :param kwargs: Keywords to pass to the callback function

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done


class Ui_GuiService(object):
    def setupUi(self, GuiService):
        self.red_img = GuiServiceMainWindow.load_image(redLed)
        logo_image = GuiServiceMainWindow.load_image(logo)

        GuiService.setObjectName("GuiService")
        GuiService.resize(1058, 664)
        self.logo_img = QLabel(GuiService)
        self.logo_img.setGeometry(QRect(10, 10, 451, 201))
        self.logo_img.setText("")
        self.logo_img.setPixmap(logo_image)
        self.logo_img.setScaledContents(True)
        self.logo_img.setObjectName("logo_img")
        self.status_img = QLabel(GuiService)
        self.status_img.setGeometry(QRect(890, 30, 80, 80))
        self.status_img.setText("")
        self.status_img.setPixmap(self.red_img)
        self.status_img.setScaledContents(True)
        self.status_img.setObjectName("status_img")
        self.connect_btn = QPushButton(GuiService)
        self.connect_btn.setGeometry(QRect(540, 50, 250, 80))
        self.connect_btn.setObjectName("connect_btn")
        self.disconnect_btn = QPushButton(GuiService)
        self.disconnect_btn.setEnabled(True)
        self.disconnect_btn.setGeometry(QRect(540, 150, 250, 80))
        self.disconnect_btn.setObjectName("disconnect_btn")
        self.output_textbox = QTextBrowser(GuiService)
        self.output_textbox.setGeometry(QRect(10, 250, 1031, 401))
        self.output_textbox.setObjectName("output_textbox")
        self.serial_port_combobox = QComboBox(GuiService)
        self.serial_port_combobox.setGeometry(QRect(810, 180, 231, 51))
        self.serial_port_combobox.setEditable(False)
        self.serial_port_combobox.setCurrentText("")
        self.serial_port_combobox.setPlaceholderText("")
        self.serial_port_combobox.setObjectName("serial_port_combobox")
        self.label = QLabel(GuiService)
        self.label.setGeometry(QRect(820, 120, 120, 50))
        font = QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setObjectName("label")

        self.retranslateUi(GuiService)
        QMetaObject.connectSlotsByName(GuiService)

    def retranslateUi(self, GuiService):
        _translate = QCoreApplication.translate
        GuiService.setWindowTitle(_translate("GuiService", "GUI_Service"))
        self.connect_btn.setText(_translate("GuiService", "Connect"))
        self.disconnect_btn.setText(_translate("GuiService", "Disconnect"))
        self.label.setText(_translate("GuiService", "Serial Port"))


class GuiServiceMainWindow(QWidget):
    def __init__(self):
        super(GuiServiceMainWindow, self).__init__()

        self.green_img = self.load_image(greenLed)
        self.red_img = self.load_image(redLed)
        self.icon_img = self.load_image(icon_s)

        self.setWindowIcon(QIcon(self.icon_img))
        self.setWindowTitle("Service GUI")
        self.ui = Ui_GuiService()
        self.ui.setupUi(self)
        self.ui.output_textbox.setText("GUI setup...")

        self.wireguard_conf_file_path = ""
        self.serial_port_selected = ""
        self.server_tcp = ""

        self.setElementDisabled()
        self.setElementEvents()

        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

    def threadComplete(self):
        print("Thread complete!")

    def outputResult(self, result):
        if result is not None and result[0] == ERROR_STATE:
            self.openDialog(result[1])
        print(result)

    def setElementDisabled(self):
        self.ui.disconnect_btn.setDisabled(True)

    def setElementEvents(self):
        self.ui.connect_btn.clicked.connect(self.workerContainer)
        self.ui.disconnect_btn.clicked.connect(self.closeSocket)

    def progressOutput(self, message):
        self.ui.output_textbox.append(message)
        self.ui.output_textbox.update()

    def closeSocket(self):
        self.server_tcp.close()

    def workerContainer(self):

        worker = Worker(self.runVPN)  # Any other args, kwargs are passed to the run function
        worker.signals.result.connect(self.outputResult)
        worker.signals.finished.connect(self.threadComplete)
        worker.signals.progress.connect(self.progressOutput)

        # Execute
        self.threadpool.start(worker)

    def runVPN(self, progress_callback):
        if self.ui.serial_port_combobox.currentText().startswith("COM"):
            try:
                self.serial_port_selected = self.ui.serial_port_combobox.currentText()

                clientRSA = TCPClientRSA('<IP_SERVER>')
                clientRSA.run()

                progress_callback.emit("Configuration file received successfully.")

                self.ui.disconnect_btn.setDisabled(False)
                self.ui.serial_port_combobox.setDisabled(True)
                self.ui.connect_btn.setDisabled(True)

                self.openVPN(progress_callback)
                self.runTCPServer(progress_callback)
                self.closeVPN(progress_callback)
            except Exception as e:
                print("Exception catched: {}".format(e))
        else:
            print("Warning: " + self.ui.serial_port_combobox.currentText())
            return ERROR_STATE, "Serial port MUST be selected!"

    def openDialog(self, message):
        messageBox = QMessageBox()
        messageBox.setIcon(QMessageBox.Warning)
        messageBox.setWindowIcon(QIcon(self.icon_img))
        messageBox.setText(message)
        messageBox.setWindowTitle("WARNING")
        messageBox.setStandardButtons(QMessageBox.Ok)
        messageBox.exec_()

    def runTCPServer(self, progress_callback):
        progress_callback.emit("Service ongoing...")
        self.server_tcp = TCPServer()
        self.server_tcp.run(self.serial_port_selected)

    def openVPN(self, progress_callback):
        try:
            where_cmd = subprocess.run(["where", "wireguard"], check=True, stdout=subprocess.PIPE, universal_newlines=True)
            print("Find Wireguard return code: {}".format(where_cmd.returncode))

            if where_cmd.returncode != 0:
                return ERROR_STATE, "Wireguard not found!"

            where_out = where_cmd.stdout.rstrip()

            wireguard_path = where_out[0:where_out.rfind('\\')]
            wireguard_conf_path = os.path.join(wireguard_path, "Data", "Configurations")
            self.wireguard_conf_file_path = os.path.join(wireguard_conf_path, TCPClientRSA.configFileName + ".dpapi")

            shutil.move(TCPClientRSA.configFileName, wireguard_conf_path)

            wg_start_cmd = subprocess.run(
                "wireguard /installtunnelservice \"{}\"".format(self.wireguard_conf_file_path),
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                universal_newlines=True
            )

            print("Start Wireguard return code: {}".format(wg_start_cmd.returncode))

            if wg_start_cmd.returncode != 0:
                return ERROR_STATE, "Wireguard, error on startup!"

            progress_callback.emit("VPN activated!")
            self.ui.status_img.setPixmap(self.green_img)
        except Exception as e:
            print("Exception catched on openVPN: {}".format(e))
            self.setRedLight()
            return ERROR_STATE, "Error on VPN startup!"

    def closeVPN(self, progress_callback):
        try:
            wg_end_cmd = subprocess.run(
                "wireguard /uninstalltunnelservice {}".format(TCPClientRSA.configFileName.replace(".conf", "")),
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                universal_newlines=True
            )

            print("Close VPN return code: {}".format(wg_end_cmd.returncode))

            if wg_end_cmd.returncode != 0:
                return ERROR_STATE, "Wireguard, error on close!"

            os.remove(self.wireguard_conf_file_path)

            progress_callback.emit("VPN closed!")
            self.setRedLight()

        except Exception as e:
            print("Exception catched on closeVPN: {}".format(e))
            return ERROR_STATE, "Error on closing VPN!"

    @staticmethod
    def load_image(image_alias):
        byte_data = base64.b64decode(image_alias)
        image_data = BytesIO(byte_data)
        image = Image.open(image_data)

        qImage = ImageQt.ImageQt(image)
        return QPixmap.fromImage(qImage)

    def populateAvailableSerialPorts(self):
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        else:
            raise EnvironmentError('Unsupported platform')

        self.ui.serial_port_combobox.addItem("Select serial port...")
        comPorts = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                comPorts.append(port)
                self.ui.serial_port_combobox.addItem(port)
            except (OSError, serial.SerialException):
                pass

        print(comPorts)
        message = "No COM port available"
        if len(comPorts) > 0:
            message = "COM port available: {0}".format(comPorts)

        self.ui.output_textbox.append(message)

    def setRedLight(self):
        self.ui.status_img.setPixmap(self.red_img)
        self.ui.disconnect_btn.setDisabled(True)
        self.ui.connect_btn.setDisabled(False)
        self.ui.serial_port_combobox.setDisabled(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = GuiServiceMainWindow()
    win.populateAvailableSerialPorts()
    win.show()
    sys.exit(app.exec_())
