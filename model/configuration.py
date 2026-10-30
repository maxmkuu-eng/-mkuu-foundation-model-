from dataclasses import dataclass

@dataclass
class ModelConfig:
    vocab_size: int = 48000
    d_model: int = 1024
    n_layers: int = 16
    n_heads: int = 16
    ffn_hidden_size: int = 2816
    max_seq_len: int = 2048
    dropout: float = 0.0
    tie_embeddings: bool = False
    rope_theta: float = 10000.0

    def __post_init__(self):
        if self.d_model % self.n_heads or self.d_model % 2:
            raise ValueError("d_model must be even and divisible by n_heads")
        if min(self.vocab_size, self.d_model, self.n_layers, self.n_heads,
               self.ffn_hidden_size, self.max_seq_len) <= 0:
            raise ValueError("Model dimensions must be positive")

    @property
    def head_dim(self):
        return self.d_model // self.n_heads

    @classmethod
    def from_dict(cls, values):
        return cls(**values.get("model", values))
