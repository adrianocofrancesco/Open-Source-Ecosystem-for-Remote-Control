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

import base64


def pic2str(file, functionName):
    pic = open(file, 'rb')
    content = '{} = {}\n'.format(functionName, base64.b64encode(pic.read()))
    pic.close()

    with open('pic2str.py', 'a') as f:
        f.write(content)


if __name__ == '__main__':
    pic2str('./ui/img/icon_s.png', 'icon_s')
    pic2str('./ui/img/devops-infinite.png', 'logo')
    pic2str('./ui/img/green-led-on.png', 'greenLed')
    pic2str('./ui/img/red-led-on.png', 'redLed')