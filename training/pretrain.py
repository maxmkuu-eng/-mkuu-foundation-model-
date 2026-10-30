import argparse, json, math, random
from pathlib import Path
import sentencepiece as spm
import torch, yaml
from torch.utils.data import Dataset, DataLoader
from model import ModelConfig, MKUUTransformer

class TextDataset(Dataset):
    def __init__(self,path,tokenizer,seq_len):
        self.rows=[]
        self.seq_len=seq_len
        with open(path,encoding="utf-8") as f:
            for line_no,line in enumerate(f,1):
                if not line.strip():
                    continue
                row=json.loads(line)
                if not row.get("license") or not row.get("source"):
                    raise ValueError(f"Line {line_no}: license and source provenance are required")
                text=row.get("text")
                if not isinstance(text,str) or not text.strip():
                    raise ValueError(f"Line {line_no}: text must be non-empty")
                ids=tokenizer.encode(text,out_type=int)
                for start in range(0,max(0,len(ids)-1),seq_len):
                    chunk=ids[start:start+seq_len+1]
                    if len(chunk)>1:
                        self.rows.append(chunk)
        if not self.rows:
            raise ValueError("No usable token sequences found in training data")
    def __len__(self): return len(self.rows)
    def __getitem__(self,i):
        ids=self.rows[i]
        # Model.forward performs the next-token shift; return unshifted labels.
        x,y=ids[:-1],ids
        pad=self.seq_len-len(x)
        if pad>0:
            x=x+[0]*pad
            y=y+[-100]*pad
        return torch.tensor(x[:self.seq_len]),torch.tensor(y[:self.seq_len])

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--data",required=True)
    p.add_argument("--tokenizer",required=True)
    p.add_argument("--output",default="checkpoints")
    p.add_argument("--resume")
    a=p.parse_args()
    with open(a.config,encoding="utf-8") as f: raw=yaml.safe_load(f)
    cfg=ModelConfig.from_dict(raw); tc=raw.get("training",{})
    seed=int(tc.get("seed",42)); random.seed(seed); torch.manual_seed(seed)
    tok=spm.SentencePieceProcessor(model_file=a.tokenizer)
    if tok.get_piece_size() != cfg.vocab_size:
        raise ValueError(
            f"Tokenizer vocabulary ({tok.get_piece_size()}) does not match "
            f"model config ({cfg.vocab_size})"
        )
    seq=min(int(tc.get("sequence_length",512)),cfg.max_seq_len)
    if seq < 1 or int(tc.get("batch_size",1)) < 1:
        raise ValueError("sequence_length and batch_size must be positive")
    if int(tc.get("max_steps",1000)) < 1:
        raise ValueError("max_steps must be positive")
    ds=TextDataset(a.data,tok,seq)
    loader=DataLoader(ds,batch_size=int(tc.get("batch_size",1)),shuffle=True,
                      num_workers=int(tc.get("num_workers",0)))
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model=MKUUTransformer(cfg).to(device)
    base_lr=float(tc.get("learning_rate",1e-4))
    min_lr=float(tc.get("min_learning_rate",1e-5))
    optimizer=torch.optim.AdamW(model.parameters(),lr=base_lr,
                                weight_decay=float(tc.get("weight_decay",0.1)))
    step=0
    if a.resume:
        state=torch.load(a.resume,map_location=device)
        model.load_state_dict(state["model"]); optimizer.load_state_dict(state["optimizer"])
        step=int(state.get("step",0))
    max_steps=int(tc.get("max_steps",1000))
    accum=max(1,int(tc.get("gradient_accumulation_steps",1)))
    warmup=int(tc.get("warmup_steps",100))
    log_every=max(1,int(tc.get("log_every",10)))
    save_every=max(1,int(tc.get("save_every",250)))
    out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    optimizer.zero_grad(set_to_none=True); model.train()
    micro=0; running_loss=0.0
    while step<max_steps:
        for x,y in loader:
            progress=min(step/max(1,max_steps),1.0)
            lr=base_lr*(step+1)/max(1,warmup) if step<warmup else min_lr+0.5*(base_lr-min_lr)*(1+math.cos(math.pi*progress))
            for group in optimizer.param_groups: group["lr"]=lr
            loss=model(x.to(device),labels=y.to(device))["loss"]
            (loss/accum).backward(); running_loss+=loss.item(); micro+=1
            if micro%accum==0:
                torch.nn.utils.clip_grad_norm_(model.parameters(),float(tc.get("max_grad_norm",1.0)))
                optimizer.step(); optimizer.zero_grad(set_to_none=True); step+=1
                if step%log_every==0:
                    print(f"step={step} loss={running_loss/accum:.4f} lr={lr:.3e}")
                    running_loss=0.0
                if step%save_every==0:
                    torch.save({"model":model.state_dict(),"optimizer":optimizer.state_dict(),
                                "step":step,"config":raw},out/f"step-{step}.pt")
                if step>=max_steps: break
        else:
            continue
        break
    if micro%accum:
        remainder=micro%accum
        scale=accum/remainder
        for param in model.parameters():
            if param.grad is not None: param.grad.mul_(scale)
        torch.nn.utils.clip_grad_norm_(model.parameters(),float(tc.get("max_grad_norm",1.0)))
        optimizer.step()
    torch.save({"model":model.state_dict(),"optimizer":optimizer.state_dict(),
                "step":step,"config":raw},out/"last.pt")

if __name__=="__main__": main()
