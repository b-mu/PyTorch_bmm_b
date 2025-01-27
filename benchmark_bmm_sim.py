from __future__ import division
from __future__ import print_function

import argparse
import math
import time

import torch
from torch.profiler import profile, record_function, ProfilerActivity


TIME_SCALES = {'s': 1, 'ms': 1000, 'us': 1000000}

parser = argparse.ArgumentParser()
parser.add_argument('-b', '--batch-size', type=int, default=128)
parser.add_argument('-r', '--runs', type=int, default=100)
parser.add_argument('--scale', choices=['s', 'ms', 'us'], default='us')
parser.add_argument('-n', '--n', type=int, default=1)
parser.add_argument('-m', '--mode', type=str, default='all')
parser.add_argument('-p', '--pytorch', type=str, default='true')
parser.add_argument('-v', '--debug', type=str, default='false')
parser.add_argument('-tran', '--tran', type=int, default=0)
parser.add_argument('-i', '--in_', nargs='+', default=[32, 64, 128, 256, 512])
parser.add_argument('-o', '--out_', nargs='+', default=[32, 64, 128, 256, 512])
options = parser.parse_args()

# change this line
from cuda.bmm import BMM



options.cuda = True
device = torch.device("cuda") if options.cuda else torch.device("cpu")
dtype = torch.float32

kwargs = {'dtype': dtype,
          'device': device,
          'requires_grad': False}

# generate "n" set of random matrix with given dims
i_size = [int(i) for i in options.in_]
o_size = [int(o) for o in options.out_]
i_size = i_size * options.n
o_size = o_size * options.n
assert(len(i_size) == len(o_size))
options.n = len(i_size)
print('=== n: %d ===' % options.n)
# r_size = [100 400]
# r_size = [8]
A = []
B = []
C = []

mshapes = []
nshapes = []
kshapes = []
# index = torch.randint(0, len(r_size), (options.n,))


sum_size_A = 0
sum_size_B = 0
sum_size_C = 0
C_true=[]
for i in range(len(i_size)):

    if options.tran == 0: # A * B
        A_s = torch.randn(options.batch_size, i_size[i], **kwargs)
        B_s = torch.randn(i_size[i], o_size[i], **kwargs)
        C_s = torch.zeros(options.batch_size, o_size[i], **kwargs)
        C_true.append(torch.matmul(A_s, B_s))
        mshapes.append(A_s.shape[0])
        nshapes.append(B_s.shape[1])
        kshapes.append(A_s.shape[1])
    elif options.tran == 1: # A * B^T
        A_s = torch.randn(options.batch_size, i_size[i], **kwargs)
        B_s = torch.randn(o_size[i], i_size[i] , **kwargs)
        C_s = torch.zeros(options.batch_size, o_size[i], **kwargs)
        C_true.append(torch.matmul(A_s, B_s.t()))
        mshapes.append(A_s.shape[0])
        nshapes.append(B_s.shape[0])
        kshapes.append(A_s.shape[1])
    elif options.tran == 2: # A^T * B
        A_s = torch.randn(i_size[i], options.batch_size,  **kwargs)
        B_s = torch.randn(i_size[i], o_size[i], **kwargs)
        C_s = torch.zeros(options.batch_size, o_size[i], **kwargs)
        C_true.append(torch.matmul(A_s.t(), B_s))
        mshapes.append(A_s.shape[1])
        nshapes.append(B_s.shape[1])
        kshapes.append(A_s.shape[0])
    elif options.tran == 3: # A^T * B^T
        A_s = torch.randn(i_size[i], options.batch_size,  **kwargs)
        B_s = torch.randn(o_size[i], i_size[i], **kwargs)
        C_s = torch.zeros(options.batch_size, o_size[i], **kwargs)
        C_true.append(torch.matmul(A_s.t(), B_s.t()))
        mshapes.append(A_s.shape[1])
        nshapes.append(B_s.shape[0])
        kshapes.append(A_s.shape[0])



    A.append(A_s)
    B.append(B_s)
    C.append(C_s)
    

    

    sum_size_A = sum_size_A + A_s.numel()
    sum_size_B = sum_size_B + B_s.numel()
    sum_size_C = sum_size_C + C_s.numel()

# adding one extra elements since magma needs it
mshapes.append(0)
nshapes.append(0)
kshapes.append(0)

### making a contiguous tensor
A_con = torch.zeros(sum_size_A, **kwargs)
B_con = torch.zeros(sum_size_B, **kwargs)
C_con = torch.zeros(sum_size_C, **kwargs)
# C_con_magma = torch.zeros(sum_size_C, **kwargs)

# print('tensors created with size:', sum_size_A)
offset_A = 0
offset_B = 0
offset_C = 0
all_offset_A = [offset_A]
all_offset_B= [offset_B]
all_offset_C = [offset_C]
for i in range(options.n):
    A_con[0 + offset_A:A[i].numel() + offset_A] = torch.reshape(A[i], [1,-1])
    B_con[0 + offset_B:B[i].numel() + offset_B] = torch.reshape(B[i], [1,-1])
    C_con[0 + offset_C:C[i].numel() + offset_C] = torch.reshape(C[i], [1,-1])
    # C_con_magma[0 + offset_C:C[i].numel() + offset_C] = torch.reshape(C[i], [1,-1])
    offset_A = offset_A + A[i].numel()
    offset_B = offset_B + B[i].numel()
    offset_C = offset_C + C[i].numel()
    all_offset_A.append(offset_A)
    all_offset_B.append(offset_B)
    all_offset_C.append(offset_C)



# m_arr = torch.cuda.IntTensor(mshapes).to('cpu')
# n_arr = torch.cuda.IntTensor(nshapes).to('cpu')
# k_arr = torch.cuda.IntTensor(kshapes).to('cpu')


m_magma = torch.cuda.IntTensor(mshapes)
n_magma = torch.cuda.IntTensor(nshapes)
k_magma = torch.cuda.IntTensor(kshapes)

m_arr = mshapes
n_arr = nshapes
k_arr = kshapes

Mul = BMM(A_con, B_con, C_con, options.n, all_offset_A, all_offset_B, all_offset_C, m_magma, n_magma, k_magma)
# C_con = torch.zeros(sum_size_C, **kwargs)

# C_s_true_all=[]

pytorch_time = 0

if options.pytorch == 'true':
    for j in range(options.runs):
        for i in range(options.n):
            torch.cuda.synchronize()
            start = time.time()
            if options.tran == 0:
                C_s_true = torch.matmul(A[i], B[i])
            elif options.tran ==1:
                C_s_true = torch.matmul(A[i], B[i].t())
            elif options.tran ==2:
                C_s_true = torch.matmul(A[i].t(), B[i])
            elif options.tran ==3:
                C_s_true = torch.matmul(A[i].t(), B[i].t())
            torch.cuda.synchronize()
            elapsed = time.time() - start
            pytorch_time += elapsed
        # C_s_true_all.append(C_s_true)
    
torch.cuda.synchronize()

if options.tran == 0:
    A_T = False
    B_T = False
elif options.tran == 1:
    A_T = False
    B_T = True
elif options.tran == 2:
    A_T = True
    B_T = False
elif options.tran == 3:
    A_T = True
    B_T = True

cublas_time = 0
if options.mode == 'cublas' or options.mode == 'all':
    print('performing cublas operations...')
    for j in range(options.runs):
        torch.cuda.synchronize()
        start = time.time()
        result = Mul.CublasForward(A_con, B_con, C_con, m_arr, n_arr, k_arr, options.n, all_offset_A, all_offset_B, all_offset_C, A_T, B_T)
        torch.cuda.synchronize()
        elapsed = time.time() - start
        cublas_time += elapsed
#   
magma_time = 0
if options.mode == 'magma' or options.mode == 'all':
    print('performing magma operations...')
    for j in range(options.runs):
        torch.cuda.synchronize()
        start = time.time()
        result = Mul.MagmaForward(A_con, B_con, C_con, m_magma, n_magma, k_magma, options.n)
        torch.cuda.synchronize()
        elapsed = time.time() - start
        magma_time += elapsed



print('checking that the error is near zero')
# if options.mode == 'all':
for k in range(options.n):
    C_ = C_con[0 + all_offset_C[k]: C_true[k].numel() + all_offset_C[k]]
    C_ = C_.view_as(C_true[k])
    if not torch.allclose(C_, C_true[k]) and options.debug == 'true':
        print('A:', A[k])
        print('B:', B[k])
        print('C True:', C_true[k])
        print('C Comp:', C_)
        print("C Comp: L2 and Fro norms are: %s and %s" % (torch.linalg.norm(C_, ord=2), torch.linalg.norm(C_, ord='fro')))
        print('C True: L2 and Fro norms are: %s and %s' % (torch.linalg.norm(C_true[k], ord=2), torch.linalg.norm(C_true[k], ord='fro')))
        print('matmul error w.r.t pytorch:', C_-C_true[k])
print('#'*20)
        

 
scale = TIME_SCALES[options.scale]
pytorch_average = pytorch_time / options.runs * scale
cublas_average = cublas_time / options.runs * scale
magma_average = magma_time / options.runs * scale

print('PyTorch: {0:.3f} {3} | cublas {1:.3f} {3} | magma {2:.3f} {3}'.format(
     pytorch_average,  cublas_average, magma_average,
    options.scale))

