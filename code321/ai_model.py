"""Compact byte-level Transformer used by the experimental 321 AI trainer.

This is an educational from-scratch model, not a pretrained foundation model.
"""
from __future__ import annotations

import torch
from torch import nn


class TinyGPT(nn.Module):
    def __init__(
        self,
        vocab_size: int = 256,
        width: int = 128,
        layers: int = 4,
        heads: int = 4,
        context: int = 128,
        dropout: float = 0.1,
    ):
        super().__init__()
        if width % heads:
            raise ValueError("width musi być podzielne przez heads")
        if not 0.0 <= dropout < 1.0:
            raise ValueError("dropout musi należeć do zakresu [0, 1)")
        self.context = context
        self.token = nn.Embedding(vocab_size, width)
        self.position = nn.Embedding(context, width)
        block = nn.TransformerEncoderLayer(
            d_model=width,
            nhead=heads,
            dim_feedforward=width * 4,
            dropout=dropout,
            batch_first=True,
            norm_first=True,
            activation="gelu",
        )
        self.blocks = nn.TransformerEncoder(block, num_layers=layers)
        self.norm = nn.LayerNorm(width)
        self.output = nn.Linear(width, vocab_size, bias=False)
        self.output.weight = self.token.weight

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        _, length = tokens.shape
        if length > self.context:
            tokens = tokens[:, -self.context:]
            length = tokens.shape[1]
        positions = torch.arange(length, device=tokens.device).unsqueeze(0)
        hidden = self.token(tokens) + self.position(positions)
        causal_mask = torch.triu(
            torch.ones(length, length, device=tokens.device, dtype=torch.bool),
            diagonal=1,
        )
        hidden = self.blocks(hidden, mask=causal_mask)
        return self.output(self.norm(hidden))
