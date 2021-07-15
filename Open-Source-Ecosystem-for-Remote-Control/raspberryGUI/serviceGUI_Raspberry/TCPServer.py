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
import time
import yaml


class TCPServer:

    def __init__(self, host='0.0.0.0', port=65001, max_clients=3):
        self.host = host
        self.port = port
        self.timeout = 120
        self.counter_limit = 10
        self.socket_buffer = 1024
        self.time_sleep = 0.5

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        self.socket.listen(max_clients)
        self.socket.settimeout(self.timeout)

        self.client = None
        self.result = None

    def run(self, message):

        print("Server {} listening on port {}".format(self.host, self.port))
        try:
            self.client = None
            # accept client connection
            self.client, addr = self.socket.accept()
            self.runServer(self.client, addr, message)
            self.close()
            return self.result

        except socket.timeout:
            print("Closing Server")
            self.socket.close()
        except Exception as e:
            print("Error: {}".format(e))
            self.socket.close()

    def runServer(self, client, address, message):
        print("Server {} listening on port {}".format(self.host, self.port))
        try:
            with client:
                print("Connected by: {}".format(address))
                counter = 0
                try:
                    client.sendall(message.encode('utf-8'))
                except Exception as error:
                    print("Server recv error: {}".format(error))

                while True:
                    # receive data from client
                    try:
                        print("Waiting for messages...")
                        data = client.recv(self.socket_buffer)
                        print("Received from Client {}: {}".format(address, data))
                    except Exception as error:
                        print("Server recv error: {}".format(error))
                        break

                    try:
                        if data:
                            # populate COM port
                            data_yaml = yaml.load(data.decode('utf-8'), Loader=yaml.FullLoader)
                            if data_yaml and 'comPorts' in data_yaml:
                                self.result = data_yaml['comPorts']
                                break
                            elif data_yaml and 'openConnection' in data_yaml:
                                self.result = data_yaml['openConnection']
                                break
                            elif data_yaml and 'closeConnection' in data_yaml:
                                self.result = data_yaml['closeConnection']
                                break
                            elif data_yaml and 'check' in data_yaml:
                                self.result = data_yaml['check']
                                break

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
        print("Closing Server...")
        if self.client is not None:
            self.client.close()
        self.socket.close()

    def overrideTimeout(self, timeout):
        self.socket.settimeout(timeout)