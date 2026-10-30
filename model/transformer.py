import torch
from torch import nn
from torch.nn import functional as F
from .configuration import ModelConfig

class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps
    def forward(self, x):
        var = x.float().pow(2).mean(dim=-1, keepdim=True)
        return x * torch.rsqrt(var + self.eps).to(x.dtype) * self.weight

def apply_rope(x, positions, theta=10000.0):
    dim = x.shape[-1]
    half = dim // 2
    freq = theta ** (-torch.arange(half, device=x.device, dtype=torch.float32) / half)
    angle = positions.float().unsqueeze(-1) * freq
    cos, sin = angle.cos().to(x.dtype).unsqueeze(0).unsqueeze(0), angle.sin().to(x.dtype).unsqueeze(0).unsqueeze(0)
    a, b = x[..., :half], x[..., half:]
    return torch.cat((a*cos-b*sin, b*cos+a*sin), dim=-1)

class CausalSelfAttention(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.heads, self.head_dim = cfg.n_heads, cfg.head_dim
        self.qkv = nn.Linear(cfg.d_model, 3*cfg.d_model, bias=False)
        self.proj = nn.Linear(cfg.d_model, cfg.d_model, bias=False)
        self.dropout, self.theta = cfg.dropout, cfg.rope_theta
    def forward(self, x):
        b,t,c = x.shape
        q,k,v = self.qkv(x).chunk(3, dim=-1)
        def split(z):
            return z.view(b,t,self.heads,self.head_dim).transpose(1,2)
        q,k,v = split(q),split(k),split(v)
        pos = torch.arange(t, device=x.device)
        q,k = apply_rope(q,pos,self.theta),apply_rope(k,pos,self.theta)
        y = F.scaled_dot_product_attention(q,k,v,is_causal=True,
              dropout_p=self.dropout if self.training else 0.0)
        return self.proj(y.transpose(1,2).contiguous().view(b,t,c))

class SwiGLU(nn.Module):
    def __init__(self,cfg):
        super().__init__()
        self.gate=nn.Linear(cfg.d_model,cfg.ffn_hidden_size,bias=False)
        self.up=nn.Linear(cfg.d_model,cfg.ffn_hidden_size,bias=False)
        self.down=nn.Linear(cfg.ffn_hidden_size,cfg.d_model,bias=False)
    def forward(self,x):
        return self.down(F.silu(self.gate(x))*self.up(x))

class TransformerBlock(nn.Module):
    def __init__(self,cfg):
        super().__init__()
        self.norm1,self.attn=RMSNorm(cfg.d_model),CausalSelfAttention(cfg)
        self.norm2,self.ffn=RMSNorm(cfg.d_model),SwiGLU(cfg)
    def forward(self,x):
        x=x+self.attn(self.norm1(x))
        return x+self.ffn(self.norm2(x))

class MKUUTransformer(nn.Module):
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.config=config
        self.token_embedding=nn.Embedding(config.vocab_size,config.d_model)
        self.layers=nn.ModuleList([TransformerBlock(config) for _ in range(config.n_layers)])
        self.norm=RMSNorm(config.d_model)
        self.lm_head=nn.Linear(config.d_model,config.vocab_size,bias=False)
        if config.tie_embeddings:
            self.lm_head.weight=self.token_embedding.weight
        self.apply(self._init_weights)
    @staticmethod
    def _init_weights(m):
        if isinstance(m,(nn.Linear,nn.Embedding)):
            nn.init.normal_(m.weight,mean=0.0,std=0.02)
    def forward(self,input_ids,labels=None):
        if input_ids.ndim!=2:
            raise ValueError("input_ids must have shape [batch, sequence]")
        if input_ids.size(1)>self.config.max_seq_len:
            raise ValueError("Sequence exceeds max_seq_len")
        x=self.token_embedding(input_ids)
        for layer in self.layers:
            x=layer(x)
        logits=self.lm_head(self.norm(x))
        loss=None
        if labels is not None:
            if labels.shape!=input_ids.shape:
                raise ValueError("labels must match input_ids shape")
            loss=F.cross_entropy(logits[:,:-1,:].contiguous().view(-1,logits.size(-1)),
                labels[:,1:].contiguous().view(-1),ignore_index=-100)
        return {"logits":logits,"loss":loss}
    def parameter_count(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
