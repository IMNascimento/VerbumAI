"""
verbum/providers/base.py
========================
Interface base que todos os providers devem implementar.
"""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Contrato mínimo para um provider de LLM."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome legível do provider (ex: 'Claude claude-opus-4-6')."""

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """
        Envia system + user prompt e retorna a resposta do modelo como string.
        Raises:
            ValueError: credencial ausente ou configuração inválida.
            ConnectionError: falha de rede.
        """
