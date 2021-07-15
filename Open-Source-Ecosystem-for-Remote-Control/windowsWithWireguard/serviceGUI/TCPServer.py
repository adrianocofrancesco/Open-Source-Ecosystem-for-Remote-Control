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


class TCPServer:

    def __init__(self, host='0.0.0.0', port=65001, max_clients=3):
        self.host = host
        self.port = port
        self.timeout = 30
        self.counter_limit = 10
        self.socket_buffer = 1024
        self.time_sleep = 0.5

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        self.socket.listen(max_clients)
        self.socket.settimeout(self.timeout)

        self.client = None

    def run(self, selectedComPort):

        print("Server {} listening on port {}".format(self.host, self.port))
        try:
            while True:
                self.client = None
                # accept client connection
                conn, addr = self.socket.accept()
                self.client = conn

                self.runThread(conn, addr, selectedComPort)

        except socket.timeout:
            print("Closing Server")
            self.socket.close()
        except Exception as e:
            print("Error: {}".format(e))
            self.socket.close()

    def runThread(self, client, address, comPort):
        print("Server {} listening on port {}".format(self.host, self.port))
        try:
            with client:
                print("Connected by: {}".format(address))
                counter = 0
                while True:
                    # receive data from client
                    try:
                        data = client.recv(self.socket_buffer)
                        print("Received from Client {}: {}".format(address, data))
                    except Exception as error:
                        print("Server recv error: {}".format(error))
                        break

                    try:
                        if data:
                            try:
                                ser = serial.Serial(comPort, timeout=10)
                                print("Selected: {}".format(ser.name))  # check which port was really used
                                ser.write(data + b'\n')  # write a string

                                print("Data sent to serial port")
                                s = ser.readline()
                                print("Received from serial port: '{}'".format(s.decode()))
                                ser.close()

                                if not s:
                                    s = b"null\n"

                                client.sendall(s)
                            except:
                                msg = "Error on serial: {}\n".format(sys.exc_info()[0])
                                print(msg)
                                client.sendall(msg.encode('utf-8'))
                        else:
                            counter += 1
                            print("waiting...")
                            time.sleep(self.time_sleep)
                            if counter > self.counter_limit:
                                print("Closing connection with Client: {}".format(address))
                                client.close()
                                break
                    except Exception as e:
                        print("Error: {}".format(e))
                        client.close()
                        break

        except socket.timeout:
            print("Closing Server")
            self.socket.close()
        except Exception as e:
            print("Error: {}".format(e))
            self.socket.close()

    def close(self):
        if self.client is not None:
            self.client.close()
        self.socket.close()