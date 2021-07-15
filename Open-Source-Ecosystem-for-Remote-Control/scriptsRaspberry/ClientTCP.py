#
#   Copyright 2021  Adriano Cofrancesco
#   Open-Source-Ecosystem-for-Remote-Control is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#   Open-Source-Ecosystem-for-Remote-Control is distributed in the hope that it will be useful,
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

import socket
import serial
import time
import sys
import yaml
import glob
import subprocess


class TCPClient:

    def __init__(self, host='0.0.0.0', port=65001):
        self.host = host
        self.port = port
        self.timeout = 30
        self.socket_buffer = 1024

        self.socket = None
        self.com_ports = []

    def run(self):
        data = b""
        while True:
            try:
                print("Connection")
                cat_stdout = self.checkEthUp()
                if cat_stdout.strip('\n') == "0":
                    print("DOWN")
                    break

                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
                self.socket.settimeout(self.timeout)
                
                while True:
                    try:
                        data = self.socket.recv(1024)
                    except BaseException as error:
                        print("Client recv error: {}".format(error))
                        self.socket.close()
                        break
                        
                    if data:

                        print("Received from Server: ", repr(data))

                        data_yaml = yaml.load(data.decode('utf-8'), Loader=yaml.FullLoader)
                        
                        if data_yaml and 'msg' in data_yaml:

                            if data_yaml['msg'] == "GET_PORTS":
                                self.getSerialPorts()
                                yaml_data = yaml.dump({'comPorts': self.com_ports})
                            elif data_yaml['msg'] == "OPEN_CONNECTION":
                                subprocess.Popen(["sudo", "/home/pi/Desktop/runClientRSA.sh", data_yaml['comPort']], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                                yaml_data = yaml.dump({'openConnection': 'OK'})
                            elif data_yaml['msg'] == "CLOSE_CONNECTION":
                                subprocess.Popen(["sudo", "/home/pi/Desktop/closeServices.sh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                                yaml_data = yaml.dump({'closeConnection': 'OK'})
                            elif data_yaml['msg'] == "CHECK":
                                check_rsa = subprocess.Popen(["sudo", "/home/pi/Desktop/checkTCPClientRSA.sh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                                check_rsa_stdout, stderr = check_rsa.communicate()
                                print("RetCode02: {}".format(check_rsa_stdout))
                                yaml_data = yaml.dump({'check': check_rsa_stdout})

                            data_binary = yaml_data.encode()
                            try:
                                self.socket.sendall(data_binary)
                                print("sent: {}\n".format(data_binary))
                                data = ""
                                self.socket.close()
                                break
                            except socket.error as error:
                                print("Client send error: {}".format(error))
                                self.socket.close()
                                break

            except socket.timeout:
                print("Closing Server")
                self.socket.close()
            except Exception as error:
                print("Client connection error: {}".format(error))
                time.sleep(2)

    def checkEthUp(self):
        cat_cmd = subprocess.Popen(["sudo", "cat", "/sys/class/net/eth0/carrier"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        cat_stdout, stderr = cat_cmd.communicate()
        # print("CAT: '{}'".format(cat_stdout))

        return cat_stdout

    def getSerialPorts(self):
        ports = []
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[0-9A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        for port in ports:
            try:
                ser = serial.Serial(port)
                ser.close()
                self.com_ports.append(port)
            except (OSError, serial.SerialException):
                pass


if __name__ == "__main__":
    ip = "0.0.0.0"
    if len(sys.argv) > 1:
        ip = sys.argv[1]

    print("IP: {}".format(ip))
    client = TCPClient(ip)
    client.run()
