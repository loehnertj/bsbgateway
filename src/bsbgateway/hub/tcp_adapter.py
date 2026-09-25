import logging
from quickrpc.transports import RestartingTransport
from quickrpc.network_transports import TcpClientTransport
from .adapter_settings import AdapterSettings
from .event import event

L = lambda: logging.getLogger(__name__)

class TcpClientTransportWithToken(TcpClientTransport):
    def __init__(self, host:str, port:int, token:bytes, connect_timeout=10, buffersize:int=1024):
        super().__init__(host, port, connect_timeout=connect_timeout, buffersize=buffersize)
        self.token = token
    
    def open(self):
        """Open the connection and send the token for authentication."""
        super().open()
        # cannot use self.send, because running flag is not yet set.
        self.socket.sendall(self.token)

class TcpAdapter:
    def __init__(self, host: str, port:int, token:bytes):
        self.transport = RestartingTransport(TcpClientTransportWithToken(host, port, token=token))
        self.transport.set_on_received(self._on_received)
        self.host = host
        self.port = port
    
    @classmethod
    def from_adapter_settings(cls, settings: AdapterSettings):
        assert settings.adapter_type == 'tcp'
        token = bytes.fromhex(settings.tcp_token)
        if len(token) != 32:
            raise ValueError("Token must be 32 bytes long")
        return cls(settings.tcp_host, settings.tcp_port, token)

    @event
    def rx_bytes(data: bytes): # type: ignore
        """Emitted when data is received from the TCP server.
        """

    def start_thread(self):
        """Start client"""
        # actually, TcpClientTransport maintains the thread.
        self.transport.start()

    def stop(self):
        """Stop client"""
        self.transport.stop()

    def _on_received(self, sender:str, data: bytes) -> bytes:
        """Handle data received from the TCP server. Returns leftover data."""
        self.rx_bytes(data)
        return b''

    def tx_bytes(self, data: bytes):
        """Send data to the TCP server."""
        try:
            self.transport.send(data)
        except OSError as e:
            L().error(f"Failed to send data to TCP server {self.host}:{self.port}: {e}")