"""Small unconditional DDPM U-Net built from scratch for 64px images."""
from __future__ import annotations
import math
import torch
from torch import nn
import torch.nn.functional as F

def timestep_embedding(timesteps: torch.Tensor, dim: int) -> torch.Tensor:
    half=dim//2
    scale=math.log(10000)/(max(half-1,1))
    values=torch.exp(torch.arange(half,device=timesteps.device)*-scale)
    angles=timesteps.float()[:,None]*values[None,:]
    emb=torch.cat((torch.sin(angles),torch.cos(angles)),dim=1)
    return F.pad(emb,(0,dim-emb.shape[1]))

class ResBlock(nn.Module):
    def __init__(self,cin,cout,time_dim):
        super().__init__()
        self.norm1=nn.GroupNorm(8,cin); self.conv1=nn.Conv2d(cin,cout,3,padding=1)
        self.norm2=nn.GroupNorm(8,cout); self.conv2=nn.Conv2d(cout,cout,3,padding=1)
        self.time=nn.Linear(time_dim,cout); self.skip=nn.Conv2d(cin,cout,1) if cin!=cout else nn.Identity()
    def forward(self,x,t):
        h=self.conv1(F.silu(self.norm1(x)))
        h=h+self.time(t)[:,:,None,None]
        h=self.conv2(F.silu(self.norm2(h)))
        return h+self.skip(x)

class ImageUNet(nn.Module):
    def __init__(self,base=64,time_dim=256):
        super().__init__()
        self.time=nn.Sequential(nn.Linear(time_dim,time_dim*4),nn.SiLU(),nn.Linear(time_dim*4,time_dim))
        self.input=nn.Conv2d(3,base,3,padding=1)
        self.down1=ResBlock(base,base,time_dim); self.downsample1=nn.Conv2d(base,base*2,4,2,1)
        self.down2=ResBlock(base*2,base*2,time_dim); self.downsample2=nn.Conv2d(base*2,base*4,4,2,1)
        self.mid1=ResBlock(base*4,base*4,time_dim); self.mid2=ResBlock(base*4,base*4,time_dim)
        self.up2=nn.ConvTranspose2d(base*4,base*2,4,2,1); self.up_block2=ResBlock(base*4,base*2,time_dim)
        self.up1=nn.ConvTranspose2d(base*2,base,4,2,1); self.up_block1=ResBlock(base*2,base,time_dim)
        self.output=nn.Sequential(nn.GroupNorm(8,base),nn.SiLU(),nn.Conv2d(base,3,3,padding=1))
        self.time_dim=time_dim
    def forward(self,x,timesteps):
        t=self.time(timestep_embedding(timesteps,self.time_dim))
        a=self.down1(self.input(x),t); b=self.down2(self.downsample1(a),t)
        h=self.mid2(self.mid1(self.downsample2(b),t),t)
        h=self.up_block2(torch.cat((self.up2(h),b),dim=1),t)
        h=self.up_block1(torch.cat((self.up1(h),a),dim=1),t)
        return self.output(h)

def cosine_beta_schedule(steps:int,device):
    s=0.008
    x=torch.linspace(0,steps,steps+1,device=device)
    alpha=torch.cos(((x/steps+s)/(1+s))*math.pi*0.5)**2
    alpha=alpha/alpha[0]
    return torch.clamp(1-alpha[1:]/alpha[:-1],0.0001,0.999)
