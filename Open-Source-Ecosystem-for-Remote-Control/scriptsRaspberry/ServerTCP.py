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
import os
import sys
import subprocess


class ServerTCP:

    def __init__(self, host='0.0.0.0', port=65001, com_port='/dev/null', max_clients=3):
        self.host = host
        self.port = port
        self.com_port = com_port
        self.timeout = 60
        self.counter_limit = 10
        self.socket_buffer = 1024
        self.time_sleep = 0.5

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        self.socket.listen(max_clients)
        self.socket.settimeout(self.timeout)

    def run(self):

        print("Server {} listening on port {}".format(self.host, self.port))
        try:
            while True:
                # accept client connection
                conn, addr = self.socket.accept()
                with conn:
                    print("Connected by: {}".format(addr))
                    counter = 0
                    while True:
                        # receive data from client
                        try:
                            data = conn.recv(self.socket_buffer)
                            print("Received from Client {}: {}".format(addr, data))
                        except Exception as error:
                            print("Server recv error: {}".format(error))
                            break

                        try:
                            if data:
                                try:
                                    ser = serial.Serial(self.com_port, timeout=10)
                                    print(ser.name)  # check which port was really used
                                    ser.write(data + b'\n')  # write a string

                                    print("Data sent to serial port")
                                    s = ser.readline()
                                    print("Received from serial port: ", s.decode())
                                    ser.close()

                                    conn.sendall(s)
                                except Exception as e:
                                    print("Error: {}".format(e))
                            else:
                                counter += 1
                                print("waiting...")
                                time.sleep(self.time_sleep)
                                if counter > self.counter_limit:
                                    print("Closing connection with Client: {}".format(addr))
                                    conn.close()
                                    break
                        except Exception as e:
                            print("Error: {}".format(e))
                            conn.close()
                            break

        except socket.timeout:
            print("Closing Server")
            self.socket.close()
        except Exception as e:
            print("Error: {}".format(e))
            self.socket.close()


if __name__ == '__main__':
    com_port = "/dev/null"
    wireguard_conf_file_path = "wg0"
    if len(sys.argv) > 2:
        com_port = sys.argv[1]
        wireguard_conf_file_path = sys.argv[2]
    server = ServerTCP('0.0.0.0', 65001, com_port)
    server.run()

    wg_down_cmd = subprocess.Popen(["sudo", "wg-quick", "down", wireguard_conf_file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    wg_down_stdout, stderr = wg_down_cmd.communicate()

    os.remove(wireguard_conf_file_path)
    print("DONE")
