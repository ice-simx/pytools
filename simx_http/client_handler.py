#
# Author    : Simrat Singh
# Date      : Apr-2020
#

import threading
import socket
import select
import time


def nextValueOf(text, src_list):
    print(src_list)
    x = len(src_list)
    flag = 0
    for i in range(x):
        if (flag == 1): return src_list[i]
        #
        # pattern found, now need to return the next value
        # set flag to return on next value
        #
        if (src_list[i] == text): flag = 1      
    raise ValueError


def portForService(protocol):
    if ("http" == protocol):
        return 80
    elif ("https" == protocol):
        return 443


class clientHandlerThread(threading.Thread):
    static_resp = ("HTTP/1.0 200 OK \r\n"
            "Date: Thu, 14 Mar 2019 16:28:53 GMT\r\n"
            "Server: Apache/2.2.14 (Win32)\r\n"
            "Last-Modified: Wed, 22 Jul 2009 19:15:56 GMT\r\n"
            "Content-Length: 0\r\n"
            "Content-Type: text/html\r\n"
            "\r\n")


    def __init__(self, thread_id, conn, addr, data=""):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.conn = conn
        self.addr = addr
        self.data = data


    def run(self):        
        
        # self.conn.setblocking(False) # working for HTTP but error with SSL
        self.conn.setblocking(True)

        if not self.data:
            print("[=] receiving data!!!")
            data = self.conn.recv(8192)
            self.data = data.decode("utf-8")

        # print("[{0:03d}] recv data ----------[ {0} ]\n==>{1}<==\n".format(self.thread_id, self.data))
        try:
            self._processRequest()
           
        except socket.error as e:
            print("[{:03d}] exception occurs 01: {}".format(self.thread_id, e))
        except ValueError as e:
            print("[{:03d}] exception occurs 02: {}".format(self.thread_id, e))
        except IndexError as e:
            print("[{:03d}] exception occurs 03: {}".format(self.thread_id, e))            
        finally:
            if (self.conn): 
                print("[{0:03d}] closing client connection ----------------[ {0:d} ]".format(self.thread_id))
                self.conn.close()
                

    def _processRequest(self):
        # ============ Sample Request Format for HTTPS =============================================
        # CONNECT null-byte.wonderhowto.com:443 HTTP/1.1
        # User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:67.0) Gecko/20100101 Firefox/67.0
        # Proxy-Connection: keep-alive
        # Connection: keep-alive
        # Host: null-byte.wonderhowto.com:443        
        # ==========================================================================================

        # self.conn.send(self.static_resp.encode("utf-8"))
        
        #
        # Fetching webserver address and port from 
        # the very first line of request        
        #
        first_line = self.data.split('\n')[0]

        # check for HTTP Method in client request
        header_list = first_line.split(' ')
        if (header_list[0] not in ["GET", "POST", "CONNECT"]):
            print("[{:03d}] invalid HTTP method: {}".format(self.thread_id, header_list[0]) )
            return

        #
        # item at index 1 of first-line is the webserver/website/target server address
        #
        url = header_list[1]

        webserver = ""
        port = -1
        protocol = ""

        temp_index = url.find("://")
        if (temp_index != -1):
            #
            # skip "://" and get the rest of url
            # the 'url' may be like
            # <ip-address>:<port>
            #
            protocol = url[:temp_index]
            url = url[(temp_index + 3):]
            
        index_p = url.find(":")
        index_r = url.find("/")
        if (index_r == -1): index_r = len(url)

        if (index_p == -1):
            #
            # do not found the port index ':' in url
            # webserver is considered upto location of '/'
            # absense of port means default 'port-80'
            #
            webserver = url[:index_r]
            port = portForService(protocol)
        else:
            #
            # port index has been found
            #
            webserver = url[:index_p]
            port = int(url[index_p + 1:index_r] )

        #
        # connecting to remote server (ie destination webserver)
        # pass self.data ie original request to it
        # and send back the response to client
        #
        print("[{:03d}] connecting: server => {} : {}".format(self.thread_id, webserver, str(port)) )
        if (header_list[0] in ["GET", "POST"]):
            self.targetHTTPServer(webserver, port)
        elif (header_list[0] == "CONNECT"):
            self.targetSSLServer(webserver, port)
        else:
            print("[{:03d}] ALERT!!! this statement should never execute!!!".format(self.thread_id))
            return


    def targetHTTPServer(self, webserver, port):
        try:
            sock_web = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_web.connect((webserver, port))
            #
            # to avoid WinError 10035:
            # "A non-blocking socket operation could not be completed immediately"
            # which occurs during conn.recv() call
            # so setting blocking to True ie setblocking(True)
            #
            # Solution: use select() and do setblocking(False)
            # It is normal for WSAEWOULDBLOCK to be reported as the result from 
            # calling connect on a nonblocking SOCK_STREAM socket, since 
            # some time must elapse for the connection to be established.
            #
            # another similar error:
            # WinError 10056 - socket already connected
            #
            sock_web.setblocking(False)
            sock_web.sendall(str.encode(self.data))

            while True:
                ready = select.select([sock_web], [], [], 8)
                if (not ready[0] and not ready[1] and not ready[2]): break
                for s in ready[0]:
                    if s is sock_web:                
                        reply = sock_web.recv(4096)
                        if (len(reply) > 0):
                            self.conn.send(reply)
                            dar = float(len(reply))
                            dar = float(dar / 1024)
                            dar = "%.3s" % (str(dar))
                            dar = "%s KB" % (dar)
                            print("[{:03d}] request done: {} => {} <=".format(self.thread_id, str(self.addr[0]), str(dar)) )
                        else:
                            s.shutdown(socket.SHUT_RD)

        except socket.error as e:
            print("[{:03d}] exception occurs: {}".format(self.thread_id, e))
        # except:
        #     print("[{:03d}] exception occurs: unknown exception".format(self.thread_id))
        finally:
            print("[{:03d}] closing webserver socket".format(self.thread_id))
            sock_web.close()

    
    def targetSSLServer(self, webserver, port):
        #
        # https://www.ietf.org/rfc/rfc2817.txt
        # Page 5: HTTP upgrade to TLS
        #
        # Any successful (2xx) response to a CONNECT request indicates that the
        # proxy has established a connection to the requested host and port,
        # and has switched to tunneling the current connection to that server
        # connection.
        #
        # A proxy MUST NOT respond with any 2xx status code
        # unless it has either a direct or tunnel connection established to the
        # authority.
        #
        proxy_resp = "HTTP/1.1 200 Connection established\nProxy-Agent: THE Simx ProxyGateway\n\n"
        try:
            sock_web = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_web.connect((webserver, port))
            #
            # to avoid WinError 10035: 
            # "A non-blocking socket operation could not be completed immediately"
            # which occurs during conn.recv() call
            # so setting blocking to True
            #
            # using select() as solution to this issue
            #
            sock_web.setblocking(False)
            self.conn.setblocking(False)

            # print("[{:03d}] client socket: {}".format(self.thread_id, self.conn))
            # print("[{:03d}] web+++ socket: {}".format(self.thread_id, sock_web))

            #
            # since connection with server is successful
            # Proxy should send the 2xx reply to client.
            #
            self.conn.sendall(proxy_resp.encode("utf-8") )

            #
            # now need to start the loop for handing over request-reponse
            # between client and server via proxy
            #
            inputs = [sock_web, self.conn]
            outputs = []
            while True:
                # ready = select.select(inputs, outputs, inputs, 8) # WHY FAILS WITH THIS
                ready = select.select([sock_web, self.conn], [], [], 8)
                if (not ready[0] and not ready[1] and not ready[2]): break
                for s in ready[0]:
                    sock_recv = None
                    sock_send = None

                    if s is self.conn:
                        #
                        # data from client is received by proxy
                        # read from self.conn.recv()
                        # 
                        print("[{:03d}] client --> webserver ".format(self.thread_id), end='')
                        sock_recv = self.conn
                        sock_send = sock_web
                    
                    elif s is sock_web:
                        #
                        # data from server is received by proxy
                        # read from sock_web.recv()
                        #                 
                        print("[{:03d}] client <-- webserver ".format(self.thread_id), end='')
                        sock_recv = sock_web
                        sock_send = self.conn

                    else:
                        print("[{:03d}] xxxxxxxx data from none side xxxxxxxx {}".format(self.thread_id, ready[0]))
                        time.sleep(1)
                        break

                    #
                    # normal send-recv between client and webserver
                    #
                    reply = sock_recv.recv(4096)
                    if (len(reply) > 0):
                        dar = float(len(reply))
                        dar = float(dar / 1024)
                        dar = "%.3s" % (str(dar))
                        dar = "%s KB" % (dar)
                        print("=> {} <=".format(dar))
                        sock_send.sendall(reply)                 
                    else:
                        #
                        # sock_recv is done with sending data and no data will ever receive on this socket
                        #
                        print("^_^")
                        sock_recv.shutdown(socket.SHUT_RD)
                        inputs.remove(sock_recv)

        except socket.error as e:
            print("[{:03d}] exception occurs: {}".format(self.thread_id, e))
        # except:
        #     print("[{:03d}] exception occurs: unknown exception".format(self.thread_id))
        finally:
            print("[{:03d}] closing webserver socket".format(self.thread_id))
            sock_web.close()