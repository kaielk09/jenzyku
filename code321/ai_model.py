"""Small byte-level GPT-style language model used by 321 AI Creator."""
from __future__ import annotations

import torch
from torch import nn


class TinyGPT(nn.Module):
    def __init__(self, vocab_size: int = 256, width: int = 128, layers: int = 4,
                 heads: int = 4, context: int = 128):
        super().__init__()
        if width % heads:
            raise ValueError("width musi być podzielne przez heads")
        self.context = context
        self.token = nn.Embedding(vocab_size, width)
        self.position = nn.Embedding(context, width)
        block = nn.TransformerEncoderLayer(
            d_model=width, nhead=heads, dim_feedforward=width * 4,
            dropout=0.1, batch_first=True, norm_first=True, activation="gelu"
        )
        self.blocks = nn.TransformerEncoder(block, num_layers=layers)
        self.norm = nn.LayerNorm(width)
        self.output = nn.Linear(width, vocab_size, bias=False)
        self.output.weight = self.token.weight

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        batch, length = tokens.shape
        if length > self.context:
            tokens = tokens[:, -self.context:]
            length = tokens.shape[1]
        positions = torch.arange(length, device=tokens.device).unsqueeze(0)
        x = self.token(tokens) + self.position(positions)
        # True entries are masked: tokens cannot look into the future.
        mask = torch.triu(torch.ones(length, length, device=tokens.device, dtype=torch.bool), diagonal=1)
        x = self.blocks(x, mask=mask)
        return self.output(self.norm(x))
