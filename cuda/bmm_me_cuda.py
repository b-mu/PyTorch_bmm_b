import math
import torch

import bmm_me_cuda

torch.manual_seed(42)



class bmm_me():
    def __init__(self):
        self.x = 1

    def forward(self, A, B):
        return bmm_me.forward(A, B)