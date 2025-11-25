"""logic.py
Módulo de lógica de negocio y cálculo financiero para apuestas.

Inspirado en arquitecturas de bots de arbitraje open source, pero adaptado
a un diseño orientado a objetos moderno con Dataclasses.

Responsabilidades:
1. Definir estructuras de datos comunes (Match, Odd).
2. Calcular probabilidades implícitas.
3. Detectar oportunidades de valor (EV+) y Arbitraje.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class BettingOdd:
    """Representa una cuota específica de una casa de apuestas."""
    bookmaker: str
    odd_value: float
    selection: str  # '1', 'X', '2', 'Over 2.5', etc.
    extracted_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def implied_probability(self) -> float:
        """
        Calcula la probabilidad implícita de la cuota.
        Fórmula: 1 / cuota
        """
        if self.odd_value <= 0:
            return 0.0
        return 1 / self.odd_value

@dataclass
class MatchEvent:
    """Representa un evento deportivo unificado."""
    home_team: str
    away_team: str
    league: str
    match_time: datetime
    odds: List[BettingOdd] = field(default_factory=list)

    def add_odd(self, odd: BettingOdd) -> None:
        self.odds.append(odd)

class BetCalculator:
    """
    Motor de cálculo matemático.
    No mantiene estado, solo procesa datos puros.
    """

    @staticmethod
    def calculate_arbitrage_margin(odds: List[float]) -> float:
        """
        Calcula el margen de mercado (Vigorish).
        Si la suma de probabilidades implícitas < 1.0 (100%), existe arbitraje.
        
        Args:
            odds: Lista de cuotas para todos los resultados posibles (ej. [1.5, 4.0, 6.0])
        
        Returns:
            float: Suma de probabilidades implícitas.
        """
        if not odds:
            return 0.0
        return sum(1 / odd for odd in odds if odd > 0)

    @staticmethod
    def is_arbitrage_opportunity(odds: List[float]) -> bool:
        """Determina si existe una oportunidad de Surebet."""
        margin = BetCalculator.calculate_arbitrage_margin(odds)
        return 0.0 < margin < 1.0

    @staticmethod
    def calculate_expected_value(
        odd_value: float, 
        true_probability: float, 
        stake: float = 100.0
    ) -> float:
        """
        Calcula el Valor Esperado (EV) de una apuesta.
        
        Fórmula: (Probabilidad_Ganar * Ganancia_Neta) - (Probabilidad_Perder * Apuesta)
        
        Args:
            odd_value: La cuota ofrecida por la casa.
            true_probability: La probabilidad real estimada (0.0 a 1.0).
            stake: Cantidad apostada.
            
        Returns:
            float: Valor monetario esperado.
        """
        potential_profit = (odd_value * stake) - stake
        probability_loss = 1 - true_probability
        
        ev = (true_probability * potential_profit) - (probability_loss * stake)
        return ev

    @staticmethod
    def kelly_criterion(odd_value: float, true_probability: float, bankroll: float, fraction: float = 1.0) -> float:
        """
        Calcula el tamaño de apuesta óptimo usando el criterio de Kelly.
        
        Fórmula: f* = (bp - q) / b
        Donde:
            b = cuota decimal - 1
            p = probabilidad de éxito
            q = probabilidad de fracaso (1 - p)
        """
        b = odd_value - 1
        p = true_probability
        q = 1 - p
        
        if b <= 0: return 0.0
        
        f_star = (b * p - q) / b
        
        # Si f* es negativo, no apostar. Aplicar fracción de Kelly para reducir riesgo.
        return max(0.0, f_star) * fraction * bankroll
