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

import sys, traceback, time, yaml
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

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
    message = pyqtSignal()


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

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress
        self.kwargs['socket_message'] = self.signals.message

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

        self.serial_port_selected = ""
        self.client_tcp = None
        self.server_tcp = None

        self.check_sleep = 2
        self.ping_sleep = 0.5
        self.override_timeout = 10

        self.message = ""

        self.thread = None
        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        self.setElementDisabled()
        self.setElementEvents()

        self.ui.serial_port_combobox.addItem("Select serial port...")

    def threadComplete(self):
        print("Thread complete!")

    def outputResult(self, result):
        if result is not None and result[0] == ERROR_STATE:
            self.openDialog(result[1])

    def progressOutput(self, message):
        self.ui.output_textbox.append(message)
        self.ui.output_textbox.update()

    def setElementDisabled(self):
        self.ui.disconnect_btn.setDisabled(True)

    def setElementEvents(self):
        self.ui.connect_btn.clicked.connect(self.workerContainerOpenConnection)
        self.ui.disconnect_btn.clicked.connect(self.workerContainerCloseConnection)

    def getPortsMessage(self):
        self.message = "GET_PORTS"

    def getOpenConnectionMessage(self):
        self.message = "OPEN_CONNECTION"

    def getCloseConnectionMessage(self):
        self.message = "CLOSE_CONNECTION"

    def workerContainer(self):
        worker = Worker(self.runSocket)  # Any other args, kwargs are passed to the run function
        worker.signals.result.connect(self.outputResult)
        worker.signals.finished.connect(self.threadComplete)
        worker.signals.progress.connect(self.progressOutput)
        worker.signals.message.connect(self.getPortsMessage)

        self.threadpool.start(worker)

    def workerContainerOpenConnection(self):
        worker = Worker(self.runSocket)
        worker.signals.result.connect(self.outputResult)
        worker.signals.finished.connect(self.threadComplete)
        worker.signals.progress.connect(self.progressOutput)
        worker.signals.message.connect(self.getOpenConnectionMessage)

        self.threadpool.start(worker)

    def workerContainerCloseConnection(self):
        worker = Worker(self.runSocket)
        worker.signals.result.connect(self.outputResult)
        worker.signals.finished.connect(self.threadComplete)
        worker.signals.progress.connect(self.progressOutput)
        worker.signals.message.connect(self.getCloseConnectionMessage)

        self.threadpool.start(worker)

    def runSocket(self, progress_callback, socket_message):
        try:
            socket_message.emit()
            time.sleep(self.ping_sleep)
            print("Message : {}".format(self.message))
            if self.message == "GET_PORTS":
                ports = self.runTCPServer(self.message, {'msg': self.message})
                self.populateAvailableSerialPorts(ports)
                self.server_tcp.close()

            elif self.message == "OPEN_CONNECTION":
                if self.ui.serial_port_combobox.currentText().startswith("/dev/"):

                    open_result = self.runTCPServer(self.message, {'msg': self.message, 'comPort': self.ui.serial_port_combobox.currentText()}, True)

                    if open_result is not None:
                        progress_callback.emit("Service ongoing...")

                        self.setConnectedGUI()
                        self.server_tcp.close()

                        while True:

                            check_result = self.runTCPServer(self.message, {'msg': "CHECK"}, True)
                            self.server_tcp.close()
                            time.sleep(self.check_sleep)

                            if check_result is None or not check_result.strip('\n'):
                                progress_callback.emit("Service ended.")
                                break
                    else:
                        progress_callback.emit("Connection lost...")

                    self.setDisconnectedGUI()

                else:
                    print("Warning: " + self.ui.serial_port_combobox.currentText())
                    return ERROR_STATE, "Serial port MUST be selected!"

            elif self.message == "CLOSE_CONNECTION":

                self.runTCPServer(self.message, {'msg': self.message})

                self.server_tcp.close()
                self.setDisconnectedGUI()

        except Exception as e:
            print("Exception catched: {}".format(e))

    def runTCPServer(self, message, yaml_packet, override_timeout=False):
        self.server_tcp = TCPServer()
        if override_timeout:
            self.server_tcp.overrideTimeout(self.override_timeout)
        yaml_data = yaml.dump(yaml_packet)
        result = self.server_tcp.run(yaml_data)

        print("{}: {}".format(message, result))

        return result

    def setDisconnectedGUI(self):
        self.ui.disconnect_btn.setDisabled(True)
        self.ui.connect_btn.setDisabled(False)
        self.ui.serial_port_combobox.setDisabled(False)
        self.ui.status_img.setPixmap(self.red_img)

    def setConnectedGUI(self):
        self.ui.disconnect_btn.setDisabled(False)
        self.ui.serial_port_combobox.setDisabled(True)
        self.ui.connect_btn.setDisabled(True)
        self.ui.status_img.setPixmap(self.green_img)

    def openDialog(self, message):
        messageBox = QMessageBox()
        messageBox.setIcon(QMessageBox.Warning)
        messageBox.setWindowIcon(QIcon(self.icon_img))
        messageBox.setText(message)
        messageBox.setWindowTitle("WARNING")
        messageBox.setStandardButtons(QMessageBox.Ok)
        messageBox.exec_()

    @staticmethod
    def load_image(image_alias):
        byte_data = base64.b64decode(image_alias)
        image_data = BytesIO(byte_data)
        image = Image.open(image_data)

        qImage = ImageQt.ImageQt(image)
        return QPixmap.fromImage(qImage)

    def populateAvailableSerialPorts(self, serialPorts):
        for port in serialPorts:
            self.ui.serial_port_combobox.addItem(port)

        message = "No COM port available"
        if len(serialPorts) > 0:
            message = "COM port available: {0}".format(serialPorts)

        self.ui.output_textbox.append(message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = GuiServiceMainWindow()
    win.workerContainer()
    win.show()
    sys.exit(app.exec_())
