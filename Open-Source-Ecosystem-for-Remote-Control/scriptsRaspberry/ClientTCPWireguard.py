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

from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import AES, PKCS1_OAEP
import yaml
import socket
import serial
import time
import subprocess
import shutil
import os
import sys
import glob

configFileName = 'Service.conf'


class TCPClientRSA:

    def __init__(self, host='0.0.0.0', port=65001):
        self.private_key = ""
        self.public_key = ""
        self.rsa_key_size = 2048
        self.session_key_size = 16
        self.host = host
        self.port = port
        self.timeout = 10
        self.counter_limit = 10
        self.socket_buffer = 1024
        self.time_sleep = 0.5
        self.file_name = configFileName

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)

    # function used to generate RSA private and public key
    def generate_keys(self):
        self.private_key = RSA.generate(self.rsa_key_size)

        # public key
        self.public_key = self.private_key.public_key().export_key()

    def run(self):
        self.generate_keys()

        # open socket with server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.settimeout(self.timeout)

            # build yaml object to send public key to server
            public_key_yaml = yaml.dump({'pubkey': self.public_key.decode()})
            public_key_yaml_binary = public_key_yaml.encode()

            # send key to server
            s.sendall(public_key_yaml_binary)

            # receive configuration file from server
            data_received = s.recv(self.socket_buffer)

            try:
                # retrieve all keys to perform decryption
                session_key_index = self.private_key.size_in_bytes()
                nonce_index = session_key_index + self.session_key_size
                tag_index = nonce_index + self.session_key_size

                enc_session_key = data_received[:session_key_index]
                nonce = data_received[session_key_index:nonce_index]
                tag = data_received[nonce_index:tag_index]
                cipher_text = data_received[tag_index:]

                cipher_rsa = PKCS1_OAEP.new(self.private_key)
                session_key = cipher_rsa.decrypt(enc_session_key)

                # decrypt the data with the AES session key
                cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)

                # get data decrypted
                data = cipher_aes.decrypt_and_verify(cipher_text, tag)

                try:
                    # save configuration file received
                    file = open(self.file_name, 'wb')

                    with file:
                        file.write(data)

                    print("Configuration file received successfully.")

                except OSError:
                    print("Could not open file")

            except ValueError as e:
                print("ValueError: {}".format(e))

            except Exception as e:
                print("Error: {}".format(e))


class ClientTCPWireguard:

    def __init__(self, host='0.0.0.0', port=65001):
        print(host)
        self.host = host
        self.port = port
        self.timeout = 30
        self.socket_buffer = 1024

        self.socket = None
        self.com_ports = []
        self.wireguard_conf_file_path = ""

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
                                client = TCPClientRSA('<IP_SERVER>')
                                client.run()
                                self.openVPN()
                                yaml_data = yaml.dump({'openConnection': 'OK'})
                            elif data_yaml['msg'] == "CLOSE_CONNECTION":
                                self.closeVPN()
                                yaml_data = yaml.dump({'closeConnection': 'OK'})
                            elif data_yaml['msg'] == "CHECK":
                                check_rsa = subprocess.Popen(["sudo", "/home/pi/Desktop/checkServerTCP.sh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                                check_rsa_stdout, stderr = check_rsa.communicate()
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

    def openVPN(self):
        where_cmd = subprocess.Popen(["sudo", "whereis", "wireguard"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        where_stdout, stderr = where_cmd.communicate()
        splitRes = where_stdout.split(':')
        if len(splitRes) > 1:
            where_stdout = splitRes[1].rstrip('\n').lstrip()

        self.wireguard_conf_file_path = os.path.join(where_stdout, configFileName)

        shutil.move(configFileName, self.wireguard_conf_file_path)

        wg_up_cmd = subprocess.Popen(["sudo", "wg-quick", "up", self.wireguard_conf_file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        wg_up_stdout, stderr = wg_up_cmd.communicate()

        subprocess.Popen(["sudo", "/home/pi/Desktop/runServerTCP.sh", data_yaml['comPort'], self.wireguard_conf_file_path],stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    def closeVPN(self):
        close_services = subprocess.Popen(["sudo", "/home/pi/Desktop/closeServerTCP.sh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        close_services_stdout, stderr = close_services.communicate()
        wg_down_cmd = subprocess.Popen(["sudo", "wg-quick", "down", self.wireguard_conf_file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        wg_down_cmd.communicate()

        os.remove(self.wireguard_conf_file_path)


if __name__ == "__main__":
    ip = "0.0.0.0"
    if len(sys.argv) > 1:
        ip = sys.argv[1]

    print("IP: {}".format(ip))
    client = ClientTCPWireguard(ip)
    client.run()
