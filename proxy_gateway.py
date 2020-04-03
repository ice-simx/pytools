#
# Author    : Simrat Singh
# Date      : Apr-2020
#

import socket
import select
import sys
import time
import enum

from simx_http.client_handler import clientHandlerThread

"""
https://null-byte.wonderhowto.com/how-to/sploit-make-proxy-server-python-0161232/

Types of Proxy:
1) PHP Proxy
2) CGI Proxy
3) HTTP Proxy
4) Gateway Proxy    <== [the one implementing here]
5) DNS Proxy
6) Anonymous HTTPS Proxy
7) Suffix Proxy
8) TOR Proxy
9) I2P Anonymous Proxy

https://www.geeksforgeeks.org/creating-a-proxy-webserver-in-python-set-1/

"""

class ProxyType(enum.Enum):
    direct = 1
    proxy = 2
        

if __name__ == "__main__":

    max_connection = 5
    buf_size = 8192
    port = 3139
    proxy_type = ProxyType.direct
    id = 0
    inputs = []
    outputs = []

    try:
        sock_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock_server.bind(('', port))
        sock_server.listen(max_connection)
        sock_server.setblocking(False)
        print("[=] server started successfully on port {}".format(port))

        inputs.append(sock_server)
        # inputs.append(sys.stdin)
        while inputs:
            print("[=] waiting for new request")
            #
            # todo: need to implement select
            # timeout field has been set as on Windows during select() prog
            # do respond to Ctrl+C
            # It is after timeout it accept 'pending' user interrupt
            #
            readable, writable, exceptional = select.select (inputs, outputs, inputs, 20)
            for s in readable:
                if s is sock_server:
                    id = id + 1
                    print("[{:03d}] accepting new request".format(id))
                    sock_client, addr = s.accept()

                    #
                    # starting a new thread
                    #
                    clientHandlerThread(id, sock_client, addr).start()

    except KeyboardInterrupt as e:
        print("[=] user interrupt")
        sys.exit(1)

    # except:
    #     print("[-] unknown exception occurs")

    finally:
        if (sock_server):
            sock_server.close()
            print("[=] server socket closed")
# --end--