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


class TCPClientRSA:
    configFileName = 'Service.conf'

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
        self.file_name = TCPClientRSA.configFileName

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)

    # function used to generate RSA private and public key
    def generate_keys(self):
        self.private_key = RSA.generate(self.rsa_key_size)

        # public key
        self.public_key = self.private_key.publickey().export_key()

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