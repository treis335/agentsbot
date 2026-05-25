"""
security/scanner.py — Scanner de seguranca para detetar secrets e padroes perigosos.

Inspirado no Mission Control:
- Detecao de tokens e chaves API
- Detecao de comandos perigosos
- Score de postura (0-100)
- Prevencao de push com secrets
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SecretScanner:
    """
    Scanner de seguranca.

    Detecta:
    - API keys (sk-, ghp_, etc.)
    - Private keys
    - Tokens Telegram
    - Conexoes perigosas
    - Comandos shell suspeitos
    """

    # Padroes de secrets conhecidos
    PATTERNS = {
        "deepseek_key": r"sk-[a-zA-Z0-9]{20,}",
        "github_token": r"gh[poau]_[a-zA-Z0-9]{36}",
        "telegram_token": r"\d{8,10}:AA[a-zA-Z0-9_-]{30,}",
        "private_key_hex": r"0x[a-fA-F0-9]{64}",
        "aws_key": r"AKIA[0-9A-Z]{16}",
        "generic_api_key": r"api[_-]?key['\"]?\s*[:=]\s*['\"][a-zA-Z0-9_\-]{20,}['\"]",
        "password_field": r"password\s*[:=]\s*['\"][^'\"]+['\"]",
        "jwt_token": r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}",
    }

    # Comandos shell perigosos
    DANGEROUS_COMMANDS = [
        "rm -rf /", "rm -rf ~", "mkfs", "dd if=", "> /dev/sda",
        ":(){ :|:& };:", "chmod 777 /", "wget http://", "curl http://",
        "eval ", "exec ", "source /dev/stdin",
    ]

    def scan_text(self, text: str) -> list[dict]:
        """
        Escaneia um texto a procura de secrets.

        Returns:
            Lista de dicts com tipo, padrao e posicao
        """
        findings = []
        for name, pattern in self.PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                findings.append({
                    "type": name,
                    "pattern": pattern,
                    "match": match.group()[:20] + "...",  # Apenas preview
                    "position": match.start(),
                    "severity": "high",
                })
        return findings

    def scan_file(self, filepath: str) -> list[dict]:
        """Escaneia um ficheiro a procura de secrets."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return self.scan_text(content)
        except Exception as e:
            logger.error(f"[SecretScanner] Erro ao ler {filepath}: {e}")
            return []

    def is_dangerous_command(self, command: str) -> tuple[bool, str]:
        """
        Verifica se um comando shell e perigoso.

        Returns:
            (is_dangerous, reason)
        """
        cmd_lower = command.lower()
        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous in cmd_lower:
                return True, f"Comando perigoso detetado: {dangerous}"
        return False, ""

    def calculate_posture_score(self, audit_logs: list[dict]) -> int:
        """
        Calcula score de postura de seguranca (0-100).

        Baseado em:
        - Numero de secrets detetados
        - Tentativas de comandos perigosos
        - Erros de seguranca
        """
        score = 100

        for entry in audit_logs:
            if entry.get("type") == "security_violation":
                score -= 20
            elif entry.get("type") == "dangerous_command_blocked":
                score -= 15
            elif entry.get("type") == "secret_detected":
                score -= 10

        return max(0, score)
