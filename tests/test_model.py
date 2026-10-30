import torch
from model import ModelConfig, MKUUTransformer

def tiny():
    return ModelConfig(vocab_size=128,d_model=64,n_layers=2,n_heads=4,
                       ffn_hidden_size=128,max_seq_len=32)

def test_forward_and_loss():
    m=MKUUTransformer(tiny())
    ids=torch.randint(0,128,(2,12))
    out=m(ids,labels=ids)
    assert out["logits"].shape==(2,12,128)
    assert out["loss"].ndim==0 and torch.isfinite(out["loss"])

def test_parameter_count():
    assert MKUUTransformer(tiny()).parameter_count()>0

def test_sequence_limit():
    m=MKUUTransformer(tiny())
    ids=torch.randint(0,128,(1,33))
    try:
        m(ids)
    except ValueError:
        return
    raise AssertionError("Expected ValueError")
