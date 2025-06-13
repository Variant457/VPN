from socket import error, gethostbyname, AF_INET
from logging import getLogger, basicConfig, DEBUG, error as log_error, critical, warning, debug
from datetime import datetime
from os import environ
import asyncio
import csv

serverName = environ.get("SERVER")
logger = getLogger(__name__)
csvFile = []

class Server:
    def __init__(self):
        self.host = "0.0.0.0"   # Empty IP Address since AWS handles the IP
        self.port = 12780
        self.dns_cache = {}

    @staticmethod
    async def socket_handler(client:asyncio.StreamWriter, remote:asyncio.StreamWriter= None):
        # Closes the socket if it is still open
        if client and not client.is_closing():
            client.close()
            await client.wait_closed()
        if remote and not remote.is_closing():
            remote.close()
            await remote.wait_closed()

    async def create_socket(self):
        try:
            # Creates TCP socket and asyncio server handling
            server = await asyncio.start_server(self.accept_conn, self.host, self.port)
            print(f"Hosting on {self.host}:{self.port}")
            debug(f"Hosting on {self.host}:{self.port}")

            # Keeps server running
            async with server: await server.serve_forever()
        except error as e:
            log_error(f"Error Creating Socket: {e}\n")

    async def accept_conn(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        payload = None
        try:
            # Gets Client's IP and Initial Request Payload
            strConnectTime = datetime.now()
            addr = client_writer.get_extra_info("peername")
            init_data = await asyncio.wait_for(client_reader.read(4096), timeout= 15.0)     # Timeout to close connection if Client sends nothing

            # Ensures there is data to evaluate
            if not init_data:
                await self.socket_handler(client_writer)
                return

            # Parses payload based on the request type to get the data needed to establish a connection
            payload = init_data.decode().strip()
            domain = None
            port = None
            if(payload.startswith("CONNECT")):
                data = payload.splitlines()[0].split()[1].split(':')
                domain = data[0]
                port = int(data[1])
            elif(payload.startswith("GET") or payload.startswith("HEAD") or payload.startswith("POST")):
                data = payload.splitlines()[0].split()[1]
                protocol = data.split('://')[0]
                domain = data.split('/')[2]

                # Establishes ports based on the protocol type
                if(protocol == "http"):
                    port = 80
                elif(protocol == "https"):
                    port = 443

                # Changes any IPv6 domain to a IPv4 domain
                if(domain.startswith("ipv6")):
                    domain = domain.split('.')
                    domain[0] = "www"
                    domain = '.'.join(domain)
            else:
                raise Exception("Unknown Request Type; Request Type not Supported")
            
            await self.remote_conn(client_reader, client_writer, addr, domain, port, init_data, strConnectTime)
        except asyncio.TimeoutError:
            warning(f"Client {addr} Timed Out")
        except error as e:
            # Ignores typical network errors outside of our control
            if(type(e) not in [ConnectionAbortedError, ConnectionResetError, BrokenPipeError]):
                log_error(f"Error while parsing payload: {e}\n")
            if client_writer and not client_writer.is_closing():
                client_writer.write(b'HTTP/1.1 400 Bad Request\r\n\r\n')
                await client_writer.drain()
                await self.socket_handler(client_writer)
        except asyncio.CancelledError:
            await self.socket_handler(client_writer)
        except Exception as e:
            log_error(f"Error: {type(e)}, Args: {e.args}")
            if payload: debug(f"Payload:\n{payload.strip()}\n")
            if client_writer and not client_writer.is_closing():
                client_writer.write(b'HTTP/1.1 501 Not Implemented\r\n\r\n')
                await client_writer.drain()
                await self.socket_handler(client_writer)            

    async def get_host(self, domain):
        #Checks if domain has already been gathered before
        #Caches new domains to prevent reaccuring calls for the same domains
        if(domain in self.dns_cache): return self.dns_cache[domain]
        else:
            try:
                loop = asyncio.get_running_loop()
                result = await loop.getaddrinfo(domain, None, family= AF_INET)
                host = None
                if result: 
                    host = result[0][4][0]
                    self.dns_cache[domain] = host
                return host
            except error as e:
                log_error(f"Error getting remote IP from {domain}: {e}")
                return None

    async def remote_conn(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter, client_addr, remote_domain, remote_port, data: bytes, srtTime: datetime):
        remote_writer = None
        try:
            # Gets IP from the Remote Domain
            host = await self.get_host(remote_domain)

            if not host:
                raise error("Host IP not Found")
            
            # Establishes TCP connection to Remote Server, tells Client it's connected
            remote_reader, remote_writer = await asyncio.wait_for(asyncio.open_connection(host, remote_port), timeout= 15.0)
            if data.startswith(b"CONNECT"):
                client_writer.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')
                await client_writer.drain()
            else:
                if remote_writer and not remote_writer.is_closing():
                    remote_writer.write(data)
                    await remote_writer.drain()

            # Establishes bidirectional communication between the Client and the Remote Server
            client_to_remote = asyncio.create_task(self.data_comm(client_reader, client_addr, remote_writer, remote_domain))
            remote_to_client = asyncio.create_task(self.data_comm(remote_reader, remote_domain, client_writer, client_addr))

            # Waits for one of the communication lines to close
            done, pending = await asyncio.wait({client_to_remote, remote_to_client}, return_when= asyncio.FIRST_COMPLETED)

            # Ends the remaining communication line after the first one ends
            for task in pending:
                task.cancel()
                await task
            if pending: await asyncio.wait(pending)
        except asyncio.TimeoutError:
            log_error(f"Server took too long to establish a connection to {remote_domain}@{remote_port}")
            if client_writer and not client_writer.is_closing():
                client_writer.write(b'HTTP/1.1 504 Gateway Timeout\r\n\r\n')
                await client_writer.drain()
        except error as e:
            log_error(f"Error while connecting to {remote_domain}@{remote_port}: {e}\n")
            if client_writer and not client_writer.is_closing():
                client_writer.write(b'HTTP/1.1 502 Connection Failed\r\n\r\n')
                await client_writer.drain()
        except Exception as e:
            critical(f"CRITICAL!!! - Coroutine Error while transferring packets: {e}\n")
            if client_writer and not client_writer.is_closing():
                client_writer.write(b'HTTP/1.1 500 Internal Server Error\r\n\r\n')
                await client_writer.drain()
        finally:
            # Output execution time for testing purposes
            print(len(asyncio.all_tasks()))     # Debugging Tool to see active socket count
            endTime = datetime.now()
            exeTime = endTime - srtTime
            print(exeTime)
            csvFile.append({"Server Name": serverName, "Version": "Async", "Active Socket Count": len(asyncio.all_tasks()), "Execution Time": exeTime})

            await self.socket_handler(client_writer, remote_writer)

    @staticmethod
    async def data_comm(sender: asyncio.StreamReader, sender_name: str, receiver: asyncio.StreamWriter, receiver_name: str):
        # Receives data from either the Client or Remote Server and passes it to the other
        try:
            while True:
                data = await asyncio.wait_for(sender.read(8192), timeout= 300.0)
                if not data: break                  # End Loop when Payload no longer has Data

                receiver.write(data)
                await receiver.drain()
        except error as e:
            # Outputs Errors besides the ones that we are not worried about
            if(type(e) not in [ConnectionAbortedError, ConnectionResetError, BrokenPipeError]):
                log_error(f"Communication Error: {type(e)} : {e}\nOccurred when attempting to transmit payload from {sender_name} to {receiver_name}\n")
        except asyncio.TimeoutError:
            log_error(f"Timeout while sending payload from {sender_name} to {receiver_name}")
        finally:
            if receiver and not receiver.is_closing():
                if receiver.can_write_eof():
                    receiver.write_eof()
                    await receiver.drain()

def main():
    try:
        # Sets up log and starts server
        basicConfig(filename= "server.log", level= DEBUG, format= "%(asctime)s - %(levelname)s - %(message)s", datefmt= "%m/%d %H:%M:%S %Z%z", filemode= 'w')
        asyncio.run(Server().create_socket())
    except KeyboardInterrupt:
        with open("output.csv", 'a') as file:
            writer = csv.DictWriter(file, fieldnames= ["Server Name", "Version", "Active Socket Count", "Execution Time"])
            writer.writeheader()
            for row in csvFile:
                writer.writerow(row)
    except Exception as e:
        critical(f"CRITICAL!!! - Unknown Error: {e}\n")

main()