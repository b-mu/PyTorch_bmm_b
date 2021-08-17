GPU_TARGET =  Turing
CC        = gcc
CXX       = g++
NVCC      = nvcc
#FORT      = gfortran

ARCH      = ar
ARCHFLAGS = cr
RANLIB    = ranlib

#FPIC      = -fPIC

CXXFLAGS := $(CFLAGS) -std=c++11
CFLAGS    = -O3 $(FPIC) -fopenmp -DNDEBUG -DADD_ -Wall -Wno-strict-aliasing -Wshadow 
CFLAGS   += -std=c99


# --------------------
# directories

# define library directories preferably in your environment, or here.
#ACMLDIR  ?= /opt/acml
CUDADIR  = /usr/local/cuda
-include make.check-cuda

LIBDIR    = -L$(CUDADIR)/lib64 

INC       = -I$(CUDADIR)/include