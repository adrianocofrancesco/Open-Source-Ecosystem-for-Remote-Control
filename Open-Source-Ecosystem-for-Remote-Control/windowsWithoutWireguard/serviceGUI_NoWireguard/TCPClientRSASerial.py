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
from Cryptodome.Random import get_random_bytes

import yaml
import serial
import socket
import time


class TCPClientRSASerial:

    def __init__(self, host='0.0.0.0', port=65001):
        self.private_key = ""
        self.public_key = ""
        self.rsa_key_size = 2048
        self.session_key_size = 16
        self.host = host
        self.port = port
        self.timeout = 60
        self.counter_limit = 10
        self.socket_buffer = 1024
        self.time_sleep = 0.5
        self.server_public_key = ""

        self.socket = None

    # function used to generate RSA private and public key
    def generate_keys(self):
        self.private_key = RSA.generate(self.rsa_key_size)

        # public key
        self.public_key = self.private_key.publickey().export_key()

    def run(self, selectedSerialPort):
        self.generate_keys()

        # open socket with server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.socket:
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(self.timeout)

            pubkey_found = False
            counter = 0
            while not pubkey_found:

                # receive public key from server
                try:
                    print("Client pubkey receive waiting...")
                    data = self.socket.recv(self.socket_buffer)
                    print("Received by Client: ", repr(data))
                except socket.error as error:
                    print("Client timeout... closing client: {}".format(error))
                    self.socket.close()
                    break

                if data:
                    # decode data received by client and convert it in dictionary object
                    data_yaml = yaml.load(data.decode('utf-8'), Loader=yaml.FullLoader)

                    if data_yaml and 'pubkey' in data_yaml:

                        try:
                            # get server public key
                            self.server_public_key = RSA.import_key(data_yaml['pubkey'])
                        except ValueError as e:
                            print("RSA Value Error: {}".format(e))
                            self.send_error(self.socket, 'Wrong RSA key')
                        except Exception as e:
                            print("Error: {}".format(e))
                            self.send_error(self.socket, 'Client internal error')

                        if self.server_public_key:
                            print("Client: received server public key")
                            pubkey_found = True

                            public_key_yaml = yaml.dump({'pubkey': self.public_key.decode('utf-8')})

                            public_key_yaml_binary = public_key_yaml.encode('utf-8')

                            encrypted_data = self.encrypt_data(public_key_yaml_binary)

                            # send public key to server
                            self.socket.sendall(encrypted_data)

                            print("Client public key has been sent.")

                    else:
                        print("Wrong format! {}".format(data_yaml))
                        self.send_error(self.socket, 'Wrong message format')
                else:
                    print("waiting...")
                    counter += 1
                    time.sleep(self.time_sleep)
                    if counter > self.counter_limit:
                        print("Closing connection with Server: {}".format(self.host))
                        self.socket.close()
                        break

            if pubkey_found:
                counter = 0
                while True:
                    try:
                        print("Client receive waiting...")
                        data_received = self.socket.recv(self.socket_buffer)
                    except socket.timeout:
                        print("Closing Client")
                        self.socket.close()
                        break

                    except BaseException as error:
                        print("Client recv error: {}".format(error))
                        self.socket.close()
                        break

                    if data_received:
                        try:
                            data = self.decrypt_data(data_received)

                            print("Received by Client: ", repr(data))

                            data_from_serial = self.serial_communication(selectedSerialPort, data)

                            encrypted_data = self.encrypt_data(data_from_serial)

                            # send serial response to server
                            self.socket.sendall(encrypted_data)

                        except ValueError as e:
                            print("ValueError: {}".format(e))

                        except Exception as e:
                            print("Error: {}".format(e))

                    else:
                        print("waiting...")
                        counter += 1
                        time.sleep(self.time_sleep)
                        if counter > self.counter_limit:
                            print("Closing connection with Server: {}".format(self.host))
                            self.socket.close()
                            break

    def send_error(self, conn, message):
        msg_to_server = yaml.dump({'error': message}).encode('utf-8')
        conn.sendall(msg_to_server)

    def encrypt_data(self, data):
        session_key = get_random_bytes(self.session_key_size)
        cipher_rsa = PKCS1_OAEP.new(self.server_public_key)
        enc_session_key = cipher_rsa.encrypt(session_key)

        cipher_aes = AES.new(session_key, AES.MODE_EAX)
        cipher_text, tag = cipher_aes.encrypt_and_digest(data)

        encrypted_data = enc_session_key + cipher_aes.nonce + tag + cipher_text

        return encrypted_data

    def decrypt_data(self, data_received):

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
        return cipher_aes.decrypt_and_verify(cipher_text, tag)

    def serial_communication(self, serialPort, data):
        ser = serial.Serial(serialPort, timeout=5)
        print(ser.name)  # check which port was really used
        ser.write(data + b'\n')  # write a string

        print("Data sent to serial port {}".format(data + b'\n'))
        serial_result = ser.readline()
        print("Received from serial port: {}".format(serial_result.decode('utf-8')))
        ser.close()

        if not serial_result:
            serial_result = b"null\n"

        return serial_result.decode('utf-8').strip("\n").encode('utf-8')

    def close(self):
        self.socket.close()


if __name__ == '__main__':
    client = TCPClientRSASerial('127.0.0.1')
    client.run()