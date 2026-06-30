import socket
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ACBrMonitorError(Exception):
    pass


class ACBrMonitorClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 3434, timeout: int = 30):
        self.host = host
        self.port = port
        self.timeout = timeout

    def _recv_ate_etx(self, sock: socket.socket) -> bytes:
        dados = b""
        while True:
                try:
                    chunk = sock.recv(8192)
                    if not chunk:
                        break
                    dados += chunk
                    if b"\x03" in chunk:
                        break
                except socket.timeout:
                    break
        return dados

    def enviar_comando(self, comando: str) -> str:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.host, self.port))
            # ACBrMonitorPLUS envia banner ao conectar, ler antes de enviar comando
            banner = self._recv_ate_etx(sock)
            # Agora enviar o comando
            sock.sendall(f"{comando}\r\n.\r\n".encode())
            resposta = self._recv_ate_etx(sock)
            texto = resposta.decode("utf-8", errors="replace").strip()
            return texto
        except ConnectionRefusedError:
            raise ACBrMonitorError(
                f"Conexao recusada em {self.host}:{self.port}. "
                "ACBrMonitor esta rodando?"
            )
        except Exception as e:
            raise ACBrMonitorError(f"Erro de comunicacao: {e}")
        finally:
            sock.close()

    def status(self) -> str:
        return self.enviar_comando("NFE.StatusServico()")

    def criar_enviar_nfe(self, ini: str | Path, lote: int = 1) -> str:
        if isinstance(ini, Path):
            ini_content = ini.read_text(encoding="utf-8")
        elif isinstance(ini, str) and "\n" in ini:
            ini_content = ini
        else:
            ini_content = Path(ini).read_text(encoding="utf-8")
        escaped = ini_content.replace("\\", "\\\\").replace('"', '""')
        return self.enviar_comando(f'NFE.CriarEnviarNFe("{escaped}", {lote})')

    def consultar(self, chave: str) -> str:
        return self.enviar_comando(f"NFE.ConsultarNFe({chave})")

    def cancelar(self, chave: str, justificativa: str) -> str:
        return self.enviar_comando(f"NFE.CancelarNFe({chave},{justificativa})")

    def inutilizar(
        self, cnpj: str, modelo: str, serie: str,
        n_inicial: str, n_final: str, justificativa: str,
    ) -> str:
        return self.enviar_comando(
            f"NFE.InutilizarNFe({cnpj},{modelo},{serie},{n_inicial},{n_final},{justificativa})"
        )

    def cce(self, chave: str, correcao: str) -> str:
        return self.enviar_comando(f"NFE.CartaCorrecao({chave},{correcao})")

    def set_certificado(self, serial: str, senha: str = "") -> str:
        if senha:
            return self.enviar_comando(f'NFE.SetCertificado("{serial}","{senha}")')
        return self.enviar_comando(f"NFE.SetCertificado({serial})")

    def set_ambiente(self, ambiente: int) -> str:
        return self.enviar_comando(f"NFE.SetAmbiente({ambiente})")

    def set_forma_emissao(self, forma: int) -> str:
        return self.enviar_comando(f"NFE.SetFormaEmissao({forma})")

    def imprimir_danfe(self, chave: str) -> str:
        return self.enviar_comando(f"NFE.ImprimirDANFe({chave})")
